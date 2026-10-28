"""Poly Haven CC0 textures and models, locked by checksum, shared by every site.

A project configures this module, then calls it (see projects/*/…/cinema_assets.py, assets.py):

    from bmodels import polyhaven as ph
    ph.LOCK = HERE / "assets/polyhaven.lock.json"     # committed: URL, size and MD5 of every file
    ph.TEXTURES = {"concrete": "2k"}; ph.MODELS = {"cement_bag": "1k"}; ph.PARTS = {}

`lock()` records every file's URL, size and MD5 from the Poly Haven API in LOCK; `fetch()`
downloads exactly those files into build/assets/polyhaven and verifies them. Files are not
committed. Textures are box-projected in real-world units, so procedural boxes need no UV
unwrap. All assets are illustrative dressing.
"""
import hashlib
import json
import math
import random
import sys
import urllib.request
from pathlib import Path

from bmodels.paths import ROOT

LOCK = None  # set by the project before lock()/fetch()
CACHE = ROOT/'build/assets/polyhaven'
I = .0254
TEXTURES = {}  # id: resolution
MAPS = {'diff': 'Diffuse', 'rough': 'Rough', 'disp': 'Displacement'}
MODELS = {}    # id: resolution
PARTS = {}     # id: predicate on object name, for model files that hold variants side by side
API = 'https://api.polyhaven.com'


def api(path):
    req = urllib.request.Request(API+path, headers={'User-Agent': 'highland-cinema-build'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def lock():
    """Resolve the asset list to concrete files with sizes and MD5 checksums."""
    files, info = [], {}
    for tid, res in TEXTURES.items():
        d = api(f'/files/{tid}'); meta = api(f'/info/{tid}')
        info[tid] = {'type': 'texture', 'resolution': res, 'dimensions_mm': meta.get('dimensions')}
        for key, name in MAPS.items():
            f = d[name][res]['jpg']
            files.append({'asset': tid, 'path': f'{tid}/{tid}_{key}_{res}.jpg', 'url': f['url'], 'size': f['size'], 'md5': f['md5']})
    for mid, res in MODELS.items():
        b = api(f'/files/{mid}')['blend'][res]['blend']; meta = api(f'/info/{mid}')
        info[mid] = {'type': 'model', 'resolution': res, 'dimensions_mm': meta.get('dimensions')}
        files.append({'asset': mid, 'path': f'{mid}/{mid}_{res}.blend', 'url': b['url'], 'size': b['size'], 'md5': b['md5']})
        for rel, f in b.get('include', {}).items():
            files.append({'asset': mid, 'path': f'{mid}/{rel}', 'url': f['url'], 'size': f['size'], 'md5': f['md5']})
    data = {'source': 'Poly Haven (polyhaven.com), CC0 1.0', 'assets': info, 'files': files,
            'total_mb': round(sum(f['size'] for f in files)/1e6, 1)}
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(data, indent=1)+'\n')
    return data


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch():
    """Download the locked files once, verifying each MD5."""
    data = json.loads(LOCK.read_text())
    for f in data['files']:
        path = CACHE/f['path']
        if path.exists() and path.stat().st_size == f['size'] and md5(path) == f['md5']:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix+'.part')
        tmp.unlink(missing_ok=True)
        for attempt in range(6):
            # Resume interrupted transfers with a Range request.
            have = tmp.stat().st_size if tmp.exists() else 0
            if have >= f['size']:
                break
            req = urllib.request.Request(f['url'], headers={'User-Agent': 'highland-cinema-build', 'Range': f'bytes={have}-'})
            try:
                with urllib.request.urlopen(req, timeout=300) as r, open(tmp, 'ab' if have and r.status == 206 else 'wb') as out:
                    for chunk in iter(lambda: r.read(1 << 20), b''):
                        out.write(chunk)
            except Exception as e:
                print(f'retry {attempt+1} {f["path"]}: {e}', flush=True)
        if md5(tmp) != f['md5']:
            tmp.unlink(); raise SystemExit(f'Checksum mismatch for {f["url"]}')
        tmp.rename(path)
    return data


# ---------------------------------------------------------------- Blender side

def tile_m(data, tid):
    return data['assets'][tid]['dimensions_mm'][0]/1000


def image(path, colorspace):
    import bpy
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def rotated(path):
    """A 90-degree copy, so box projection runs wood grain vertically on walls and doors."""
    out = path.with_name(path.stem+'_rot90'+path.suffix)
    if not out.exists():
        from PIL import Image
        Image.open(path).transpose(Image.Transpose.ROTATE_90).save(out, quality=95)
    return out


def pbr(mat, data, tid, tint=(1, 1, 1), rough=(0, 1), bump=.25, scale=1., rotate=0., wet=False, coord='Object', vertical=False, variation=1.):
    """Drive an existing Principled BSDF from a box-projected texture set, keeping any
    wrapper shaders (the x-ray section mix) intact."""
    n, l = mat.node_tree.nodes, mat.node_tree.links
    b = n.get('Principled BSDF')
    for name in ('Base Color', 'Roughness', 'Normal'):
        for link in list(b.inputs[name].links):
            l.remove(link)
    res = data['assets'][tid]['resolution']
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1/(tile_m(data, tid)*scale),)*3
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(rotate))
    l.new(tc.outputs[coord], mp.inputs['Vector'])

    def tex(key, colorspace):
        path = CACHE/tid/f'{tid}_{key}_{res}.jpg'
        t = n.new('ShaderNodeTexImage'); t.image = image(rotated(path) if vertical else path, colorspace)
        t.projection = 'BOX'; t.projection_blend = .2; t.interpolation = 'Cubic'
        l.new(mp.outputs[0], t.inputs['Vector']); return t
    diff, rgh, disp = tex('diff', 'sRGB'), tex('rough', 'Non-Color'), tex('disp', 'Non-Color')
    # variation < 1 keeps a flat finish colour (paint) with only a trace of the scan's tone.
    tone = n.new('ShaderNodeMix'); tone.data_type = 'RGBA'; tone.inputs['Factor'].default_value = variation
    tone.inputs['A'].default_value = (.75, .75, .75, 1); l.new(diff.outputs['Color'], tone.inputs['B'])
    tinted = n.new('ShaderNodeMix'); tinted.data_type = 'RGBA'; tinted.blend_type = 'MULTIPLY'
    tinted.inputs['Factor'].default_value = 1; tinted.inputs['B'].default_value = (*tint, 1)
    l.new(tone.outputs['Result'], tinted.inputs['A'])
    r = n.new('ShaderNodeMapRange'); r.inputs['To Min'].default_value, r.inputs['To Max'].default_value = rough
    l.new(rgh.outputs['Color'], r.inputs['Value'])
    bp = n.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = .004*scale
    l.new(disp.outputs['Color'], bp.inputs['Height'])
    color, roughness = tinted.outputs['Result'], r.outputs['Result']
    if wet:
        # Puddles: a low-frequency mask darkens the surface and makes it glossy.
        nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .22; nz.inputs['Detail'].default_value = 5
        l.new(tc.outputs[coord], nz.inputs['Vector'])
        mask = n.new('ShaderNodeMapRange'); mask.inputs['From Min'].default_value = .57; mask.inputs['From Max'].default_value = .62
        l.new(nz.outputs['Fac'], mask.inputs['Value'])
        dark = n.new('ShaderNodeMix'); dark.data_type = 'RGBA'; dark.blend_type = 'MULTIPLY'
        dark.inputs['B'].default_value = (.45, .47, .5, 1); l.new(mask.outputs['Result'], dark.inputs['Factor']); l.new(color, dark.inputs['A'])
        gloss = n.new('ShaderNodeMix'); gloss.inputs['B'].default_value = .03
        l.new(mask.outputs['Result'], gloss.inputs['Factor']); l.new(roughness, gloss.inputs['A'])
        flat = n.new('ShaderNodeMix'); flat.data_type = 'VECTOR'
        geo = n.new('ShaderNodeNewGeometry'); l.new(mask.outputs['Result'], flat.inputs['Factor'])
        l.new(bp.outputs['Normal'], flat.inputs[4]); l.new(geo.outputs['Normal'], flat.inputs[5])
        color, roughness, normal = dark.outputs['Result'], gloss.outputs['Result'], flat.outputs[1]
    else:
        normal = bp.outputs['Normal']
    l.new(color, b.inputs['Base Color']); l.new(roughness, b.inputs['Roughness']); l.new(normal, b.inputs['Normal'])
    mat['texture'] = f'Poly Haven {tid} ({res}), CC0'
    return mat


def library(scene, data):
    """Append each model once into a hidden collection for instancing."""
    import bpy
    root = bpy.data.collections.get('Cinema assets / Poly Haven CC0 sources')
    if not root:
        root = bpy.data.collections.new('Cinema assets / Poly Haven CC0 sources'); scene.collection.children.link(root)
    out = {}
    for mid, res in MODELS.items():
        col = bpy.data.collections.new('Poly Haven / '+mid); root.children.link(col)
        with bpy.data.libraries.load(str(CACHE/mid/f'{mid}_{res}.blend'), link=False) as (src, dst):
            dst.objects = [name for name in src.objects]
        keep = PARTS.get(mid, lambda name: True)
        for o in dst.objects:
            if o is not None and o.type in ('MESH', 'EMPTY', 'CURVE') and keep(o.name):
                col.objects.link(o)
        # Instance origin at the footprint centre, on the lowest point.
        meshes = [o for o in col.objects if o.type == 'MESH']
        pts = [o.matrix_world@__import__('mathutils').Vector(c) for o in meshes for c in o.bound_box]
        lo = [min(p[k] for p in pts) for k in range(3)]; hi = [max(p[k] for p in pts) for k in range(3)]
        col.instance_offset = ((lo[0]+hi[0])/2, (lo[1]+hi[1])/2, lo[2])
        col['source'] = f'Poly Haven {mid} ({res}), CC0'
        out[mid] = (col, [hi[k]-lo[k] for k in range(3)])
    bpy.context.view_layer.update()
    for lc in bpy.context.view_layer.layer_collection.children:
        if lc.collection == root:
            lc.exclude = True
    return out


def instance(lib, mid, col, loc, yaw=0., scale=1., name=None):
    import bpy
    e = bpy.data.objects.new(name or 'Instance / '+mid, None)
    e.instance_type = 'COLLECTION'; e.instance_collection = lib[mid][0]
    e.location = loc; e.rotation_euler = (0, 0, yaw); e.scale = (scale,)*3
    e['basis'] = 'Illustrative dressing; Poly Haven CC0 model'
    col.objects.link(e)
    return e


def ground(scene, x, y, top=40.):
    """Height of the first surface below (x, y), in metres."""
    import bpy
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = scene.ray_cast(dg, Vector((x, y, top)), Vector((0, 0, -1)))
    return loc.z if hit else 0.
