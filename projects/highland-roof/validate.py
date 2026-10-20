"""Read back geometry, source controls, packed assets, cameras and export metadata."""
import csv
import hashlib
import json
import struct
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from PIL import Image, ImageStat
from geometry import inventory, digest, TRADES

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT/'deliverables/highland-roof'
I = .0254


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cfg = json.loads((HERE/'geometry.json').read_text())
    spec = json.loads((HERE/'geometry-revision.spec.json').read_text())
    baseline = json.loads((ROOT/cfg['base_spec']).read_text())
    assert {k:v for k,v in spec.items() if k != 'roof_geometry_revision'} == baseline
    geometry = json.loads((OUT/'geometry-validation.json').read_text())
    assert sha(ROOT/cfg['base_blend']) == geometry['base_blend_sha256']
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/cfg['base_blend']), load_ui=False, use_scripts=False)
    assert inventory() == geometry['before']
    divider_before = {name:[list(v.co) for v in bpy.data.objects[name].data.vertices] for name in geometry['window_dividers']}
    native = OUT/'Highland-roof-and-terrace-revised.blend'
    bpy.ops.wm.open_mainfile(filepath=str(native), load_ui=False, use_scripts=False)
    assert inventory() == geometry['after'] and len(inventory()) == 969
    assert geometry['unchanged_meshes'] == 914
    assert len(geometry['window_dividers']) == 8
    for name, before in divider_before.items():
        obj = bpy.data.objects[name]
        assert len(obj.data.vertices) == len(before) == 48
        for i in [*range(32),*range(40,48)]:
            assert list(obj.data.vertices[i].co) == before[i]
        lo = min(v.co.x for v in obj.data.vertices)
        hi = max(v.co.x for v in obj.data.vertices)
        ratio = (sum(v.co.x for v in obj.data.vertices[32:40])/8-lo)/(hi-lo)
        assert abs(ratio-obj['divider_fraction_from_min_x']) < 1e-5
    top_errors = {}
    for obj in bpy.data.collections['Roof'].objects:
        if obj.name.startswith('roof-parapet-') or any(obj.name.startswith(e['id']+'-cap-') for e in spec['roof_features']):
            measured = 342+max((obj.matrix_world@v.co).z for v in obj.data.vertices)/I/12
            top_errors[obj.name] = abs(measured-obj['top_elevation_ft'])
    assert max(top_errors.values()) < 1e-4
    for feature in spec['roof_features']:
        body=bpy.data.objects[feature['id']]
        assert abs(max(v.co.z for v in body.data.vertices)/I-(feature['top']-cfg['roof_coping']['tower_cap_thickness_in'])) < .001
    slab_errors = {}
    for level in spec['levels']:
        obj = bpy.data.objects['slab-'+level['name']]
        slab_errors[level['name']] = abs(max(v.co.z for v in obj.data.vertices)/I-level['z'])
    assert max(slab_errors.values()) < .001
    assert len(spec['openings']) == 175 and len(spec['rejected_candidates']) == 16
    assert len(bpy.data.scenes) == 2
    architecture = [o for trade in TRADES for o in bpy.data.collections[trade].objects if o.type=='MESH']
    corners = [o.matrix_world@Vector(c) for o in architecture for c in o.bound_box]
    lo = [min(p[k] for p in corners) for k in range(3)]
    hi = [max(p[k] for p in corners) for k in range(3)]
    envelope = [Vector((x,y,z)) for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
    camera_path = json.loads((OUT/'camera-path.json').read_text())
    margins = {}
    untagged = []
    for scene in bpy.data.scenes:
        bpy.context.window.scene = scene
        untagged += [o.name for o in scene.objects if o.type in ('MESH','CURVE') and not all(o.get(k) for k in ('source','status','basis'))]
        assert all(n.scene == scene for n in scene.compositing_node_group.nodes if n.bl_idname == 'CompositorNodeRLayers')
        if scene.name.startswith('Daylight'):
            assert scene.camera.animation_data is None
            fit = json.loads((OUT/'camera-fit.json').read_text())
            errors=[]
            for item in fit['landmarks']:
                p=world_to_camera_view(scene,scene.camera,Vector(item['position_m']))
                errors.append(((p.x*665-item['projected_pixel'][0])**2+((1-p.y)*441-item['projected_pixel'][1])**2)**.5)
            assert max(errors)<.001
            frames=[1]
        else:
            frames=range(1,433)
        minimum=1
        for frame in frames:
            scene.frame_set(frame)
            points=[world_to_camera_view(scene,scene.camera,p) for p in (corners if scene.name.startswith('Daylight') else envelope)]
            if not scene.name.startswith('Daylight'):
                recorded=camera_path[frame-1]
                assert recorded['frame']==frame
                assert (scene.camera.location-Vector(recorded['position_m'])).length < 1e-5
                forward=scene.camera.rotation_euler.to_quaternion()@Vector((0,0,-1))
                assert forward.dot((Vector(recorded['target_m'])-scene.camera.location).normalized()) > .999999
            minimum=min(minimum,min(min(p.x,p.y,1-p.x,1-p.y) for p in points))
            assert all(p.z>0 for p in points)
        assert minimum>.005
        margins[scene.name]=minimum
    assert not untagged
    external=[i.filepath for i in bpy.data.images if i.source=='FILE' and i.users and not i.packed_file]
    assert not external
    binary=(OUT/'Highland-geometry-revised.glb').read_bytes()
    magic,version,length=struct.unpack_from('<4sII',binary)
    assert (magic,version,length)==(b'glTF',2,len(binary))
    n,kind=struct.unpack_from('<I4s',binary,12)
    assert kind==b'JSON'
    gltf=json.loads(binary[20:20+n])
    nodes=[n for n in gltf['nodes'] if 'mesh' in n]
    assert all(all(n.get('extras',{}).get(k) for k in ('source','status','basis')) for n in nodes)
    assert set(geometry['after']) <= {n.get('name') for n in nodes}
    still=OUT/'Highland-daylight-geometry-revised.png'
    with Image.open(still) as im:
        assert im.size==(1995,1323)
        variation=max(ImageStat.Stat(im.convert('RGB').resize((128,128))).stddev)/255
        assert variation>.03
    with (OUT/'element-provenance.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['element','type','status','source','basis','datum_status','top_elevation_ft','datum_applies_to','height_status','height_uncertainty_in','divider_status','divider_fraction_from_min_x'])
        for obj in sorted(bpy.data.objects,key=lambda o:o.name):
            if obj.type in ('MESH','CURVE'):
                writer.writerow([obj.name,obj.type,*[obj.get(k,'') for k in ('status','source','basis','datum_status','top_elevation_ft','datum_applies_to','height_status','height_uncertainty_in','divider_status','divider_fraction_from_min_x')]])
    result={'native_readback':True,'scene_count':2,'architecture_meshes':969,'unchanged_architecture_meshes':914,
            'architecture_sha256':digest(inventory()),'registered_controls_and_opening_records_unchanged':True,
            'opening_inventory':175,'remaining_unresolved':16,'internal_window_bars_changed':8,
            'opening_bounds_glass_sills_perimeters_preserved':True,'maximum_parapet_top_error_ft':max(top_errors.values()),
            'maximum_slab_top_error_in':max(slab_errors.values()),'all_432_native_camera_frames_checked':True,
            'minimum_architectural_frame_margins':margins,'maximum_fit_projection_error_px':max(errors),
            'external_images_required':external,'untagged_geometry':untagged,'glb_mesh_nodes':len(nodes),
            'still_dimensions':[1995,1323],'pixel_standard_deviation':variation,
            'native_sha256':sha(native),'still_sha256':sha(still),'glb_sha256':hashlib.sha256(binary).hexdigest(),
            'scope':'Source-control and delivery consistency checks. Provisional scan heights/pane ratios and assumed complete components do not establish surveyed accuracy.'}
    (OUT/'delivery-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
