"""Entorno real alrededor de las 4 manzanas: relieve SRTM, edificios y vias de OpenStreetMap, parques y bosque."""

CTX = json.load(open(os.path.join(ROOT, "data", "context.json"), encoding="utf-8"))
_NXS = np.asarray(CTX['near']['xs'], dtype=float)
_NYS = np.asarray(CTX['near']['ys'], dtype=float)
_NZ = np.asarray(CTX['near']['z'], dtype=float).reshape(len(_NYS), len(_NXS))
_FXS = np.asarray(CTX['far']['xs'], dtype=float)
_FYS = np.asarray(CTX['far']['ys'], dtype=float)
_FZ = np.asarray(CTX['far']['z'], dtype=float).reshape(len(_FYS), len(_FXS))
_GR = [tuple(p) for p in SC['G'][0][0]]
_GSEG = ring_segs(_GR)
_MK = CTX['mask']
_MU = np.asarray(_MK['urban'], dtype=float).reshape(_MK['ny'], _MK['nx'])
_MF = np.asarray(_MK['forest'], dtype=float).reshape(_MK['ny'], _MK['nx'])
_MP = np.asarray(_MK['park'], dtype=float).reshape(_MK['ny'], _MK['nx'])
MONS = (1591.0, 888.0)


def _bilin(Z, xs, ys, P):
    fx = (P[:, 0] - xs[0]) / (xs[1] - xs[0])
    fy = (P[:, 1] - ys[0]) / (ys[1] - ys[0])
    i = np.clip(np.floor(fx).astype(int), 0, len(xs) - 2)
    j = np.clip(np.floor(fy).astype(int), 0, len(ys) - 2)
    tx = np.clip(fx - i, 0.0, 1.0)
    ty = np.clip(fy - j, 0.0, 1.0)
    return (Z[j, i] * (1 - tx) + Z[j, i + 1] * tx) * (1 - ty) + (Z[j + 1, i] * (1 - tx) + Z[j + 1, i + 1] * tx) * ty


def _ss(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def dist_G(P):
    d = np.zeros(len(P))
    CH = 5000
    for s in range(0, len(P), CH):
        d[s:s + CH] = seg_dist_np(P[s:s + CH], _GSEG).min(axis=1)
    d[pip_np(P, _GR)] = 0.0
    return d


def Tc_np(P):
    """Altura del terreno para cualquier punto: polinomio del modelo cerca, SRTM real lejos."""
    P = np.asarray(P, dtype=float)
    zn = _bilin(_NZ, _NXS, _NYS, P)
    zf = _bilin(_FZ, _FXS, _FYS, P)
    dnb = np.minimum(960.0 - np.abs(P[:, 0]), 960.0 - np.abs(P[:, 1]))
    wn = _ss(dnb / 220.0)
    z = wn * zn + (1 - wn) * zf
    near = (np.abs(P[:, 0]) < 520) & (np.abs(P[:, 1]) < 520)
    if near.any():
        d = dist_G(P[near])
        w = _ss(1.0 - d / 120.0)
        zt = T_np(P[near])
        z[near] = w * zt + (1 - w) * z[near]
    return z


def mask_np(P):
    mx = np.stack([(P[:, 0] - _MK['x0']) / _MK['cs'], (P[:, 1] - _MK['y0']) / _MK['cs']], axis=1)
    xs = np.arange(_MK['nx'], dtype=float)
    ys = np.arange(_MK['ny'], dtype=float)
    inside = (mx[:, 0] >= 0) & (mx[:, 0] <= _MK['nx'] - 1) & (mx[:, 1] >= 0) & (mx[:, 1] <= _MK['ny'] - 1)
    f = _bilin(_MF, xs, ys, mx)
    p = _bilin(_MP, xs, ys, mx)
    u = _bilin(_MU, xs, ys, mx)
    return f, p, u, inside


def build_far(M):
    """Terreno del entorno (anillos desde el borde del modelo hasta los cerros) + santuario de Monserrate."""
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Entorno_lejano', root)
    clear_coll('CB_Entorno_lejano')
    d = densify(_GR, 5.0)
    Pg = np.asarray(d)
    cx, cy = Pg.mean(axis=0)
    dists = [0, 6, 14, 24, 36, 50, 66, 84, 104, 126, 150, 178, 210, 246, 286, 330, 380, 436, 500, 570, 650, 740, 840, 950, 1080, 1230, 1400,
             1590, 1800, 2030, 2280, 2550, 2850, 3200, 3550]
    n = len(d)
    V = Pg - np.array([cx, cy])
    V = V / np.hypot(V[:, 0], V[:, 1])[:, None]
    rows = []
    for dk in dists:
        Pk = Pg + V * dk
        z = Tc_np(Pk) - (0.03 if dk == 0 else 0.06)
        rows.append(np.column_stack([Pk, z]))
    mb = MB()
    for k in range(len(rows) - 1):
        r0, r1 = rows[k], rows[k + 1]
        for i in range(n):
            j = (i + 1) % n
            q = [tuple(r0[i]), tuple(r0[j]), tuple(r1[j]), tuple(r1[i])]
            mb.face(q, 0, WHITE, [(p[0], p[1]) for p in q], True)
    ob = mb.build('Terreno_entorno', coll, [M['lejano']], weld=True)
    me = ob.data
    nl = len(me.loops)
    vi = np.zeros(nl, dtype=np.int32)
    me.loops.foreach_get('vertex_index', vi)
    co = np.zeros(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3).astype(float)
    f, p, u, inside = mask_np(co[:, :2])
    zabs = co[:, 2] + ZREF
    f_far = _ss((zabs - 2700.0) / 60.0)
    r = np.hypot(co[:, 0], co[:, 1])
    forest = np.where(inside, np.maximum(f, f_far * (1 - u)), f_far)
    hill = _ss((zabs - 2642.0) / 26.0)
    park = np.where(inside, np.maximum(p, (1 - u) * hill), hill)
    carpet = _ss((r - 820.0) / 160.0)
    cols = np.ones((nl, 4), dtype=np.float32)
    cols[:, 0] = forest[vi]
    cols[:, 1] = park[vi]
    cols[:, 2] = carpet[vi]
    me.color_attributes['Col'].data.foreach_set('color', cols.ravel())
    for pl in me.polygons:
        pl.use_smooth = True
    # santuario de Monserrate en la cima real
    zm = float(Tc_np(np.asarray([MONS]))[0])
    mb = MB()
    wcol = srgb('#f3f1ea')
    mb.box((MONS[0] - 9, MONS[1] - 22, zm - 6), (18, 0, 0), (0, 44, 0), (0, 0, 22), 0, wcol)
    mb.box((MONS[0] - 5, MONS[1] + 22, zm - 6), (10, 0, 0), (0, 10, 0), (0, 0, 42), 0, wcol)
    for sg in (-1, 1):
        mb.face([(MONS[0], MONS[1] - 23, zm + 22), (MONS[0], MONS[1] + 23, zm + 22), (MONS[0] + sg * 10, MONS[1] + 23, zm + 16), (MONS[0] + sg * 10, MONS[1] - 23, zm + 16)],
                1, (0.9, 0.9, 0.9, 1), [(0, 3.5), (46, 3.5), (46, 3.0), (0, 3.0)])
    mb.build('Santuario_de_Monserrate', coll, [M['fachada_ctx'], M['teja']])
    return zm


def build_ctx_roads(M):
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Entorno_ciudad', root)
    for ob in list(coll.objects):
        if ob.name.startswith('Vias_entorno'):
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(me)
    mb = MB()
    for rd in CTX['roads']:
        pts = densify_line([tuple(p) for p in rd['pts']], 9.0)
        if len(pts) < 2:
            continue
        P = np.asarray(pts)
        w = rd['w']
        dv = np.zeros_like(P)
        dv[1:-1] = P[2:] - P[:-2]
        dv[0] = P[1] - P[0]
        dv[-1] = P[-1] - P[-2]
        ln = np.hypot(dv[:, 0], dv[:, 1])
        ln[ln < 1e-6] = 1.0
        nrm = np.column_stack([-dv[:, 1] / ln, dv[:, 0] / ln])
        Lp = P + nrm * w
        Rp = P - nrm * w
        lift = 0.1 + 0.0007 * np.hypot(P[:, 0], P[:, 1])
        zl = Tc_np(Lp) + lift
        zr = Tc_np(Rp) + lift
        zc = np.maximum(zl, zr)
        for i in range(len(P) - 1):
            mb.face([(Rp[i][0], Rp[i][1], float(zc[i])), (Rp[i + 1][0], Rp[i + 1][1], float(zc[i + 1])),
                     (Lp[i + 1][0], Lp[i + 1][1], float(zc[i + 1])), (Lp[i][0], Lp[i][1], float(zc[i]))], 0, WHITE)
    mb.build('Vias_entorno', coll, [M['asfalto']])
    return mb.stats()


def densify_line(pts, step):
    out = [pts[0]]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(math.ceil(L / step)))
        for j in range(1, k + 1):
            t = j / k
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


CTX_WALLS = [('#efece3', 14), ('#e6dcc6', 10), ('#d9c9a8', 6), ('#e2b450', 5), ('#c9654a', 4), ('#de9a7c', 3), ('#7f9fc4', 3), ('#8fb08a', 2),
             ('#b9b4aa', 9), ('#a39b90', 7), ('#9a5f4a', 8), ('#c9c2b4', 6), ('#8a8d92', 4)]
CTX_TALL = [('#b9b4aa', 6), ('#a39b90', 5), ('#c9c2b4', 5), ('#8a8d92', 5), ('#9a5f4a', 4), ('#d8d3c8', 4), ('#6f7a86', 3), ('#e6dcc6', 2)]
CTX_ROOF = ['#77736c', '#8a867e', '#6a6661', '#7a4a3a', '#9a958c', '#5f5b57', '#a8a59e']


def build_ctx_buildings(M):
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Entorno_ciudad', root)
    for ob in list(coll.objects):
        if ob.name.startswith('Edificios_entorno'):
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(me)
    mats = [M['fachada_ctx'], M['teja'], M['azotea']]
    quads = {}
    nb = 0
    for b in CTX['buildings']:
        ring = [tuple(p) for p in b['ring']]
        n = len(ring)
        if n < 3:
            continue
        if ring_area(ring) < 0:
            ring = ring[::-1]
        rnd = random.Random(b['seed'])
        P = np.asarray(ring)
        zt = Tc_np(P)
        floor = float(zt.mean())
        zbot = float(zt.min()) - 1.2
        h = b['h']
        top = floor + h
        flat = b['kind'] == 'plano'
        wcol = srgb(wpick(rnd, CTX_TALL if (flat and h > 13) else CTX_WALLS))
        key = (0 if P[:, 0].mean() < 0 else 1, 0 if P[:, 1].mean() < 0 else 1)
        if key not in quads:
            quads[key] = MB()
        mb = quads[key]
        par = 0.75 if flat else 0.0
        u0 = rnd.uniform(0, 3)
        for i in range(n):
            a = ring[i]
            c = ring[(i + 1) % n]
            L = math.hypot(c[0] - a[0], c[1] - a[1])
            if L < 0.05:
                continue
            mb.face([(a[0], a[1], zbot), (c[0], c[1], zbot), (c[0], c[1], top + par), (a[0], a[1], top + par)], 0, wcol,
                    [(u0, zbot - floor), (u0 + L, zbot - floor), (u0 + L, h + par), (u0, h + par)])
            u0 += L
        if flat:
            pts, tris = tri_poly([ring], 8.0, grid=9.0)
            rc = srgb(rnd.choice(CTX_ROOF))
            for a_, b_, c_ in tris:
                mb.face([(pts[a_][0], pts[a_][1], top), (pts[b_][0], pts[b_][1], top), (pts[c_][0], pts[c_][1], top)], 2, rc)
            if b['area'] > 260 and tris:
                for q in range(rnd.randint(1, 3)):
                    t_ = tris[rnd.randrange(len(tris))]
                    cxp = (pts[t_[0]][0] + pts[t_[1]][0] + pts[t_[2]][0]) / 3
                    cyp = (pts[t_[0]][1] + pts[t_[1]][1] + pts[t_[2]][1]) / 3
                    sx, sy = rnd.uniform(2.5, 6.0), rnd.uniform(2.5, 5.0)
                    ang = GRID_ANGLE
                    ex = (math.cos(ang) * sx, math.sin(ang) * sx, 0)
                    ey = (-math.sin(ang) * sy, math.cos(ang) * sy, 0)
                    if all(pip(cxp + ex[0] * fx + ey[0] * fy, cyp + ex[1] * fx + ey[1] * fy, ring) for fx in (0, 1) for fy in (0, 1)):
                        mb.box((cxp, cyp, top), ex, ey, (0, 0, rnd.uniform(2.3, 3.6)), 0, shade(wcol, 0.92), 'z')
        else:
            Pm = sum(math.hypot(ring[(i + 1) % n][0] - ring[i][0], ring[(i + 1) % n][1] - ring[i][1]) for i in range(n))
            A = abs(ring_area(ring))
            mw = (Pm - math.sqrt(max(Pm * Pm - 16 * A, 0.0))) / 4.0
            D = min(4.5, max(1.8, 0.5 * mw))
            tanp = rnd.uniform(0.42, 0.55)
            segs = ring_segs(ring)
            pts, tris = tri_poly([ring], 2.4, grid=2.6, margin=0.3)
            if not tris:
                continue
            Pp = np.asarray(pts)
            dm = seg_dist_np(Pp, segs).min(axis=1)
            x_ = np.maximum(dm - D, 0.0)
            tri_ = D - np.abs((x_ % (2 * D)) - D)
            hh = np.where(dm <= D, dm, D - 0.5 * tri_) * tanp
            Z = top + hh
            TR = np.asarray(tris, dtype=int)
            Cn = (Pp[TR[:, 0]] + Pp[TR[:, 1]] + Pp[TR[:, 2]]) / 3.0
            kc = seg_dist_np(Cn, segs).argmin(axis=1)
            S = np.asarray(segs)
            sg = S[kc]
            ex_ = sg[:, 2] - sg[:, 0]
            ey_ = sg[:, 3] - sg[:, 1]
            ll = np.hypot(ex_, ey_)
            ll[ll < 1e-6] = 1.0
            tdx, tdy = ex_ / ll, ey_ / ll
            tint = rnd.uniform(0.72, 1.05)
            tcol = (tint, tint * rnd.uniform(0.93, 1.0), tint * rnd.uniform(0.88, 1.0), 1.0)
            uvs = []
            for j in range(3):
                pj = Pp[TR[:, j]]
                rx = pj[:, 0] - sg[:, 0]
                ry = pj[:, 1] - sg[:, 1]
                uvs.append(np.stack([rx * tdx + ry * tdy, -rx * tdy + ry * tdx + 3.0], axis=1))
            for t in range(len(TR)):
                a_, b_, c_ = TR[t]
                mb.face([(pts[a_][0], pts[a_][1], float(Z[a_])), (pts[b_][0], pts[b_][1], float(Z[b_])), (pts[c_][0], pts[c_][1], float(Z[c_]))], 1, tcol,
                        [(float(uvs[0][t][0]), float(uvs[0][t][1])), (float(uvs[1][t][0]), float(uvs[1][t][1])), (float(uvs[2][t][0]), float(uvs[2][t][1]))])
        nb += 1
    tot = 0
    for key, mb in quads.items():
        mb.build('Edificios_entorno_%d%d' % key, coll, mats)
        tot += mb.stats()
    return nb, tot


def build_ctx_trees(M, keep_park=0.55, keep_forest=0.8):
    """Arboles del entorno fusionados en pocas mallas (parques y bosque de los cerros)."""
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Entorno_ciudad', root)
    for ob in list(coll.objects):
        if ob.name.startswith('Arboles_entorno'):
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(me)
    rnd = random.Random(31)
    protos = []
    for ti in range(3):
        blobs = [(0.0, 0.0, 5.6, 2.3)]
        for q in range(3):
            a = 2.1 * q + ti
            blobs.append((math.cos(a) * 1.5, math.sin(a) * 1.5, 4.9 + 0.5 * q, 1.5))
        me = _tree_mesh('tmp_arbol_%d' % ti, 70 + ti, blobs, 4.6, 0.3, 2, 1, None)
        nv = len(me.vertices)
        co = np.zeros(nv * 3, dtype=np.float32)
        me.vertices.foreach_get('co', co)
        faces = [tuple(p.vertices) for p in me.polygons]
        mi = [p.material_index for p in me.polygons]
        protos.append((co.reshape(-1, 3).astype(float), faces, mi))
        bpy.data.meshes.remove(me)
    trees = [t for t in CTX['trees'] if rnd.random() < (keep_forest if t[3] == 1 else keep_park)]
    if not trees:
        return 0
    TP = np.asarray([[t[0], t[1]] for t in trees])
    TZ = Tc_np(TP)
    groups = {}
    for (t, z) in zip(trees, TZ):
        key = (0 if t[0] < 0 else 1, 0 if t[1] < 0 else 1)
        groups.setdefault(key, []).append((t, float(z)))
    tot = 0
    for key, lst in groups.items():
        verts = []
        faces = []
        mats_i = []
        cols = []
        base = 0
        for (t, z) in lst:
            co, fc, mi = protos[rnd.randrange(3)]
            s = t[2] * rnd.uniform(0.85, 1.2)
            a = rnd.uniform(0, 6.283)
            ca, sa = math.cos(a), math.sin(a)
            x = co[:, 0] * ca - co[:, 1] * sa
            y = co[:, 0] * sa + co[:, 1] * ca
            vv = np.column_stack([x * s + t[0], y * s + t[1], co[:, 2] * s * rnd.uniform(0.9, 1.25) + z - 0.2])
            verts.append(vv)
            tint = rnd.uniform(0.7, 1.15)
            tc = (tint * rnd.uniform(0.9, 1.05), tint, tint * rnd.uniform(0.8, 1.0), 1.0)
            for f, m in zip(fc, mi):
                faces.append(tuple(base + i for i in f))
                mats_i.append(m)
                cols.append(tc)
            base += len(co)
        V = np.vstack(verts)
        me = bpy.data.meshes.new('Arboles_entorno_%d%d' % key)
        me.from_pydata(V.tolist(), [], faces)
        me.polygons.foreach_set('material_index', np.asarray(mats_i, dtype=np.int32))
        me.polygons.foreach_set('use_smooth', np.ones(len(faces), dtype=bool))
        counts = np.fromiter((len(f) for f in faces), dtype=np.int32, count=len(faces))
        ca_ = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        ca_.data.foreach_set('color', np.repeat(np.asarray(cols, dtype=np.float32), counts, axis=0).ravel())
        me.materials.append(M['tronco'])
        me.materials.append(M['hoja'])
        me.update()
        ob = bpy.data.objects.new('Arboles_entorno_%d%d' % key, me)
        coll.objects.link(ob)
        tot += len(faces)
    return len(trees), tot
