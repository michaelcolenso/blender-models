"""Build provisional terrace arrangement using explicit source paths."""
import math

import bpy
from mathutils import Vector

I=.0254


def existing_names():
    return {o.name for o in bpy.data.objects if o.name.startswith(('R5-terrace-', 'R5 source terrace band / ',
            'R5 terrace ', 'south-clerestory', 'clerestory-glass-', 'clerestory-frame-'))}


def rebuild(spec,scope):
    cfg=spec['terrace_review'];obj,slab,boxes,part,segment=[scope[n] for n in ('obj','slab','boxes','facade_part','segment_data')]
    created=[]
    def tag(o,basis):
        o['geometry_revision']=cfg['revision'];o['xy_status']='provisional';o['basis']=basis
        created.append(o.name);return o
    for row in cfg['surfaces']:
        planter=row['kind']=='planter'
        bottom,thickness=(637,2) if planter else (625,2)
        o=slab('R5 terrace surface / '+row['id'],row['polygon'],bottom,thickness,
               'roof' if planter else 'concrete','Roof','A2.07 / '+row['id']+' source outline')
        tag(o,'Measured plan outline; surface thickness/levels, drainage falls, thresholds and finish remain assumed. '+('Decorative gravel appearance and planter depth are illustrative.' if planter else 'Flat representative walking surface.'))
        o['surface_kind']=row['kind']

    def path_sections(path,width,closed=False):
        p=[Vector(v) for v in path];normals=[]
        count=len(p) if closed else len(p)-1
        for k in range(count):
            u=(p[(k+1)%len(p)]-p[k]).normalized();normals.append(Vector((-u.y,u.x)))
        def corner(k,d):
            if not closed and k==0:return p[k]+normals[0]*d
            if not closed and k==len(p)-1:return p[k]+normals[-1]*d
            n1,n2=normals[k-1],normals[k%len(normals)]
            return p[k]+(n1+n2)*d/(1+n1.dot(n2))
        return [[corner(k,-width/2),corner((k+1)%len(p),-width/2),
                 corner((k+1)%len(p),width/2),corner(k,width/2)] for k in range(count)]

    def solid(vertices,faces,polygon,bottom,top):
        start=len(vertices);vertices.extend([(p.x*I,p.y*I,z*I) for z in (bottom,top) for p in polygon])
        faces.extend([tuple(start+j for j in f) for f in scope['FACES']])

    for row in cfg['bands']:
        vertices=[];faces=[];height=row['height_in'];cap=row['cap_height_in']
        body=path_sections(row['path'],8,row.get('closed',False));caps=path_sections(row['path'],row['cap_width_in'],row.get('closed',False))
        for p in body:solid(vertices,faces,p,627,627+height-cap)
        for p in caps:solid(vertices,faces,p,627+height-cap,627+height)
        material='brick-x' if row['finish']=='brick' else 'concrete'
        o=obj('R5 terrace band / '+row['id'],vertices,faces,material,'Roof',cfg['source'],basis=row['basis'])
        if material=='brick-x':
            o.data.materials.append(bpy.data.materials['concrete'])
            for face in o.data.polygons:face.material_index=int(face.index>=6*len(body))
        tag(o,row['basis']);o['height_status']='provisional';o['height_uncertainty_in']=3

    section=cfg['guard_section'];height=section['height_in']
    for row in cfg['guards']:
        vertices=[];faces=[];path=row['path'];strips=path_sections(path,section['rail_depth_in'])
        for k,p in enumerate(strips):
            band=row['band_heights_in'][k]
            solid(vertices,faces,p,627+height-section['top_rail_height_in'],627+height)
            for j in range(section['wire_rows']):
                z=4+j*(height-8)/(section['wire_rows']-1);h=section['wire_height_in']
                if z-h/2<=band:continue
                solid(vertices,faces,p,627+z-h/2,627+z+h/2)
        # Corner posts are built once and start above the higher adjacent band.
        posts=[]
        for k,p in enumerate(path):
            adjacent=row['band_heights_in'][max(0,k-1):min(len(path)-1,k+1)]
            posts.append((p,max(adjacent)))
        for k,(a,b) in enumerate(zip(path,path[1:])):
            a,b=Vector(a),Vector(b);length=(b-a).length;count=max(1,math.ceil(length/section['post_spacing_max_in']))
            for j in range(1,count):posts.append((a+(b-a)*j/count,row['band_heights_in'][k]))
        for p,base in posts:
            p=Vector(p);w=section['post_width_in']/2
            polygon=[p+Vector(v) for v in [(-w,-w),(w,-w),(w,w),(-w,w)]]
            solid(vertices,faces,polygon,627+base,627+height)
        o=obj('R5 terrace guard / '+row['id'],vertices,faces,'rail','Roof',cfg['source'],basis=section['basis'])
        tag(o,section['basis']+' Guard paths are provisional; rails/posts are omitted below band tops rather than running through the masonry.')
        o['guard_height_status']='assumed';o['guard_top_in']=627+height
        o['source_path_in']=str(path);o['band_mount_heights_in']=row['band_heights_in']

    # Keep the established top datum while correcting the clerestory plan tie-in.
    feature=next(e for e in spec['roof_features'] if e['id']=='south-clerestory')
    poly=feature['polygon'];top=feature['top'];cap=spec['shell_reconciliation']['roof_coping']['tower_cap_thickness_in']
    o=slab('south-clerestory',poly,feature['z'],top-cap-feature['z'],'metal','Roof',feature['source'])
    tag(o,feature['basis']);o['datum_status']='confirmed';o['top_elevation_ft']=342+top/12;o['datum_applies_to']='complete capped feature'
    strips=path_sections(poly,spec['shell_reconciliation']['roof_coping']['tower_cap_width_in'],True)
    for k,p in enumerate(strips):
        vs=[];fs=[];solid(vs,fs,p,top-cap,top)
        o=obj(f'south-clerestory-cap-{k}',vs,fs,'concrete','Roof',feature['source'],basis=feature['basis'])
        tag(o,feature['basis']);o['datum_status']='confirmed';o['top_elevation_ft']=342+top/12
    a,b=poly[2],poly[3];v,n,length=segment(a,b)
    for k in range(4):
        u=(k+.5)*length/4;width=length/4-22;z=(feature['z']+top)/2
        glass=boxes(f'clerestory-glass-{k}',[part(a,v,n,u,z,width,23,1,5)],'glass','Glazing',feature['source'])
        tag(glass,'A2.08 clerestory location / A3.01 four upper glazing fields; full glass/frame sizes remain assumed.')
        pieces=[part(a,v,n,u-width/2,z,2,25,2,6),part(a,v,n,u+width/2,z,2,25,2,6),
                part(a,v,n,u,z-12,width,2,2,6),part(a,v,n,u,z+12,width,2,2,6)]
        frame=boxes(f'clerestory-frame-{k}',pieces,'frame','Glazing',feature['source'])
        tag(frame,'A3.01 upper glazing pattern; complete frame sections remain assumed.')
    return created
