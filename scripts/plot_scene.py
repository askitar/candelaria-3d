import sys, json
from PIL import Image, ImageDraw

sc = json.load(open(sys.argv[1]))
out = sys.argv[2]
S = 3.6
X0, Y0, X1, Y1 = -215, -225, 235, 230
W, H = int((X1 - X0) * S), int((Y1 - Y0) * S)
img = Image.new('RGB', (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)


def P(p):
    return ((p[0] - X0) * S, H - (p[1] - Y0) * S)


def fill(polys, col, hole=(255, 255, 255)):
    for rings in polys:
        d.polygon([P(p) for p in rings[0]], fill=col)
        for h in rings[1:]:
            d.polygon([P(p) for p in h], fill=hole)


fill(sc['G'], (235, 235, 235))
fill(sc['interior'], (200, 225, 190), (235, 235, 235))
fill(sc['sidewalk'], (215, 210, 200), (200, 225, 190))
cols = {'asfalto': (90, 90, 95), 'adoquin': (170, 110, 90), 'empedrado': (130, 130, 110), 'losa': (180, 180, 170)}
for k, v in sc['roads'].items():
    for rings in v:
        d.polygon([P(p) for p in rings[0]], fill=cols[k])
        for h in rings[1:]:
            d.polygon([P(p) for p in h], fill=(215, 210, 200))
pc = {'plaza': (250, 235, 140), 'empedrado': (150, 170, 200), 'losa': (190, 200, 220), 'adoquin': (200, 150, 150)}
for k, v in sc['ped'].items():
    for rings in v:
        d.polygon([P(p) for p in rings[0]], fill=pc.get(k, (255, 0, 255)))
for b in sc['buildings']:
    r = b['ring']
    base = {1: (245, 215, 185), 2: (235, 190, 150), 3: (215, 160, 120)}.get(b['levels'], (200, 130, 100))
    if b['kind'] == 'moderno':
        base = (170, 170, 200)
    d.polygon([P(p) for p in r], fill=base)
    if b['patio']:
        d.polygon([P(p) for p in b['patio']], fill=(160, 210, 160), outline=(60, 120, 60))
    n = len(r)
    for i in range(n):
        a, c = r[i], r[(i + 1) % n]
        if b['street'][i]:
            col, wd = ((0, 90, 255) if b['ped'][i] else (220, 0, 0)), 3
        elif b['free'][i]:
            col, wd = (0, 150, 0), 1
        else:
            col, wd = (110, 110, 110), 1
        d.line([P(a), P(c)], fill=col, width=wd)
sp = sc['specials']
for b in sc['buildings']:
    if b['id'] == sp.get('ermita_id'):
        d.polygon([P(p) for p in b['ring']], outline=(255, 0, 255), width=4)
c = sp['chorro_centro']
d.ellipse([P(c)[0] - 5, P(c)[1] - 5, P(c)[0] + 5, P(c)[1] + 5], fill=(0, 0, 0))
for gx in range(-200, 240, 50):
    d.text(((gx - X0) * S, 3), str(gx), fill=(0, 0, 0))
for gy in range(-200, 240, 50):
    d.text((3, H - (gy - Y0) * S), str(gy), fill=(0, 0, 0))
img.save(out)
print(out, W, H)
