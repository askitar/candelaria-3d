"""Plazoleta (fuente, arcos, sombrillas), vegetacion, postes y cables."""
from mathutils import noise as _noise
from mathutils import Matrix


def frustum(mb, cx, cy, r0, z0, r1, z1, k, mat, col, cap_top=False, cap_bot=False, rot=0.0, smooth=False):
    ang = [rot + 2 * math.pi * i / k for i in range(k)]
    lo = [(cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0) for a in ang]
    hi = [(cx + r1 * math.cos(a), cy + r1 * math.sin(a), z1) for a in ang]
    for i in range(k):
        j = (i + 1) % k
        mb.face([lo[i], lo[j], hi[j], hi[i]], mat, col, [(0, 0), (1, 0), (1, 1), (0, 1)], smooth)
    if cap_top:
        mb.face(hi, mat, col)
    if cap_bot:
        mb.face(lo[::-1], mat, col)


def build_plaza(M):
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Plazoleta', root)
    clear_coll('CB_Plazoleta')
    mats = [M['piedra'], M['agua'], M['fachada'], M['teja'], M['madera'], M['hierro']]
    PI_, AG, FA, TE, MA_, HI = range(6)
    cx, cy = SC['specials']['chorro_centro']
    z0 = T(cx, cy) + CURB
    mb = MB()
    r8 = math.pi / 8
    frustum(mb, cx, cy, 2.7, z0 - 0.3, 2.7, z0 + 0.14, 8, PI_, WHITE, True, False, r8)
    frustum(mb, cx, cy, 1.85, z0 + 0.14, 1.8, z0 + 0.72, 8, PI_, WHITE, False, False, r8)
    frustum(mb, cx, cy, 1.5, z0 + 0.72, 1.5, z0 + 0.2, 8, PI_, shade(WHITE, 0.8), False, False, r8)
    k = 8
    for i in range(k):
        a0 = r8 + 2 * math.pi * i / k
        a1 = r8 + 2 * math.pi * (i + 1) / k
        mb.face([(cx + 1.8 * math.cos(a0), cy + 1.8 * math.sin(a0), z0 + 0.72), (cx + 1.8 * math.cos(a1), cy + 1.8 * math.sin(a1), z0 + 0.72),
                 (cx + 1.5 * math.cos(a1), cy + 1.5 * math.sin(a1), z0 + 0.72), (cx + 1.5 * math.cos(a0), cy + 1.5 * math.sin(a0), z0 + 0.72)], PI_, WHITE)
    mb.face([(cx + 1.5 * math.cos(r8 + 2 * math.pi * i / k), cy + 1.5 * math.sin(r8 + 2 * math.pi * i / k), z0 + 0.56) for i in range(k)], AG, WHITE)
    frustum(mb, cx, cy, 0.42, z0 + 0.2, 0.34, z0 + 0.9, 8, PI_, WHITE, False, False, r8)
    frustum(mb, cx, cy, 0.3, z0 + 0.9, 0.24, z0 + 1.75, 8, PI_, WHITE, False, False, r8)
    frustum(mb, cx, cy, 0.24, z0 + 1.75, 0.85, z0 + 2.0, 12, PI_, WHITE, False, False, 0)
    frustum(mb, cx, cy, 0.85, z0 + 2.0, 0.88, z0 + 2.1, 12, PI_, WHITE, False, False, 0)
    mb.face([(cx + 0.78 * math.cos(2 * math.pi * i / 12), cy + 0.78 * math.sin(2 * math.pi * i / 12), z0 + 2.05) for i in range(12)], AG, WHITE)
    frustum(mb, cx, cy, 0.14, z0 + 2.0, 0.1, z0 + 2.55, 8, PI_, WHITE, False, False, r8)
    frustum(mb, cx, cy, 0.2, z0 + 2.55, 0.0, z0 + 2.95, 8, PI_, WHITE, False, False, r8)
    mb.build('Fuente_Chorro_de_Quevedo', coll, mats)

    erm = None
    for b in SC['buildings']:
        if b['kind'] == 'ermita':
            erm = b
    if erm is None:
        return
    ring = [tuple(p) for p in erm['ring']]
    n = len(ring)
    best = None
    for i in range(n):
        a = ring[i]
        c = ring[(i + 1) % n]
        d = math.hypot((a[0] + c[0]) / 2 - cx, (a[1] + c[1]) / 2 - cy)
        if erm['street'][i] and (best is None or d < best[0]):
            best = (d, i)
    if best is None:
        return
    i = best[1]
    a = ring[i]
    c = ring[(i + 1) % n]
    L = math.hypot(c[0] - a[0], c[1] - a[1])
    tx, ty = (c[0] - a[0]) / L, (c[1] - a[1]) / L
    nx, ny = ty, -tx
    others = [[tuple(p) for p in b['ring']] for b in SC['buildings'] if b['kind'] != 'ermita']
    plz = [[tuple(p) for p in rings[0]] for rings in SC['ped'].get('plaza', [])]
    OFFP = 2.5  # los arcos van como portal exento delante de la casa vecina a la ermita

    def free_len(ox, oy, dx, dy, maxlen):
        s = 0.0
        while s < maxlen:
            px, py = ox + dx * (s + 0.5), oy + dy * (s + 0.5)
            if not any(pip(px, py, r) for r in plz):
                break
            hit = False
            for r in others:
                if abs(r[0][0] - px) < 70 and abs(r[0][1] - py) < 70 and (pip(px, py, r) or pip(px + nx * 0.6, py + ny * 0.6, r) or pip(px - nx * 0.6, py - ny * 0.6, r)):
                    hit = True
                    break
            if hit:
                break
            s += 0.5
        return s

    ln = 0.0
    for OFFP in (2.5, 3.2, 4.0, 4.8):
        oa = (a[0] + nx * OFFP, a[1] + ny * OFFP)
        oc_ = (c[0] + nx * OFFP, c[1] + ny * OFFP)
        cand = [(free_len(oc_[0], oc_[1], tx, ty, 11.6), oc_, (tx, ty)), (free_len(oa[0], oa[1], -tx, -ty, 11.6), oa, (-tx, -ty))]
        ln, org, (dx, dy) = max(cand, key=lambda q: q[0])
        if ln >= 7.4:
            break
    globals()['ARCADE'] = None
    mod = 2.25
    na = int((ln - 0.6) / mod)
    if na < 2:
        return
    mb = MB()
    white = srgb('#f6f4ee')
    th = 0.45
    H = 3.5
    zs = 2.05
    ra = 0.82

    def P3(u, z, o=0.0):
        return (org[0] + dx * u + nx * o, org[1] + dy * u + ny * o, z)

    zb = min(T(org[0] + dx * u, org[1] + dy * u) for u in (0, na * mod + 0.6)) + CURB - 0.4
    zg = max(T(org[0] + dx * u, org[1] + dy * u) for u in (0, na * mod + 0.6)) + CURB
    for j in range(na + 1):
        u0 = j * mod
        mb.box(P3(u0, zb, -th / 2), (dx * 0.6, dy * 0.6, 0), (nx * th, ny * th, 0), (0, 0, zg + H - zb), FA, white)
    for j in range(na):
        u0 = j * mod + 0.6
        u1 = u0 + (mod - 0.6)
        um = (u0 + u1) / 2
        arc = [(um + ra * math.cos(math.pi - math.pi * q / 10), zg + zs + ra * math.sin(math.pi * q / 10)) for q in range(11)]
        for o_, rev in ((th / 2, False), (-th / 2, True)):
            for q in range(10):
                p = [(arc[q][0], arc[q][1]), (arc[q + 1][0], arc[q + 1][1]), (arc[q + 1][0], zg + H), (arc[q][0], zg + H)]
                pts = [P3(pp[0], pp[1], o_) for pp in p]
                mb.face(pts[::-1] if rev else pts, FA, white, [(pp[0], pp[1] - zg) for pp in (p[::-1] if rev else p)])
        for q in range(10):
            mb.face([P3(arc[q][0], arc[q][1], -th / 2), P3(arc[q + 1][0], arc[q + 1][1], -th / 2), P3(arc[q + 1][0], arc[q + 1][1], th / 2), P3(arc[q][0], arc[q][1], th / 2)],
                    FA, shade(white, 0.85), [(0, 4.0), (0.2, 4.0), (0.2, 4.5), (0, 4.5)])
    Lt = na * mod + 0.6
    zt = zg + H
    for sgn in (-1, 1):
        p = [P3(-0.1, zt + 0.28, 0.0), P3(Lt + 0.1, zt + 0.28, 0.0), P3(Lt + 0.1, zt - 0.02, sgn * (th / 2 + 0.2)), P3(-0.1, zt - 0.02, sgn * (th / 2 + 0.2))]
        mb.face(p if sgn > 0 else p[::-1], TE, (0.95, 0.9, 0.88, 1.0), [(0, 3.5), (Lt, 3.5), (Lt, 3.0), (0, 3.0)] if sgn > 0 else [(0, 3.0), (Lt, 3.0), (Lt, 3.5), (0, 3.5)])
    mb.build('Arcos_Chorro_de_Quevedo', coll, mats)
    globals()['ARCADE'] = (org, (dx, dy), Lt)


def _tree_mesh(name, seed, blobs, trunk_h=4.8, trunk_r=0.3, subdiv_big=3, subdiv_small=2, M=None):
    """Arbol de copa irregular: tronco + racimos de follaje deformados con ruido."""
    import bmesh
    bm = bmesh.new()
    rnd = random.Random(seed)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=trunk_r, radius2=trunk_r * 0.55, depth=trunk_h, matrix=Matrix.Translation((0, 0, trunk_h / 2)))
    ntr = len(bm.faces)
    for kk, (ox, oy, oz, r) in enumerate(blobs):
        off = Vector((ox, oy, oz))
        ret = bmesh.ops.create_icosphere(bm, subdivisions=subdiv_big if kk == 0 else subdiv_small, radius=r, matrix=Matrix.Translation(off))
        for v in ret['verts']:
            dv = (v.co - off)
            d = _noise.noise(v.co * (1.1 / max(r, 0.5)) + Vector((seed * 3.1, kk * 3.0, 0.0)))
            d2 = _noise.noise(v.co * 2.3 + Vector((kk * 5.0, seed, 2.0)))
            v.co = off + dv * (1.0 + 0.42 * d + 0.16 * d2)
            v.co.z = off.z + (v.co.z - off.z) * 0.8
    bm.faces.ensure_lookup_table()
    for fi, f in enumerate(bm.faces):
        f.material_index = 0 if fi < ntr else 1
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if M is not None:
        me.materials.append(M['tronco'])
        me.materials.append(M['hoja'])
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    ca.data.foreach_set('color', np.ones(len(me.loops) * 4, dtype=np.float32))
    return me


def tree_protos(M):
    protos = []
    rnd = random.Random(5)
    for ti in range(3):
        blobs = [(0.0, 0.0, 6.4 + ti * 0.4, 2.5 + 0.2 * ti)]
        nb = 7 + ti
        for q in range(nb):
            a = 2 * math.pi * q / nb + rnd.uniform(-0.3, 0.3)
            rr = rnd.uniform(1.5, 2.6)
            blobs.append((math.cos(a) * rr, math.sin(a) * rr, 5.2 + rnd.uniform(-0.6, 1.9), rnd.uniform(1.15, 1.8)))
        protos.append(_tree_mesh('Arbol_%d' % ti, 40 + ti, blobs, 5.0, 0.32, 3, 2, M))
    return protos


def palm_mesh(M):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=0.2, radius2=0.13, depth=13.0, matrix=Matrix.Translation((0, 0, 6.5)))
    ntr = len(bm.faces)
    for fr in range(13):
        ang = 2 * math.pi * fr / 13 + 0.2
        ca, sa = math.cos(ang), math.sin(ang)
        prev = None
        droop = 1.2 + 0.9 * (fr % 3)
        for s in range(7):
            t = s / 6.0
            rad = 0.2 + 3.6 * t
            zz = 13.0 + 1.4 * math.sin(t * 2.2) - droop * t * t
            w = 0.6 * (1 - t) + 0.06
            pl = bm.verts.new((ca * rad - sa * w, sa * rad + ca * w, zz - 0.3 * (1 - t)))
            pm = bm.verts.new((ca * rad, sa * rad, zz))
            pr = bm.verts.new((ca * rad + sa * w, sa * rad - ca * w, zz - 0.3 * (1 - t)))
            if prev:
                bm.faces.new((prev[0], prev[1], pm, pl))
                bm.faces.new((prev[1], prev[2], pr, pm))
            prev = (pl, pm, pr)
    bm.faces.ensure_lookup_table()
    for fi, f in enumerate(bm.faces):
        f.material_index = 0 if fi < ntr else 1
        f.smooth = True
    me = bpy.data.meshes.new('Palma_de_cera')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M['tronco'])
    me.materials.append(M['hoja'])
    ca_ = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    ca_.data.foreach_set('color', np.ones(len(me.loops) * 4, dtype=np.float32))
    return me


def build_trees(M):
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Vegetacion', root)
    clear_coll('CB_Vegetacion')
    protos = tree_protos(M)
    palm = palm_mesh(M)
    rnd = random.Random(11)
    cnt = 0
    for (x, y, s, ty) in SC['trees']:
        is_palm = rnd.random() < 0.09
        me = palm if is_palm else protos[ty % 3]
        ob = bpy.data.objects.new(('Palma_%03d' if is_palm else 'Arbol_%03d') % cnt, me)
        ob.location = (x, y, T(x, y) + CURB - 0.05)
        sc = s * (1.0 if is_palm else rnd.uniform(0.75, 1.2))
        ob.scale = (sc, sc, sc * rnd.uniform(0.9, 1.2))
        ob.rotation_euler = (0, 0, rnd.uniform(0, 6.283))
        coll.objects.link(ob)
        cnt += 1
    for (x, y, z, area) in PATIOS:
        if area < 30:
            continue
        me = protos[rnd.randrange(3)]
        ob = bpy.data.objects.new('Arbol_patio_%03d' % cnt, me)
        ob.location = (x, y, z)
        sc = min(0.6, 0.26 + area / 500.0)
        ob.scale = (sc, sc, sc)
        ob.rotation_euler = (0, 0, rnd.uniform(0, 6.283))
        coll.objects.link(ob)
        cnt += 1
    return cnt


def _wire(mb, p0, p1, sag, r, mat, nseg=10):
    """Cable con catenaria aproximada, seccion triangular."""
    dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    L = math.hypot(dx, dy)
    if L < 0.5:
        return
    sx, sy = -dy / L * r, dx / L * r
    prev = None
    for q in range(nseg + 1):
        t = q / nseg
        cx_, cy_ = p0[0] + dx * t, p0[1] + dy * t
        cz_ = p0[2] + dz * t - sag * 4 * t * (1 - t)
        ring = [(cx_ + sx, cy_ + sy, cz_ - r * 0.6), (cx_ - sx, cy_ - sy, cz_ - r * 0.6), (cx_, cy_, cz_ + r)]
        if prev:
            for a in range(3):
                b = (a + 1) % 3
                mb.face([prev[a], prev[b], ring[b], ring[a]], mat, WHITE)
        prev = ring


def build_furniture(M, avoid=None):
    """Postes de concreto con luminaria, cables aereos y sombrillas de cafe en la plazoleta."""
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Mobiliario', root)
    clear_coll('CB_Mobiliario')
    mats = [M['poste'], M['cable'], M['hierro'], M['farol'], M['lona'], M['madera']]
    PO, CA, HI, FL, LO, MA_ = range(6)
    rnd = random.Random(77)
    Gr = [tuple(p) for p in SC['G'][0][0]]
    brings = [[tuple(p) for p in b['ring']] for b in SC['buildings']]
    bbox = [(min(p[0] for p in r), min(p[1] for p in r), max(p[0] for p in r), max(p[1] for p in r)) for r in brings]

    def in_building(x, y, m=0.5):
        for r, (x0, y0, x1, y1) in zip(brings, bbox):
            if x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m:
                if pip(x, y, r) or pip(x + m, y, r) or pip(x - m, y, r) or pip(x, y + m, r) or pip(x, y - m, r):
                    return True
        return False

    mb = MB()
    npoles = 0
    for st in SC['streets']:
        if st['cls'] != 'veh':
            continue
        pts = [tuple(p) for p in st['pts']]
        segl = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
        Ltot = sum(segl)
        if Ltot < 40:
            continue

        def at(s):
            acc = 0.0
            for i in range(len(segl)):
                if acc + segl[i] >= s or i == len(segl) - 1:
                    t = min(1.0, max(0.0, (s - acc) / max(segl[i], 1e-6)))
                    dx, dy = (pts[i + 1][0] - pts[i][0]) / max(segl[i], 1e-6), (pts[i + 1][1] - pts[i][1]) / max(segl[i], 1e-6)
                    return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t), (dx, dy)
                acc += segl[i]

        side = 1 if rnd.random() < 0.5 else -1
        off = st['hw'] + 0.62
        s = rnd.uniform(9, 16)
        placed = []
        while s < Ltot - 8:
            (px, py), (dx, dy) = at(s)
            ok = None
            for sd in (side, -side):
                qx, qy = px + dy * off * sd, py - dx * off * sd
                if pip(qx, qy, Gr) and not in_building(qx, qy, 0.35) and (avoid is None or not len(avoid) or float(np.hypot(avoid[:, 0] - qx, avoid[:, 1] - qy).min()) > 2.6):
                    ok = (qx, qy, sd)
                    break
            if ok:
                placed.append((ok[0], ok[1], dx, dy, ok[2]))
            s += rnd.uniform(27, 34)
        prev = None
        for (qx, qy, dx, dy, sd) in placed:
            z0 = T(qx, qy) + CURB
            H = 8.6
            frustum(mb, qx, qy, 0.15, z0 - 0.3, 0.1, z0 + H, 8, PO, WHITE, True, False, 0.0, True)
            # cruceta y aisladores
            cx_, cy_ = dy, -dx
            zc = z0 + H - 0.5
            mb.box((qx - cx_ * 0.8 - dx * 0.05, qy - cy_ * 0.8 - dy * 0.05, zc), (cx_ * 1.6, cy_ * 1.6, 0), (dx * 0.1, dy * 0.1, 0), (0, 0, 0.1), MA_, srgb('#4a3a2a'))
            tops = []
            for o_ in (-0.7, 0.0, 0.7):
                ix, iy = qx + cx_ * o_, qy + cy_ * o_
                mb.box((ix - 0.03, iy - 0.03, zc + 0.1), (0.06, 0, 0), (0, 0.06, 0), (0, 0, 0.14), FL, WHITE)
                tops.append((ix, iy, zc + 0.25))
            tele = [(qx - cx_ * sd * 0.16, qy - cy_ * sd * 0.16, z0 + 6.1), (qx - cx_ * sd * 0.16, qy - cy_ * sd * 0.16, z0 + 5.75)]
            # luminaria hacia la calzada
            ax_, ay_ = -cx_ * sd, -cy_ * sd
            mb.box((qx, qy, z0 + 7.5), (ax_ * 1.5, ay_ * 1.5, 0.25), (dx * 0.05, dy * 0.05, 0), (0, 0, 0.05), HI, WHITE)
            mb.box((qx + ax_ * 1.35 - dx * 0.12, qy + ay_ * 1.35 - dy * 0.12, z0 + 7.66), (ax_ * 0.55, ay_ * 0.55, 0), (dx * 0.24, dy * 0.24, 0), (0, 0, 0.1), PO, WHITE)
            if rnd.random() < 0.14:
                frustum(mb, qx + dx * 0.36, qy + dy * 0.36, 0.27, z0 + 6.3, 0.27, z0 + 7.05, 10, PO, shade(WHITE, 0.7), True, True, 0.0, True)
            if prev is not None and math.hypot(prev[0][0][0] - tops[0][0], prev[0][0][1] - tops[0][1]) < 46:
                for a, b in zip(prev[0], tops):
                    _wire(mb, a, b, rnd.uniform(0.25, 0.45), 0.012, CA)
                for a, b in zip(prev[1], tele):
                    _wire(mb, a, b, rnd.uniform(0.5, 0.85), 0.022, CA)
            prev = (tops, tele)
            npoles += 1
    mb.build('Postes_y_cables', coll, mats, weld=True)

    # sombrillas y mesas en la plazoleta
    cx, cy = SC['specials']['chorro_centro']
    plz = [tuple(p) for p in SC['specials']['chorro_ring']]
    segs = []
    for r in brings:
        segs.extend(ring_segs(r))
    segs = [s_ for s_ in segs if abs(s_[0] - cx) < 60 and abs(s_[1] - cy) < 60]
    cand = []
    for q in range(900):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(7.5, 20.0)
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        if not pip(x, y, plz) or in_building(x, y, 1.2):
            continue
        d = float(seg_dist_np(np.asarray([[x, y]]), segs).min())
        if not (2.3 <= d <= 4.6):
            continue
        if avoid is not None and len(avoid):
            if float(np.hypot(avoid[:, 0] - x, avoid[:, 1] - y).min()) < 4.2:
                continue
        if any(math.hypot(x - c_[0], y - c_[1]) < 3.4 for c_ in cand):
            continue
        arc = globals().get('ARCADE')
        if arc is not None:
            (ax0, ay0), (adx, ady), al = arc
            tt = max(0.0, min(al, (x - ax0) * adx + (y - ay0) * ady))
            if math.hypot(x - (ax0 + adx * tt), y - (ay0 + ady * tt)) < 3.2:
                continue
        cand.append((x, y))
        if len(cand) >= 7:
            break
    mb = MB()
    pal = [('#b8322a', '#f1ead8'), ('#2f6a4a', '#f1ead8'), ('#d9a02b', '#f4efe0'), ('#274b7a', '#e9e4d6'), ('#c0562a', '#f1ead8')]
    for (x, y) in cand:
        z0 = T(x, y) + CURB
        c1, c2 = [srgb(h) for h in rnd.choice(pal)]
        frustum(mb, x, y, 0.028, z0, 0.028, z0 + 2.45, 6, HI, WHITE)
        rot = rnd.uniform(0, 1)
        k = 8
        for i in range(k):
            a0 = rot + 2 * math.pi * i / k
            a1 = rot + 2 * math.pi * (i + 1) / k
            p0 = (x + 1.35 * math.cos(a0), y + 1.35 * math.sin(a0), z0 + 2.08)
            p1 = (x + 1.35 * math.cos(a1), y + 1.35 * math.sin(a1), z0 + 2.08)
            col = c1 if i % 2 == 0 else c2
            mb.face([p0, p1, (x, y, z0 + 2.5)], LO, col)
            mb.face([(p0[0], p0[1], p0[2] - 0.13), (p1[0], p1[1], p1[2] - 0.13), p1, p0], LO, col)
        frustum(mb, x + 0.35, y, 0.42, z0 + 0.71, 0.42, z0 + 0.75, 12, MA_, srgb('#5a3a22'), True, True)
        frustum(mb, x + 0.35, y, 0.035, z0, 0.035, z0 + 0.71, 6, HI, WHITE)
        for q in range(3):
            a = rot * 6 + 2.1 * q
            sx_, sy_ = x + 0.35 + math.cos(a) * 0.78, y + math.sin(a) * 0.78
            mb.box((sx_ - 0.2, sy_ - 0.2, z0 + 0.43), (0.4, 0, 0), (0, 0.4, 0), (0, 0, 0.04), MA_, srgb('#6b4a2b'))
            for lx, ly in ((-0.18, -0.18), (0.15, -0.18), (-0.18, 0.15), (0.15, 0.15)):
                mb.box((sx_ + lx, sy_ + ly, z0), (0.03, 0, 0), (0, 0.03, 0), (0, 0, 0.43), MA_, srgb('#4a3626'))
            bx_, by_ = math.cos(a), math.sin(a)
            mb.box((sx_ + bx_ * 0.18 - by_ * 0.2, sy_ + by_ * 0.18 + bx_ * 0.2, z0 + 0.47), (by_ * 0.4, -bx_ * 0.4, 0), (bx_ * 0.03, by_ * 0.03, 0), (0, 0, 0.42), MA_, srgb('#6b4a2b'))
    mb.build('Sombrillas_y_mesas', coll, mats)
    return npoles, len(cand)
