"""Entorno amplio: edificios, vias, parques y relieve reales alrededor de las 4 manzanas -> data/context.json

Uso: python -I preprocess_ctx.py <carpeta_osm> <carpeta_data> <pylib>
"""
import sys, json, math, random, glob, os
import xml.etree.ElementTree as ET

OSM_DIR, DATA, PYLIB = sys.argv[1:4]
sys.path.insert(0, PYLIB)
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.geometry.polygon import orient
from scipy import ndimage

sc = json.load(open(os.path.join(DATA, 'scene.json'), encoding='utf-8'))
o = sc['origin']
LAT0, LON0, SHIFT, MLAT, MLON = o['lat0'], o['lon0'], o['shift'], o['mlat'], o['mlon']
G = Polygon(sc['G'][0][0])
scene_ids = set(b['id'] for b in sc['buildings'])
scene_union = unary_union([Polygon(b['ring']) for b in sc['buildings']])
ZREF = sc['terrain']['zref']
GA = sc['grid_angle']
RMAX = 1010.0

nodes = {}
tree_nodes = []
ways = {}
rels = []
for f in sorted(glob.glob(os.path.join(OSM_DIR, 'ctx_*.osm'))):
    root = ET.parse(f).getroot()
    for n in root.iter('node'):
        nid = n.get('id')
        if nid in nodes:
            continue
        x = (float(n.get('lon')) - LON0) * MLON - SHIFT[0]
        y = (float(n.get('lat')) - LAT0) * MLAT - SHIFT[1]
        nodes[nid] = (x, y)
        for t in n.findall('tag'):
            if t.get('k') == 'natural' and t.get('v') == 'tree':
                tree_nodes.append((x, y))
    for w in root.iter('way'):
        wid = w.get('id')
        if wid in ways:
            continue
        ways[wid] = ({t.get('k'): t.get('v') for t in w.findall('tag')}, [nd.get('ref') for nd in w.findall('nd')])
    for r in root.iter('relation'):
        tags = {t.get('k'): t.get('v') for t in r.findall('tag')}
        if 'building' in tags:
            rels.append((r.get('id'), tags, [m.get('ref') for m in r.findall('member') if m.get('type') == 'way' and m.get('role') in ('outer', '')]))
print('nodos', len(nodes), 'vias', len(ways), 'relaciones edificio', len(rels))


def pts_of(refs):
    return [nodes[r] for r in refs if r in nodes]


def num(s):
    try:
        return float(str(s).replace('m', '').replace(',', '.').split()[0])
    except Exception:
        return None


# ---------------------------------------------------------------- edificios
cand = []
for wid, (tags, refs) in ways.items():
    if 'building' in tags and len(refs) >= 4 and refs[0] == refs[-1]:
        cand.append((wid, tags, pts_of(refs)))
for rid, tags, members in rels:
    for m in members:
        if m in ways and ways[m][1] and ways[m][1][0] == ways[m][1][-1] and 'building' not in ways[m][0]:
            cand.append(('r' + rid + '_' + m, tags, pts_of(ways[m][1])))

blds = []
for bid, tags, pts in cand:
    if bid in scene_ids or len(pts) < 4:
        continue
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.geom_type == 'MultiPolygon':
        poly = max(poly.geoms, key=lambda g: g.area)
    if poly.is_empty or poly.geom_type != 'Polygon' or poly.area < 25:
        continue
    c = poly.centroid
    if math.hypot(c.x, c.y) > RMAX:
        continue
    if scene_union.intersects(poly) and scene_union.intersection(poly).area > 0.3 * poly.area:
        continue
    poly = orient(Polygon(poly.exterior).simplify(0.6), 1.0)
    if poly.is_empty or poly.area < 25 or len(poly.exterior.coords) < 4:
        continue
    blds.append((bid, tags, poly))
print('edificios de entorno', len(blds))

out_b = []
ca, sa = math.cos(GA), math.sin(GA)
for bid, tags, poly in blds:
    seed = abs(hash(bid)) % 1000003 if not bid.isdigit() else int(bid) % 1000003
    rnd = random.Random(seed)
    area = poly.area
    c = poly.centroid
    west = -(c.x * ca + c.y * sa)
    north = (-c.x * sa + c.y * ca)
    h = num(tags.get('height')) if 'height' in tags else None
    lv = num(tags.get('building:levels')) if 'building:levels' in tags else None
    src = 'tag'
    if h is None and lv is not None:
        h = lv * 3.1 + 0.8
    if h is None:
        src = 'est'
        r = rnd.random()
        if area < 120:
            lv = 1 if r < 0.45 else 2
        elif area < 400:
            lv = 2 if r < 0.55 else (3 if r < 0.85 else 1)
        elif area < 1200:
            lv = 3 if r < 0.4 else (2 if r < 0.65 else (4 if r < 0.85 else 6))
        else:
            lv = 4 if r < 0.35 else (3 if r < 0.55 else (6 if r < 0.8 else 9))
        if west > 230 and north > 60 and area > 350:
            lv = int(round(lv * rnd.uniform(1.4, 2.4)))
        h = lv * 3.1 + 0.6
    h = max(3.0, min(h, 190.0))
    kind = 'plano' if (h > 12.5 or area > 1400 or rnd.random() < 0.2) else 'teja'
    ring = [[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]
    out_b.append({'id': bid, 'ring': ring, 'h': round(h, 1), 'kind': kind, 'area': round(area, 1), 'seed': seed, 'src': src})
print('con altura real (tag):', sum(1 for b in out_b if b['src'] == 'tag'), '| planos:', sum(1 for b in out_b if b['kind'] == 'plano'),
      '| max h', max(b['h'] for b in out_b))

# ---------------------------------------------------------------- vias
HW = {'motorway': 8.0, 'trunk': 7.5, 'primary': 7.0, 'secondary': 5.5, 'tertiary': 4.2, 'residential': 3.0, 'unclassified': 3.0,
      'living_street': 2.6, 'pedestrian': 2.6, 'primary_link': 4.0, 'secondary_link': 3.5, 'tertiary_link': 3.0, 'busway': 3.5}
Gin = G.buffer(-0.5)
roads = []
road_lines = []
for wid, (tags, refs) in ways.items():
    hw = tags.get('highway')
    if hw not in HW:
        continue
    pts = pts_of(refs)
    if len(pts) < 2 or (tags.get('area') == 'yes'):
        continue
    line = LineString(pts)
    if line.length < 4:
        continue
    out = line.difference(Gin)
    parts = [out] if out.geom_type == 'LineString' else list(getattr(out, 'geoms', []))
    for p in parts:
        if p.geom_type != 'LineString' or p.length < 3:
            continue
        cs = list(p.simplify(0.4).coords)
        if max(math.hypot(x, y) for x, y in cs) > RMAX + 60 and min(math.hypot(x, y) for x, y in cs) > RMAX:
            continue
        roads.append({'w': HW[hw], 'kind': hw, 'pts': [[round(x, 2), round(y, 2)] for x, y in cs]})
        road_lines.append(p)
print('tramos de via', len(roads))

# ---------------------------------------------------------------- verdes
parks = []
for wid, (tags, refs) in ways.items():
    kind = None
    if tags.get('leisure') in ('park', 'garden'):
        kind = 'parque'
    elif tags.get('landuse') in ('grass', 'meadow', 'recreation_ground', 'village_green'):
        kind = 'pasto'
    elif tags.get('landuse') == 'forest' or tags.get('natural') in ('wood', 'scrub'):
        kind = 'bosque'
    if kind is None or len(refs) < 4 or refs[0] != refs[-1]:
        continue
    poly = Polygon(pts_of(refs))
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty or poly.geom_type != 'Polygon' or poly.area < 60:
        continue
    poly = poly.difference(G.buffer(1.0))
    if poly.is_empty:
        continue
    for pp in ([poly] if poly.geom_type == 'Polygon' else list(poly.geoms)):
        if pp.geom_type == 'Polygon' and pp.area > 60:
            parks.append((kind, pp))
print('zonas verdes', len(parks))
park_union = unary_union([p for _, p in parks]) if parks else Polygon()

# ---------------------------------------------------------------- relieve
near = json.load(open(os.path.join(DATA, 'elev_near.json')))
far = json.load(open(os.path.join(DATA, 'elev_far.json')))
nx, ny = len(near['xs']), len(near['ys'])
Zn = np.array(near['z'], dtype=float).reshape(ny, nx)
Zn = ndimage.gaussian_filter(Zn, 1.1) - ZREF
fx, fy = len(far['xs']), len(far['ys'])
Zf = np.array(far['z'], dtype=float).reshape(fy, fx)
Zf = ndimage.gaussian_filter(Zf, 0.5) - ZREF
print('relieve cerca %.0f..%.0f  lejos %.0f..%.0f (m sobre el punto bajo del modelo)' % (Zn.min(), Zn.max(), Zf.min(), Zf.max()))

# pendiente del relieve cercano
gy_, gx_ = np.gradient(Zn, 40.0)
slope = np.hypot(gx_, gy_)

# ---------------------------------------------------------------- rasters urbano / bosque / parque (15 m)
CS = 15.0
gxs = np.arange(-960, 960 + 0.1, CS)
gys = np.arange(-960, 960 + 0.1, CS)
b_polys = [p for _, _, p in blds] + [Polygon(b['ring']) for b in sc['buildings']]
bt = STRtree(b_polys)
rt = STRtree(road_lines) if road_lines else None
urban = np.zeros((len(gys), len(gxs)))
park = np.zeros((len(gys), len(gxs)))
for j, y in enumerate(gys):
    for i, x in enumerate(gxs):
        p = Point(x, y)
        d = b_polys[bt.nearest(p)].distance(p)
        u = max(0.0, min(1.0, 1.0 - (d - 22.0) / 45.0))
        if rt is not None:
            dr = road_lines[rt.nearest(p)].distance(p)
            u = max(u, max(0.0, min(1.0, 1.0 - (dr - 8.0) / 25.0)))
        if G.contains(p):
            u = 1.0
        urban[j, i] = u
        if not park_union.is_empty and park_union.contains(p):
            park[j, i] = 1.0
urban = ndimage.gaussian_filter(urban, 0.8)
park = ndimage.gaussian_filter(park, 0.6)


def sample(Z, xs, ys, x, y):
    fx_ = (x - xs[0]) / (xs[1] - xs[0])
    fy_ = (y - ys[0]) / (ys[1] - ys[0])
    i = int(max(0, min(len(xs) - 2, math.floor(fx_))))
    j = int(max(0, min(len(ys) - 2, math.floor(fy_))))
    tx = max(0.0, min(1.0, fx_ - i))
    ty = max(0.0, min(1.0, fy_ - j))
    return (Z[j, i] * (1 - tx) + Z[j, i + 1] * tx) * (1 - ty) + (Z[j + 1, i] * (1 - tx) + Z[j + 1, i + 1] * tx) * ty


forest = np.zeros_like(urban)
for j, y in enumerate(gys):
    for i, x in enumerate(gxs):
        s = sample(slope, near['xs'], near['ys'], x, y)
        e = sample(Zn, near['xs'], near['ys'], x, y) + ZREF
        hill = max(min(1.0, max(0.0, (s - 0.11) / 0.09)), min(1.0, max(0.0, (e - 2690.0) / 40.0)))
        forest[j, i] = (1.0 - urban[j, i]) * hill
forest = ndimage.gaussian_filter(forest, 0.7)
print('fraccion bosque %.2f urbano %.2f' % (float((forest > 0.5).mean()), float((urban > 0.5).mean())))

# ---------------------------------------------------------------- arboles del entorno
rnd = random.Random(21)
trees = []
for x, y in tree_nodes:
    if not G.contains(Point(x, y)) and math.hypot(x, y) < RMAX:
        trees.append([round(x, 1), round(y, 1), round(rnd.uniform(0.8, 1.3), 2), 0])
for kind, poly in parks:
    dens = 1 / 55.0 if kind == 'bosque' else (1 / 130.0 if kind == 'parque' else 1 / 300.0)
    n = min(260, int(poly.area * dens))
    bx0, by0, bx1, by1 = poly.bounds
    k = 0
    tries = 0
    while k < n and tries < n * 30:
        tries += 1
        x = rnd.uniform(bx0, bx1)
        y = rnd.uniform(by0, by1)
        p = Point(x, y)
        if poly.contains(p) and math.hypot(x, y) < RMAX and b_polys[bt.nearest(p)].distance(p) > 3.5:
            trees.append([round(x, 1), round(y, 1), round(rnd.uniform(0.8, 1.5), 2), 0])
            k += 1
n_park = len(trees)
k = 0
tries = 0
while k < 5200 and tries < 700000:
    tries += 1
    x = rnd.uniform(-950, 950)
    y = rnd.uniform(-950, 950)
    i = int((x + 960) / CS)
    j = int((y + 960) / CS)
    if forest[j, i] > 0.55 and rnd.random() < forest[j, i] and not G.buffer(6).contains(Point(x, y)):
        trees.append([round(x, 1), round(y, 1), round(rnd.uniform(1.2, 2.3), 2), 1])
        k += 1
print('arboles entorno: parques', n_park, 'bosque', k)

json.dump({
    'buildings': out_b,
    'roads': roads,
    'parks': [{'kind': k_, 'ring': [[round(x, 1), round(y, 1)] for x, y in list(orient(Polygon(p.exterior), 1.0).exterior.coords)[:-1]]} for k_, p in parks],
    'trees': trees,
    'near': {'xs': near['xs'], 'ys': near['ys'], 'z': [round(float(v), 2) for v in Zn.ravel()]},
    'far': {'xs': far['xs'], 'ys': far['ys'], 'z': [round(float(v), 1) for v in Zf.ravel()]},
    'mask': {'x0': -960.0, 'y0': -960.0, 'cs': CS, 'nx': len(gxs), 'ny': len(gys),
             'urban': [round(float(v), 3) for v in urban.ravel()], 'forest': [round(float(v), 3) for v in forest.ravel()],
             'park': [round(float(v), 3) for v in park.ravel()]},
}, open(os.path.join(DATA, 'context.json'), 'w'))
print('OK context.json')
