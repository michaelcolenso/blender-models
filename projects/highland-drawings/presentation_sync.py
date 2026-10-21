"""Move existing illustrative window dressing with its source-governed opening."""
import re

import bpy
from mathutils import Matrix, Vector


def controls(openings):
    result={}
    for e in openings:
        obj=bpy.data.objects.get(e['id']+'-glazing')
        if obj is None:continue
        pts=[obj.matrix_world@v.co for v in obj.data.vertices]
        axis=0 if e['face'] in ('north','south') else 1
        lo=Vector([min(p[k] for p in pts) for k in range(3)])
        hi=Vector([max(p[k] for p in pts) for k in range(3)])
        result[e['id']]={'center':(lo+hi)/2,'width':hi[axis]-lo[axis],'height':hi.z-lo.z,'axis':axis}
    return result


def refresh(spec,ledger,before,architecture):
    # Lighting is excluded from the daylight view layer. Evaluate the dusk layer
    # before reading object transforms; excluded lights can have stale matrices.
    scene=next(s for s in bpy.data.scenes if s.name.startswith('Dusk'))
    bpy.context.window.scene=scene
    bpy.context.view_layer.update()
    cfg=spec['presentation_refresh'];after=controls(spec['openings'])
    targets={r['id'] for r in ledger['opening_changes'] if r['new']['face'] not in cfg['deferred_faces']}
    transforms={}
    for ident in targets & before.keys() & after.keys():
        old,new=before[ident],after[ident]
        scale=Vector((1,1,1));scale[old['axis']]=new['width']/old['width'];scale.z=new['height']/old['height']
        matrix=Matrix.Diagonal((*scale,1))
        matrix.translation=new['center']-matrix.to_3x3()@old['center']
        transforms[ident]=matrix
    selected=[]
    pattern=re.compile(r'((?:north|south|east|west)-(?:P1|R[1-5])-(?:\d{2}|garage|service))(?=-glazing)')
    for obj in bpy.data.objects:
        match=pattern.search(obj.name)
        if obj.name in architecture or obj.type not in ('MESH','CURVE','LIGHT') or not match:continue
        ident=match[1]
        if ident in transforms:
            original=obj.matrix_basis.copy() if obj.parent is None else obj.matrix_world.copy()
            selected.append((obj,ident,original))
    def depth(obj):
        count=0
        while obj.parent:count+=1;obj=obj.parent
        return count
    records=[];pending=[]
    for obj,ident,original in sorted(selected,key=lambda row:depth(row[0])):
        center=original.translation if obj.type=='LIGHT' else original@(sum((Vector(p) for p in obj.bound_box),Vector())/8)
        expected=transforms[ident]@center
        if obj.type=='LIGHT':
            # A light's rotated area cannot represent the shear produced by
            # nonuniform world scaling. Move it and preserve its native shape.
            target=original.copy();target.translation=expected;obj.matrix_world=target
        else:obj.matrix_world=transforms[ident]@original
        obj['reference_opening']=ident;obj['presentation_revision']=cfg['revision']
        obj['basis']=str(obj.get('basis',''))+' Location/size refreshed against the corrected glazing; room dressing and light behavior remain illustrative.'
        pending.append((obj,ident,original,expected))
    bpy.context.view_layer.update()
    largest_error=0
    for obj,ident,original,expected in pending:
        center=obj.matrix_world.translation if obj.type=='LIGHT' else obj.matrix_world@(sum((Vector(p) for p in obj.bound_box),Vector())/8)
        error=(center-expected).length;largest_error=max(largest_error,error)
        assert error<.0001,(obj.name,error,'presentation center mapping failed')
        records.append({'name':obj.name,'opening':ident,'old_matrix_world':[list(r) for r in original],
                        'new_matrix_world':[list(r) for r in obj.matrix_world],'mapped_center_m':list(expected)})
    return {'status':'PASS','revision':cfg['revision'],'evaluation_scene':scene.name,'objects_refreshed':len(records),
            'openings_with_existing_props_refreshed':len({r['opening'] for r in records}),
            'north_props_refreshed':0,'center_mapping_max_error_m':largest_error,'basis':cfg['window_dressing'],'records':records}
