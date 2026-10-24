"""Read-only evaluated-scene checks; does not save changes to the model."""
import bpy, json, math, runpy
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
scene=bpy.context.scene
slab=bpy.data.objects['BuildingB_SOG_5p5in']
ctrl=bpy.data.objects['PHASE_CONTROLLER']
report={'frames':[], 'invalid_drivers':[], 'nonfinite_objects':[], 'flagged_driver_errors':[]}
for frame in [1,38,50,61,68,76,83,89,91,121,151,181,211]:
    scene.frame_set(frame)
    dg=bpy.context.evaluated_depsgraph_get(); dg.update()
    counts=Counter(o.get('PHASE_ROLE','UNCLASSIFIED') for o in bpy.data.objects if not o.evaluated_get(dg).hide_render)
    mod=slab.evaluated_get(dg).modifiers.get('MEYD_Trench_Difference')
    report['frames'].append({'frame':frame,'phase':ctrl.get('Construction_Phase'),'demo':ctrl.get('Demolition_Subphase'),'boolean_viewport':mod.show_viewport,'boolean_render':mod.show_render,'render_visible_roles':dict(counts)})
    for group in [bpy.data.objects,bpy.data.materials,bpy.data.node_groups]:
        for block in group:
            for owner in [block]+([block.node_tree] if getattr(block,'node_tree',None) else []):
                ad=owner.animation_data
                if ad:
                    for fc in ad.drivers:
                        if not fc.driver.is_valid: report['invalid_drivers'].append({'frame':frame,'owner':owner.name,'path':fc.data_path})
for o in bpy.data.objects:
    if o.get('MEYD_DRIVER_ERROR'):report['flagged_driver_errors'].append(o.name)
    if not all(math.isfinite(v) for row in o.matrix_world for v in row):report['nonfinite_objects'].append(o.name)
report['motion_checks']=[]
for role,fa,fb in [('DEMO_SALVAGE',38,48),('DEMO_SLAB_CHUNK',68,76)]:
    objects=[o for o in bpy.data.objects if o.get('PHASE_ROLE')==role]
    scene.frame_set(fa); dg=bpy.context.evaluated_depsgraph_get();dg.update()
    starts={o.name:o.evaluated_get(dg).matrix_world.translation.copy() for o in objects}
    scene.frame_set(fb);dg=bpy.context.evaluated_depsgraph_get();dg.update()
    report['motion_checks'].append({'role':role,'start_frame':fa,'end_frame':fb,'objects':[{'name':o.name,'delta_ft':list(o.evaluated_get(dg).matrix_world.translation-starts[o.name])} for o in objects]})
scene.frame_set(89); dg=bpy.context.evaluated_depsgraph_get(); dg.update()
evalslab=slab.evaluated_get(dg); mesh=evalslab.to_mesh()
verts=[slab.matrix_world@v.co for v in mesh.vertices]
faces=[tuple(p.vertices) for p in mesh.polygons]
bvh=BVHTree.FromPolygons(verts,faces)
edge_counts=Counter(tuple(sorted((p.vertices[i],p.vertices[(i+1)%len(p.vertices)]))) for p in mesh.polygons for i in range(len(p.vertices)))
report['slab']={'vertices':len(verts),'faces':len(faces),'nonmanifold_edges':sum(n!=2 for n in edge_counts.values()),'z_min':min(v.z for v in verts),'z_max':max(v.z for v in verts)}
cutters=list(bpy.data.collections['Concrete_Slab_Trench_Cuts_DEMO'].objects)
boxes=[]
for o in cutters:
    bb=[Vector(v) for v in o.bound_box]
    boxes.append((o.name,o.matrix_world.inverted(),[min(v[i] for v in bb) for i in range(3)],[max(v[i] for v in bb) for i in range(3)]))
def cutter_at(x,y):
    p=Vector((x,y,-0.1))
    return [name for name,inv,lo,hi in boxes if all(lo[i]+1e-5<(inv@p)[i]<hi[i]-1e-5 for i in range(3))]
def slab_at(x,y):return bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)),3)[0] is not None
# A regular 3-inch grid inside original slab bounds checks that Boolean openings match cutter union.
bb=[slab.matrix_world@Vector(v) for v in slab.bound_box]
xlo,xhi=min(v.x for v in bb),max(v.x for v in bb); ylo,yhi=min(v.y for v in bb),max(v.y for v in bb)
step=.25; mismatches=[]; tested=0; cut_samples=0
x=xlo+step*.371
while x<xhi:
    y=ylo+step*.413
    while y<yhi:
        expected=bool(cutter_at(x,y)); actual=not slab_at(x,y)
        tested+=1;cut_samples+=actual
        if expected!=actual:mismatches.append([x,y,expected,actual])
        y+=step
    x+=step
report['boolean_grid']={'spacing_model_units':step,'samples':tested,'open_samples':cut_samples,'mismatch_count':len(mismatches),'mismatch_examples':mismatches[:20]}
env=bpy.data.objects['B101_DEMO_PriorRepair_NoDemo_Envelope']; eb=[env.matrix_world@Vector(v) for v in env.bound_box]
elo=[min(v[i] for v in eb) for i in range(3)]; ehi=[max(v[i] for v in eb) for i in range(3)]
overlaps=[]; n=0
x=elo[0]+step/2
while x<ehi[0]:
    y=elo[1]+step/2
    while y<ehi[1]:
        n+=1
        if not slab_at(x,y): overlaps.append({'x':x,'y':y,'cutters':cutter_at(x,y)})
        y+=step
    x+=step
report['prior_abs_envelope']={'samples':n,'opening_samples':len(overlaps),'approx_open_area_square_model_units':len(overlaps)*step*step,'examples':overlaps[:20]}
report['counts']={ 'junction_bodies':sum(o.name.startswith('B101_DEMO_CI_Wye_') and o.name.endswith('_BODY') for o in bpy.data.objects),'ptraps':sum(o.name.startswith('B101_DEMO_ExistingPTrap_') for o in bpy.data.objects),'plan_bend_objects':sum(o.name.startswith('B101_DEMO_CI_Bend_') for o in bpy.data.objects),'temporary_supports':sum('_TempSupport_' in o.name for o in bpy.data.objects)}
ns=runpy.run_path(str(ROOT/'scripts/build_meydenbauer_b101_v4.py'),run_name='qa_reference')
net=ns['compute_unit_network_3d'](ns['ROUTE_DATA']['B101'])
report['saved_route_checks']=[]
for name,key in [('NEW_ABS_B101_4in_MAIN','main4'),('NEW_ABS_B101_6in_LATERAL_18IN_LIMIT','lateral6'),('B101_Prior_4in_ABS_REMAIN','prior4')]:
    o=bpy.data.objects[name]
    actual=[o.matrix_world@Vector(p.co[:3]) for sp in o.data.splines for p in sp.points]
    expected=[Vector(v) for v in net[key]]
    error=max((a-b).length for a,b in zip(actual,expected)) if len(actual)==len(expected) else None
    report['saved_route_checks'].append({'object':name,'actual_points':len(actual),'expected_points':len(expected),'max_error_ft':error,'passed':error is not None and error<1e-4})
report['missing_external_assets']=[{'image':im.name,'path':bpy.path.abspath(im.filepath)} for im in bpy.data.images if im.source=='FILE' and not im.packed_file and im.filepath and not Path(bpy.path.abspath(im.filepath)).exists()]
report['field_verify_count']=sum(bool(o.get('FIELD_VERIFY')) for o in bpy.data.objects)
report['cut_objects']=[{'name':o.name,'location':list(o.location),'field_verify':bool(o.get('FIELD_VERIFY'))} for o in bpy.data.objects if o.name.startswith('B101_DEMO_Cut_')]
evalslab.to_mesh_clear()
(ROOT/'output/extended_runtime_qa.json').write_text(json.dumps(report,indent=2))
print('EXTENDED_QA_COMPLETE', flush=True)
