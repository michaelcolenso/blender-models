"""Read back native meshes, protected controls, source links and portable export."""
import hashlib
import csv
import json
import struct
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from build import inventory

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'deliverables/highland-drawings'
I=.0254


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    spec=json.loads((HERE/'reconciled.spec.json').read_text())
    cfg=json.loads((HERE/'decisions.json').read_text())
    base=json.loads((ROOT/cfg['base_spec']).read_text())
    ledger=json.loads((OUT/'change-ledger.json').read_text())
    geometry=json.loads((OUT/'geometry-validation.json').read_text())
    audit=json.loads((OUT/'opening-audit.json').read_text())
    native=OUT/'Highland-drawing-reconciled.blend'
    assert geometry['native_sha256']==sha(native)
    assert geometry['revised_spec_sha256']==sha(HERE/'reconciled.spec.json')
    assert len(spec['openings'])==189 and len(spec['rejected_candidates'])==2
    assert (audit['accepted_candidates'],audit['rejected_candidates'],audit['remaining_unresolved'])==(13,1,2)
    protected=('polygons','levels','grid_dimensions_in','roof_features','roof_plate_z','north_roof_plate_z','north_roof_split_y')
    for key in protected:assert spec[key]==base[key]
    bpy.ops.wm.open_mainfile(filepath=str(native),load_ui=False,use_scripts=False)
    assert inventory()==geometry['after']
    expected_scenes={'Daylight / drawing reconciliation 04','Dusk / drawing reconciliation 04'}
    assert set(bpy.data.scenes.keys())==expected_scenes
    missing=[o.name for o in bpy.data.objects if o.type in ('MESH','CURVE') and not all(o.get(k) for k in ('source','basis','status'))]
    assert not missing,missing[:20]
    assert all(im.packed_file for im in bpy.data.images if im.source=='FILE')
    largest_error=0
    for c in ledger['opening_changes']:
        e=c['new'];o=bpy.data.objects[e['id']+'-frames']
        pts=[o.matrix_world@v.co for v in o.data.vertices]
        measured=[min(p.x for p in pts)/I,max(p.x for p in pts)/I,min(p.z for p in pts)/I,max(p.z for p in pts)/I]
        target=[e['u']-e['width']/2,e['u']+e['width']/2,e['z'],e['z']+e['height']]
        largest_error=max(largest_error,max(abs(a-b) for a,b in zip(measured,target)))
        assert max(abs(a-b) for a,b in zip(measured,target))<.001,e['id']
        assert o['reference_opening']==e['id'] and o['scheduled_size_verified']==False
    # No two opening voids overlap on a corrected wall, including retained records.
    patched={(e['new']['level'],e['new']['segment']) for e in ledger['opening_changes']}
    for level,segment in patched:
        ops=[e for e in spec['openings'] if e['level']==level and e['segment']==segment]
        for i,e in enumerate(ops):
            for other in ops[i+1:]:
                horizontal=min(e['u']+e['width']/2,other['u']+other['width']/2)-max(e['u']-e['width']/2,other['u']-other['width']/2)
                vertical=min(e['z']+e['height'],other['z']+other['height'])-max(e['z'],other['z'])
                assert horizontal<=0 or vertical<=0,(e['id'],other['id'])
    for level in ('R2','R3','R4','R5'):
        assert len([e for e in spec['openings'] if e['face']=='north' and e['level']==level])==6
    # Verify all architecture is present in the portable GLB.
    glb=OUT/'Highland-drawing-reconciled.glb'
    data=glb.read_bytes();magic,version,length=struct.unpack_from('<4sII',data)
    assert (magic,version,length)==(b'glTF',2,len(data))
    size,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
    doc=json.loads(data[20:20+size]);names={node['name'] for node in doc['nodes'] if 'mesh' in node}
    assert set(geometry['after'])<=names,set(geometry['after'])-names
    architecture=[bpy.data.objects[name] for name in geometry['after']]
    corners=[o.matrix_world@Vector(v) for o in architecture for v in o.bound_box]
    lo=Vector([min(v[k] for v in corners) for k in range(3)])
    hi=Vector([max(v[k] for v in corners) for k in range(3)])
    bounds=[Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)]
    margins={}
    for scene in bpy.data.scenes:
        frames=range(1,433) if scene.name.startswith('Dusk') else (scene.frame_current,)
        minimum=1
        for frame in frames:
            scene.frame_set(frame);bpy.context.window.scene=scene;bpy.context.view_layer.update()
            # The photo camera is fitted to the stepped building silhouette;
            # empty corners of its global box extend outside that silhouette.
            points=[world_to_camera_view(scene,scene.camera,p) for p in (bounds if scene.name.startswith('Dusk') else corners)]
            minimum=min(minimum,min(min(p.x,p.y,1-p.x,1-p.y) for p in points))
        assert minimum>.015,(scene.name,minimum)
        margins[scene.name]=minimum
    report={'status':'PASS','native_sha256':sha(native),'glb_sha256':sha(glb),
        'opening_inventory':189,'accepted_candidates':13,'rejected_candidates':1,'unresolved_candidates':2,
        'changed_opening_records':len(ledger['opening_changes']),'architecture_meshes':len(geometry['after']),
        'unchanged_architecture_meshes':geometry['unchanged_meshes'],'protected_spec_controls':list(protected),
        'roof_geometry_unchanged':True,'corrected_wall_void_overlaps':0,'north_R2_to_R5_count_per_floor':6,
        'frame_readback_max_error_in':largest_error,'frame_readback_error_note':'Floating-point consistency with the spec; not source accuracy.',
        'missing_source_tags':missing,'external_image_dependencies':0,'glb_mesh_nodes':len(names),
        'saved_scenes':sorted(expected_scenes),'camera_frames_checked':432,'minimum_camera_margin':margins,
        'source_pdf_sha256':{s['file']:sha(HERE/'references'/s['file']) for s in cfg['sources']}}
    (OUT/'delivery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    with (OUT/'element-provenance.csv').open('w',newline='') as stream:
        fields=('name','collections','status','xy_status','source','basis')
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for obj in sorted(bpy.data.objects,key=lambda o:o.name):
            if obj.type not in ('MESH','CURVE'):continue
            writer.writerow({'name':obj.name,'collections':'; '.join(c.name for c in obj.users_collection),
                             **{k:obj.get(k,'') for k in fields[2:]}})
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
