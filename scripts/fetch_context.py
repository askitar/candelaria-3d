"""Baja el entorno amplio: 4 teselas OSM (1.6 km x 1.6 km) y dos grillas de elevacion SRTM.

Uso: python -I fetch_context.py <carpeta_osm> <carpeta_data>
"""
import json, math, os, sys, time, urllib.request

OSM_DIR, DATA_DIR = sys.argv[1], sys.argv[2]
LAT0, LON0 = 4.5975, -74.07025
MLAT = 110574.0
MLON = 111320.0 * math.cos(math.radians(LAT0))
SHIFT = (-65.0, 30.0)
UA = {'User-Agent': 'blender-scene-builder/1.0'}


def ll(x, y):
    """Coordenadas de escena (m) -> lat, lon."""
    return LAT0 + (y + SHIFT[1]) / MLAT, LON0 + (x + SHIFT[0]) / MLON


def get(url, timeout=90):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            print('reintento', attempt, str(e)[:120], flush=True)
            time.sleep(3 + attempt * 2)
    raise SystemExit('fallo: ' + url[:100])


# ---- OSM en 4 teselas
R = 800.0
edges = [-R, 0.0, R]
for i in range(2):
    for j in range(2):
        out = os.path.join(OSM_DIR, 'ctx_%d%d.osm' % (i, j))
        if os.path.exists(out) and os.path.getsize(out) > 10000:
            print('ya existe', out, flush=True)
            continue
        la0, lo0 = ll(edges[i], edges[j])
        la1, lo1 = ll(edges[i + 1], edges[j + 1])
        url = 'https://api.openstreetmap.org/api/0.6/map?bbox=%.6f,%.6f,%.6f,%.6f' % (lo0, la0, lo1, la1)
        data = get(url, 120)
        open(out, 'wb').write(data)
        print('osm', out, len(data), flush=True)
        time.sleep(2)


# ---- elevacion
def grid(name, xs, ys):
    out = os.path.join(DATA_DIR, name)
    if os.path.exists(out):
        print('ya existe', out, flush=True)
        return
    pts = [(x, y) for y in ys for x in xs]
    zs = []
    for k in range(0, len(pts), 100):
        chunk = pts[k:k + 100]
        loc = '|'.join('%.6f,%.6f' % ll(x, y) for x, y in chunk)
        data = json.loads(get('https://api.opentopodata.org/v1/srtm30m?locations=' + loc, 60).decode('utf-8'))
        zs.extend(r['elevation'] for r in data['results'])
        time.sleep(1.15)
        if (k // 100) % 5 == 0:
            print(name, k, '/', len(pts), flush=True)
    json.dump({'xs': xs, 'ys': ys, 'z': zs}, open(out, 'w'))
    print(name, 'ok', len(zs), min(zs), max(zs), flush=True)


grid('elev_near.json', list(range(-960, 961, 40)), list(range(-960, 961, 40)))
grid('elev_far.json', list(range(-3600, 3901, 150)), list(range(-3600, 3601, 150)))
print('LISTO', flush=True)
