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
from shell_mesh import SUPPORTS

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
    assert sha(OUT/'reconciled.spec.json')==sha(HERE/'reconciled.spec.json')
    assert len(spec['openings'])==192 and len(spec['rejected_candidates'])==0
    assert (audit['accepted_candidates'],audit['rejected_candidates'],audit['remaining_unresolved'])==(15,1,0)
    protected=('grid_dimensions_in','roof_features','roof_plate_z','north_roof_plate_z','north_roof_split_y')
    for key in protected:assert spec[key]==base[key]
    assert spec['polygons']['r1']==base['polygons']['r1'] and spec['polygons']['typical']==base['polygons']['typical']
    assert [(e['name'],e['z']) for e in spec['levels']]==[(e['name'],e['z']) for e in base['levels']]
    assert spec['levels'][0]['polygon']=='p1' and len([e for e in spec['openings'] if e['level']=='P1'])==14
    for i,p in enumerate(base['polygons']['r5']):
        if i not in (4,5,6): assert spec['polygons']['r5'][i]==p
    bpy.ops.wm.open_mainfile(filepath=str(native),load_ui=False,use_scripts=False)
    assert inventory()==geometry['after']
    expected_scenes={'Daylight / drawing reconciliation 05','Dusk / drawing reconciliation 05'}
    assert set(bpy.data.scenes.keys())==expected_scenes
    missing=[o.name for o in bpy.data.objects if o.type in ('MESH','CURVE') and not all(o.get(k) for k in ('source','basis','status'))]
    assert not missing,missing[:20]
    assert all(im.packed_file for im in bpy.data.images if im.source=='FILE')
    north=json.loads((HERE/'revision04-north-baseline.json').read_text())
    assert all(geometry['after'].get(n)==h for n,h in north['mesh_hashes'].items()), 'North geometry changed'
    changed={n for n in geometry['before'] if geometry['after'].get(n)!=geometry['before'][n]}
    assert changed <= set(geometry['allowed_existing'])
    largest_error=0
    for c in ledger['opening_changes']:
        e=c['new'];o=bpy.data.objects[e['id']+'-frames']
        pts=[o.matrix_world@v.co for v in o.data.vertices]
        axis=0 if e['face'] in ('north','south') else 1
        measured=[min(p[axis] for p in pts)/I,max(p[axis] for p in pts)/I,min(p.z for p in pts)/I,max(p.z for p in pts)/I]
        target=[e['u']-e['width']/2,e['u']+e['width']/2,e['z'],e['z']+e['height']]
        largest_error=max(largest_error,max(abs(a-b) for a,b in zip(measured,target)))
        assert max(abs(a-b) for a,b in zip(measured,target))<.001,e['id']
        poly=spec['polygons'][e['polygon']];a,b=poly[e['segment']],poly[(e['segment']+1)%len(poly)]
        assert min(a[axis],b[axis])<target[0]<target[1]<max(a[axis],b[axis]), e['id']
        # Read back the wall-normal location, not just the frame's width/height.
        v=Vector((b[0]-a[0],b[1]-a[1],0)).normalized();n=Vector((-v.y,v.x,0))
        expected_depth=a[1-axis]+n[1-axis]*(spec['wall_thickness']/2+.5)
        depth=(min(p[1-axis] for p in pts)+max(p[1-axis] for p in pts))/(2*I)
        assert abs(depth-expected_depth)<.001, (e['id'],'frame on wrong wall')
        assert o['reference_opening']==e['id'] and o['scheduled_size_verified']==False
    # No two opening voids overlap on a corrected wall, including retained records.
    patched={(e['new']['level'],e['new']['segment']) for e in ledger['opening_changes']}
    patched |= {('P1',i) for i in range(len(spec['polygons']['p1']))}
    patched |= {('R5',i) for i in spec['shell_reconciliation']['changed_r5_segments']}
    for level,segment in patched:
        ops=[e for e in spec['openings'] if e['level']==level and e['segment']==segment]
        for i,e in enumerate(ops):
            for other in ops[i+1:]:
                horizontal=min(e['u']+e['width']/2,other['u']+other['width']/2)-max(e['u']-e['width']/2,other['u']-other['width']/2)
                vertical=min(e['z']+e['height'],other['z']+other['height'])-max(e['z'],other['z'])
                assert horizontal<=0 or vertical<=0,(e['id'],other['id'])
    for level in ('R2','R3','R4','R5'):
        assert len([e for e in spec['openings'] if e['face']=='north' and e['level']==level])==6
    # Read back slab perimeter, face area and top datum from the actual meshes.
    from mathutils.geometry import intersect_line_line_2d
    for key in ('p1','r5'):
        poly=spec['polygons'][key]
        for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
            assert (a[0]==b[0]) != (a[1]==b[1]), ('non-orthogonal/zero edge',key,i)
            for j in range(i+2,len(poly)):
                if i==0 and j==len(poly)-1: continue
                assert intersect_line_line_2d(Vector(a),Vector(b),Vector(poly[j]),Vector(poly[(j+1)%len(poly)])) is None, ('self crossing',key,i,j)
        slab=bpy.data.objects['slab-'+key.upper()]
        actual=[(v.co.x/I,v.co.y/I) for v in slab.data.vertices]
        assert len(actual)==2*len(poly)
        assert max(min(max(abs(a[0]-b[0]),abs(a[1]-b[1])) for b in poly) for a in actual)<.001
        assert max(min(max(abs(a[0]-b[0]),abs(a[1]-b[1])) for b in actual) for a in poly)<.001
        area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2
        top_area=sum(p.area for p in slab.data.polygons if p.normal.z>.9)/I**2
        assert abs(top_area-area)<1, (key,area,top_area)
        target_z=0 if key=='p1' else 627
        assert abs(max(v.co.z for v in slab.data.vertices)/I-target_z)<.001
    for name in SUPPORTS:
        if not name.startswith('roof-parapet'): continue
        o=bpy.data.objects[name]
        assert abs(max(v.co.z for v in o.data.vertices)/I-(406.25-342)*12)<.001
    # Adjacent cap edges must meet after the corner moves; top datum alone is insufficient.
    cap_join_error=0
    for first,second in [('roof-parapet-3-south','roof-parapet-4'),('roof-parapet-4','roof-parapet-5'),('roof-parapet-5','roof-parapet-6'),('roof-parapet-6','roof-parapet-7')]:
        a,b=bpy.data.objects[first],bpy.data.objects[second]
        for i,j in [(9,8),(10,11),(13,12),(14,15)]:
            error=(a.data.vertices[i].co-b.data.vertices[j].co).length/I
            cap_join_error=max(cap_join_error,error)
            assert error<.001,(first,second,error)
    assert all(n in geometry['after'] for n in SUPPORTS)
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
        'opening_inventory':192,'accepted_candidates':15,'rejected_candidates':1,'unresolved_candidates':0,
        'candidate_disposition_note':'Presence and provisional placement only; dimensional/source issues remain open',
        'p1_openings_rechecked':14,'north_meshes_identical_to_revision04':len(north['mesh_hashes']),
        'changed_opening_records':len(ledger['opening_changes']),'architecture_meshes':len(geometry['after']),
        'unchanged_architecture_meshes':geometry['unchanged_meshes'],'protected_spec_controls':list(protected),
        'roof_geometry_unchanged':False,'roof_changes_allowlist':geometry['roof_changes_allowlist'],'coping_join_max_error_in':cap_join_error,'corrected_wall_void_overlaps':0,'north_R2_to_R5_count_per_floor':6,
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
                             **{k:str(obj.get(k,'')).strip() for k in fields[2:]}})
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
