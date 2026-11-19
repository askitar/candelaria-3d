"""Baja una grilla de elevacion SRTM (opentopodata) para el sector y la guarda en data/elev.json."""
import json, math, sys, time, urllib.request

out = sys.argv[1]
LAT0, LON0 = 4.5975, -74.07025
MLAT = 110574.0
MLON = 111320.0 * math.cos(math.radians(LAT0))

xs = list(range(-360, 241, 40))
ys = list(range(-260, 321, 40))
pts = [(x, y) for y in ys for x in xs]
res = []
for i in range(0, len(pts), 90):
    chunk = pts[i:i + 90]
    loc = '|'.join(f'{LAT0 + y / MLAT:.6f},{LON0 + x / MLON:.6f}' for x, y in chunk)
    url = 'https://api.opentopodata.org/v1/srtm30m?locations=' + loc
    req = urllib.request.Request(url, headers={'User-Agent': 'blender-scene-builder/1.0'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read().decode('utf-8'))
            break
        except Exception as e:
            print('retry', attempt, e)
            time.sleep(2.5)
    else:
        raise SystemExit('elevation fetch failed')
    for (x, y), rr in zip(chunk, data['results']):
        res.append([x, y, rr['elevation']])
    time.sleep(1.3)
json.dump({'xs': xs, 'ys': ys, 'samples': res}, open(out, 'w'))
zs = [r[2] for r in res]
print('samples', len(res), 'min', min(zs), 'max', max(zs))
