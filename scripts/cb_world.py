"""Cielo HDRI real con sol y sombras, ajustes de EEVEE, color, compositor y camaras fijas."""

HDRI_NAME = 'kloofendal_48d_partly_cloudy_puresky_4k'
SUN_AZ = 250.0  # azimut deseado del sol (grados desde el norte, sentido horario): tarde, desde el oeste-suroeste


def hdri_sun(img):
    """Direccion del sol dentro del HDRI (en coordenadas de textura) y color medio del horizonte."""
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    lum = px[:, :, 0] + px[:, :, 1] + px[:, :, 2]
    mx = float(lum.max())
    jj, ii = np.nonzero(lum > mx * 0.35)
    wgt = lum[jj, ii]
    i = float((ii * wgt).sum() / wgt.sum())
    j = float((jj * wgt).sum() / wgt.sum())
    u = (i + 0.5) / w
    v = (j + 0.5) / h
    el = (v - 0.5) * math.pi
    phi = (u - 0.5) * 2 * math.pi
    d = (-math.cos(phi) * math.cos(el), math.sin(phi) * math.cos(el), math.sin(el))
    # horizonte: franja justo sobre el ecuador, lejos del sol
    j0, j1 = int(h * 0.505), int(h * 0.545)
    band = px[j0:j1, :, :3]
    cols = np.arange(w)
    far = np.abs(((cols - i + w / 2) % w) - w / 2) > w * 0.2
    hz = band[:, far, :].reshape(-1, 3).mean(axis=0)
    return d, el, [float(c) for c in hz], mx


def setup_world(strength=1.0):
    scn = bpy.context.scene
    img = bpy.data.images[HDRI_NAME]
    d, el, hz, mx = hdri_sun(img)
    a_tex = math.atan2(d[1], d[0])
    a_des = math.pi / 2 - math.radians(SUN_AZ)
    theta = a_tex - a_des
    w = bpy.data.worlds.get('CB_Cielo') or bpy.data.worlds.new('CB_Cielo')
    scn.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0.0, 0.0, theta)
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = img
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    for k, v in (('sun_threshold', 10.0), ('sun_angle', math.radians(1.1)), ('use_sun_shadow', True), ('sun_shadow_maximum_resolution', 0.001),
                 ('sun_shadow_filter_radius', 1.0), ('use_sun_shadow_jitter', True), ('sun_shadow_jitter_overblur', 12.0), ('probe_resolution', '1024')):
        try:
            setattr(w, k, v)
        except Exception as e:
            print('world', k, e)
    # color de la neblina = horizonte real del HDRI
    ng = haze_group()
    hc = ng.nodes.get('ColorNeblina')
    if hc is not None:
        hc.outputs[0].default_value = (hz[0] * strength * 0.82, hz[1] * strength * 0.86, hz[2] * strength * 0.9, 1.0)
    for wd in list(bpy.data.worlds):
        if wd.name != 'CB_Cielo' and wd.users == 0:
            bpy.data.worlds.remove(wd)
    sun_world = (math.cos(a_des) * math.cos(el), math.sin(a_des) * math.cos(el), math.sin(el))
    return {'elev_deg': math.degrees(el), 'theta': theta, 'haze': hz, 'max': mx, 'sun': sun_world}


def setup_render(samples=32):
    scn = bpy.context.scene
    ee = scn.eevee
    sets = (('use_shadows', True), ('shadow_ray_count', 2), ('shadow_step_count', 6), ('shadow_resolution_scale', 1.0),
            ('use_raytracing', True), ('ray_tracing_method', 'SCREEN'),
            ('use_fast_gi', True), ('fast_gi_method', 'GLOBAL_ILLUMINATION'), ('fast_gi_resolution', '2'), ('fast_gi_ray_count', 2),
            ('fast_gi_step_count', 8), ('fast_gi_quality', 0.3), ('fast_gi_distance', 30.0), ('fast_gi_thickness_near', 0.25),
            ('taa_samples', 16), ('taa_render_samples', samples), ('use_overscan', True), ('overscan_size', 4.0),
            ('motion_blur_steps', 1), ('use_volumetric_shadows', False))
    for k, v in sets:
        try:
            setattr(ee, k, v)
        except Exception as e:
            print('eevee', k, e)
    ro = ee.ray_tracing_options
    for k, v in (('resolution_scale', '2'), ('trace_max_roughness', 0.45), ('use_denoise', True), ('screen_trace_quality', 0.3), ('screen_trace_thickness', 0.3)):
        try:
            setattr(ro, k, v)
        except Exception as e:
            print('rt', k, e)
    r = scn.render
    r.use_motion_blur = True
    r.motion_blur_shutter = 0.28
    try:
        r.motion_blur_position = 'CENTER'
    except Exception:
        pass
    r.resolution_x = 1920
    r.resolution_y = 1080
    r.resolution_percentage = 100
    r.fps = 30
    r.fps_base = 1.0
    r.film_transparent = False
    import os
    os.makedirs(os.path.join(ROOT, "render", "frames"), exist_ok=True)
    try:
        r.image_settings.media_type = 'IMAGE'
    except Exception:
        pass
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGB'
    r.image_settings.color_depth = '8'
    r.image_settings.compression = 15
    r.filepath = os.path.join(ROOT, "render", "frames", "dron_")
    r.use_file_extension = True
    r.use_overwrite = True
    r.use_placeholder = False
    scn.view_settings.view_transform = 'AgX'
    for lk in ('AgX - Medium High Contrast', 'Medium High Contrast'):
        try:
            scn.view_settings.look = lk
            break
        except Exception:
            pass
    scn.view_settings.exposure = 0.0
    scn.view_settings.gamma = 1.0


def setup_compositor(bloom=0.22, vignette=0.32):
    """Brillo suave en altas luces, leve distorsion de lente y vineta (como camara de dron)."""
    scn = bpy.context.scene
    old = bpy.data.node_groups.get('CB_Compositor')
    if old is not None:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new('CB_Compositor', 'CompositorNodeTree')
    ng.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers')
    go = N.new('NodeGroupOutput')
    cur = rl.outputs['Image']
    try:
        gl = N.new('CompositorNodeGlare')
        for val in ('Bloom', 'BLOOM', 'Fog Glow', 'FOG_GLOW'):
            try:
                gl.inputs['Type'].default_value = val
                break
            except Exception:
                pass
        for k, v in (('Threshold', 1.6), ('Smoothness', 0.4), ('Strength', bloom), ('Saturation', 0.9), ('Size', 0.5)):
            try:
                gl.inputs[k].default_value = v
            except Exception as e:
                print('glare', k, e)
        L.new(cur, gl.inputs['Image'])
        cur = gl.outputs['Image']
    except Exception as e:
        print('glare fallo', e)
    try:
        ld = N.new('CompositorNodeLensdist')
        ld.inputs['Distortion'].default_value = -0.012
        ld.inputs['Dispersion'].default_value = 0.004
        try:
            ld.inputs['Fit'].default_value = True
        except Exception:
            pass
        L.new(cur, ld.inputs['Image'])
        cur = ld.outputs['Image']
    except Exception as e:
        print('lens fallo', e)
    try:
        el = N.new('CompositorNodeEllipseMask')
        el.inputs['Size'].default_value = (0.86, 0.8)
        bl = N.new('CompositorNodeBlur')
        bl.inputs['Size'].default_value = (220.0, 220.0)
        L.new(el.outputs[0], bl.inputs['Image'])
        mr = N.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = 1.0 - vignette
        mr.inputs['To Max'].default_value = 1.0
        L.new(bl.outputs[0], mr.inputs['Value'])
        mx = N.new('ShaderNodeMix')
        mx.data_type = 'RGBA'
        mx.blend_type = 'MULTIPLY'
        [s for s in mx.inputs if s.name == 'Factor' and s.type == 'VALUE'][0].default_value = 1.0
        L.new(cur, [s for s in mx.inputs if s.name == 'A' and s.type == 'RGBA'][0])
        L.new(mr.outputs[0], [s for s in mx.inputs if s.name == 'B' and s.type == 'RGBA'][0])
        cur = [s for s in mx.outputs if s.type == 'RGBA'][0]
    except Exception as e:
        print('vineta fallo', e)
    L.new(cur, go.inputs[0])
    scn.compositing_node_group = ng
    scn.render.use_compositing = True
    try:
        scn.render.compositor_device = 'GPU'
    except Exception:
        pass
    return ng


def street_along(name, cls, start_near):
    """Polilinea de una via, orientada desde el extremo mas cercano a start_near."""
    best = None
    for st in SC['streets']:
        if st['name'] != name or st['cls'] != cls:
            continue
        pts = [tuple(q) for q in st['pts']]
        for seq in (pts, pts[::-1]):
            dd = math.hypot(seq[0][0] - start_near[0], seq[0][1] - start_near[1])
            if best is None or dd < best[0]:
                best = (dd, seq)
    return best[1]


def poly_at(seq, s):
    acc = 0.0
    for q in range(len(seq) - 1):
        l = math.hypot(seq[q + 1][0] - seq[q][0], seq[q + 1][1] - seq[q][1])
        if acc + l >= s or q == len(seq) - 2:
            t = min(1.0, max(0.0, (s - acc) / max(l, 1e-6)))
            return (seq[q][0] + (seq[q + 1][0] - seq[q][0]) * t, seq[q][1] + (seq[q + 1][1] - seq[q][1]) * t)
        acc += l


def setup_cameras():
    scn = bpy.context.scene
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Luz_y_camaras', root)
    for ob in list(coll.objects):
        if ob.name == 'Cam_Dron':
            continue
        data = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)

    def cam(name, loc, target, lens=35.0):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_start = 0.4
        cd.clip_end = 12000.0
        ob = bpy.data.objects.new(name, cd)
        ob.location = loc
        dv = Vector(target) - Vector(loc)
        ob.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()
        coll.objects.link(ob)
        return ob

    def along(name, cls, start_near, s0, s1, h0=1.7, h1=3.0):
        seq = street_along(name, cls, start_near)
        a = poly_at(seq, s0)
        b = poly_at(seq, s1)
        return (a[0], a[1], T(a[0], a[1]) + h0), (b[0], b[1], T(b[0], b[1]) + h1)

    cx, cy = SC['specials']['chorro_centro']
    zc = T(cx, cy) + CURB
    c1 = cam('Cam_Aerea', (-285.0, -215.0, 118.0), (70.0, 5.0, 22.0), 30.0)
    cam('Cam_Cenital', (10.0, 0.0, 520.0), (10.0, 0.5, 0.0), 35.0)
    erm = [b for b in SC['buildings'] if b['kind'] == 'ermita']
    ex, ey = (np.asarray(erm[0]['ring']).mean(axis=0) if erm else (cx - 15, cy))
    vx, vy = cx - ex, cy - ey
    vl = math.hypot(vx, vy)
    cam('Cam_Chorro_de_Quevedo', (cx + vx / vl * 9.0 - vy / vl * 5.0, cy + vy / vl * 9.0 + vx / vl * 5.0, zc + 1.65), (ex + vx / vl * 4.0, ey + vy / vl * 4.0, zc + 3.2), 24.0)
    l, t = along('Calle 12B', 'veh', (-95.7, 55.2), 22.0, 90.0)
    cam('Cam_Calle_12B', l, t, 26.0)
    l, t = along('Carrera 3', 'veh', (4.45, -11.57), 12.0, 70.0)
    cam('Cam_Carrera_3', l, t, 26.0)
    l, t = along('Carrera 2', 'ped', (114.6, -83.86), 46.0, 95.0, 1.65, 2.6)
    cam('Cam_Callejon_del_Embudo', l, t, 22.0)
    if scn.camera is None or scn.camera.name not in bpy.data.objects:
        scn.camera = c1
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for sp in area.spaces:
                    if sp.type == 'VIEW_3D':
                        sp.clip_start = 0.5
                        sp.clip_end = 12000.0
    return c1
