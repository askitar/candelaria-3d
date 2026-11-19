"""Utilidades comunes para construir La Candelaria en Blender (se ejecuta dentro de Blender)."""
import bpy, json, math, random
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

import os
# Project root = folder that holds candelaria.blend (or set CANDELARIA_ROOT).
ROOT = os.environ.get("CANDELARIA_ROOT") or os.path.dirname(bpy.data.filepath)
SC = json.load(open(os.path.join(ROOT, "data", "scene.json"), encoding="utf-8"))
_tc = SC['terrain']
_COEF = _tc['coef']
_TERMS = _tc['terms']
_NORM = _tc['norm']
ZREF = _tc['zref']
CURB = 0.15
GRID_ANGLE = SC['grid_angle']


def T(x, y):
    """Altura del terreno (m) sobre el punto mas bajo del sector."""
    xn = x / _NORM
    yn = y / _NORM
    s = 0.0
    for c, (i, j) in zip(_COEF, _TERMS):
        s += c * xn ** i * yn ** j
    return s - ZREF


def T_np(P):
    xn = P[:, 0] / _NORM
    yn = P[:, 1] / _NORM
    s = np.zeros(len(P))
    for c, (i, j) in zip(_COEF, _TERMS):
        s += c * xn ** i * yn ** j
    return s - ZREF


def srgb(hexstr, a=1.0):
    """'#rrggbb' sRGB -> tupla lineal RGBA."""
    h = hexstr.lstrip('#')
    out = []
    for k in (0, 2, 4):
        c = int(h[k:k + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], a)


def shade(col, f):
    return (col[0] * f, col[1] * f, col[2] * f, col[3])


def mixc(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(4))


WHITE = (1.0, 1.0, 1.0, 1.0)


# ------------------------------------------------------------------ geometria 2D
def pip(x, y, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def pip_np(P, ring):
    """Vector booleano: puntos P (N,2) dentro del anillo."""
    R = np.asarray(ring, dtype=float)
    x = P[:, 0][:, None]
    y = P[:, 1][:, None]
    xi = R[:, 0][None, :]
    yi = R[:, 1][None, :]
    xj = np.roll(R[:, 0], 1)[None, :]
    yj = np.roll(R[:, 1], 1)[None, :]
    with np.errstate(divide='ignore', invalid='ignore'):
        cond = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
    return (cond.sum(axis=1) % 2) == 1


def inside_rings(P, rings):
    """Par-impar sobre todos los anillos (exterior + huecos)."""
    res = np.zeros(len(P), dtype=bool)
    for r in rings:
        res ^= pip_np(P, r)
    return res


def seg_dist_np(P, segs):
    """Distancias (N,M) de puntos P (N,2) a segmentos segs (M,4)."""
    S = np.asarray(segs, dtype=float)
    ax, ay, bx, by = S[:, 0][None, :], S[:, 1][None, :], S[:, 2][None, :], S[:, 3][None, :]
    px = P[:, 0][:, None]
    py = P[:, 1][:, None]
    dx = bx - ax
    dy = by - ay
    L2 = dx * dx + dy * dy
    L2 = np.where(L2 < 1e-12, 1e-12, L2)
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
    cx = ax + t * dx
    cy = ay + t * dy
    return np.hypot(px - cx, py - cy)


def ring_segs(ring):
    n = len(ring)
    return [(ring[i][0], ring[i][1], ring[(i + 1) % n][0], ring[(i + 1) % n][1]) for i in range(n)]


def densify(ring, step):
    out = []
    n = len(ring)
    for i in range(n):
        a = ring[i]
        b = ring[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(math.ceil(L / step)))
        for j in range(k):
            t = j / k
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def ring_area(ring):
    s = 0.0
    n = len(ring)
    for i in range(n):
        a = ring[i]
        b = ring[(i + 1) % n]
        s += a[0] * b[1] - b[0] * a[1]
    return s * 0.5


def tri_poly(rings, step, grid=None, extra=None, extra_edges=None, margin=0.35):
    """Triangula un poligono con huecos (CDT) con puntos interiores en grilla.

    Devuelve (lista de puntos 2D, lista de triangulos (i,j,k))."""
    verts = []
    edges = []
    for ring in rings:
        d = densify(ring, step)
        i0 = len(verts)
        verts.extend(d)
        n = len(d)
        edges.extend((i0 + k, i0 + (k + 1) % n) for k in range(n))
    nb = len(verts)
    bsegs = [(verts[a][0], verts[a][1], verts[b][0], verts[b][1]) for a, b in edges]
    if extra:
        i0 = len(verts)
        verts.extend(extra)
        if extra_edges:
            edges.extend((i0 + a, i0 + b) for a, b in extra_edges)
    g = grid if grid is not None else step
    xs = [p[0] for p in rings[0]]
    ys = [p[1] for p in rings[0]]
    gx = np.arange(min(xs) + g * 0.5, max(xs), g)
    gy = np.arange(min(ys) + g * 0.5, max(ys), g)
    if len(gx) and len(gy):
        GX, GY = np.meshgrid(gx, gy)
        P = np.stack([GX.ravel(), GY.ravel()], axis=1)
        keep = inside_rings(P, rings)
        P = P[keep]
        if len(P):
            ok = np.ones(len(P), dtype=bool)
            CH = 4000
            for s in range(0, len(P), CH):
                d = seg_dist_np(P[s:s + CH], bsegs).min(axis=1)
                ok[s:s + CH] = d > g * margin
            if extra:
                E = np.asarray(extra, dtype=float)
                for s in range(0, len(P), CH):
                    dd = np.hypot(P[s:s + CH, 0][:, None] - E[:, 0][None, :], P[s:s + CH, 1][:, None] - E[:, 1][None, :]).min(axis=1)
                    ok[s:s + CH] &= dd > g * 0.45
            P = P[ok]
            verts.extend((float(a), float(b)) for a, b in P)
    res = delaunay_2d_cdt([Vector(v) for v in verts], edges, [], 0, 1e-5, False)
    vout = [(v.x, v.y) for v in res[0]]
    fout = res[2]
    if not fout:
        return vout, []
    VA = np.asarray(vout)
    tris = []
    F = np.asarray([f for f in fout if len(f) == 3], dtype=int)
    if len(F) == 0:
        return vout, []
    C = (VA[F[:, 0]] + VA[F[:, 1]] + VA[F[:, 2]]) / 3.0
    keep = inside_rings(C, rings)
    for f, k in zip(F, keep):
        if k:
            a, b, c = int(f[0]), int(f[1]), int(f[2])
            # orientacion CCW
            if (VA[b][0] - VA[a][0]) * (VA[c][1] - VA[a][1]) - (VA[c][0] - VA[a][0]) * (VA[b][1] - VA[a][1]) < 0:
                b, c = c, b
            tris.append((a, b, c))
    return vout, tris


# ------------------------------------------------------------------ constructor de mallas
class MB:
    """Acumula caras sueltas (vertices propios por cara) con material, color y UV."""

    def __init__(self):
        self.v = []
        self.f = []
        self.m = []
        self.c = []
        self.uv = []
        self.sm = []

    def face(self, pts, mat, col, uvs=None, smooth=False):
        i0 = len(self.v)
        n = len(pts)
        self.v.extend(pts)
        self.f.append(tuple(range(i0, i0 + n)))
        self.m.append(mat)
        self.c.append(col)
        if uvs is None:
            uvs = [(0.0, 0.0)] * n
        self.uv.extend(uvs)
        self.sm.append(smooth)

    def box(self, o, ex, ey, ez, mat, col, skip=''):
        """Caja desde la esquina o con aristas ex, ey, ez. skip: letras de caras a omitir (x X y Y z Z)."""
        ox, oy, oz = o
        p = []
        for k in range(8):
            fx = k & 1
            fy = (k >> 1) & 1
            fz = (k >> 2) & 1
            p.append((ox + ex[0] * fx + ey[0] * fy + ez[0] * fz,
                      oy + ex[1] * fx + ey[1] * fy + ez[1] * fz,
                      oz + ex[2] * fx + ey[2] * fy + ez[2] * fz))
        lx = math.sqrt(ex[0] ** 2 + ex[1] ** 2 + ex[2] ** 2)
        ly = math.sqrt(ey[0] ** 2 + ey[1] ** 2 + ey[2] ** 2)
        lz = math.sqrt(ez[0] ** 2 + ez[1] ** 2 + ez[2] ** 2)
        # signo de orientacion para que las normales salgan hacia afuera
        cx = (ex[1] * ey[2] - ex[2] * ey[1], ex[2] * ey[0] - ex[0] * ey[2], ex[0] * ey[1] - ex[1] * ey[0])
        flip = (cx[0] * ez[0] + cx[1] * ez[1] + cx[2] * ez[2]) < 0
        quads = (('x', (0, 4, 6, 2), ly, lz), ('X', (1, 3, 7, 5), ly, lz),
                 ('y', (0, 1, 5, 4), lx, lz), ('Y', (2, 6, 7, 3), lx, lz),
                 ('z', (0, 2, 3, 1), lx, ly), ('Z', (4, 5, 7, 6), lx, ly))
        for key, idx, w, h in quads:
            if key in skip:
                continue
            if flip:
                idx = idx[::-1]
            self.face([p[i] for i in idx], mat, col, [(0, 0), (w, 0), (w, h), (0, h)])

    def build(self, name, coll, mats, weld=False):
        if not self.f:
            return None
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        nl = len(me.loops)
        me.polygons.foreach_set('material_index', np.asarray(self.m, dtype=np.int32))
        me.polygons.foreach_set('use_smooth', np.asarray(self.sm, dtype=bool))
        counts = np.fromiter((len(f) for f in self.f), dtype=np.int32, count=len(self.f))
        cols = np.repeat(np.asarray(self.c, dtype=np.float32), counts, axis=0)
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        ca.data.foreach_set('color', cols.ravel())
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', np.asarray(self.uv, dtype=np.float32).ravel())
        for m in mats:
            me.materials.append(m)
        me.update()
        if weld:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008)
            bm.to_mesh(me)
            bm.free()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        return ob

    def stats(self):
        return len(self.f)


def get_coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def clear_coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        return
    for ob in list(c.objects):
        me = ob.data if ob.type == 'MESH' else None
        bpy.data.objects.remove(ob, do_unlink=True)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
