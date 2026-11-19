"""Recorrido de dron por La Candelaria: camara animada 'Cam_Dron' con posicion y objetivo interpolados."""

TSCALE = 0.85  # factor de tiempo del recorrido (menor = mas rapido)


def _hermite(ts, ps, t):
    """Interpolacion cubica de Hermite (tangentes por diferencias finitas, reposo en los extremos)."""
    n = len(ts)
    P = np.asarray(ps, dtype=float)
    m = np.zeros_like(P)
    for i in range(1, n - 1):
        m[i] = 0.5 * ((P[i + 1] - P[i]) / (ts[i + 1] - ts[i]) + (P[i] - P[i - 1]) / (ts[i] - ts[i - 1]))
    if t <= ts[0]:
        return P[0]
    if t >= ts[-1]:
        return P[-1]
    k = max(0, min(n - 2, int(np.searchsorted(ts, t) - 1)))
    h = ts[k + 1] - ts[k]
    s = (t - ts[k]) / h
    h00 = 2 * s ** 3 - 3 * s ** 2 + 1
    h10 = s ** 3 - 2 * s ** 2 + s
    h01 = -2 * s ** 3 + 3 * s ** 2
    h11 = s ** 3 - s ** 2
    return h00 * P[k] + h10 * h * m[k] + h01 * P[k + 1] + h11 * h * m[k + 1]


def drone_keys():
    """Puntos de control: (tiempo s, posicion xyz, objetivo xyz)."""
    c12b = street_along('Calle 12B', 'veh', (-95.7, 55.2))      # de la Carrera 4 hacia el oriente
    emb = street_along('Carrera 2', 'ped', (114.6, -83.86))     # callejon del Embudo, de sur a norte
    cx, cy = SC['specials']['chorro_centro']
    erm = [b for b in SC['buildings'] if b['kind'] == 'ermita']
    ex, ey = (np.asarray(erm[0]['ring']).mean(axis=0) if erm else (cx - 15, cy))
    vx, vy = cx - ex, cy - ey
    vl = math.hypot(vx, vy)
    efx, efy = ex + vx / vl * 5.0, ey + vy / vl * 5.0             # frente de la ermita

    def g(p, h):
        return (p[0], p[1], T(p[0], p[1]) + h)

    def s12(s, h):
        return g(poly_at(c12b, s), h)

    def se(s, h):
        return g(poly_at(emb, s), h)

    SE0 = 0.0
    acc = 0.0
    for q in range(len(emb) - 1):
        if abs(emb[q][0] - 122.91) < 0.2 and abs(emb[q][1] + 43.7) < 0.2:
            SE0 = acc
        acc += math.hypot(emb[q + 1][0] - emb[q][0], emb[q + 1][1] - emb[q][1])

    d0 = (c12b[1][0] - c12b[0][0], c12b[1][1] - c12b[0][1])
    dl = math.hypot(d0[0], d0[1])
    back = (c12b[0][0] - d0[0] / dl * 95.0, c12b[0][1] - d0[1] / dl * 95.0)
    zc = T(cx, cy)
    erm_t = (efx - 1.5, efy, T(efx, efy) + 3.4)
    K = []
    # 1) llegada desde el aire sobre la Calle 12B
    K.append((0.0, g(back, 86.0), s12(150.0, 6.0)))
    K.append((5.0, s12(52.0, 27.0), s12(150.0, 5.0)))
    K.append((9.0, s12(121.0, 10.8), s12(200.0, 4.5)))
    K.append((14.0, s12(182.0, 5.6), s12(250.0, 3.5)))
    # 2) entrada al Chorro de Quevedo y giro alrededor de la fuente (lado sur y oriente, el libre)
    K.append((17.8, s12(237.0, 3.9), (cx - 2.0, cy - 1.0, zc + 2.4)))
    K.append((19.3, g((cx - 11.6, cy - 17.2), 3.7), (cx - 6.0, cy + 1.0, zc + 2.8)))
    K.append((20.9, g((cx - 5.2, cy - 12.9), 3.5), erm_t))
    K.append((22.6, g((cx - 0.4, cy - 5.1), 3.3), erm_t))
    K.append((25.0, g((cx + 6.8, cy - 0.6), 3.3), (cx - 13.0, cy + 2.0, zc + 3.2)))
    K.append((27.3, g((cx + 4.6, cy + 8.4), 3.2), se(SE0 + 14.0, 3.2)))
    # 3) Callejon del Embudo, centrado y por debajo de los balcones
    K.append((29.6, se(SE0, 2.8), se(SE0 + 34.0, 2.9)))
    K.append((31.4, se(SE0 + 9.3, 2.6), se(SE0 + 45.0, 2.9)))
    K.append((35.6, se(SE0 + 38.9, 2.6), se(SE0 + 76.0, 3.4)))
    K.append((38.2, se(SE0 + 57.2, 3.0), se(SE0 + 92.0, 6.0)))
    # 4) salida vertical entre los aleros y vista final sobre los tejados
    K.append((40.2, se(SE0 + 70.0, 8.5), se(SE0 + 96.0, 12.0)))
    pe = poly_at(emb, SE0 + 86.0)
    K.append((43.0, g((pe[0] + 2.0, pe[1] + 1.0), 38.0), g((40.0, 0.0), 9.0)))
    K.append((47.5, g((pe[0] + 44.0, pe[1] + 34.0), 98.0), g((-25.0, -5.0), 8.0)))
    return [(t * TSCALE, p, l) for (t, p, l) in K]


def _wall_rays():
    segs = []
    for b in SC['buildings']:
        segs.extend(ring_segs([tuple(q) for q in b['ring']]))
    S = np.asarray(segs)

    def ray(p, n, R=9.0):
        near = S[(np.minimum(S[:, 0], S[:, 2]) < p[0] + R) & (np.maximum(S[:, 0], S[:, 2]) > p[0] - R) &
                 (np.minimum(S[:, 1], S[:, 3]) < p[1] + R) & (np.maximum(S[:, 1], S[:, 3]) > p[1] - R)]
        if not len(near):
            return R
        qx = near[:, 0] - p[0]
        qy = near[:, 1] - p[1]
        ex = near[:, 2] - near[:, 0]
        ey = near[:, 3] - near[:, 1]
        den = n[0] * ey - n[1] * ex
        ok = np.abs(den) > 1e-9
        den = np.where(ok, den, 1.0)
        sv = (qx * ey - qy * ex) / den
        u = (qx * n[1] - qy * n[0]) / den
        hit = ok & (sv > 0) & (u >= 0) & (u <= 1)
        return float(sv[hit].min()) if hit.any() else R

    def nearest(p):
        near = S[(np.abs(S[:, 0] - p[0]) < 30) & (np.abs(S[:, 1] - p[1]) < 30)]
        return float(seg_dist_np(np.asarray([[p[0], p[1]]]), near).min()) if len(near) else 99.0

    return ray, nearest


def drone_samples(fps=30):
    """Posicion y objetivo por cuadro, con la ruta centrada entre fachadas en los tramos bajos."""
    K = drone_keys()
    ts = [k[0] for k in K]
    ps = [k[1] for k in K]
    ls = [k[2] for k in K]
    nfr = int(round(ts[-1] * fps)) + 1
    Pp = np.array([_hermite(ts, ps, f / fps) for f in range(nfr)])
    Ll = np.array([_hermite(ts, ls, f / fps) for f in range(nfr)])
    ray, nearest = _wall_rays()
    hg = Pp[:, 2] - T_np(Pp[:, :2])
    off = np.zeros(nfr)
    NL = np.zeros((nfr, 2))
    for f in range(nfr):
        a = Pp[max(0, f - 1)]
        b = Pp[min(nfr - 1, f + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        l = math.hypot(dx, dy) or 1.0
        NL[f] = (-dy / l, dx / l)
        if hg[f] < 12.0:
            dL = ray(Pp[f], NL[f])
            dR = ray(Pp[f], (-NL[f][0], -NL[f][1]))
            if dL < 9.0 and dR < 9.0:
                off[f] = (dL - dR) / 2.0
            elif dL < 2.4:
                off[f] = dL - 2.4
            elif dR < 2.4:
                off[f] = 2.4 - dR
    ker = np.ones(41) / 41.0
    for _ in range(2):
        off = np.convolve(np.pad(off, 20, mode='edge'), ker, mode='valid')
    Pp[:, 0] += NL[:, 0] * off
    Pp[:, 1] += NL[:, 1] * off
    # vaiven minimo del estabilizador, como en una toma real de dron
    for f in range(nfr):
        t = f / fps
        dv = Ll[f] - Pp[f]
        dist = float(np.linalg.norm(dv))
        if dist < 1e-3:
            continue
        dn = dv / dist
        right = np.array([dn[1], -dn[0], 0.0])
        rl = float(np.linalg.norm(right)) or 1.0
        right = right / rl
        sx = math.sin(2 * math.pi * 0.27 * t + 1.3) + 0.6 * math.sin(2 * math.pi * 0.71 * t + 0.4)
        sz = math.sin(2 * math.pi * 0.33 * t + 2.1) + 0.5 * math.sin(2 * math.pi * 0.83 * t + 0.9)
        Ll[f] = Ll[f] + right * dist * 0.0022 * sx + np.array([0.0, 0.0, 1.0]) * dist * 0.0015 * sz
    clear = np.array([nearest(Pp[f]) if hg[f] < 12.0 else 99.0 for f in range(nfr)])
    return Pp, Ll, hg, clear, ts[-1]


def build_drone(fps=30, lens=20.0):
    scn = bpy.context.scene
    root = get_coll('La_Candelaria')
    coll = get_coll('CB_Luz_y_camaras', root)
    old = bpy.data.objects.get('Cam_Dron')
    if old is not None:
        cd_old = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if cd_old.users == 0:
            bpy.data.cameras.remove(cd_old)
    for act in list(bpy.data.actions):
        if act.users == 0:
            bpy.data.actions.remove(act)
    cd = bpy.data.cameras.new('Cam_Dron')
    cd.lens = lens
    cd.sensor_width = 36.0
    cd.clip_start = 0.3
    cd.clip_end = 12000.0
    cam = bpy.data.objects.new('Cam_Dron', cd)
    coll.objects.link(cam)
    cam.rotation_mode = 'QUATERNION'
    Pp, Ll, hg, clear, dur = drone_samples(fps)
    nfr = len(Pp)
    scn.render.fps = fps
    scn.frame_start = 1
    scn.frame_end = nfr
    prevq = None
    for f in range(nfr):
        p = Pp[f]
        l = Ll[f]
        dv = Vector((l[0] - p[0], l[1] - p[1], l[2] - p[2]))
        q = dv.to_track_quat('-Z', 'Y')
        if prevq is not None and q.dot(prevq) < 0:
            q.negate()
        prevq = q.copy()
        cam.location = (float(p[0]), float(p[1]), float(p[2]))
        cam.rotation_quaternion = q
        cam.keyframe_insert('location', frame=f + 1)
        cam.keyframe_insert('rotation_quaternion', frame=f + 1)
    scn.camera = cam
    scn.frame_set(1)
    k = int(clear.argmin())
    spd = np.hypot(np.diff(Pp[:, 0]), np.diff(Pp[:, 1])) * fps
    print('dron: %d cuadros (%.1f s a %d fps); minima distancia a fachada %.2f m en t=%.1f s (altura %.1f); altura minima %.1f m; velocidad max baja %.1f m/s' % (
        nfr, dur, fps, float(clear[k]), k / fps, float(hg[k]), float(hg.min()), float(spd[hg[1:] < 12].max())))
    low = hg < 13.0
    return Pp[low][:, :2]
