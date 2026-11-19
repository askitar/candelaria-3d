"""Dibuja la ruta del dron sobre el plano de predios para revisarla."""
import sys, json
from PIL import Image, ImageDraw

sc = json.load(open(sys.argv[1], encoding='utf-8'))
dp = json.load(open(sys.argv[2]))
out = sys.argv[3]
X0, Y0, X1, Y1 = [float(v) for v in sys.argv[4:8]]
S = float(sys.argv[8]) if len(sys.argv) > 8 else 6.0
W, H = int((X1 - X0) * S), int((Y1 - Y0) * S)
img = Image.new('RGB', (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)


def P(p):
    return ((p[0] - X0) * S, H - (p[1] - Y0) * S)


for k, v in sc['roads'].items():
    for rings in v:
        d.polygon([P(p) for p in rings[0]], fill=(205, 205, 210))
for k, v in sc['ped'].items():
    for rings in v:
        d.polygon([P(p) for p in rings[0]], fill=(250, 238, 160) if k == 'plaza' else (200, 215, 235))
for b in sc['buildings']:
    col = (240, 205, 175) if b['levels'] == 1 else ((225, 175, 135) if b['levels'] == 2 else (200, 140, 100))
    if b['kind'] == 'ermita':
        col = (255, 120, 255)
    d.polygon([P(p) for p in b['ring']], fill=col, outline=(120, 70, 40))
c = sc['specials']['chorro_centro']
d.ellipse([P(c)[0] - 2.7 * S, P(c)[1] - 2.7 * S, P(c)[0] + 2.7 * S, P(c)[1] + 2.7 * S], outline=(0, 0, 200), width=2)
for st in sc['streets']:
    pts = [P(p) for p in st['pts']]
    d.line(pts, fill=(150, 150, 255) if st['cls'] == 'ped' else (170, 170, 170), width=1)
pp = dp['path']
for i in range(len(pp) - 1):
    hg = pp[i][4]
    col = (255, 0, 0) if hg < 6 else ((255, 140, 0) if hg < 14 else (0, 160, 0))
    d.line([P(pp[i][1:3]), P(pp[i + 1][1:3])], fill=col, width=3)
for i in range(0, len(pp), 10):
    p = pp[i]
    q = P(p[1:3])
    d.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], fill=(0, 0, 0))
    d.text((q[0] + 6, q[1] - 6), '%ds h%.0f' % (p[0], p[4]), fill=(0, 0, 0))
    l = P(p[5:7])
    dx, dy = l[0] - q[0], l[1] - q[1]
    ll = max(1e-6, (dx * dx + dy * dy) ** 0.5)
    d.line([q, (q[0] + dx / ll * 28, q[1] + dy / ll * 28)], fill=(0, 0, 255), width=2)
for gx in range(int(X0 // 10 * 10), int(X1) + 1, 10):
    d.line([((gx - X0) * S, 0), ((gx - X0) * S, 8)], fill=(0, 0, 0))
    if gx % 20 == 0:
        d.text(((gx - X0) * S + 2, 9), str(gx), fill=(0, 0, 0))
for gy in range(int(Y0 // 10 * 10), int(Y1) + 1, 10):
    d.line([(0, H - (gy - Y0) * S), (8, H - (gy - Y0) * S)], fill=(0, 0, 0))
    if gy % 20 == 0:
        d.text((10, H - (gy - Y0) * S - 5), str(gy), fill=(0, 0, 0))
img.save(out)
print(out, W, H)
