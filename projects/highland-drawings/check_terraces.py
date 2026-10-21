"""Read back terrace surfaces, guard paths and protected R5 enclosure meshes."""
import json
from pathlib import Path

import bpy

from terraces import inside, intersection_area

I=.0254


def validate(spec,geometry,out):
    cfg=spec['terrace_review'];stage1=json.loads(Path(__file__).with_name('stage1-r5-baseline.json').read_text())
    assert stage1['status']=='PASS'
    assert all(geometry['after'].get(n)==h for n,h in stage1['core_mesh_hashes'].items()),'Terrace stage changed an audited R5 opening/wall'
    assert not any(n.startswith(('R5-terrace-','R5 source terrace band / ')) for n in geometry['after'])
    largest_surface_error=0
    for row in cfg['surfaces']:
        obj=bpy.data.objects['R5 terrace surface / '+row['id']]
        polygon=row['polygon'];points=[(v.co.x/I,v.co.y/I) for v in obj.data.vertices]
        error=max(min(max(abs(a[0]-b[0]),abs(a[1]-b[1])) for b in polygon) for a in points)
        largest_surface_error=max(largest_surface_error,error);assert error<.001,row['id']
        expected=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(polygon,polygon[1:]+polygon[:1])))/2
        actual=sum(p.area for p in obj.data.polygons if p.normal.z>.9)/I**2
        assert abs(expected-actual)<.5,(row['id'],expected,actual)
        assert intersection_area(polygon,spec['polygons']['r5'])<.001,row['id']
        assert abs(max(v.co.z for v in obj.data.vertices)/I-(639 if row['kind']=='planter' else 627))<.001
    for row in cfg['guards']:
        obj=bpy.data.objects['R5 terrace guard / '+row['id']]
        assert abs(max(v.co.z for v in obj.data.vertices)/I-(627+cfg['guard_section']['height_in']))<.001
        for a,b in zip(row['path'],row['path'][1:]):
            axis=0 if a[0]!=b[0] else 1
            low,high=sorted((a[axis],b[axis]));cuts=sorted({low,high,*[p[axis] for p in spec['polygons']['r5'] if low<p[axis]<high]})
            for lo,hi in zip(cuts,cuts[1:]):
                p=list(a);p[axis]=(lo+hi)/2
                assert not inside(p,spec['polygons']['r5']),('guard enters enclosure',row['id'],p)
        # All actual bars and posts must start above their supporting band.
        assert len(obj.data.vertices)%8==0
        for start in range(0,len(obj.data.vertices),8):
            vertices=obj.data.vertices[start:start+8]
            center=[sum(v.co[k] for v in vertices)/(8*I) for k in (0,1)]
            candidates=[]
            for k,(a,b) in enumerate(zip(row['path'],row['path'][1:])):
                axis=0 if a[0]!=b[0] else 1
                if min(a[axis],b[axis])-.5<=center[axis]<=max(a[axis],b[axis])+.5:
                    distance=abs(center[1-axis]-a[1-axis])
                    if distance<.5:candidates.append(row['band_heights_in'][k])
            assert candidates,('unmapped guard part',row['id'],center)
            minimum=min(v.co.z for v in vertices)/I
            # A cap wire on the lower side of a height change stays on its own segment.
            is_corner=any(max(abs(center[0]-p[0]),abs(center[1]-p[1]))<.001 for p in row['path'])
            expected=627+(max(candidates) if is_corner else min(candidates))
            assert minimum>=expected-.001,('rail enters band',row['id'],minimum,expected)
    for row in cfg['bands']:
        obj=bpy.data.objects['R5 terrace band / '+row['id']]
        assert abs(max(v.co.z for v in obj.data.vertices)/I-(627+row['height_in']))<.001
    feature=next(e for e in spec['roof_features'] if e['id']=='south-clerestory')
    body=bpy.data.objects['south-clerestory']
    assert max(min(max(abs(v.co.x/I-p[0]),abs(v.co.y/I-p[1])) for p in feature['polygon']) for v in body.data.vertices)<.001
    for k in range(4):
        cap=bpy.data.objects[f'south-clerestory-cap-{k}']
        assert abs(max(v.co.z for v in cap.data.vertices)/I-feature['top'])<.001
        nxt=bpy.data.objects[f'south-clerestory-cap-{(k+1)%4}']
        for i,j in [(1,0),(2,3),(5,4),(6,7)]:
            assert (cap.data.vertices[i].co-nxt.data.vertices[j].co).length/I<.001
    return {'status':'PASS','audited_R5_core_meshes_preserved':len(stage1['core_mesh_hashes']),
        'terrace_and_planter_surfaces':len(cfg['surfaces']),'guard_paths':len(cfg['guards']),
        'band_paths':len(cfg['bands']),'enclosure_surface_overlap_sq_in':0,'guard_centerlines_inside_enclosure':0,
        'surface_readback_max_error_in':largest_surface_error,'guard_sections':'assumed / arrangement provisional',
        'clerestory_top_ft':342+feature['top']/12}
