"""Rebuild the slabs, split roof plates and mitered coping around the R5 shell."""
import bpy
from mathutils import Vector

I=.0254
BASE_SUPPORTS={'slab-P1','slab-R5','roof-south','roof-north','roof-step-closure'}


def roof_edges(spec):
    edges=[];poly=spec['polygons']['r5'];split=spec['north_roof_split_y']
    for index,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
        cuts=[Vector(a)]
        if (a[1]-split)*(b[1]-split)<0:
            cuts.append(Vector((a[0]+(split-a[1])/(b[1]-a[1])*(b[0]-a[0]),split)))
        cuts.append(Vector(b))
        for start,end in zip(cuts,cuts[1:]):
            zone='north' if (start.y+end.y)/2>split else 'south'
            name=f'roof-parapet-{index}'+('-'+zone if len(cuts)==3 else '')
            edges.append((name,start,end,zone))
    return edges


def support_names(spec):
    return BASE_SUPPORTS | {e[0] for e in roof_edges(spec)}


def existing_support_names():
    return BASE_SUPPORTS | {o.name for o in bpy.data.collections['Roof'].objects if o.name.startswith('roof-parapet-')}


def rebuild(spec,scope):
    slab,clip,obj,boxes=[scope[k] for k in ('slab','clip','obj','boxes')]
    for name in existing_support_names():
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    slab('slab-P1',spec['polygons']['p1'],-7,7,source='A2.02 separate P1 enclosure; flat slab and thickness assumed')
    slab('slab-R5',spec['polygons']['r5'],620,7,source='A2.07 R5 enclosure; slab thickness assumed')
    split=spec['north_roof_split_y']
    clipped={}
    for zone in ('north','south'):
        poly=clip(spec['polygons']['r5'],split,zone=='north');clipped[zone]=poly
        z=spec['north_roof_plate_z'] if zone=='north' else spec['roof_plate_z']
        slab('roof-'+zone,poly,z-5,5,'roof','Roof','A2.07/A2.08 R5 enclosure and retained roof-level split; roof thickness and drainage falls assumed')
    roof=spec['shell_reconciliation']['roof_coping'];edges=roof_edges(spec);normals=[]
    for _,a,b,_ in edges:
        v=(b-a).normalized();normals.append(Vector((-v.y,v.x)))
    def corner(k,distance):
        return edges[k][1]+(normals[k]+normals[k-1])*distance/(1+normals[k].dot(normals[k-1]))
    for k,(name,a,b,zone) in enumerate(edges):
        top=(roof[zone+'_top_ft']-342)*12
        base=spec['north_roof_plate_z'] if zone=='north' else spec['roof_plate_z']
        width=roof['wall_thickness_in']/2;n=normals[k]
        strips=[([a-n*width,b-n*width,b+n*width,a+n*width],base,top-roof['main_thickness_in'])]
        nxt=(k+1)%len(edges);half=roof['main_width_in']/2
        strips.append(([corner(k,-half),corner(nxt,-half),corner(nxt,half),corner(k,half)],top-roof['main_thickness_in'],top))
        vertices=[];faces=[]
        for polygon,bottom,zt in strips:
            offset=len(vertices);vertices.extend([(p.x*I,p.y*I,z*I) for z in (bottom,zt) for p in polygon])
            faces.extend([tuple(offset+j for j in f) for f in scope['FACES']])
        o=obj(name,vertices,faces,'concrete','Roof','A2.07 R5 wall trace / A2.08 top datum',
              basis='Mitered coping follows the source-governed enclosure; complete section and projection remain assumed.')
        o['datum_status']='confirmed';o['top_elevation_ft']=342+top/12
    xs=[p[0] for p in clipped['south'] if abs(p[1]-split)<.001];lo,hi=min(xs),max(xs)
    boxes('roof-step-closure',[([(lo+hi)/2,split,(spec['roof_plate_z']+spec['north_roof_plate_z'])/2],
          [hi-lo,8,spec['north_roof_plate_z']-spec['roof_plate_z']])],'metal','Roof',
          'A2.08 roof level change; source-governed R5 enclosure',basis='Retained split datum; representative wall section and closure thickness.')
    for name in support_names(spec):
        o=bpy.data.objects[name];o['geometry_revision']=spec['r5_completion']['revision'];o['xy_status']='provisional'
