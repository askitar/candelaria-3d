"""Casas de La Candelaria: muros con vanos, carpinteria, balcones, aleros y techos de teja."""

MAT = {'fa': 0, 'mu': 1, 'ma': 2, 'vi': 3, 'te': 4, 'hi': 5, 'fl': 6, 'pi': 7, 'lo': 8, 'ho': 9, 'vc': 10, 'pt': 11}
FLORES = ['#c8283a', '#e0457b', '#f2c230', '#d85a1e', '#b04fc0', '#f4f1ea', '#e03030']
DR = 0.26  # profundidad del vano (muros de adobe)

PAL_WALL = [('#f2efe6', 17), ('#ece3cf', 8), ('#e3b23c', 9), ('#d99a2b', 5), ('#c8553d', 7), ('#b03a2e', 4),
            ('#e08a6b', 5), ('#e7a9a0', 3), ('#4f86c6', 6), ('#2f5d9b', 4), ('#3aa6a0', 4), ('#5c9a5a', 5),
            ('#8e6fae', 2), ('#f0c987', 4), ('#d6763a', 4)]
PAL_ZOC_WHITE = ['#2f5d3a', '#8b2f24', '#274b7a', '#b4832d', '#6f6a62', '#7a4a2a']
PAL_WOOD = [('#2f5d3a', 6), ('#5a3a22', 6), ('#3b2a1c', 5), ('#274b7a', 4), ('#7a2b22', 4), ('#e9e4d6', 3),
            ('#1f3f2a', 4), ('#6b4a2b', 5), ('#1d1d1b', 2)]


def wpick(rnd, items):
    tot = sum(w for _, w in items)
    r = rnd.uniform(0, tot)
    for v, w in items:
        r -= w
        if r <= 0:
            return v
    return items[-1][0]


def offset_ring(ring, offs):
    """Desplaza cada arista i (ring[i]->ring[i+1]) hacia afuera offs[i]. Devuelve lista de listas de puntos por vertice."""
    n = len(ring)
    out = []
    for i in range(n):
        p = ring[i]
        pp = ring[i - 1]
        pn = ring[(i + 1) % n]
        l1 = math.hypot(p[0] - pp[0], p[1] - pp[1]) or 1e-9
        l2 = math.hypot(pn[0] - p[0], pn[1] - p[1]) or 1e-9
        d1 = ((p[0] - pp[0]) / l1, (p[1] - pp[1]) / l1)
        d2 = ((pn[0] - p[0]) / l2, (pn[1] - p[1]) / l2)
        n1 = (d1[1], -d1[0])
        n2 = (d2[1], -d2[0])
        o1 = offs[i - 1]
        o2 = offs[i]
        ax, ay = p[0] + n1[0] * o1, p[1] + n1[1] * o1
        bx_, by_ = p[0] + n2[0] * o2, p[1] + n2[1] * o2
        cr = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(cr) > 0.12:
            t = ((bx_ - ax) * d2[1] - (by_ - ay) * d2[0]) / cr
            q = (ax + d1[0] * t, ay + d1[1] * t)
            if math.hypot(q[0] - p[0], q[1] - p[1]) <= 3.0 * max(abs(o1), abs(o2)) + 0.01:
                out.append([q])
                continue
        if math.hypot(ax - bx_, ay - by_) < 1e-4:
            out.append([(ax, ay)])
        else:
            out.append([(ax, ay), (bx_, by_)])
    return out


class Bld:
    pass


def setup_building(b):
    B = Bld()
    rnd = random.Random(b['seed'])
    B.rnd = rnd
    B.b = b
    B.ring = [tuple(p) for p in b['ring']]
    B.n = len(B.ring)
    B.free = b['free']
    B.street = b['street']
    B.ped = b['ped']
    B.lv = b['levels']
    B.kind = b['kind']
    B.patios = [[tuple(p) for p in pr] for pr in (b.get('patios') or ([b['patio']] if b.get('patio') else []))]
    B.blk = b['blk']
    ring = B.ring
    n = B.n
    gs = []
    elen = []
    for i in range(n):
        a = ring[i]
        c = ring[(i + 1) % n]
        elen.append(math.hypot(c[0] - a[0], c[1] - a[1]))
        if B.street[i]:
            gs += [T(a[0], a[1]) + CURB, T(c[0], c[1]) + CURB, T((a[0] + c[0]) / 2, (a[1] + c[1]) / 2) + CURB]
    allg = [T(x, y) + CURB for x, y in ring]
    if not gs:
        gs = allg
    B.elen = elen
    B.base = max(sum(gs) / len(gs), max(gs) - 0.9)
    B.zbot = min(allg) - 1.0
    B.H1 = rnd.uniform(3.3, 3.8)
    B.HU = rnd.uniform(2.8, 3.1)
    B.wall_top = B.base + B.H1 + B.HU * (B.lv - 1) + (0.3 if B.lv > 1 else 0.0)
    B.tanp = rnd.uniform(0.45, 0.55)
    A = abs(ring_area(ring))
    Pm = sum(elen)
    mw = (Pm - math.sqrt(max(Pm * Pm - 16 * A, 0.0))) / 4.0
    B.D = min(4.2, max(2.0, 0.5 * mw))
    wall_hex = wpick(rnd, PAL_WALL)
    B.wall_col = srgb(wall_hex)
    if wall_hex in ('#f2efe6', '#ece3cf'):
        B.zoc_col = srgb(rnd.choice(PAL_ZOC_WHITE))
    else:
        B.zoc_col = shade(B.wall_col, 0.45) if rnd.random() < 0.6 else srgb(rnd.choice(PAL_ZOC_WHITE))
    B.wood_col = srgb(wpick(rnd, PAL_WOOD))
    B.has_trim = rnd.random() < 0.6
    B.trim_col = srgb('#f4f1ea') if rnd.random() < 0.6 else shade(B.wall_col, 0.6)
    B.has_zoc = rnd.random() < 0.88
    B.zoc_h = rnd.uniform(0.7, 1.1)
    B.mural = any(B.ped) and rnd.random() < 0.5 and B.kind == 'colonial'
    B.style_up = wpick(rnd, [('balc', 5), ('corr', 2), ('vent', 3)])
    B.wu = rnd.uniform(1.0, 1.2)
    B.bars = wpick(rnd, [('madera', 5), ('hierro', 3), ('none', 2)])
    B.pies = rnd.random() < 0.45
    B.ov = 0.75 if (B.lv >= 2 and B.style_up in ('balc', 'corr')) else 0.55
    B.culata = mixc(B.wall_col, srgb('#b3a898'), 0.65) if rnd.random() < 0.6 else srgb('#9c6a54')
    st = [i for i in range(n) if B.street[i]]
    B.main_edge = max(st, key=lambda i: elen[i]) if st else -1
    B.area = A
    if B.kind == 'moderno':
        B.wall_col = srgb(rnd.choice(['#b9b4aa', '#a39b90', '#c9c2b4', '#9a5f4a']))
        B.zoc_col = shade(B.wall_col, 0.6)
        B.has_trim = False
        B.mural = False
        B.style_up = 'vent'
        B.wu = 1.7
        B.bars = 'none'
        B.ov = 0.0
    if B.kind == 'ermita':
        B.wall_col = srgb('#f6f4ee')
        B.zoc_col = srgb('#8d877c')
        B.wood_col = srgb('#4a2f1c')
        B.has_zoc = True
        B.zoc_h = 0.8
        B.mural = False
        B.wall_top = B.base + 5.4
        B.tanp = 0.6
        B.ov = 0.5
        B.has_trim = False
    B.wa = max(0.05, min(1.0, (B.wall_top - B.base) / 20.0))
    # segmentos libres (definen las aguas del techo)
    F = []
    NIN = []
    SH = []
    for i in range(n):
        a = ring[i]
        c = ring[(i + 1) % n]
        L = elen[i]
        if L < 1e-6:
            continue
        if B.free[i] and B.kind != 'moderno':
            F.append((a[0], a[1], c[0], c[1]))
            NIN.append((-(c[1] - a[1]) / L, (c[0] - a[0]) / L))
        else:
            SH.append((a[0], a[1], c[0], c[1]))
    B.holes = []
    good = []
    for pr in B.patios:
        if ring_area(pr) < 0:
            pr = pr[::-1]
        hl = offset_ring(pr, [-0.4] * len(pr))
        hole = [p for l in hl for p in l]
        if len(hole) < 3 or ring_area(hole) < 3.0:
            hole = list(pr) if ring_area(pr) >= 6.0 else None
        if hole is None:
            continue
        good.append(pr)
        B.holes.append(hole)
        for i in range(len(pr)):
            a = pr[i]
            c = pr[(i + 1) % len(pr)]
            L = math.hypot(c[0] - a[0], c[1] - a[1])
            if L < 1e-6:
                continue
            F.append((a[0], a[1], c[0], c[1]))
            NIN.append(((c[1] - a[1]) / L, -(c[0] - a[0]) / L))
    B.patios = good
    B.F = F
    B.NIN = NIN
    B.SH = SH
    Fx = []
    for (ax, ay, bx_, by_) in F:
        L = math.hypot(bx_ - ax, by_ - ay)
        ux, uy = (bx_ - ax) / L, (by_ - ay) / L
        e = B.ov + 0.05
        Fx.append((ax - ux * e, ay - uy * e, bx_ + ux * e, by_ + uy * e))
    B.Fx = Fx
    B.uoff = [rnd.uniform(0, 5) for _ in F]
    return B


def roof_h(B, P):
    """Altura del techo sobre la cabeza del muro, indice del agua mas cercana y distancia con signo."""
    N = len(P)
    if not B.F:
        return np.full(N, B.D * B.tanp), np.zeros(N, dtype=int), np.full(N, B.D)
    d = seg_dist_np(P, B.F)
    k = d.argmin(axis=1)
    dm = d[np.arange(N), k]
    ins = pip_np(P, B.ring)
    if B.SH:
        ins |= seg_dist_np(P, B.SH).min(axis=1) < 0.02
    for pr in B.patios:
        ins &= ~pip_np(P, pr)
    out = ~ins
    if out.any():
        dx_ = seg_dist_np(P[out], B.Fx)
        k2 = dx_.argmin(axis=1)
        dm[out] = -dx_[np.arange(len(k2)), k2]
        k[out] = k2
    Dd = B.D
    x = np.maximum(dm - Dd, 0.0)
    tri = Dd - np.abs((x % (2 * Dd)) - Dd)
    hh = np.where(dm <= Dd, dm, Dd - 0.5 * tri)
    return B.tanp * hh, k, dm


def make_roof(B, RB, CBm):
    ring = B.ring
    n = B.n
    rnd = B.rnd
    tint = rnd.uniform(0.78, 1.08)
    tcol = (tint, tint * rnd.uniform(0.94, 1.0), tint * rnd.uniform(0.9, 1.0), 1.0)
    wood_dark = shade(srgb('#4a3626'), rnd.uniform(0.7, 1.1))
    if B.kind == 'moderno':
        pts, tris = tri_poly([ring], 3.0)
        z = B.wall_top
        gcol = srgb('#77736c')
        for a, b, c in tris:
            RB.face([(pts[a][0], pts[a][1], z), (pts[b][0], pts[b][1], z), (pts[c][0], pts[c][1], z)], MAT['fa'], gcol,
                    [(pts[a][0], 3.0), (pts[b][0], 3.0), (pts[c][0], 3.0)])
        return
    offs = [B.ov if B.free[i] else 0.0 for i in range(n)]
    ol = offset_ring(ring, offs)
    oring = [p for l in ol for p in l]
    if len(oring) < 3 or ring_area(oring) < ring_area(ring) * 0.95:
        ol = [[p] for p in ring]
        oring = list(ring)
    rings = [oring]
    for hl_ in B.holes:
        rings.append(hl_)
    # puntos estructurales: linea de cumbrera (distancia D) y limatesas
    extra = []
    eedges = []
    ekind = []
    seen = set()
    D = B.D

    def add_line(cands, expect, kind='cumbrera'):
        if not cands:
            return
        Pc = np.asarray(cands)
        h, k, sd = roof_h(B, Pc)
        prev = None
        for j in range(len(cands)):
            ok = abs(sd[j] - expect[j]) < 0.04
            if ok:
                key = (round(cands[j][0] / 0.3), round(cands[j][1] / 0.3))
                if key in seen:
                    prev = None
                    continue
                seen.add(key)
                extra.append(cands[j])
                idx = len(extra) - 1
                if prev is not None:
                    eedges.append((prev, idx))
                    ekind.append(kind)
                prev = idx
            else:
                prev = None

    nmult = max(1, min(7, int(math.sqrt(B.area) * 0.75 / D)))
    for (ax, ay, bx_, by_), (ix, iy) in zip(B.F, B.NIN):
        L = math.hypot(bx_ - ax, by_ - ay)
        kk = max(1, int(math.ceil(L / 0.8)))
        for mlt in range(1, nmult + 1):
            c = [(ax + (bx_ - ax) * j / kk + ix * D * mlt, ay + (by_ - ay) * j / kk + iy * D * mlt) for j in range(kk + 1)]
            add_line(c, [D * mlt] * len(c), 'cumbrera' if mlt % 2 == 1 else 'valle')
    for i in range(n):
        if B.free[i - 1] and B.free[i] and B.elen[i - 1] > 0.5 and B.elen[i] > 0.5:
            p = ring[i]
            a = ring[i - 1]
            c = ring[(i + 1) % n]
            n1 = (-(p[1] - a[1]) / B.elen[i - 1], (p[0] - a[0]) / B.elen[i - 1])
            n2 = (-(c[1] - p[1]) / B.elen[i], (c[0] - p[0]) / B.elen[i])
            if n1[0] * n2[0] + n1[1] * n2[1] > 0.9:
                continue
            hx, hy = n1[0] + n2[0], n1[1] + n2[1]
            hl = math.hypot(hx, hy)
            if hl < 0.3:
                continue
            hx, hy = hx / hl, hy / hl
            cc = hx * n1[0] + hy * n1[1]
            if cc < 0.2:
                continue
            smax = D / cc
            ss = []
            s = 0.45
            while s < smax - 0.2:
                ss.append(s)
                s += 0.75
            cands = [(p[0] + hx * s, p[1] + hy * s) for s in ss]
            add_line(cands, [s * cc for s in ss], 'limatesa')
    pts, tris = tri_poly(rings, 0.9, grid=0.9, extra=extra, extra_edges=eedges, margin=0.3)
    if not tris:
        return
    P = np.asarray(pts)
    h, k, sd = roof_h(B, P)
    Z = B.wall_top + h
    TR = np.asarray(tris, dtype=int)
    Cn = (P[TR[:, 0]] + P[TR[:, 1]] + P[TR[:, 2]]) / 3.0
    hc, kc, sdc = roof_h(B, Cn)
    if B.F:
        Fa = np.asarray(B.F)
        Na = np.asarray(B.NIN)
        Ua = np.asarray(B.uoff)
        seg = Fa[kc]
        nin = Na[kc]
        tdx = nin[:, 1]
        tdy = -nin[:, 0]
        uvs = []
        for j in range(3):
            pj = P[TR[:, j]]
            rx = pj[:, 0] - seg[:, 0]
            ry = pj[:, 1] - seg[:, 1]
            uvs.append(np.stack([rx * tdx + ry * tdy + Ua[kc], rx * nin[:, 0] + ry * nin[:, 1] + 3.0], axis=1))
    else:
        uvs = [P[TR[:, j]] for j in range(3)]
    for t in range(len(TR)):
        a, b, c = TR[t]
        RB.face([(pts[a][0], pts[a][1], float(Z[a])), (pts[b][0], pts[b][1], float(Z[b])), (pts[c][0], pts[c][1], float(Z[c]))],
                MAT['te'], tcol,
                [(float(uvs[0][t][0]), float(uvs[0][t][1])), (float(uvs[1][t][0]), float(uvs[1][t][1])), (float(uvs[2][t][0]), float(uvs[2][t][1]))])
    # caballetes sobre cumbreras y limatesas
    if extra and eedges:
        Ex = np.asarray(extra)
        he, _, _ = roof_h(B, Ex)
        zx = B.wall_top + he
        capc = (min(1.2, tcol[0] * 1.1), min(1.2, tcol[1] * 1.06), min(1.2, tcol[2] * 1.02), 1.0)
        for (ia, ib), kd in zip(eedges, ekind):
            if kd == 'valle':
                continue
            ax_, ay_ = extra[ia]
            bx2, by2 = extra[ib]
            l = math.hypot(bx2 - ax_, by2 - ay_)
            if l < 0.05:
                continue
            px, py = -(by2 - ay_) / l * 0.15, (bx2 - ax_) / l * 0.15
            za = float(zx[ia])
            zb = float(zx[ib])
            a0, a1, a2 = (ax_ - px, ay_ - py, za - 0.03), (ax_, ay_, za + 0.1), (ax_ + px, ay_ + py, za - 0.03)
            b0, b1, b2 = (bx2 - px, by2 - py, zb - 0.03), (bx2, by2, zb + 0.1), (bx2 + px, by2 + py, zb - 0.03)
            RB.face([a1, b1, b0, a0], MAT['te'], capc, [(0, 3.18), (l, 3.18), (l, 3.0), (0, 3.0)])
            RB.face([a2, b2, b1, a1], MAT['te'], capc, [(0, 3.0), (l, 3.0), (l, 3.18), (0, 3.18)])
    # frente del alero (tabla)
    ze = B.wall_top - B.ov * B.tanp
    for i in range(n):
        if not B.free[i]:
            continue
        p0 = ol[i][-1]
        p1 = ol[(i + 1) % n][0]
        CBm.face([(p0[0], p0[1], ze - 0.13), (p1[0], p1[1], ze - 0.13), (p1[0], p1[1], ze + 0.005), (p0[0], p0[1], ze + 0.005)],
                 MAT['ma'], wood_dark)
        # entablado bajo el alero
        a = ring[i]
        c = ring[(i + 1) % n]
        zt = B.wall_top - 0.025
        CBm.face([(a[0], a[1], zt), (c[0], c[1], zt), (p1[0], p1[1], ze - 0.025), (p0[0], p0[1], ze - 0.025)], MAT['ma'], shade(wood_dark, 1.5))
    for hole_ in B.holes:
        zh = B.wall_top - 0.4 * B.tanp
        m = len(hole_)
        for i in range(m):
            p0 = hole_[i]
            p1 = hole_[(i + 1) % m]
            CBm.face([(p0[0], p0[1], zh - 0.13), (p1[0], p1[1], zh - 0.13), (p1[0], p1[1], zh + 0.005), (p0[0], p0[1], zh + 0.005)],
                     MAT['ma'], wood_dark)


def plain_wall(B, WB, i, col):
    ring = B.ring
    a = ring[i]
    c = ring[(i + 1) % B.n]
    L = B.elen[i]
    if L < 1e-4:
        return
    tx, ty = (c[0] - a[0]) / L, (c[1] - a[1]) / L
    ix, iy = -ty, tx  # hacia adentro
    col = (col[0], col[1], col[2], B.wa)
    extra_h = 0.9 if B.kind == 'moderno' else 0.0
    if B.free[i] or B.kind == 'moderno':
        us = [0.0, L]
        hs = [extra_h, extra_h]
    else:
        k = max(1, int(math.ceil(L / 0.9)))
        us = [L * j / k for j in range(k + 1)]
        Pn = np.asarray([(a[0] + tx * u + ix * 0.03, a[1] + ty * u + iy * 0.03) for u in us])
        h, _, _ = roof_h(B, Pn)
        hs = [max(0.0, float(v)) for v in h]
    for j in range(len(us) - 1):
        u0, u1 = us[j], us[j + 1]
        p0 = (a[0] + tx * u0, a[1] + ty * u0)
        p1 = (a[0] + tx * u1, a[1] + ty * u1)
        WB.face([(p0[0], p0[1], B.zbot), (p1[0], p1[1], B.zbot), (p1[0], p1[1], B.wall_top + hs[j + 1]), (p0[0], p0[1], B.wall_top + hs[j])],
                MAT['fa'], col,
                [(u0, B.zbot - B.base), (u1, B.zbot - B.base), (u1, B.wall_top + hs[j + 1] - B.base), (u0, B.wall_top + hs[j] - B.base)])


def make_patio(B, WB, CBm, pr):
    m = len(pr)
    zf = B.base + 0.03
    col = mixc(B.wall_col, WHITE, 0.4)
    col = (col[0], col[1], col[2], B.wa)
    for i in range(m):
        a = pr[i]
        c = pr[(i + 1) % m]
        L = math.hypot(c[0] - a[0], c[1] - a[1])
        if L < 1e-4:
            continue
        WB.face([(c[0], c[1], zf - 0.2), (a[0], a[1], zf - 0.2), (a[0], a[1], B.wall_top), (c[0], c[1], B.wall_top)], MAT['fa'], col,
                [(0, -0.2), (L, -0.2), (L, B.wall_top - B.base), (0, B.wall_top - B.base)])
        # pies derechos del corredor
        tx, ty = (c[0] - a[0]) / L, (c[1] - a[1]) / L
        ox, oy = -ty, tx  # hacia el centro del patio (anillo CCW)
        k = max(1, int(L / 2.6))
        zt = B.wall_top - 0.36 * B.tanp - 0.1
        for j in range(k + 1):
            u = L * j / k
            px, py = a[0] + tx * u + ox * 0.3, a[1] + ty * u + oy * 0.3
            CBm.box((px - 0.07 * tx - 0.07 * ox, py - 0.07 * ty - 0.07 * oy, zf), (tx * 0.14, ty * 0.14, 0), (ox * 0.14, oy * 0.14, 0), (0, 0, zt - zf),
                    MAT['ma'], B.wood_col, 'zZ')
    pts, tris = tri_poly([pr], 3.0)
    for a, b, c in tris:
        WB.face([(pts[a][0], pts[a][1], zf), (pts[b][0], pts[b][1], zf), (pts[c][0], pts[c][1], zf)], MAT['lo'], WHITE)


def facade(B, i, WB, CBm):
    rnd = B.rnd
    a = B.ring[i]
    c = B.ring[(i + 1) % B.n]
    L = B.elen[i]
    tx, ty = (c[0] - a[0]) / L, (c[1] - a[1]) / L
    nx, ny = ty, -tx
    base = B.base
    wt = B.wall_top
    lv = B.lv
    mod = B.kind == 'moderno'

    def P3(u, z, o=0.0):
        return (a[0] + tx * u + nx * o, a[1] + ty * u + ny * o, z)

    def g(u):
        return T(a[0] + tx * u, a[1] + ty * u) + CURB

    def bx(mb, u0, u1, z0, z1, d0, d1, mat, col, skip=''):
        mb.box(P3(u0, z0, d0), (tx * (u1 - u0), ty * (u1 - u0), 0.0), (nx * (d1 - d0), ny * (d1 - d0), 0.0), (0.0, 0.0, z1 - z0), mat, col, skip)

    F1 = base + B.H1
    ops = []
    mg = 0.55
    usable = L - 2 * mg
    nb = 0
    pitch = 0.0
    if usable >= 1.3:
        bw = rnd.uniform(3.4, 4.2) if mod else rnd.uniform(2.5, 3.3)
        nb = max(1, int(usable / bw + 0.5))
        pitch = usable / nb
        centers = [mg + pitch * (j + 0.5) for j in range(nb)]
        lim0 = (F1 - 0.35) if lv > 1 else (wt - 0.5)
        main_bay = rnd.randrange(nb) if i == B.main_edge else -1
        for j, uc in enumerate(centers):
            kind = 'win'
            if j == main_bay:
                kind = 'porton' if (B.area > 180 and pitch >= 2.7 and not mod) else 'door'
            elif rnd.random() < (0.34 if B.ped[i] else 0.2):
                kind = 'door'
            if B.kind == 'ermita':
                kind = 'porton' if (nb == 1 or j == nb // 2) else 'none'
            if kind == 'none':
                continue
            if kind in ('door', 'porton'):
                w = rnd.uniform(1.9, 2.3) if kind == 'porton' else rnd.uniform(1.15, 1.45)
                w = min(w, pitch - 0.5)
                u0, u1 = uc - w / 2, uc + w / 2
                gz = max(g(u0), g(u1)) + 0.02
                hh = min(3.0 if kind == 'porton' else rnd.uniform(2.35, 2.65), lim0 - gz)
                if B.kind == 'ermita':
                    hh = 3.3
                if hh < 1.9:
                    kind = 'win'
                else:
                    ops.append({'u0': u0, 'u1': u1, 'z0': gz, 'z1': gz + hh, 'kind': kind, 'fl': 0})
            if kind == 'win':
                w = min(rnd.uniform(1.5, 2.0) if mod else rnd.uniform(0.95, 1.2), pitch - 0.5)
                u0, u1 = uc - w / 2, uc + w / 2
                gz = max(g(u0), g(u1))
                z0 = gz + rnd.uniform(0.95, 1.1)
                z1 = min(z0 + rnd.uniform(1.45, 1.7), lim0)
                if z1 - z0 >= 0.9:
                    ops.append({'u0': u0, 'u1': u1, 'z0': z0, 'z1': z1, 'kind': 'win', 'fl': 0})
        for kf in range(1, lv):
            Fk = F1 + B.HU * (kf - 1)
            limk = (Fk + B.HU - 0.35) if kf < lv - 1 else (wt - 0.5)
            for j, uc in enumerate(centers):
                w = min(B.wu, pitch - 0.5)
                u0, u1 = uc - w / 2, uc + w / 2
                if B.style_up in ('balc', 'corr') and not mod:
                    if B.style_up == 'balc' and rnd.random() < 0.18:
                        continue
                    z0 = Fk + 0.12
                    z1 = min(Fk + 2.4, limk)
                    ops.append({'u0': u0, 'u1': u1, 'z0': z0, 'z1': z1, 'kind': 'french', 'fl': kf, 'F': Fk})
                else:
                    if rnd.random() < 0.1:
                        continue
                    z0 = Fk + 0.9
                    z1 = min(Fk + (2.2 if mod else 2.35), limk)
                    if z1 - z0 >= 0.8:
                        ops.append({'u0': u0, 'u1': u1, 'z0': z0, 'z1': z1, 'kind': 'winup', 'fl': kf, 'F': Fk})

    # ---------------- muro con vanos
    zz = (max(g(0.0), g(L)) + B.zoc_h) if B.has_zoc else None
    us = sorted(set([0.0, L] + [o['u0'] for o in ops] + [o['u1'] for o in ops]))
    for k in range(len(us) - 1):
        ua, ub = us[k], us[k + 1]
        if ub - ua < 1e-4:
            continue
        cuts = sorted((o['z0'], o['z1']) for o in ops if o['u0'] - 1e-6 <= ua and o['u1'] + 1e-6 >= ub)
        z = B.zbot
        spans = []
        for z0, z1 in cuts:
            if z0 > z:
                spans.append((z, z0))
            z = max(z, z1)
        if z < wt:
            spans.append((z, wt))
        for za, zb in spans:
            parts = [(za, zb)]
            if zz is not None and za < zz < zb:
                parts = [(za, zz), (zz, zb)]
            for pa, pb in parts:
                isz = zz is not None and pb <= zz + 1e-6
                col = B.zoc_col if isz else B.wall_col
                col = (col[0], col[1], col[2], B.wa)
                mat = MAT['mu'] if (B.mural and B.ped[i] and not isz) else MAT['fa']
                WB.face([P3(ua, pa), P3(ub, pa), P3(ub, pb), P3(ua, pb)], mat, col,
                        [(ua, pa - base), (ub, pa - base), (ub, pb - base), (ua, pb - base)])

    wood = B.wood_col
    wood_d = shade(wood, 0.7)
    wood_l = mixc(wood, WHITE, 0.05)
    rev_col = shade(B.wall_col, 0.8)
    dark = (0.01, 0.01, 0.012, 1.0)

    def reveal(o):
        u0, u1, z0, z1 = o['u0'], o['u1'], o['z0'], o['z1']
        d = -DR
        uvq = [(0, 4.0), (DR, 4.0), (DR, 6.0), (0, 6.0)]
        WB.face([P3(u0, z0), P3(u0, z0, d), P3(u0, z1, d), P3(u0, z1)], MAT['fa'], rev_col, uvq)
        WB.face([P3(u1, z0, d), P3(u1, z0), P3(u1, z1), P3(u1, z1, d)], MAT['fa'], rev_col, uvq)
        WB.face([P3(u0, z1), P3(u0, z1, d), P3(u1, z1, d), P3(u1, z1)], MAT['fa'], rev_col, uvq)
        WB.face([P3(u0, z0, d), P3(u0, z0), P3(u1, z0), P3(u1, z0, d)], MAT['fa'], rev_col, uvq)
        WB.face([P3(u0, z0, d), P3(u1, z0, d), P3(u1, z1, d), P3(u0, z1, d)], MAT['fa'], dark, uvq)

    def trim(o, bottom=False):
        if not B.has_trim:
            return
        u0, u1, z0, z1 = o['u0'], o['u1'], o['z0'], o['z1']
        tw = 0.14
        zb = z0 - (tw if bottom else 0.0)
        bx(WB, u0 - tw, u0, zb, z1 + tw, 0.0, 0.025, MAT['pt'], B.trim_col, 'y')
        bx(WB, u1, u1 + tw, zb, z1 + tw, 0.0, 0.025, MAT['pt'], B.trim_col, 'y')
        bx(WB, u0, u1, z1, z1 + tw, 0.0, 0.025, MAT['pt'], B.trim_col, 'y')
        if bottom:
            bx(WB, u0, u1, zb, z0, 0.0, 0.025, MAT['pt'], B.trim_col, 'y')

    def glazed(u0, u1, z0, z1, d, nv=1, nh=2, fw=0.06):
        """Marco + vidrio + palillaje en la profundidad d (cara exterior)."""
        bx(CBm, u0, u0 + fw, z0, z1, d - 0.07, d, MAT['ma'], wood)
        bx(CBm, u1 - fw, u1, z0, z1, d - 0.07, d, MAT['ma'], wood)
        bx(CBm, u0 + fw, u1 - fw, z1 - fw, z1, d - 0.07, d, MAT['ma'], wood)
        bx(CBm, u0 + fw, u1 - fw, z0, z0 + fw, d - 0.07, d, MAT['ma'], wood)
        CBm.face([P3(u0 + fw, z0 + fw, d - 0.04), P3(u1 - fw, z0 + fw, d - 0.04), P3(u1 - fw, z1 - fw, d - 0.04), P3(u0 + fw, z1 - fw, d - 0.04)],
                 MAT['vi'], WHITE)
        for q in range(1, nv + 1):
            um = u0 + fw + (u1 - u0 - 2 * fw) * q / (nv + 1)
            bx(CBm, um - 0.018, um + 0.018, z0 + fw, z1 - fw, d - 0.045, d - 0.015, MAT['ma'], wood, 'zZ')
        for q in range(1, nh + 1):
            zm = z0 + fw + (z1 - z0 - 2 * fw) * q / (nh + 1)
            bx(CBm, u0 + fw, u1 - fw, zm - 0.015, zm + 0.015, d - 0.045, d - 0.018, MAT['ma'], wood, 'xX')

    def door(o):
        u0, u1, z0, z1 = o['u0'], o['u1'], o['z0'], o['z1']
        big = o['kind'] == 'porton'
        fw = 0.12 if big else 0.09
        d = -DR
        bx(CBm, u0, u0 + fw, z0, z1, d, d + 0.12, MAT['ma'], wood_d)
        bx(CBm, u1 - fw, u1, z0, z1, d, d + 0.12, MAT['ma'], wood_d)
        bx(CBm, u0 + fw, u1 - fw, z1 - fw, z1, d, d + 0.12, MAT['ma'], wood_d)
        um = (u0 + u1) / 2
        for (la, lb) in ((u0 + fw, um - 0.006), (um + 0.006, u1 - fw)):
            bx(CBm, la, lb, z0 + 0.015, z1 - fw, d + 0.02, d + 0.07, MAT['ma'], wood)
            npan = 3 if big else 2
            hz = (z1 - fw - z0 - 0.015)
            for q in range(npan):
                pa = z0 + 0.015 + hz * q / npan + 0.09
                pb = z0 + 0.015 + hz * (q + 1) / npan - 0.09
                bx(CBm, la + 0.08, lb - 0.08, pa, pb, d + 0.07, d + 0.092, MAT['ma'], wood_l, 'y')
                if big:
                    for su in (la + 0.045, lb - 0.045):
                        for sz in (pa - 0.045, (pa + pb) / 2, pb + 0.045):
                            bx(CBm, su - 0.018, su + 0.018, sz - 0.018, sz + 0.018, d + 0.07, d + 0.1, MAT['hi'], WHITE, 'y')
        # umbral de piedra
        gl = min(g(u0), g(u1))
        bx(WB, u0 - 0.06, u1 + 0.06, gl - 0.12, z0, -DR, 0.24, MAT['pi'], WHITE, 'y')

    def window_ground(o):
        u0, u1, z0, z1 = o['u0'], o['u1'], o['z0'], o['z1']
        glazed(u0, u1, z0, z1, -0.13, 1, 2)
        # repisa
        bx(WB, u0 - 0.1, u1 + 0.1, z0 - 0.08, z0, -0.05, 0.11, MAT['pt'], B.trim_col if B.has_trim else rev_col)
        if mod:
            return
        if B.bars == 'madera':
            w = u1 - u0
            nbar = max(3, int(w / 0.125))
            for q in range(1, nbar):
                ub_ = u0 + w * q / nbar
                bx(CBm, ub_ - 0.017, ub_ + 0.017, z0, z1, -0.06, -0.026, MAT['ma'], wood_d, 'zZ')
            zm = (z0 + z1) / 2
            bx(CBm, u0, u1, zm - 0.025, zm + 0.025, -0.07, -0.02, MAT['ma'], wood_d, 'xX')
        elif B.bars == 'hierro':
            w = u1 - u0
            for zr in (z0 + 0.04, z1 - 0.07):
                bx(CBm, u0 - 0.04, u1 + 0.04, zr, zr + 0.03, 0.0, 0.16, MAT['hi'], WHITE)
            nbar = max(4, int((w + 0.08) / 0.11))
            for q in range(nbar + 1):
                ub_ = u0 - 0.04 + (w + 0.08) * q / nbar
                bx(CBm, ub_ - 0.008, ub_ + 0.008, z0 + 0.04, z1 - 0.04, 0.142, 0.158, MAT['hi'], WHITE, 'zZ')
        else:
            # postigos abiertos
            w = (u1 - u0) / 2
            if pitch - (u1 - u0) > 2 * w + 0.3:
                bx(CBm, u0 - w - 0.03, u0 - 0.03, z0, z1, 0.0, 0.035, MAT['ma'], wood, 'y')
                bx(CBm, u1 + 0.03, u1 + w + 0.03, z0, z1, 0.0, 0.035, MAT['ma'], wood, 'y')

    def window_up(o):
        u0, u1, z0, z1 = o['u0'], o['u1'], o['z0'], o['z1']
        glazed(u0, u1, z0, z1, -0.13, 2 if mod else 1, 1 if mod else 2)
        bx(WB, u0 - 0.1, u1 + 0.1, z0 - 0.08, z0, -0.05, 0.11, MAT['pt'], B.trim_col if B.has_trim else rev_col)
        if not mod and rnd.random() < 0.35:
            w = (u1 - u0) / 2
            if pitch - (u1 - u0) > 2 * w + 0.3:
                bx(CBm, u0 - w - 0.03, u0 - 0.03, z0, z1, 0.0, 0.035, MAT['ma'], wood, 'y')
                bx(CBm, u1 + 0.03, u1 + w + 0.03, z0, z1, 0.0, 0.035, MAT['ma'], wood, 'y')

    def french(o):
        u0, u1, z0, z1 = o['u0'], o['u1'], o['z0'], o['z1']
        d = -0.14
        um = (u0 + u1) / 2
        bx(CBm, u0, u0 + 0.06, z0, z1, d - 0.08, d, MAT['ma'], wood_d)
        bx(CBm, u1 - 0.06, u1, z0, z1, d - 0.08, d, MAT['ma'], wood_d)
        bx(CBm, u0 + 0.06, u1 - 0.06, z1 - 0.06, z1, d - 0.08, d, MAT['ma'], wood_d)
        for (la, lb) in ((u0 + 0.06, um - 0.004), (um + 0.004, u1 - 0.06)):
            zp = z0 + 0.72
            bx(CBm, la, lb, z0, zp, d - 0.06, d - 0.01, MAT['ma'], wood)
            bx(CBm, la + 0.07, lb - 0.07, z0 + 0.1, zp - 0.1, d - 0.01, d + 0.008, MAT['ma'], wood_l, 'y')
            glazed(la, lb, zp, z1 - 0.06, d - 0.01, 0, 2, 0.05)

    def balcony(bu0, bu1, Fk, top, posts_u):
        bd = 0.6
        bx(CBm, bu0, bu1, Fk - 0.06, Fk + 0.02, 0.0, bd, MAT['ma'], wood_d)
        nbr = max(2, int((bu1 - bu0) / 0.9) + 1)
        for q in range(nbr):
            ub_ = bu0 + 0.08 + (bu1 - bu0 - 0.16) * q / (nbr - 1)
            bx(CBm, ub_ - 0.05, ub_ + 0.05, Fk - 0.19, Fk - 0.06, 0.0, bd - 0.05, MAT['ma'], wood_d, 'Z')
        zr0, zr1 = Fk + 0.13, Fk + 0.96
        for (za, zb) in ((zr0 - 0.04, zr0), (zr1, zr1 + 0.05)):
            bx(CBm, bu0, bu1, za, zb, bd - 0.06, bd, MAT['ma'], wood)
            bx(CBm, bu0, bu0 + 0.06, za, zb, 0.0, bd - 0.06, MAT['ma'], wood)
            bx(CBm, bu1 - 0.06, bu1, za, zb, 0.0, bd - 0.06, MAT['ma'], wood)
        nbal = max(2, int((bu1 - bu0 - 0.12) / 0.115))
        for q in range(1, nbal):
            ub_ = bu0 + 0.06 + (bu1 - bu0 - 0.12) * q / nbal
            bx(CBm, ub_ - 0.016, ub_ + 0.016, zr0, zr1, bd - 0.046, bd - 0.014, MAT['ma'], wood_l, 'zZ')
        nsd = max(2, int((bd - 0.06) / 0.115))
        for q in range(1, nsd + 1):
            dq = (bd - 0.06) * q / (nsd + 1)
            bx(CBm, bu0 + 0.014, bu0 + 0.046, zr0, zr1, dq - 0.016, dq + 0.016, MAT['ma'], wood_l, 'zZ')
            bx(CBm, bu1 - 0.046, bu1 - 0.014, zr0, zr1, dq - 0.016, dq + 0.016, MAT['ma'], wood_l, 'zZ')
        if rnd.random() < 0.6:
            npl = max(1, int((bu1 - bu0) / 1.25))
            terr = srgb('#a6583a')
            for q in range(npl):
                if rnd.random() < 0.3:
                    continue
                pw = rnd.uniform(0.5, 0.8)
                span = max(0.05, (bu1 - bu0 - 0.3 - pw))
                pu0 = bu0 + 0.15 + span * (q + rnd.random() * 0.7) / npl
                bx(CBm, pu0, pu0 + pw, zr1 - 0.3, zr1 - 0.1, bd, bd + 0.2, MAT['pt'], terr)
                bx(CBm, pu0 - 0.04, pu0 + pw + 0.04, zr1 - 0.12, zr1 + 0.13, bd - 0.03, bd + 0.25, MAT['ho'], WHITE)
                fc = srgb(rnd.choice(FLORES))
                nfl = max(4, int(pw / 0.085))
                for k3 in range(nfl):
                    fu0 = pu0 + (pw - 0.06) * k3 / nfl + rnd.uniform(0, 0.02)
                    fd = bd + rnd.uniform(0.0, 0.17)
                    fz = zr1 + rnd.uniform(0.09, 0.15)
                    bx(CBm, fu0, fu0 + 0.055, fz, fz + 0.05, fd, fd + 0.055, MAT['pt'], fc if rnd.random() < 0.8 else srgb(rnd.choice(FLORES)), 'z')
        ztop = (wt - (bd - 0.03) * B.tanp - 0.14) if (top and B.pies) else (zr1 + 0.05)
        for pu in posts_u:
            bx(CBm, pu - 0.035, pu + 0.035, Fk + 0.02, ztop, bd - 0.07, bd, MAT['ma'], wood, 'z')

    for o in ops:
        reveal(o)
        if o['kind'] in ('door', 'porton'):
            door(o)
            trim(o)
        elif o['kind'] == 'win':
            window_ground(o)
            trim(o, True)
        elif o['kind'] == 'winup':
            window_up(o)
            trim(o, True)
        elif o['kind'] == 'french':
            french(o)
            trim(o)
    # balcones
    for kf in range(1, lv):
        fr = [o for o in ops if o['kind'] == 'french' and o['fl'] == kf]
        if not fr:
            continue
        top = kf == lv - 1
        Fk = fr[0]['F']
        if B.style_up == 'corr' and len(fr) >= 2:
            bu0 = max(0.12, fr[0]['u0'] - 0.5)
            bu1 = min(L - 0.12, fr[-1]['u1'] + 0.5)
            pu = [bu0 + 0.035, bu1 - 0.035]
            for q in range(len(fr) - 1):
                pu.append((fr[q]['u1'] + fr[q + 1]['u0']) / 2)
            balcony(bu0, bu1, Fk, top, pu)
        else:
            for o in fr:
                bu0 = max(0.08, o['u0'] - 0.42)
                bu1 = min(L - 0.08, o['u1'] + 0.42)
                balcony(bu0, bu1, Fk, top, [bu0 + 0.035, bu1 - 0.035])

    if mod:
        return
    # canecillos bajo el alero
    ovr = B.ov - 0.06
    raf_col = shade(srgb('#4a3626'), 0.9)
    nr = max(1, int((L - 0.3) / 0.6))
    for q in range(nr + 1):
        u = 0.15 + (L - 0.3) * q / nr
        o3 = P3(u - 0.035, wt - 0.135, 0.0)
        CBm.box(o3, (tx * 0.07, ty * 0.07, 0.0), (nx * ovr, ny * ovr, -ovr * B.tanp), (0.0, 0.0, 0.1), MAT['ma'], raf_col, 'y')
    # faroles
    if nb >= 2 and L >= 6.5 and B.kind != 'ermita':
        step = max(1, int(round(12.0 / pitch)))
        j = 1 + rnd.randrange(max(1, min(step, nb - 1)))
        while j < nb:
            u = mg + pitch * j
            gz = g(u)
            z = min(gz + 3.0, (F1 - 0.85) if lv > 1 else (wt - 0.85))
            if z - gz > 2.0:
                bx(CBm, u - 0.015, u + 0.015, z + 0.3, z + 0.33, 0.0, 0.42, MAT['hi'], WHITE)
                bx(CBm, u - 0.01, u + 0.01, z + 0.25, z + 0.3, 0.37, 0.39, MAT['hi'], WHITE, 'zZ')
                bx(CBm, u - 0.11, u + 0.11, z + 0.22, z + 0.25, 0.27, 0.49, MAT['hi'], WHITE)
                bx(CBm, u - 0.085, u + 0.085, z - 0.03, z + 0.22, 0.295, 0.465, MAT['fl'], WHITE, 'zZ')
                bx(CBm, u - 0.07, u + 0.07, z - 0.06, z - 0.03, 0.31, 0.45, MAT['hi'], WHITE)
            j += step
    return ops


def make_skylight(B, RB, CBm, hole):
    m = len(hole)
    cx = sum(p[0] for p in hole) / m
    cy = sum(p[1] for p in hole) / m
    z0 = B.wall_top - 0.4 * B.tanp + 0.14
    z1 = z0 + 0.95
    for i in range(m):
        p0 = hole[i]
        p1 = hole[(i + 1) % m]
        l = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        if l < 0.05:
            continue
        RB.face([(p0[0], p0[1], z0), (p1[0], p1[1], z0), (cx, cy, z1)], MAT['vc'], WHITE)
        dx_, dy_ = (p1[0] - p0[0]) / l, (p1[1] - p0[1]) / l
        CBm.box((p0[0], p0[1], z0 - 0.1), (dx_ * l, dy_ * l, 0.0), (-dy_ * 0.06, dx_ * 0.06, 0.0), (0.0, 0.0, 0.12), MAT['hi'], WHITE)
        lr = math.hypot(cx - p0[0], cy - p0[1])
        if lr > 0.1:
            rx, ry = (cx - p0[0]) / lr, (cy - p0[1]) / lr
            CBm.box((p0[0], p0[1], z0 - 0.01), (cx - p0[0], cy - p0[1], z1 - z0), (-ry * 0.04, rx * 0.04, 0.0), (0.0, 0.0, 0.05), MAT['hi'], WHITE)


def make_espadana(B, WB, RB, CBm):
    """Espadana (campanario de muro) y cruz sobre la fachada de la Ermita."""
    st = [i for i in range(B.n) if B.street[i]]
    if not st:
        st = [max(range(B.n), key=lambda i: B.elen[i])]
    sp = SC['specials']['chorro_centro']

    def score(i):
        a = B.ring[i]
        c = B.ring[(i + 1) % B.n]
        return math.hypot((a[0] + c[0]) / 2 - sp[0], (a[1] + c[1]) / 2 - sp[1])

    i = min(st, key=score)
    a = B.ring[i]
    c = B.ring[(i + 1) % B.n]
    L = B.elen[i]
    tx, ty = (c[0] - a[0]) / L, (c[1] - a[1]) / L
    nx, ny = ty, -tx
    wt = B.wall_top
    um = L / 2
    white = B.wall_col

    def P3(u, z, o=0.0):
        return (a[0] + tx * u + nx * o, a[1] + ty * u + ny * o, z)

    def bx(mb, u0, u1, z0, z1, d0, d1, mat, col, skip=''):
        mb.box(P3(u0, z0, d0), (tx * (u1 - u0), ty * (u1 - u0), 0.0), (nx * (d1 - d0), ny * (d1 - d0), 0.0), (0.0, 0.0, z1 - z0), mat, col, skip)

    hw = min(1.9, L / 2 - 0.3)
    # hastial: sube el muro frontal en triangulo hasta la espadana
    zt = wt + 0.2
    bx(WB, um - L / 2, um + L / 2, wt - 0.05, zt, -0.5, 0.02, MAT['fa'], white)
    # machones y arco de campana
    bx(WB, um - hw, um - 0.55, zt, zt + 1.9, -0.5, 0.02, MAT['fa'], white)
    bx(WB, um + 0.55, um + hw, zt, zt + 1.9, -0.5, 0.02, MAT['fa'], white)
    bx(WB, um - hw, um + hw, zt + 1.9, zt + 2.5, -0.5, 0.02, MAT['fa'], white)
    # remate a dos aguas con teja
    zr = zt + 2.5
    for sgn in (-1, 1):
        p0 = P3(um, zr + 0.75, -0.6)
        p1 = P3(um, zr + 0.75, 0.12)
        p2 = P3(um + sgn * (hw + 0.2), zr - 0.05, 0.12)
        p3 = P3(um + sgn * (hw + 0.2), zr - 0.05, -0.6)
        RB.face([p0, p1, p2, p3] if sgn > 0 else [p1, p0, p3, p2], MAT['te'], (0.95, 0.9, 0.88, 1.0), [(0, 3.9), (0.72, 3.9), (0.72, 3.0), (0, 3.0)])
    WB.face([P3(um - hw - 0.2, zr - 0.05, 0.02), P3(um + hw + 0.2, zr - 0.05, 0.02), P3(um, zr + 0.75, 0.02)], MAT['fa'], white)
    WB.face([P3(um + hw + 0.2, zr - 0.05, -0.5), P3(um - hw - 0.2, zr - 0.05, -0.5), P3(um, zr + 0.75, -0.5)], MAT['fa'], white)
    # campana
    bx(CBm, um - 0.5, um + 0.5, zt + 1.62, zt + 1.7, -0.3, -0.2, MAT['ma'], srgb('#3b2a1c'))
    bx(CBm, um - 0.2, um + 0.2, zt + 1.0, zt + 1.6, -0.45, -0.05, MAT['hi'], WHITE)
    bx(CBm, um - 0.27, um + 0.27, zt + 0.9, zt + 1.05, -0.52, 0.02, MAT['hi'], WHITE)
    # cruz
    bx(CBm, um - 0.05, um + 0.05, zr + 0.7, zr + 2.0, -0.29, -0.19, MAT['hi'], WHITE)
    bx(CBm, um - 0.38, um + 0.38, zr + 1.5, zr + 1.6, -0.29, -0.19, MAT['hi'], WHITE)
    # oculo sobre el porton
    cz = B.base + 4.35
    r = 0.42
    ring_o = [P3(um + r * math.cos(t * math.pi / 8), cz + r * math.sin(t * math.pi / 8), 0.012) for t in range(16)]
    ring_i = [P3(um + (r - 0.09) * math.cos(t * math.pi / 8), cz + (r - 0.09) * math.sin(t * math.pi / 8), 0.02) for t in range(16)]
    CBm.face(ring_o, MAT['ma'], B.wood_col)
    CBm.face(ring_i, MAT['vi'], WHITE)
    # gradas de piedra
    for s in range(2):
        bx(WB, um - 1.9 - 0.3 * s, um + 1.9 + 0.3 * s, B.zbot, B.base - 0.02 - 0.16 * s, 0.0, 0.5 + 0.35 * s, MAT['pi'], WHITE)


def build_buildings(M):
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Edificios', root)
    clear_coll('CB_Edificios')
    for nm in ('Manzana_A', 'Manzana_B', 'Manzana_C', 'Manzana_D', 'Entorno'):
        clear_coll('CB_' + nm)
    mats = [M['fachada'], M['mural'], M['madera'], M['vidrio'], M['teja'], M['hierro'], M['farol'], M['piedra'], M['losa'],
            M['hoja'], M['vidrio_claro'], M['lona']]
    blocks = {}
    stats = {'bld': 0, 'ops': 0}
    patios = []
    for b in SC['buildings']:
        try:
            B = setup_building(b)
        except Exception as e:
            print('setup fallo', b['id'], e)
            continue
        if B.blk not in blocks:
            blocks[B.blk] = (MB(), MB(), MB())
        WB, RB, CBm = blocks[B.blk]
        for i in range(B.n):
            if B.elen[i] < 1e-4:
                continue
            if B.street[i] and B.elen[i] >= 0.6:
                ops = facade(B, i, WB, CBm)
                stats['ops'] += len(ops or [])
            else:
                col = B.culata if not B.free[i] else mixc(B.wall_col, B.culata, 0.5)
                plain_wall(B, WB, i, col)
        for pr in B.patios:
            make_patio(B, WB, CBm, pr)
            pc = np.asarray(pr).mean(axis=0)
            patios.append([float(pc[0]), float(pc[1]), B.base + 0.03, abs(ring_area(pr))])
        try:
            make_roof(B, RB, CBm)
        except Exception as e:
            import traceback
            print('techo fallo', b['id'], traceback.format_exc()[-300:])
        for pr, hole_ in zip(B.patios, B.holes):
            if abs(ring_area(pr)) < 160 and B.rnd.random() < 0.38:
                make_skylight(B, RB, CBm, hole_)
        if B.kind == 'ermita':
            make_espadana(B, WB, RB, CBm)
        stats['bld'] += 1
    names = {'A': 'Manzana_A', 'B': 'Manzana_B', 'C': 'Manzana_C', 'D': 'Manzana_D', 'X': 'Entorno'}
    tot = 0
    for k, (WB, RB, CBm) in blocks.items():
        sub = get_coll('CB_' + names[k], coll)
        WB.build('Muros_' + names[k], sub, mats)
        RB.build('Techos_' + names[k], sub, mats)
        CBm.build('Carpinteria_' + names[k], sub, mats)
        tot += WB.stats() + RB.stats() + CBm.stats()
    stats['faces'] = tot
    stats['patios'] = patios
    return stats
