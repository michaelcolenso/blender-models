"""Patch source-reconciled openings, P1 enclosure and southeast R5 supports."""
import ast
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from shell_mesh import SUPPORTS, rebuild as rebuild_supports

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'deliverables/highland-drawings'
I=.0254
TRADES=('Envelope','Glazing','Balconies','Roof')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    records={}
    for trade in TRADES:
        for o in bpy.data.collections[trade].objects:
            if o.type=='MESH':
                value=[o.name,[list(r) for r in o.matrix_world], [list(v.co) for v in o.data.vertices], [list(p.vertices) for p in o.data.polygons]]
                records[o.name]=hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).hexdigest()
    return records


def main():
    cfg=json.loads((HERE/'decisions.json').read_text())
    spec=json.loads((HERE/'reconciled.spec.json').read_text())
    ledger=json.loads((OUT/'change-ledger.json').read_text())
    source=ROOT/cfg['base_blend']
    bpy.context.preferences.filepaths.use_scripts_auto_execute=False
    bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
    before=inventory()
    # Reuse the existing generator's pure mesh functions, with the saved scene's
    # actual material datablocks. No scene initializer or rendering code executes.
    tree=ast.parse((ROOT/'projects/highland-exterior/build.py').read_text())
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('obj','boxes','segment_data','facade_part','slab','clip')]
    scope={'bpy':bpy,'Vector':Vector,'tessellate_polygon':tessellate_polygon,'I':I,'objects':[],
        'collections':{t:bpy.data.collections[t] for t in TRADES},
        'mats':{m.name:m for m in bpy.data.materials},
        'FACES':[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'reused_mesh_functions','exec'),scope)
    boxes,segment_data,part=[scope[n] for n in ('boxes','segment_data','facade_part')]
    patches={(e['new']['level'],e['new']['segment']) for e in ledger['opening_changes']}
    patches |= {('P1',i) for i in range(len(spec['polygons']['p1']))}
    patches |= {('R5',i) for i in spec['shell_reconciliation']['changed_r5_segments']}
    ids={e['id'] for e in ledger['opening_changes']}
    old_ids={e['old']['id'] for e in ledger['opening_changes'] if e['old']}
    allowed_existing={n for n in before if any(n.startswith(f'wall-{level}-{seg}-') for level,seg in patches)
                      or n.startswith(('wall-P1-', 'edge-P1-'))
                      or n in SUPPORTS or any(n.startswith(ident+'-') for ident in old_ids)}
    rebuild_supports(spec, scope)
    for name in allowed_existing-SUPPORTS:
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    for level,seg in sorted(patches):
        li=next(i for i,e in enumerate(spec['levels']) if e['name']==level)
        lev=spec['levels'][li];z=lev['z'];poly=spec['polygons'][lev['polygon']]
        a,b=poly[seg],poly[(seg+1)%len(poly)]
        v,n,length=segment_data(a,b)
        top=spec['levels'][li+1]['z'] if li<5 else spec['north_roof_plate_z'] if (a[1]+b[1])/2>spec['north_roof_split_y'] else spec['roof_plate_z']
        axis=0 if abs(v.x)>.99 else 1
        ops=[e for e in spec['openings'] if e['level']==level and e['segment']==seg]
        holes=[]
        for e in ops:
            assert e['kind'] in ('window','small','wide','door','garage'),e['id']
            center=(e['u']-a[axis])/v[axis]
            lo,hi=center-e['width']/2,center+e['width']/2
            zb,zt=e['z'],e['z']+e['height']
            assert 0<lo<hi<length and z<=zb<zt<=top,e['id']
            holes.append((lo,hi,zb,zt,e,center))
        for i,hole in enumerate(holes):
            for other in holes[i+1:]:
                assert min(hole[1],other[1])-max(hole[0],other[0]) <= .001 or min(hole[3],other[3])-max(hole[2],other[2]) <= .001, (hole[4]['id'],other[4]['id'],'overlapping opening voids')
        split=spec['north_roof_split_y']
        crossing=level=='R5' and (a[1]-split)*(b[1]-split)<0
        cut=(split-a[1])/v.y if crossing else None
        if crossing: top=max(spec['roof_plate_z'],spec['north_roof_plate_z'])
        xs=sorted({0,length,*[x for h in holes for x in h[:2]],*([cut] if crossing else [])})
        zs=sorted({z,top,*[x for h in holes for x in h[2:4]]})
        material='metal' if level=='R5' and (a[1]+b[1])/2<1110 else 'brick-'+('x' if axis==0 else 'y')
        if level=='P1' and n.y>.5: material='concrete'
        parts=[]
        for x0,x1 in zip(xs,xs[1:]):
            for z0,z1 in zip(zs,zs[1:]):
                u,zz=(x0+x1)/2,(z0+z1)/2
                local_top=(spec['north_roof_plate_z'] if a[1]+v.y*u>split else spec['roof_plate_z']) if crossing else top
                z1=min(z1,local_top)
                if z1<=z0: continue
                zz=(z0+z1)/2
                if any(h[0]<u<h[1] and h[2]<zz<h[3] for h in holes):continue
                parts.append(part(a,v,n,u,zz,x1-x0,z1-z0,spec['wall_thickness']))
        wall=boxes(f'wall-{level}-{seg}-{material}',parts,material,'Envelope','A2.02/A2.07 and uploaded elevations / revision 05',basis='Source-reconciled shell centerline and opening voids. Wall thickness, construction and vertical opening dimensions remain assumed.')
        wall['geometry_revision']=cfg['revision']
        for lo,hi,zb,zt,e,center in holes:
            if e['id'] not in ids:continue
            w,h=hi-lo,zt-zb;cz=(zb+zt)/2;off=spec['wall_thickness']/2+.5
            glass=boxes(e['id']+'-glazing',[part(a,v,n,center,cz,w-3,h-3,1,off-.6)],'glass','Glazing',e['source'])
            frame=[part(a,v,n,center-w/2+1,cz,2,h,3,off),part(a,v,n,center+w/2-1,cz,2,h,3,off),part(a,v,n,center,zb+1,w,2,3,off),part(a,v,n,center,zt-1,w,2,3,off)]
            divisions=1 if e['drawing_mark'] in ('MX','MZ','MK') else 3 if w>100 else 2 if w>38 else 1
            for k in range(1,divisions):frame.append(part(a,v,n,center-w/2+w*k/divisions,cz,1.6,h,3,off))
            if e['kind']=='garage':
                for zz in range(int(zb+12),int(zt),12): frame.append(part(a,v,n,center,zz,w,1.3,3,off))
            elif h>70:frame.append(part(a,v,n,center,zb+20,w,1.5,3,off))
            frames=boxes(e['id']+'-frames',frame,'frame','Glazing',e['source'])
            sill=boxes(e['id']+'-sill',[part(a,v,n,center,zb-2,w+5,3,12,off-2)],'concrete','Glazing',e['source'])
            for o in (glass,frames,sill):
                for k in ('basis','status','xy_status','geometry_revision','drawing_mark','source'):
                    o[k]=e[k]
                o['reference_opening']=e['id']
                o['plan_jamb_pixels']=e['plan_jamb_pixels']
                o['scheduled_size_verified']=False
    after=inventory()
    unchanged={n:v for n,v in before.items() if n not in allowed_existing}
    assert all(after.get(n)==h for n,h in unchanged.items())
    assert all(after[n]==h for n,h in before.items() if n not in SUPPORTS and n in {o.name for o in bpy.data.collections['Roof'].objects})
    for scene in bpy.data.scenes:
        scene.name=scene.name.replace('roof and terrace revision 03','drawing reconciliation 05')
        scene['geometry_revision']=cfg['revision']
        scene['opening_inventory']=len(spec['openings'])
        scene['remaining_opening_conflicts']=0
        scene['north_alignment_status']='Unresolved; diagnostic max center delta 42.443 overview pixels'
        scene['source_spec']='//reconciled.spec.json'
        scene['geometry_spec']='projects/highland-drawings/reconciled.spec.json'
        scene['architecture_inventory_sha256']=hashlib.sha256(json.dumps(after,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if scene.name.startswith('Daylight'):
            scene.render.filepath='//Highland-daylight-drawing-reconciled.png'
        else:scene.render.filepath='//native-dusk/frame-'
    for obj in bpy.data.objects:
        if obj.type=='FONT':
            obj.data.body=obj.data.body.replace('GEOMETRY REVISION 03','DRAWING REVISION 05')
    native=OUT/'Highland-drawing-reconciled.blend'
    bpy.context.window.scene=next(s for s in bpy.data.scenes if s.name.startswith('Daylight'))
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    (OUT/'geometry-validation.json').write_text(json.dumps({
        'status':'PASS','base_native_sha256':sha(source),'native_sha256':sha(native),
        'base_meshes':len(before),'revised_meshes':len(after),'unchanged_meshes':len(unchanged),
        'changed_existing':sorted(n for n in before.keys()&after.keys() if before[n]!=after[n]),
        'removed':sorted(before.keys()-after.keys()),'added':sorted(after.keys()-before.keys()),
        'allowed_existing':sorted(allowed_existing),'roof_geometry_unchanged':False,'roof_changes_allowlist':sorted(SUPPORTS & {o.name for o in bpy.data.collections['Roof'].objects}),
        'before':before,'after':after,'revised_spec_sha256':sha(HERE/'reconciled.spec.json')},indent=2)+'\n')
    print('SAVED',native,'UNCHANGED',len(unchanged),flush=True)
    # Keep the GLB portable; native scenes/cameras remain the editing reference.
    bpy.context.window.scene=next(s for s in bpy.data.scenes if s.name.startswith('Dusk'))
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type in ('MESH','CURVE') and not o.hide_render and o.visible_get():o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'Highland-drawing-reconciled.glb'),
        export_format='GLB',use_selection=True,export_extras=True,
        export_cameras=False,export_lights=False,export_animations=False)


if __name__=='__main__':main()
