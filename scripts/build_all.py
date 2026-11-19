"""Reconstruye toda la escena de La Candelaria dentro de Blender (v2 realista).

En Blender: Scripting > abrir este archivo > Run Script.
Necesita data/scene.json y data/context.json (los generan preprocess.py y preprocess_ctx.py)
y las texturas de Poly Haven ya importadas en el archivo .blend.
"""
import bpy, os, time

# Project root = folder that holds candelaria.blend (or set CANDELARIA_ROOT).
ROOT_DIR = os.environ.get("CANDELARIA_ROOT") or os.path.dirname(bpy.data.filepath)
P = os.path.join(ROOT_DIR, "scripts") + os.sep
t0 = time.time()
ns = {}
bpy.app.driver_namespace['CB'] = ns
for f in ('cb_lib.py', 'cb_mats.py', 'cb_ground.py', 'cb_build.py', 'cb_extras.py', 'cb_context.py', 'cb_world.py', 'cb_anim.py'):
    exec(compile(open(P + f, encoding='utf-8').read(), f, 'exec'), ns)

for name in ('Cube', 'Light', 'Camera'):
    ob = bpy.data.objects.get(name)
    if ob is not None and ob.users_collection and ob.users_collection[0].name == 'Collection':
        bpy.data.objects.remove(ob, do_unlink=True)


def step(label, fn, *a):
    t1 = time.time()
    r = fn(*a)
    print('%-22s %5.1f s  %s' % (label, time.time() - t1, r if not isinstance(r, dict) else ''))
    return r


M = step('materiales', ns['make_materials'])
ns['M'] = M
step('suelo', ns['build_ground'], M)
st = step('casas', ns['build_buildings'], M)
ns['PATIOS'] = st.pop('patios')
print('   ', st)
step('plazoleta', ns['build_plaza'], M)
step('arboles', ns['build_trees'], M)
step('terreno entorno', ns['build_far'], M)
step('vias entorno', ns['build_ctx_roads'], M)
step('edificios entorno', ns['build_ctx_buildings'], M)
step('arboles entorno', ns['build_ctx_trees'], M)
info = step('cielo', ns['setup_world'])
print('    sol: elevacion %.1f grados' % info['elev_deg'])
ns['setup_render']()
ns['setup_compositor']()
ns['setup_cameras']()
path = step('recorrido dron', ns['build_drone'])
step('mobiliario', ns['build_furniture'], M, path)
for nm in ('CB_Ciudad', 'CB_Cerros'):
    m = bpy.data.materials.get(nm)
    if m is not None and m.users == 0:
        bpy.data.materials.remove(m)
print('listo en %.1f s' % (time.time() - t0))
