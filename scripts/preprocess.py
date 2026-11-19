"""Convierte el extracto OSM de La Candelaria en data/scene.json (geometria 2D lista para Blender).

Uso: python -I preprocess.py <osm> <elev.json> <scene.json> <pylib>
"""
import sys, json, math, random
import xml.etree.ElementTree as ET

OSM, ELEV, OUT, PYLIB = sys.argv[1:5]
sys.path.insert(0, PYLIB)
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree
from shapely.geometry.polygon import orient

LAT0, LON0 = 4.5975, -74.07025
MLAT = 110574.0
MLON = 111320.0 * math.cos(math.radians(LAT0))
SHIFT = (-65.0, 30.0)  # centro de las 4 manzanas -> origen de la escena

import glob, os
osm_files = [OSM] + sorted(glob.glob(os.path.join(os.path.dirname(OSM), 'ctx_*.osm')))
nodes = {}
node_tags = {}
ways = []
rels = []
_seen_w = set()
_seen_r = set()
for _f in osm_files:
    root = ET.parse(_f).getroot()
    for n in root.iter('node'):
        nid = n.get('id')
        if nid in nodes:
            continue
        x = (float(n.get('lon')) - LON0) * MLON - SHIFT[0]
        y = (float(n.get('lat')) - LAT0) * MLAT - SHIFT[1]
        nodes[nid] = (x, y)
        tg = {t.get('k'): t.get('v') for t in n.findall('tag')}
        if tg:
            node_tags[nid] = tg
    for w in root.iter('way'):
        wid = w.get('id')
        if wid in _seen_w:
            continue
        _seen_w.add(wid)
        tags = {t.get('k'): t.get('v') for t in w.findall('tag')}
        pts = [nodes[nd.get('ref')] for nd in w.findall('nd') if nd.get('ref') in nodes]
        if pts and max(abs(pts[0][0]), abs(pts[0][1])) < 700:
            ways.append((wid, tags, pts))
    for r in root.iter('relation'):
        rid = r.get('id')
        if rid in _seen_r:
            continue
        _seen_r.add(rid)
        tags = {t.get('k'): t.get('v') for t in r.findall('tag')}
        if 'building' in tags:
            rels.append((rid, tags, [(m.get('type'), m.get('ref'), m.get('role')) for m in r.findall('member')]))

# ---------------------------------------------------------------- calles
VEH = ('residential', 'tertiary', 'secondary', 'unclassified', 'living_street')
streets = []
plazas = []
for wid, tags, pts in ways:
    hw = tags.get('highway')
    if tags.get('place') == 'square' and len(pts) >= 4:
        plazas.append((tags.get('name', 'plaza'), Polygon(pts).buffer(0)))
        continue
    if not hw or len(pts) < 2:
        continue
    closed = pts[0] == pts[-1] and len(pts) >= 4
    if hw == 'pedestrian' and closed and (tags.get('area') == 'yes' or tags.get('name') == 'Chorro de Quevedo'):
        plazas.append((tags.get('name', 'plaza'), Polygon(pts).buffer(0)))
        continue
    name = tags.get('name')
    if hw in VEH:
        cls = 'veh'
    elif hw == 'pedestrian':
        cls = 'ped'
    elif hw in ('footway', 'steps') and name:
        cls = 'ped'
    else:
        continue
    streets.append({'id': wid, 'name': name or '', 'kind': hw, 'cls': cls,
                    'surface': tags.get('surface') or '', 'line': LineString(pts)})

print('streets', len(streets), 'plazas', [(n, round(p.area)) for n, p in plazas])

# ---------------------------------------------------------------- manzanas
net = unary_union([s['line'] for s in streets])
faces = list(polygonize(net))
seeds = {'A': (-135, 10), 'B': (-35, -45), 'C': (-75, 105), 'D': (15, 45)}
core_faces = {}
for k, (sx, sy) in seeds.items():
    p = Point(sx - SHIFT[0], sy - SHIFT[1])
    for f in faces:
        if f.contains(p):
            core_faces[k] = f
            break
print('manzanas', {k: round(f.area) for k, f in core_faces.items()})
assert len(core_faces) == 4
core = unary_union(list(core_faces.values())).buffer(0.5).buffer(-0.5)
chorro = [p for n, p in plazas if n == 'Chorro de Quevedo'][0]
region = unary_union([core.buffer(46), chorro.buffer(64)]).buffer(10).buffer(-10)

# ---------------------------------------------------------------- predios (vias y relaciones multipoligono)
way_pts = {wid: pts for wid, tags, pts in ways}
cands = []
rel_outer = set()
for rid, rtags, members in rels:
    inn_polys = []
    for (mt, ref, role) in members:
        if mt == 'way' and role == 'inner':
            pts = way_pts.get(ref)
            if pts and len(pts) >= 4 and pts[0] == pts[-1]:
                ip = Polygon(pts)
                if not ip.is_valid:
                    ip = ip.buffer(0)
                if ip.geom_type == 'Polygon' and ip.area >= 6:
                    inn_polys.append(ip)
    for (mt, ref, role) in members:
        if mt == 'way' and role in ('outer', '', None):
            pts = way_pts.get(ref)
            if pts and len(pts) >= 4 and pts[0] == pts[-1]:
                rel_outer.add(ref)
                cands.append(('r%s_%s' % (rid, ref), dict(rtags), pts, inn_polys))
for wid, tags, pts in ways:
    if 'building' in tags and len(pts) >= 4 and wid not in rel_outer:
        cands.append((wid, tags, pts, []))

all_b = []
for bid, tags, pts, inns in cands:
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.geom_type == 'MultiPolygon':
        poly = max(poly.geoms, key=lambda g: g.area)
    if poly.is_empty or poly.geom_type != 'Polygon' or poly.area < 14:
        continue
    c = poly.centroid
    if math.hypot(c.x, c.y) > 420:
        continue
    poly = orient(Polygon(poly.exterior).simplify(0.12), 1.0)
    all_b.append({'id': bid, 'tags': tags, 'poly': poly, 'inners': [ip for ip in inns if poly.buffer(0.5).contains(ip)]})


def no_overlap(cand, base):
    kept = list(base)
    for b in sorted(cand, key=lambda b: -b['poly'].area):
        ok = True
        for k in kept:
            if k['poly'].intersects(b['poly']) and k['poly'].intersection(b['poly']).area > 0.5 * b['poly'].area:
                ok = False
                break
        if ok:
            kept.append(b)
    return kept


blds = no_overlap([b for b in all_b if region.contains(b['poly'].centroid)], [])
b_union = unary_union([b['poly'] for b in blds])

# ---------------------------------------------------------------- suelo
G = unary_union([region, b_union.buffer(5)]).buffer(14).buffer(-10).simplify(0.6)
if G.geom_type == 'MultiPolygon':
    G = max(G.geoms, key=lambda g: g.area)
G = Polygon(G.exterior)
_ids = set(b['id'] for b in blds)
blds = no_overlap([b for b in all_b if b['id'] not in _ids and G.contains(b['poly'].centroid)], blds)
print('predios', len(blds), '| con patios reales:', sum(1 for b in blds if b['inners']))

# La Ermita de San Miguel del Principe: el POI cae dentro de un predio real con patio.
# Se separa la capilla (7 x 11 m) sobre el borde de ese predio que mira a la plazoleta.
erm_pt = None
for nid, tg in node_tags.items():
    if 'Ermita' in tg.get('name', ''):
        erm_pt = nodes[nid]
erm_poly = None
if erm_pt is not None:
    cx, cy = chorro.centroid.x, chorro.centroid.y
    fx, fy = cx - erm_pt[0], cy - erm_pt[1]
    fl = math.hypot(fx, fy)
    fx, fy = fx / fl, fy / fl          # hacia la plaza
    sx, sy = -fy, fx
    W2, D = 3.6, 11.0
    p0 = Point(erm_pt)
    host = None
    for b in blds:
        if b['poly'].contains(p0):
            host = b
    if host is not None:
        ray = LineString([erm_pt, (erm_pt[0] + fx * 40.0, erm_pt[1] + fy * 40.0)])
        hit = ray.intersection(host['poly'].exterior)
        hp = [hit] if hit.geom_type == 'Point' else [q for q in getattr(hit, 'geoms', []) if q.geom_type == 'Point']
        dfront = min(q.distance(p0) for q in hp) if hp else 4.0
        c0 = (erm_pt[0] + fx * (dfront + 0.5), erm_pt[1] + fy * (dfront + 0.5))
        print('ermita: predio anfitrion', host['id'], 'area %.0f' % host['poly'].area, 'frente a %.1f m del POI' % dfront)
    else:
        front = min(fl - 6.5, 4.0)
        c0 = (erm_pt[0] + fx * front, erm_pt[1] + fy * front)
    rect = Polygon([(c0[0] + sx * W2, c0[1] + sy * W2), (c0[0] - sx * W2, c0[1] - sy * W2),
                    (c0[0] - sx * W2 - fx * D, c0[1] - sy * W2 - fy * D), (c0[0] + sx * W2 - fx * D, c0[1] + sy * W2 - fy * D)])
    others = unary_union([b['poly'] for b in blds if b is not host])
    rect = rect.difference(others.buffer(0.4))
    if rect.geom_type == 'MultiPolygon':
        rect = max(rect.geoms, key=lambda g: g.area)
    erm_poly = orient(Polygon(rect.exterior).simplify(0.2), 1.0)
    if host is not None:
        rest = host['poly'].difference(erm_poly.buffer(0.35))
        if rest.geom_type == 'MultiPolygon':
            rest = max(rest.geoms, key=lambda g: g.area)
        if rest.geom_type == 'Polygon' and rest.area > 30:
            host['poly'] = orient(Polygon(rest.exterior).simplify(0.12), 1.0)
            host['inners'] = [ip for ip in host['inners'] if host['poly'].buffer(-0.5).contains(ip)]
        else:
            blds.remove(host)
    blds.append({'id': '999000001', 'tags': {'name': 'Ermita de San Miguel del Principe', 'building:levels': '1'}, 'poly': erm_poly, 'inners': []})
    print('ermita creada, area %.0f m2' % erm_poly.area)
b_union = unary_union([b['poly'] for b in blds])

b_tree = STRtree([b['poly'] for b in blds])
b_polys = [b['poly'] for b in blds]


def clearance(line):
    ds = []
    n = max(2, int(line.length / 5))
    for i in range(n + 1):
        p = line.interpolate(i / n, normalized=True)
        if not G.contains(p):
            continue
        idx = b_tree.nearest(p)
        ds.append(b_polys[idx].distance(p))
    return float(np.median(ds)) if ds else 4.5


SURF = {'asphalt': 'asfalto', '': 'asfalto', 'sett': 'adoquin', 'paving_stones': 'losa',
        'unhewn_cobblestone': 'empedrado', 'concrete': 'losa', 'concrete:plates': 'losa'}
clr_by_name = {}
for s in streets:
    if not s['line'].intersects(G):
        continue
    clr_by_name.setdefault((s['name'], s['cls']), []).append((clearance(s['line']), s['line'].length))
widths = {}
for k, lst in clr_by_name.items():
    tot = sum(l for _, l in lst)
    c = sum(c * l for c, l in lst) / tot
    if k[1] == 'veh':
        hwid = min(3.7, max(2.3, c - 1.35))
    else:
        hwid = min(2.6, max(1.3, c - 0.15))
    widths[k] = hwid
    print(f'  {k[0]:28s} {k[1]} despeje {c:4.1f} -> semiancho {hwid:3.1f}')

veh_by_surf = {}
ped_by_surf = {}
for s in streets:
    if not s['line'].intersects(G):
        continue
    hwid = widths[(s['name'], s['cls'])]
    s['hw'] = hwid
    surf = SURF.get(s['surface'], 'asfalto')
    if s['kind'] == 'steps':
        surf = 'losa'
    poly = s['line'].buffer(hwid, cap_style=1, join_style=1, resolution=6)
    (veh_by_surf if s['cls'] == 'veh' else ped_by_surf).setdefault(surf, []).append(poly)

b_keep = b_union.buffer(0.9, join_style=2)
veh_all = unary_union([p for l in veh_by_surf.values() for p in l]).intersection(G).difference(b_keep)
veh_all = veh_all.buffer(-0.6).buffer(0.6)  # quita astillas
roads = {}
taken = None
for surf in ('adoquin', 'empedrado', 'losa', 'asfalto'):
    if surf not in veh_by_surf:
        continue
    u = unary_union(veh_by_surf[surf]).intersection(veh_all)
    if taken is not None:
        u = u.difference(taken)
    taken = u if taken is None else unary_union([taken, u])
    roads[surf] = u

plaza_union = unary_union([p for _, p in plazas])
if erm_poly is not None:
    plaza_union = unary_union([plaza_union, chorro.union(erm_poly.buffer(2.0)).convex_hull])
ped_all = unary_union([p for l in ped_by_surf.values() for p in l] + [plaza_union.buffer(0.3)])
ped_all = ped_all.intersection(G).difference(veh_all).difference(b_union.buffer(0.05))
ped = {}
ped['plaza'] = plaza_union.buffer(0.3).intersection(ped_all)
taken = ped['plaza']
for surf in ('empedrado', 'adoquin', 'losa', 'asfalto'):
    if surf not in ped_by_surf:
        continue
    u = unary_union(ped_by_surf[surf]).intersection(ped_all).difference(taken)
    taken = unary_union([taken, u])
    ped['losa' if surf == 'asfalto' else surf] = unary_union([ped.get('losa' if surf == 'asfalto' else surf, Polygon()), u])

slab = G.difference(veh_all).difference(ped_all)
slab = slab.buffer(-0.05).buffer(0.05)
inner = slab.buffer(-2.3)
sidewalk = slab.difference(inner)
raised = G.difference(veh_all)

# ---------------------------------------------------------------- terreno
el = json.load(open(ELEV))
S = np.array(el['samples'], dtype=float)
S[:, 0] -= SHIFT[0]
S[:, 1] -= SHIFT[1]
NORM = 300.0
TERMS = [(i, j) for i in range(4) for j in range(4) if i + j <= 3]
A = np.stack([(S[:, 0] / NORM) ** i * (S[:, 1] / NORM) ** j for i, j in TERMS], axis=1)
coef, *_ = np.linalg.lstsq(A, S[:, 2], rcond=None)
resid = A @ coef - S[:, 2]
print('terreno: residuo rms %.2f m' % float(np.sqrt((resid ** 2).mean())))


def T(x, y):
    return float(sum(c * (x / NORM) ** i * (y / NORM) ** j for c, (i, j) in zip(coef, TERMS)))


gx0, gy0, gx1, gy1 = G.bounds
zs = [T(x, y) for x in np.linspace(gx0, gx1, 30) for y in np.linspace(gy0, gy1, 30) if G.contains(Point(x, y))]
ZREF = min(zs)
print('terreno en G: %.1f a %.1f (desnivel %.1f m)' % (min(zs), max(zs), max(zs) - min(zs)))

# ---------------------------------------------------------------- analisis de predios
pub_lines = [s['line'] for s in streets if s['line'].intersects(G)]
pub_cls = [s['cls'] for s in streets if s['line'].intersects(G)]
pub_name = [s['name'] for s in streets if s['line'].intersects(G)]
pub_tree = STRtree(pub_lines)
plaza_buf = plaza_union.buffer(1.2)
b_buf = [p.buffer(0.6) for p in b_polys]
bb_tree = STRtree(b_buf)


def ring_of(poly):
    c = list(poly.exterior.coords)[:-1]
    out = [c[0]]
    for p in c[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 0.08:
            out.append(p)
    if math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 0.08:
        out.pop()
    return out


out_b = []
for bi, b in enumerate(blds):
    poly = b['poly']
    ring = ring_of(poly)
    n = len(ring)
    if n < 3:
        continue
    sid = int((''.join(ch for ch in b['id'] if ch.isdigit()) or '1')[-9:])
    rnd = random.Random(sid)
    free, street, pedf = [], [], []
    for i in range(n):
        a = ring[i]
        c = ring[(i + 1) % n]
        dx, dy = c[0] - a[0], c[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-6:
            free.append(0); street.append(0); pedf.append(0)
            continue
        nx, ny = dy / L, -dx / L  # normal exterior (anillo CCW)
        hits = 0
        for t in (0.12, 0.31, 0.5, 0.69, 0.88):
            p = Point(a[0] + dx * t + nx * 0.5, a[1] + dy * t + ny * 0.5)
            for j in bb_tree.query(p):
                if j != bi and b_buf[j].contains(p):
                    hits += 1
                    break
        is_free = hits < 3
        is_street = 0
        is_ped = 0
        if is_free and L >= 1.6:
            mx, my = a[0] + dx * 0.5, a[1] + dy * 0.5
            ray = LineString([(mx + nx * 0.4, my + ny * 0.4), (mx + nx * 12.0, my + ny * 12.0)])
            o = Point(mx, my)
            best = None
            for j in pub_tree.query(ray):
                if pub_lines[j].intersects(ray):
                    d = pub_lines[j].intersection(ray).distance(o)
                    if best is None or d < best[0]:
                        best = (d, pub_cls[j])
            if plaza_buf.intersects(ray):
                d = plaza_buf.intersection(ray).distance(o)
                if best is None or d < best[0]:
                    best = (d, 'plaza')
            if best is not None:
                blocked = False
                for j in b_tree.query(ray):
                    if j != bi and b_polys[j].intersects(ray):
                        if b_polys[j].intersection(ray).distance(o) < best[0]:
                            blocked = True
                            break
                if not blocked:
                    is_street = 1
                    is_ped = 1 if best[1] in ('ped', 'plaza') else 0
        free.append(1 if is_free else 0)
        street.append(is_street)
        pedf.append(is_ped)

    area = poly.area
    tags = b['tags']
    lv = None
    try:
        lv = int(float(tags.get('building:levels', '')))
    except ValueError:
        pass
    r = rnd.random()
    if lv is None:
        if area < 70:
            lv = 1 if r < 0.75 else 2
        elif area < 250:
            lv = 2 if r < 0.55 else (1 if r < 0.93 else 3)
        elif area < 900:
            lv = 2 if r < 0.62 else (3 if r < 0.82 else 1)
        else:
            lv = 3 if r < 0.5 else (2 if r < 0.8 else 4)
    lv = max(1, min(lv, 8))
    kind = 'colonial'
    blk = 'X'
    for kf, ff in core_faces.items():
        if ff.buffer(1.0).contains(poly.centroid):
            blk = kf
    if lv >= 4 or area > 1500 or (area > 900 and rnd.random() < 0.35):
        kind = 'moderno'

    if b['id'] == '999000001':
        kind, lv = 'ermita', 1
    patios = []
    if b.get('inners'):
        for ip in b['inners']:
            ip2 = ip.intersection(poly.buffer(-0.8))
            if ip2.geom_type == 'MultiPolygon':
                ip2 = max(ip2.geoms, key=lambda g: g.area)
            if ip2.geom_type == 'Polygon' and ip2.area >= 9:
                patios.append(ring_of(orient(Polygon(ip2.exterior).simplify(0.15), 1.0)))
    elif kind == 'colonial' and area > 300:
        inn = poly.buffer(-6.3, join_style=2)
        if not inn.is_empty:
            if inn.geom_type == 'MultiPolygon':
                inn = max(inn.geoms, key=lambda g: g.area)
            inn = inn.simplify(0.5)
            if inn.geom_type == 'Polygon' and inn.area > 22 and inn.is_valid:
                patios.append(ring_of(orient(Polygon(inn.exterior), 1.0)))

    def rr(ring_):
        return [[round(x, 3), round(y, 3)] for x, y in ring_]

    out_b.append({'id': b['id'], 'name': tags.get('name', ''), 'ring': rr(ring), 'free': free, 'street': street, 'ped': pedf, 'levels': lv, 'kind': kind,
                  'patios': [rr(p_) for p_ in patios], 'patio': rr(patios[0]) if patios else None,
                  'area': round(area, 1), 'seed': sid % 1000003, 'blk': blk})

n_street = sum(1 for b in out_b if any(b['street']))
print('predios con fachada a la calle:', n_street, '| con patio:', sum(1 for b in out_b if b['patio']),
      '| modernos:', sum(1 for b in out_b if b['kind'] == 'moderno'))
from collections import Counter
print('pisos:', sorted(Counter(b['levels'] for b in out_b).items()))

# ---------------------------------------------------------------- especiales
specials = {'ermita_id': '999000001' if erm_poly is not None else None}
c = chorro.representative_point()
specials['chorro_centro'] = [chorro.centroid.x, chorro.centroid.y]
specials['chorro_ring'] = [[round(x, 3), round(y, 3)] for x, y in ring_of(orient(chorro, 1.0))]
pois = []
for nid, tg in node_tags.items():
    if 'name' in tg and G.contains(Point(nodes[nid])) and any(k in tg for k in ('tourism', 'amenity', 'historic', 'shop')):
        pois.append({'name': tg['name'], 'kind': tg.get('tourism') or tg.get('amenity') or tg.get('historic') or tg.get('shop'),
                     'pt': [round(nodes[nid][0], 2), round(nodes[nid][1], 2)]})


# ---------------------------------------------------------------- arboles
tr_area = inner.difference(b_union.buffer(3.2)).buffer(-1.5)
trnd = random.Random(7)
trees = []
bx0, by0, bx1, by1 = tr_area.bounds
tries = 0
while len(trees) < 170 and tries < 60000:
    tries += 1
    x = trnd.uniform(bx0, bx1); y = trnd.uniform(by0, by1)
    if not tr_area.contains(Point(x, y)):
        continue
    if any((x - t[0]) ** 2 + (y - t[1]) ** 2 < 6.5 ** 2 for t in trees):
        continue
    trees.append([round(x, 2), round(y, 2), round(trnd.uniform(0.75, 1.35), 2), trnd.randrange(3)])
print('arboles', len(trees))

# ---------------------------------------------------------------- salida
def polys_of(g):
    res = []
    if g is None or g.is_empty:
        return res
    geoms = [g] if g.geom_type == 'Polygon' else list(getattr(g, 'geoms', []))
    for p in geoms:
        if p.geom_type != 'Polygon' or p.area < 0.4:
            continue
        p = orient(p.simplify(0.06), 1.0)
        if p.is_empty or p.geom_type != 'Polygon':
            continue
        rings = [[[round(x, 3), round(y, 3)] for x, y in ring_of(Polygon(p.exterior))]]
        for h in p.interiors:
            hp = Polygon(h)
            if hp.area > 0.3:
                rings.append([[round(x, 3), round(y, 3)] for x, y in ring_of(hp)])
        res.append(rings)
    return res


a_calle = math.atan2(-65.0, 110.0)
scene = {
    'origin': {'lat0': LAT0, 'lon0': LON0, 'shift': SHIFT, 'mlat': MLAT, 'mlon': MLON},
    'terrain': {'coef': [float(c) for c in coef], 'terms': TERMS, 'norm': NORM, 'zref': ZREF},
    'grid_angle': a_calle,
    'G': polys_of(G),
    'roads': {k: polys_of(v) for k, v in roads.items()},
    'ped': {k: polys_of(v) for k, v in ped.items()},
    'sidewalk': polys_of(sidewalk),
    'interior': polys_of(inner),
    'raised': polys_of(raised),
    'buildings': out_b,
    'streets': [{'name': s['name'], 'kind': s['kind'], 'cls': s['cls'], 'hw': round(s.get('hw', 0), 2),
                 'pts': [[round(x, 2), round(y, 2)] for x, y in s['line'].coords]} for s in streets if s['line'].intersects(G)],
    'specials': specials,
    'trees': trees,
    'pois': pois,
}
json.dump(scene, open(OUT, 'w'))
print('G area %.0f m2, bounds %s' % (G.area, [round(v) for v in G.bounds]))
print('roads', {k: round(v.area) for k, v in roads.items()}, 'ped', {k: round(v.area) for k, v in ped.items()})
print('specials', specials.get('ermita_id'), [round(v, 1) for v in specials['chorro_centro']], 'ermita_pt', erm_pt)
print('pois', len(pois))
print('OK ->', OUT)
