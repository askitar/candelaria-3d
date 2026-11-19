"""Suelo: calles, andenes, plazoleta, interiores de manzana, bordillos y base de maqueta."""


def build_ground(M):
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Suelo', root)
    clear_coll('CB_Suelo')
    order = ['asfalto', 'adoquin', 'empedrado', 'losa', 'plaza', 'patio', 'bordillo', 'base']
    mats = [M[k] for k in order]
    idx = {k: i for i, k in enumerate(order)}

    def layer(mb, polys, mat, dz, step=3.5):
        for rings in polys:
            if abs(ring_area(rings[0])) < 0.5:
                continue
            pts, tris = tri_poly(rings, step)
            if not tris:
                continue
            P = np.asarray(pts)
            Z = T_np(P) + dz
            for a, b, c in tris:
                mb.face([(pts[a][0], pts[a][1], float(Z[a])), (pts[b][0], pts[b][1], float(Z[b])), (pts[c][0], pts[c][1], float(Z[c]))],
                        idx[mat], WHITE, [pts[a], pts[b], pts[c]])

    mb = MB()
    for k, polys in SC['roads'].items():
        layer(mb, polys, k, 0.0)
    ob = mb.build('Calles', coll, mats)
    n1 = mb.stats()

    mb = MB()
    for k, polys in SC['ped'].items():
        layer(mb, polys, k, CURB)
    layer(mb, SC['sidewalk'], 'losa', CURB)
    # bordillos
    for rings in SC['raised']:
        for ring in rings:
            d = densify(ring, 3.0)
            n = len(d)
            for i in range(n):
                a = d[i]
                b = d[(i + 1) % n]
                za = T(a[0], a[1])
                zb = T(b[0], b[1])
                mb.face([(a[0], a[1], za - 0.3), (b[0], b[1], zb - 0.3), (b[0], b[1], zb + CURB), (a[0], a[1], za + CURB)],
                        idx['bordillo'], WHITE, [(0, 0), (1, 0), (1, 1), (0, 1)])
    mb.build('Andenes_y_plazoleta', coll, mats)
    n2 = mb.stats()

    mb = MB()
    layer(mb, SC['interior'], 'patio', CURB, 4.0)
    mb.build('Interior_manzanas', coll, mats)
    n3 = mb.stats()

    # base tipo maqueta
    mb = MB()
    ZB = -7.0
    ring = SC['G'][0][0]
    d = densify(ring, 4.0)
    n = len(d)
    for i in range(n):
        a = d[i]
        b = d[(i + 1) % n]
        mb.face([(a[0], a[1], ZB), (b[0], b[1], ZB), (b[0], b[1], T(b[0], b[1]) + 0.001), (a[0], a[1], T(a[0], a[1]) + 0.001)],
                idx['base'], WHITE)
    mb.build('Base_maqueta', coll, mats)
    return (n1, n2, n3)
