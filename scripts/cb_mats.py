"""Materiales de La Candelaria v2: texturas PBR reales (Poly Haven, CC0) + desgaste procedural + neblina atmosferica.

Se ejecuta dentro de Blender despues de cb_lib. Necesita las imagenes importadas:
clay_roof_tiles_02, painted_plaster_wall, asphalt_04, cobblestone_02, herringbone_brick_03,
square_tiles, black_painted_planks, leafy_grass (mapas Diffuse / Rough / nor_gl).
"""
import bpy, math

HAZE_LEN = 3200.0  # metros para perder ~63% de contraste


def haze_group():
    ng = bpy.data.node_groups.get('CB_Neblina')
    if ng is not None:
        dn = ng.nodes.get('Densidad')
        if dn is not None:
            dn.outputs[0].default_value = 1.0 / HAZE_LEN
        return ng
    ng = bpy.data.node_groups.new('CB_Neblina', 'ShaderNodeTree')
    ng.interface.new_socket(name='Color', in_out='INPUT', socket_type='NodeSocketColor')
    ng.interface.new_socket(name='Base', in_out='OUTPUT', socket_type='NodeSocketColor')
    ng.interface.new_socket(name='Emision', in_out='OUTPUT', socket_type='NodeSocketColor')
    ng.interface.new_socket(name='Factor', in_out='OUTPUT', socket_type='NodeSocketFloat')
    N = ng.nodes
    L = ng.links
    gi = N.new('NodeGroupInput')
    go = N.new('NodeGroupOutput')
    cam = N.new('ShaderNodeCameraData')
    dens = N.new('ShaderNodeValue')
    dens.name = dens.label = 'Densidad'
    dens.outputs[0].default_value = 1.0 / HAZE_LEN
    hc = N.new('ShaderNodeRGB')
    hc.name = hc.label = 'ColorNeblina'
    hc.outputs[0].default_value = (0.42, 0.5, 0.62, 1.0)
    m1 = N.new('ShaderNodeMath')
    m1.operation = 'MULTIPLY'
    L.new(cam.outputs['View Distance'], m1.inputs[0])
    L.new(dens.outputs[0], m1.inputs[1])
    m2 = N.new('ShaderNodeMath')
    m2.operation = 'MULTIPLY'
    L.new(m1.outputs[0], m2.inputs[0])
    m2.inputs[1].default_value = -1.0
    m3 = N.new('ShaderNodeMath')
    m3.operation = 'EXPONENT'
    L.new(m2.outputs[0], m3.inputs[0])
    f = N.new('ShaderNodeMath')
    f.operation = 'SUBTRACT'
    f.use_clamp = True
    f.inputs[0].default_value = 1.0
    L.new(m3.outputs[0], f.inputs[1])

    def mixn(a_sock, b_sock, a_val=None, b_val=None):
        n = N.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        fa = [s for s in n.inputs if s.name == 'Factor' and s.type == 'VALUE'][0]
        A = [s for s in n.inputs if s.name == 'A' and s.type == 'RGBA'][0]
        B = [s for s in n.inputs if s.name == 'B' and s.type == 'RGBA'][0]
        L.new(f.outputs[0], fa)
        if a_sock is not None:
            L.new(a_sock, A)
        else:
            A.default_value = a_val
        if b_sock is not None:
            L.new(b_sock, B)
        else:
            B.default_value = b_val
        return [s for s in n.outputs if s.type == 'RGBA'][0]

    base = mixn(gi.outputs['Color'], None, None, (0, 0, 0, 1))
    emis = mixn(None, hc.outputs[0], (0, 0, 0, 1), None)
    L.new(base, go.inputs['Base'])
    L.new(emis, go.inputs['Emision'])
    L.new(f.outputs[0], go.inputs['Factor'])
    return ng


class G:
    """Mini constructor de grafos de nodos."""

    def __init__(self, name):
        m = bpy.data.materials.get(name)
        if m is None:
            m = bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        self.m = m
        self.nt = m.node_tree
        self.nt.nodes.clear()
        self.col = 0
        self.out = self.nt.nodes.new('ShaderNodeOutputMaterial')
        self.out.location = (1100, 0)
        self.bsdf = self.nt.nodes.new('ShaderNodeBsdfPrincipled')
        self.bsdf.location = (800, 0)
        self.nt.links.new(self.bsdf.outputs[0], self.out.inputs[0])

    def node(self, typ, **props):
        n = self.nt.nodes.new(typ)
        self.col += 1
        n.location = (-1700 + (self.col % 10) * 220, 600 - (self.col // 10) * 340)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def set(self, sock, val):
        if hasattr(val, 'is_output') or hasattr(val, 'links'):
            self.nt.links.new(val, sock)
        else:
            sock.default_value = val

    def inp(self, node, name, typ=None):
        for s in node.inputs:
            if s.name == name and (typ is None or s.type == typ):
                return s
        raise KeyError(name)

    def outp(self, node, name, typ=None):
        for s in node.outputs:
            if s.name == name and (typ is None or s.type == typ):
                return s
        raise KeyError(name)

    # ---- coordenadas
    def obj_coords(self, rot_z=0.0, scale=1.0):
        tc = self.node('ShaderNodeTexCoord')
        mp = self.node('ShaderNodeMapping')
        mp.inputs['Rotation'].default_value = (0.0, 0.0, rot_z)
        mp.inputs['Scale'].default_value = (scale, scale, scale)
        self.nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
        return mp.outputs['Vector']

    def uv(self):
        return self.node('ShaderNodeTexCoord').outputs['UV']

    def mapped(self, vec, sx, sy=None, rot=0.0, off=(0.0, 0.0)):
        mp = self.node('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (sx, sx if sy is None else sy, sx)
        mp.inputs['Rotation'].default_value = (0.0, 0.0, rot)
        mp.inputs['Location'].default_value = (off[0], off[1], 0.0)
        self.nt.links.new(vec, mp.inputs['Vector'])
        return mp.outputs['Vector']

    def attr(self, name='Col'):
        a = self.node('ShaderNodeAttribute')
        a.attribute_name = name
        return a

    def attr_col(self, name='Col'):
        return self.attr(name).outputs['Color']

    # ---- texturas
    def img(self, name, vec, noncolor=False, box=False):
        n = self.node('ShaderNodeTexImage')
        n.image = bpy.data.images[name]
        if box:
            n.projection = 'BOX'
            n.projection_blend = 0.25
        if vec is not None:
            self.nt.links.new(vec, n.inputs['Vector'])
        return n

    def pbr(self, prefix, vec, nstrength=1.0, box=False):
        d = self.img(prefix + '_Diffuse', vec, False, box)
        r = self.img(prefix + '_Rough', vec, True, box)
        nimg = self.img(prefix + '_nor_gl', vec, True, box)
        nm = self.node('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = nstrength
        self.nt.links.new(nimg.outputs['Color'], nm.inputs['Color'])
        return d.outputs['Color'], r.outputs['Color'], nm.outputs['Normal']

    def noise(self, vec, scale, detail=3.0, rough=0.55, dim='3D'):
        n = self.node('ShaderNodeTexNoise')
        n.noise_dimensions = dim
        if vec is not None:
            self.nt.links.new(vec, n.inputs['Vector'])
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        return n

    def math(self, op, a, b=None, clamp=False):
        n = self.node('ShaderNodeMath')
        n.operation = op
        n.use_clamp = clamp
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        return n.outputs[0]

    def mix(self, fac, a, b, blend='MIX'):
        n = self.node('ShaderNodeMix')
        n.data_type = 'RGBA'
        n.blend_type = blend
        self.set(self.inp(n, 'Factor', 'VALUE'), fac)
        self.set(self.inp(n, 'A', 'RGBA'), a)
        self.set(self.inp(n, 'B', 'RGBA'), b)
        return self.outp(n, 'Result', 'RGBA')

    def ramp(self, fac, stops, interp='LINEAR'):
        n = self.node('ShaderNodeValToRGB')
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p
            e.color = c
        self.set(n.inputs['Fac'], fac)
        return n.outputs['Color']

    def maprange(self, v, a0, a1, b0, b1, clamp=True):
        n = self.node('ShaderNodeMapRange')
        n.clamp = clamp
        self.set(n.inputs['Value'], v)
        n.inputs['From Min'].default_value = a0
        n.inputs['From Max'].default_value = a1
        n.inputs['To Min'].default_value = b0
        n.inputs['To Max'].default_value = b1
        return n.outputs['Result']

    def sep(self, vec):
        n = self.node('ShaderNodeSeparateXYZ')
        self.nt.links.new(vec, n.inputs[0])
        return n.outputs

    def comb(self, x, y, z=0.0):
        n = self.node('ShaderNodeCombineXYZ')
        self.set(n.inputs[0], x)
        self.set(n.inputs[1], y)
        self.set(n.inputs[2], z)
        return n.outputs[0]

    def bw(self, col):
        n = self.node('ShaderNodeRGBToBW')
        self.nt.links.new(col, n.inputs[0])
        return n.outputs[0]

    def bump(self, height, strength=0.3, dist=0.02, normal=None):
        n = self.node('ShaderNodeBump')
        n.inputs['Strength'].default_value = strength
        n.inputs['Distance'].default_value = dist
        self.set(n.inputs['Height'], height)
        if normal is not None:
            self.nt.links.new(normal, n.inputs['Normal'])
        return n.outputs['Normal']

    def finish(self, color, rough=0.8, metallic=0.0, normal=None, spec=0.3, haze=True):
        if haze:
            hz = self.node('ShaderNodeGroup')
            hz.node_tree = haze_group()
            hz.location = (560, -260)
            self.set(hz.inputs['Color'], color)
            self.nt.links.new(hz.outputs['Base'], self.bsdf.inputs['Base Color'])
            self.nt.links.new(hz.outputs['Emision'], self.bsdf.inputs['Emission Color'])
            self.bsdf.inputs['Emission Strength'].default_value = 1.0
        else:
            self.set(self.bsdf.inputs['Base Color'], color)
        self.set(self.bsdf.inputs['Roughness'], rough)
        self.set(self.bsdf.inputs['Metallic'], metallic)
        self.bsdf.inputs['Specular IOR Level'].default_value = spec
        if normal is not None:
            self.nt.links.new(normal, self.bsdf.inputs['Normal'])
        return self.m


def C(h):
    return srgb(h)


def gray(v):
    return (v, v, v, 1.0)


def make_materials():
    M = {}
    ang = -GRID_ANGLE

    # ================= fachadas: pintura (color por vertice) sobre panete real + desgaste
    def wall_base(g, with_mural=False):
        a = g.attr('Col')
        col = a.outputs['Color']
        alpha = a.outputs['Alpha']
        uvv = g.uv()
        uvs = g.sep(uvv)
        P, Pr, Pn = g.pbr('painted_plaster_wall', g.mapped(uvv, 0.5), 0.8)
        oc = g.obj_coords()
        if with_mural:
            nd = g.noise(uvv, 0.7, 2.0)
            warp = g.node('ShaderNodeMix')
            warp.data_type = 'VECTOR'
            warp.inputs[0].default_value = 0.18
            g.nt.links.new(uvv, g.inp(warp, 'A', 'VECTOR'))
            g.nt.links.new(nd.outputs['Color'], g.inp(warp, 'B', 'VECTOR'))
            wv = g.outp(warp, 'Result', 'VECTOR')
            vor = g.node('ShaderNodeTexVoronoi')
            g.nt.links.new(wv, vor.inputs['Vector'])
            vor.inputs['Scale'].default_value = 1.1
            ve = g.node('ShaderNodeTexVoronoi')
            ve.feature = 'DISTANCE_TO_EDGE'
            g.nt.links.new(wv, ve.inputs['Vector'])
            ve.inputs['Scale'].default_value = 1.1
            hs = g.node('ShaderNodeHueSaturation')
            hs.inputs['Saturation'].default_value = 1.35
            hs.inputs['Value'].default_value = 0.85
            g.nt.links.new(vor.outputs['Color'], hs.inputs['Color'])
            line = g.maprange(ve.outputs['Distance'], 0.02, 0.035, 1.0, 0.0)
            paint = g.mix(line, hs.outputs['Color'], (0.01, 0.01, 0.012, 1.0))
            band = g.math('MULTIPLY', g.maprange(uvs[1], 0.2, 0.35, 0.0, 1.0), g.maprange(uvs[1], 2.9, 3.25, 1.0, 0.0))
            col = g.mix(band, col, paint)
        c = g.mix(0.8, col, P, 'OVERLAY')
        n1 = g.noise(oc, 0.33, 4.0)
        c = g.mix(1.0, c, g.ramp(n1.outputs['Fac'], [(0.25, gray(0.8)), (0.75, gray(1.04))]), 'MULTIPLY')
        # pintura deslavada por parches
        n5 = g.noise(oc, 0.85, 5.0, 0.7)
        fade = g.maprange(n5.outputs['Fac'], 0.56, 0.8, 0.0, 0.4)
        c = g.mix(fade, c, C('#d8d2c4'))
        # salpicadura y mugre junto al anden
        low = g.maprange(uvs[1], 0.02, 1.4, 1.0, 0.0)
        n2 = g.noise(oc, 2.2, 4.0, 0.65)
        dirt = g.math('MULTIPLY', low, g.maprange(n2.outputs['Fac'], 0.3, 0.75, 0.12, 0.6))
        c = g.mix(dirt, c, C('#3b352e'))
        # chorreaduras bajo el alero (la altura del muro va en el alfa del color)
        dtop = g.math('SUBTRACT', g.math('MULTIPLY', alpha, 20.0), uvs[1])
        top = g.maprange(dtop, 0.0, 1.7, 1.0, 0.0)
        sv = g.comb(g.math('MULTIPLY', uvs[0], 5.5), g.math('MULTIPLY', uvs[1], 0.22))
        n3 = g.noise(sv, 1.0, 3.0, 0.6, '2D')
        streak = g.math('MULTIPLY', top, g.maprange(n3.outputs['Fac'], 0.45, 0.75, 0.0, 0.5))
        c = g.mix(streak, c, C('#2f2b27'))
        # desconchados que dejan ver el adobe
        n6 = g.noise(oc, 0.55, 5.0, 0.62)
        patch = g.math('MULTIPLY', g.maprange(n6.outputs['Fac'], 0.705, 0.735, 0.0, 0.9), g.maprange(uvs[1], 0.25, 2.8, 1.0, 0.0))
        c = g.mix(patch, c, g.mix(1.0, C('#9a7654'), P, 'MULTIPLY'))
        rough = g.maprange(g.bw(Pr), 0.0, 1.0, 0.72, 1.0)
        nrm = g.bump(patch, 0.5, 0.03, Pn)
        return c, rough, nrm

    g = G('CB_Fachada')
    c, r, n = wall_base(g)
    M['fachada'] = g.finish(c, r, 0.0, n, 0.25)

    g = G('CB_Mural')
    c, r, n = wall_base(g, True)
    M['mural'] = g.finish(c, r, 0.0, n, 0.25)

    # fachadas del entorno: mismo panete + rejilla de ventanas pintada
    g = G('CB_FachadaEntorno')
    a = g.attr('Col')
    uvv = g.uv()
    uvs = g.sep(uvv)
    P, Pr, Pn = g.pbr('painted_plaster_wall', g.mapped(uvv, 0.5), 0.5)
    c = g.mix(0.7, a.outputs['Color'], P, 'OVERLAY')
    oc = g.obj_coords()
    n1 = g.noise(oc, 0.2, 4.0)
    c = g.mix(1.0, c, g.ramp(n1.outputs['Fac'], [(0.25, gray(0.78)), (0.75, gray(1.04))]), 'MULTIPLY')
    fu = g.math('FRACT', g.math('DIVIDE', uvs[0], 3.1))
    fv = g.math('FRACT', g.math('DIVIDE', uvs[1], 3.1))
    wu = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', fu, 0.5)), 0.2)
    wv = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', fv, 0.52)), 0.24)
    win = g.math('MULTIPLY', g.math('MULTIPLY', wu, wv), g.math('GREATER_THAN', uvs[1], 0.4))
    wn = g.node('ShaderNodeTexWhiteNoise')
    wn.noise_dimensions = '2D'
    g.nt.links.new(g.comb(g.math('FLOOR', g.math('DIVIDE', uvs[0], 3.1)), g.math('FLOOR', g.math('DIVIDE', uvs[1], 3.1))), wn.inputs['Vector'])
    glass = g.ramp(wn.outputs['Value'], [(0.0, (0.012, 0.016, 0.022, 1)), (0.7, (0.03, 0.04, 0.05, 1)), (1.0, (0.12, 0.11, 0.09, 1))])
    c = g.mix(win, c, glass)
    low = g.maprange(uvs[1], 0.0, 1.6, 0.5, 0.0)
    c = g.mix(low, c, C('#3b352e'))
    rough = g.mix(win, gray(0.9), gray(0.12))
    M['fachada_ctx'] = g.finish(c, g.bw(rough), 0.0, Pn, 0.3)

    # azoteas planas del entorno
    g = G('CB_Azotea')
    oc = g.obj_coords()
    A, Ar, An = g.pbr('asphalt_04', g.mapped(oc, 0.12), 0.4)
    c = g.mix(0.6, g.attr_col(), A, 'OVERLAY')
    n1 = g.noise(oc, 0.12, 5.0, 0.65)
    c = g.mix(1.0, c, g.ramp(n1.outputs['Fac'], [(0.3, gray(0.65)), (0.7, gray(1.05))]), 'MULTIPLY')
    M['azotea'] = g.finish(c, 0.9, 0.0, An, 0.2)

    # ================= madera pintada
    g = G('CB_Madera')
    uvv = g.uv()
    W, Wr, Wn = g.pbr('black_painted_planks', g.mapped(uvv, 0.625), 0.9)
    oc = g.obj_coords()
    n1 = g.noise(oc, 7.0, 3.0)
    c = g.mix(1.0, g.attr_col(), g.ramp(n1.outputs['Fac'], [(0.3, gray(0.72)), (0.7, gray(1.02))]), 'MULTIPLY')
    wear = g.maprange(g.bw(W), 0.08, 0.35, 0.0, 0.35)
    c = g.mix(wear, c, C('#6a5a48'))
    M['madera'] = g.finish(c, g.maprange(g.bw(Wr), 0.0, 1.0, 0.5, 0.85), 0.0, Wn, 0.3)

    # ================= vidrio
    g = G('CB_Vidrio')
    oc = g.obj_coords()
    n1 = g.noise(oc, 0.4, 2.0)
    c = g.ramp(n1.outputs['Fac'], [(0.3, (0.012, 0.017, 0.024, 1)), (0.7, (0.03, 0.036, 0.042, 1))])
    M['vidrio'] = g.finish(c, 0.05, 0.0, None, 0.9)

    g = G('CB_VidrioClaro')
    M['vidrio_claro'] = g.finish((0.32, 0.4, 0.42, 1.0), 0.12, 0.0, None, 0.8)

    # ================= teja de barro real
    g = G('CB_Teja')
    uvv = g.uv()
    D, R, N = g.pbr('clay_roof_tiles_02', g.mapped(uvv, 0.4), 1.2)
    oc = g.obj_coords()
    hs = g.node('ShaderNodeHueSaturation')
    hs.inputs['Saturation'].default_value = 0.82
    hs.inputs['Value'].default_value = 0.72
    g.nt.links.new(D, hs.inputs['Color'])
    c = g.mix(1.0, hs.outputs['Color'], g.attr_col(), 'MULTIPLY')
    n1 = g.noise(oc, 0.2, 5.0, 0.62)
    moss = g.maprange(n1.outputs['Fac'], 0.46, 0.74, 0.0, 0.75)
    c = g.mix(moss, c, C('#34382a'))
    n2 = g.noise(oc, 0.045, 3.0)
    c = g.mix(1.0, c, g.ramp(n2.outputs['Fac'], [(0.3, gray(0.78)), (0.7, gray(1.08))]), 'MULTIPLY')
    M['teja'] = g.finish(c, g.maprange(g.bw(R), 0.0, 1.0, 0.7, 0.98), 0.0, N, 0.3)

    # ================= metal y farol
    g = G('CB_Hierro')
    M['hierro'] = g.finish((0.02, 0.02, 0.022, 1.0), 0.5, 0.8, None, 0.5)
    g = G('CB_FarolLuz')
    g.bsdf.inputs['Emission Color'].default_value = (1.0, 0.72, 0.38, 1.0)
    g.bsdf.inputs['Emission Strength'].default_value = 3.0
    M['farol'] = g.finish((1.0, 0.8, 0.5, 1.0), 0.3, 0.0, None, 0.5, haze=False)

    # ================= suelos con textura real
    def ground(name, prefix, size, rot, tint=None, nstr=1.0, rmin=0.6, rmax=1.0, wet=0.0, var=(0.72, 1.06)):
        g = G(name)
        oc = g.obj_coords(rot)
        D, R, N = g.pbr(prefix, g.mapped(oc, 1.0 / size), nstr)
        c = D
        if tint is not None:
            c = g.mix(1.0, c, tint, 'MULTIPLY')
        n1 = g.noise(oc, 0.09, 5.0, 0.62)
        c = g.mix(1.0, c, g.ramp(n1.outputs['Fac'], [(0.3, gray(var[0])), (0.72, gray(var[1]))]), 'MULTIPLY')
        n2 = g.noise(oc, 0.6, 4.0, 0.6)
        c = g.mix(g.maprange(n2.outputs['Fac'], 0.55, 0.8, 0.0, 0.3), c, C('#2a2622'))
        rough = g.maprange(g.bw(R), 0.0, 1.0, rmin, rmax)
        if wet > 0:
            n3 = g.noise(oc, 0.25, 3.0, 0.5)
            w = g.maprange(n3.outputs['Fac'], 0.52, 0.66, 0.0, wet)
            c = g.mix(w, c, g.mix(1.0, c, gray(0.55), 'MULTIPLY'))
            rough = g.math('MULTIPLY', rough, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', w, 0.75)))
        return g.finish(c, rough, 0.0, N, 0.35)

    M['asfalto'] = ground('CB_Asfalto', 'asphalt_04', 4.04, ang, gray(0.8), 0.8, 0.62, 0.95, 0.7)
    M['adoquin'] = ground('CB_Adoquin', 'herringbone_brick_03', 1.98, ang, None, 1.0, 0.7, 0.98, 0.4)
    M['plaza'] = ground('CB_Plaza', 'herringbone_brick_03', 1.98, ang + math.radians(45.0), (1.0, 0.93, 0.86, 1.0), 1.0, 0.7, 0.98, 0.3)
    M['empedrado'] = ground('CB_Empedrado', 'cobblestone_02', 2.7, ang, (0.9, 0.88, 0.86, 1.0), 1.4, 0.65, 0.98, 0.35)
    # andenes: concreto en losas con juntas (textura real de grano + juntas procedurales)
    g = G('CB_Losa')
    oc = g.obj_coords(ang)
    D, R, N = g.pbr('asphalt_04', g.mapped(oc, 1.0 / 2.6), 0.55)
    c = g.mix(1.0, g.mix(0.75, C('#8d867a'), D, 'OVERLAY'), (1.25, 1.2, 1.12, 1.0), 'MULTIPLY')
    b = g.node('ShaderNodeTexBrick')
    g.nt.links.new(oc, b.inputs['Vector'])
    b.inputs['Scale'].default_value = 1.0
    b.inputs['Brick Width'].default_value = 0.8
    b.inputs['Row Height'].default_value = 0.6
    b.inputs['Mortar Size'].default_value = 0.012
    b.inputs['Mortar Smooth'].default_value = 0.3
    b.inputs['Color1'].default_value = (1.0, 1.0, 1.0, 1)
    b.inputs['Color2'].default_value = (0.86, 0.86, 0.86, 1)
    b.inputs['Mortar'].default_value = (0.3, 0.28, 0.26, 1)
    c = g.mix(1.0, c, b.outputs['Color'], 'MULTIPLY')
    n1 = g.noise(oc, 0.35, 5.0, 0.62)
    c = g.mix(1.0, c, g.ramp(n1.outputs['Fac'], [(0.3, gray(0.72)), (0.72, gray(1.05))]), 'MULTIPLY')
    n2 = g.noise(oc, 1.4, 4.0, 0.6)
    c = g.mix(g.maprange(n2.outputs['Fac'], 0.58, 0.8, 0.0, 0.35), c, C('#2e2a25'))
    M['losa'] = g.finish(c, g.maprange(g.bw(R), 0.0, 1.0, 0.72, 0.98), 0.0, g.bump(g.math('SUBTRACT', 1.0, b.outputs['Fac']), 0.35, 0.01, N), 0.3)

    # pasto y tierra de los interiores de manzana
    g = G('CB_Patio')
    oc = g.obj_coords()
    D, R, N = g.pbr('leafy_grass', g.mapped(oc, 0.5), 1.0)
    D2 = g.img('leafy_grass_Diffuse', g.mapped(oc, 0.137, None, 0.65)).outputs['Color']
    c = g.mix(1.0, g.mix(0.5, D, D2), (0.5, 0.66, 0.38, 1.0), 'MULTIPLY')
    n1 = g.noise(oc, 0.07, 6.0, 0.65)
    c = g.mix(g.maprange(n1.outputs['Fac'], 0.56, 0.74, 0.0, 0.7), c, C('#4f4230'))
    n2 = g.noise(oc, 0.25, 4.0)
    c = g.mix(1.0, c, g.ramp(n2.outputs['Fac'], [(0.3, gray(0.7)), (0.7, gray(1.1))]), 'MULTIPLY')
    M['patio'] = g.finish(c, 0.95, 0.0, N, 0.12)

    g = G('CB_Bordillo')
    oc = g.obj_coords()
    n1 = g.noise(oc, 3.0, 4.0)
    P, Pr, Pn = g.pbr('painted_plaster_wall', g.mapped(oc, 0.5), 0.8, True)
    c = g.mix(0.6, g.ramp(n1.outputs['Fac'], [(0.3, C('#6a665f')), (0.7, C('#8c877e'))]), P, 'OVERLAY')
    M['bordillo'] = g.finish(c, 0.88, 0.0, Pn, 0.25)

    g = G('CB_Base')
    M['base'] = g.finish(C('#1c1b1a'), 0.9, 0.0, None, 0.1, haze=False)

    g = G('CB_Piedra')
    oc = g.obj_coords()
    n1 = g.noise(oc, 2.5, 5.0, 0.6)
    P, Pr, Pn = g.pbr('painted_plaster_wall', g.mapped(oc, 0.7), 1.2, True)
    c = g.mix(0.7, g.ramp(n1.outputs['Fac'], [(0.3, C('#5f5a52')), (0.7, C('#8f887b'))]), P, 'OVERLAY')
    n2 = g.noise(oc, 0.8, 4.0)
    c = g.mix(g.maprange(n2.outputs['Fac'], 0.55, 0.75, 0.0, 0.5), c, C('#3a3d30'))
    M['piedra'] = g.finish(c, 0.9, 0.0, g.bump(n1.outputs['Fac'], 0.3, 0.02, Pn), 0.2)

    g = G('CB_Agua')
    oc = g.obj_coords()
    n1 = g.noise(oc, 6.0, 2.0)
    M['agua'] = g.finish((0.02, 0.06, 0.07, 1.0), 0.03, 0.0, g.bump(n1.outputs['Fac'], 0.12, 0.01), 0.8)

    # vegetacion
    g = G('CB_Hoja')
    oc = g.obj_coords()
    n1 = g.noise(oc, 1.4, 6.0, 0.72)
    n2 = g.noise(oc, 5.5, 3.0, 0.6)
    c = g.ramp(n1.outputs['Fac'], [(0.28, C('#16280f')), (0.5, C('#2c4a1f')), (0.74, C('#56712f'))])
    c = g.mix(g.maprange(n2.outputs['Fac'], 0.35, 0.75, 0.0, 0.55), c, C('#0e1a0a'))
    oi = g.node('ShaderNodeObjectInfo')
    c = g.mix(1.0, c, g.ramp(oi.outputs['Random'], [(0.0, (0.72, 0.8, 0.62, 1)), (1.0, (1.18, 1.12, 0.92, 1))]), 'MULTIPLY')
    c = g.mix(1.0, c, g.attr_col(), 'MULTIPLY')
    hgt = g.math('ADD', g.math('MULTIPLY', n1.outputs['Fac'], 0.6), g.math('MULTIPLY', n2.outputs['Fac'], 0.4))
    M['hoja'] = g.finish(c, 0.9, 0.0, g.bump(hgt, 0.9, 0.35), 0.15)

    g = G('CB_Tronco')
    oc = g.obj_coords()
    n1 = g.noise(oc, 6.0, 4.0)
    M['tronco'] = g.finish(g.ramp(n1.outputs['Fac'], [(0.3, C('#3a2d22')), (0.7, C('#5e4c3a'))]), 0.9, 0.0, g.bump(n1.outputs['Fac'], 0.5, 0.03), 0.15)

    # mobiliario
    g = G('CB_Poste')
    oc = g.obj_coords()
    n1 = g.noise(oc, 4.0, 4.0)
    M['poste'] = g.finish(g.ramp(n1.outputs['Fac'], [(0.3, C('#6e6b65')), (0.7, C('#8f8b83'))]), 0.85, 0.0, None, 0.2)
    g = G('CB_Cable')
    M['cable'] = g.finish((0.012, 0.012, 0.013, 1.0), 0.6, 0.0, None, 0.3)
    g = G('CB_Lona')
    oc = g.obj_coords()
    n1 = g.noise(oc, 3.0, 3.0)
    c = g.mix(1.0, g.attr_col(), g.ramp(n1.outputs['Fac'], [(0.3, gray(0.82)), (0.7, gray(1.02))]), 'MULTIPLY')
    M['lona'] = g.finish(c, 0.8, 0.0, None, 0.2)

    # ================= terreno del entorno: ciudad, parques y bosque de los cerros
    g = G('CB_Lejano')
    a = g.attr('Col')
    ch = g.sep(a.outputs['Vector'])
    oc = g.obj_coords(-GRID_ANGLE)
    oc2 = g.obj_coords()
    # alfombra urbana lejana: manzanas y calles difusas
    b = g.node('ShaderNodeTexBrick')
    g.nt.links.new(oc, b.inputs['Vector'])
    b.offset = 0.0
    b.inputs['Scale'].default_value = 1.0
    b.inputs['Brick Width'].default_value = 104.0
    b.inputs['Row Height'].default_value = 104.0
    b.inputs['Mortar Size'].default_value = 3.6
    b.inputs['Mortar Smooth'].default_value = 0.0
    b.inputs['Color1'].default_value = (1, 1, 1, 1)
    b.inputs['Color2'].default_value = (1, 1, 1, 1)
    b.inputs['Mortar'].default_value = (0, 0, 0, 1)
    v = g.node('ShaderNodeTexVoronoi')
    g.nt.links.new(oc, v.inputs['Vector'])
    v.inputs['Scale'].default_value = 0.16
    roofs = g.ramp(g.bw(v.outputs['Color']), [(0.0, C('#6f5348')), (0.4, C('#7d6255')), (0.55, C('#74716c')), (0.75, C('#8a857d')), (0.92, C('#4a5540'))], 'CONSTANT')
    streets = g.math('SUBTRACT', 1.0, b.outputs['Fac'])
    carpet = g.mix(streets, C('#3f3f41'), roofs)
    carpet = g.mix(0.45, carpet, C('#6f6a66'))
    # suelo urbano cercano (andenes, patios, parqueaderos)
    T2, T2r, T2n = g.pbr('asphalt_04', g.mapped(oc, 1.0 / 4.04), 0.5)
    n4 = g.noise(oc2, 0.05, 5.0, 0.6)
    urban = g.mix(1.0, g.mix(0.7, C('#7d776d'), T2, 'OVERLAY'), g.ramp(n4.outputs['Fac'], [(0.3, gray(0.65)), (0.7, gray(1.1))]), 'MULTIPLY')
    city = g.mix(ch[2], urban, carpet)
    # pasto de parques y bosque
    Gd, Gr, Gn = g.pbr('leafy_grass', g.mapped(oc2, 0.21), 0.8)
    n1 = g.noise(oc2, 0.006, 8.0, 0.62)
    n2 = g.noise(oc2, 0.06, 6.0, 0.7)
    fo = g.ramp(n1.outputs['Fac'], [(0.3, C('#15240f')), (0.5, C('#22381a')), (0.72, C('#3a4d27'))])
    n3 = g.noise(oc2, 0.23, 4.0, 0.7)
    fo = g.mix(1.0, fo, g.ramp(n3.outputs['Fac'], [(0.3, gray(0.5)), (0.7, gray(1.2))]), 'MULTIPLY')
    fo = g.mix(1.0, fo, g.ramp(n2.outputs['Fac'], [(0.3, gray(0.55)), (0.7, gray(1.1))]), 'MULTIPLY')
    fo = g.mix(0.18, fo, g.mix(1.0, Gd, (0.6, 0.9, 0.5, 1.0), 'MULTIPLY'))
    grass = g.mix(1.0, g.mix(1.0, Gd, (0.5, 0.72, 0.4, 1.0), 'MULTIPLY'), g.ramp(n2.outputs['Fac'], [(0.3, gray(0.62)), (0.7, gray(1.08))]), 'MULTIPLY')
    grass = g.mix(g.maprange(n1.outputs['Fac'], 0.5, 0.7, 0.0, 0.55), grass, C('#4a4630'))
    c = g.mix(ch[1], city, grass)
    c = g.mix(ch[0], c, fo)
    M['lejano'] = g.finish(c, 1.0, 0.0, g.bump(n2.outputs['Fac'], 0.6, 2.0), 0.0)
    return M
