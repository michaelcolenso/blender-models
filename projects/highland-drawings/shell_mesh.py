"""Rebuild only the slabs and coping that depend on the corrected shell."""
import bpy
from mathutils import Vector

I = .0254
SUPPORTS = {'slab-P1', 'slab-R5', 'roof-south', 'roof-parapet-3-south',
            'roof-parapet-4', 'roof-parapet-5', 'roof-parapet-6'}


def rebuild(spec, scope):
    slab, clip, obj = [scope[k] for k in ('slab', 'clip', 'obj')]
    for name in SUPPORTS:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    slab('slab-P1', spec['polygons']['p1'], -7, 7, source='A2.02 separate P1 enclosure; flat slab and thickness assumed')
    slab('slab-R5', spec['polygons']['r5'], 620, 7, source='A2.07 southeast R5 enclosure; slab thickness assumed')
    slab('roof-south', clip(spec['polygons']['r5'], spec['north_roof_split_y'], False),
         spec['roof_plate_z']-5, 5, 'roof', 'Roof', 'A2.07 / A2.08 southeast return; roof thickness and falls assumed')
    roof = spec['shell_reconciliation']['roof_coping']
    # Split at the retained roof-level control, then miter the caps in plan.
    edges = []
    for index, (a, b) in enumerate(zip(spec['polygons']['r5'], spec['polygons']['r5'][1:]+spec['polygons']['r5'][:1])):
        cuts = [Vector(a)]; split = spec['north_roof_split_y']
        if (a[1]-split)*(b[1]-split) < 0:
            cuts.append(Vector((a[0]+(split-a[1])/(b[1]-a[1])*(b[0]-a[0]), split)))
        cuts.append(Vector(b))
        for start, end in zip(cuts, cuts[1:]):
            zone = 'north' if (start.y+end.y)/2 > split else 'south'
            name = f'roof-parapet-{index}'+('-'+zone if len(cuts)==3 else '')
            edges.append((name,start,end,zone))
    normals = []
    for _,a,b,_ in edges:
        v=(b-a).normalized(); normals.append(Vector((-v.y,v.x)))
    def corner(k, distance):
        return edges[k][1]+(normals[k]+normals[k-1])*distance/(1+normals[k].dot(normals[k-1]))
    for k,(name,a,b,zone) in enumerate(edges):
        if name not in SUPPORTS: continue
        top=(roof[zone+'_top_ft']-342)*12
        base=spec['north_roof_plate_z'] if zone=='north' else spec['roof_plate_z']
        width=roof['wall_thickness_in']/2; n=normals[k]
        strips=[([a-n*width,b-n*width,b+n*width,a+n*width],base,top-roof['main_thickness_in'])]
        nxt=(k+1)%len(edges); half=roof['main_width_in']/2
        strips.append(([corner(k,-half),corner(nxt,-half),corner(nxt,half),corner(k,half)],top-roof['main_thickness_in'],top))
        vertices=[];faces=[]
        for polygon,bottom,zt in strips:
            offset=len(vertices)
            vertices.extend([(p.x*I,p.y*I,z*I) for z in (bottom,zt) for p in polygon])
            faces.extend([tuple(offset+j for j in f) for f in scope['FACES']])
        o=obj(name,vertices,faces,'concrete','Roof','A2.07/A2.08 southeast return and inherited parapet top datum',
              basis='Mitered cap follows the reconciled southeast shell; complete section and projection remain assumed.')
        o['datum_status']='confirmed';o['top_elevation_ft']=342+top/12
    for name in SUPPORTS:
        o=bpy.data.objects[name]
        o['geometry_revision']=spec['shell_reconciliation']['revision']
        o['xy_status']='provisional'

