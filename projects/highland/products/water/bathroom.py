"""Refine the five-fixture pilot without asserting undocumented fitting selections.

All spatial dimensions are inches. Model checks use explicit ports, independent
of the visual mesh. Fitting quantities are derived model quantities, not takeoff.
"""
import math

def refine(elements, source):
    byid={e['id']:e for e in elements}
    fixtures=['master-shower','master-bath','master-wc','master-lav-1','master-lav-2']
    routes=['A-cold-master','A-hot-master','A-cold-lavs','A-hot-bath-loop',
        'shower-master-cw','shower-master-hw','bath-cw','bath-hw','wc-master-cw',
        'lav-300-cw','lav-300-hw','lav-375-cw','lav-375-hw']
    def add(id,kind,system,**kw):
        e=dict(id=id,kind=kind,scene='unit',system=system,status='assumed',source=source,
          basis='Representative bathroom hardware and connection geometry; exact fitting product, access, heights and configuration are not established by the drawings.',
          pilot=True,hardware_status='assumed',xy_status='assumed',**kw)
        elements.append(e);byid[id]=e
        return e
    def pipe(id,system,points,size,role):
        return add(id,'pipe',system,points=points,nominal_in=size,size_status='assumed',
          size_basis='Representative fixture connector or mixed-water outlet; not a documented product selection.',
          terminal=True,role=role)
    for id in fixtures+routes:byid[id]['pilot']=True
    # Remove a doubled-back segment in the earlier schematic; keep the same
    # traced supply and circulating loop paths with a single connection.
    byid['A-hot-bath-loop']['points']=byid['A-hot-bath-loop']['points'][1:]
    # Drop routes originally included a short overlapping length along a main.
    # Start at the actual perpendicular takeoff so every tee has one center.
    for id in routes[4:]:
        e=byid[id]
        if len(e['points'])>2 and e['points'][0]!=e['points'][1]:
            e['points']=e['points'][1:]
    contract=[]
    # Lavatory connector ports terminate beneath the faucet body, above the
    # stop valve. The pipe route remains independent of the fixture envelope.
    for index,prefix in [(1,'lav-300'),(2,'lav-375')]:
        f=byid['master-lav-'+str(index)];x,y,z=f['at'];f['pilot_device']='lavatory'
        f['supply_ports']={}
        for system,suffix,sign in [('CW','cw',-1),('HW','hw',1)]:
            drop=byid[prefix+'-'+suffix];start=drop['points'][0]
            end=[drop['points'][-1][0],round(y+18,5),24]
            drop['points']=[start,[start[0],end[1],start[2]],end]
            drop['xy_status']='assumed';drop['local_offset_assumed']=True
            drop['basis']='Assumed wall-side drop 18 in behind fixture center, avoiding the porcelain envelope; source branch and nominal diameter retained.'
            port=[round(x+sign*2.5,5),round(y+6.3,5),30.0]
            hoseid=f['id']+'-'+suffix+'-connector'
            hose=pipe(hoseid,system,[end,[end[0],end[1]-3,21],[port[0],port[1],25],port],.375,'fixture supply connector')
            hose['sweep_style']='smooth';hose['fixture_id']=f['id']
            add(f['id']+'-'+suffix+'-stop','stop',system,at=[end[0],end[1],26],
                axis=[0,0,1],nominal_in=.5,ports=[[end[0],end[1],24],[end[0],end[1],28]],role='representative lavatory stop',route_id=drop['id'])
            f['supply_ports'][system]=port
            contract.append(dict(fixture=f['id'],system=system,drop=drop['id'],connector=hoseid,port=port))
    f=byid['master-wc'];x,y,z=f['at'];f['pilot_device']='toilet';drop=byid['wc-master-cw']
    start=[round(x-4,5),drop['points'][0][1],drop['points'][0][2]]
    end=[round(x-4,5),round(y+18,5),12]
    drop['points']=[start,[start[0],end[1],start[2]],end]
    drop['xy_status']='assumed';drop['local_offset_assumed']=True
    drop['basis']='Assumed wall-side toilet drop behind the tank; source nominal supply retained.'
    port=[round(x-4,5),round(y+9.4,5),18.0];f['supply_ports']={'CW':port}
    hose=pipe('master-wc-cw-connector','CW',[end,[end[0]-3,end[1]-3,10],[port[0],port[1]-2,14],port],.375,'toilet supply connector');hose['sweep_style']='smooth';hose['fixture_id']=f['id']
    add('master-wc-stop','stop','CW',at=[end[0],end[1],14],axis=[0,0,1],nominal_in=.5,
        ports=[[end[0],end[1],12],[end[0],end[1],16]],role='representative toilet stop',route_id=drop['id'])
    contract.append(dict(fixture=f['id'],system='CW',drop=drop['id'],connector=hose['id'],port=port))
    devices=[]
    for fid,prefix,zout,diam in [('master-shower','shower-master',50,.5),('master-bath','bath',26,.75)]:
        f=byid[fid];f['pilot_device']='shower' if fid=='master-shower' else 'tub'
        cold=byid[prefix+'-cw'];hot=byid[prefix+'-hw']
        cp,hp=cold['points'][-1],hot['points'][-1]
        center=[(a+b)/2 for a,b in zip(cp,hp)];out=[center[0],center[1],zout]
        device=add(fid+'-mixing-body','mixer','equipment',at=center,
            supply_ports={'CW':cp,'HW':hp},outlet=out,nominal_in=diam,
            inlet_sizes={'CW':cold['nominal_in'],'HW':hot['nominal_in']},
            fixture_id=fid,role='representative mixing body; control type and internal stops unverified')
        f['supply_ports']={'CW':cp,'HW':hp}
        for system,drop in [('CW',cold),('HW',hot)]:
            contract.append(dict(fixture=fid,system=system,drop=drop['id'],connector=None,port=drop['points'][-1],device=device['id']))
        if fid=='master-shower':
            end=[center[0],center[1]+6,80]
            points=[out,[center[0],center[1]+16.5,zout],[center[0],center[1]+16.5,80],end]
            f['head_port']=end
        else:
            end=[center[0],center[1]-7,23]
            points=[out,[center[0],center[1]-7,zout],end]
            f['spout_port']=end
        outlet=pipe(fid+'-mixed-outlet','MW',points,diam,'mixed-water fixture outlet')
        outlet['fixture_id']=fid;devices.append(dict(device=device['id'],outlet_route=outlet['id'],outlet=out,end=end))

    # Generate rounded centerlines and separately identified elbow sleeves.
    def sub(a,b):return [x-y for x,y in zip(a,b)]
    def length(a):return math.sqrt(sum(x*x for x in a))
    def unit(a):
        n=length(a);return [x/n for x in a]
    def rounded(e):
        pts=[]
        for p in e['points']:
            if not pts or length(sub(p,pts[-1]))>1e-6:pts.append(p)
        out=[pts[0]]
        for i in range(1,len(pts)-1):
            a,b,c=pts[i-1:i+2];u=unit(sub(b,a));v=unit(sub(c,b));dot=sum(x*y for x,y in zip(u,v))
            if abs(dot)>1e-5:
                out.append(b);continue
            radius=min(e['nominal_in']*2.5,length(sub(b,a))*.2,length(sub(c,b))*.2)
            center=[b[k]-u[k]*radius+v[k]*radius for k in range(3)]
            arc=[[round(center[k]+radius*(u[k]*math.sin(t*math.pi/16)-v[k]*math.cos(t*math.pi/16)),5) for k in range(3)] for t in range(9)]
            out.extend(arc)
            add(e['id']+'-elbow-'+str(i),'elbow',e['system'],points=arc,ports=[arc[0],arc[-1]],
                nominal_in=e['nominal_in'],bend_radius_in=radius,route_id=e['id'],role='representative 90 degree elbow')
        out.append(pts[-1]);e['render_points']=out
    for e in list(elements):
        if e.get('pilot') and e['kind']=='pipe':
            clean=[]
            for p in e['points']:
                if not clean or length(sub(p,clean[-1]))>1e-6:clean.append(p)
            e['points']=clean
            if e.get('sweep_style')!='smooth':rounded(e)

    # Infer tee bodies at branch starts on the interior of another pilot route.
    pilotpipes=[e for e in elements if e.get('pilot') and e['kind']=='pipe' and e['system'] in ['CW','HW']]
    for e in pilotpipes:
        if 'connector' in e['id']:continue
        start=e['points'][0];pnext=e['points'][1]
        if length(sub(pnext,start))<1e-5:continue
        branchdir=unit(sub(pnext,start));found=False
        for main in pilotpipes:
            if main is e or main['system']!=e['system']:continue
            for a,b in zip(main['points'],main['points'][1:]):
                d=sub(b,a);n=length(d)
                if n<1e-6:continue
                t=sum(x*y for x,y in zip(sub(start,a),d))/(n*n)
                residual=length(sub(start,[a[k]+t*d[k] for k in range(3)]))
                if 1e-5<t<1-1e-5 and residual<.001 and abs(sum(x*y for x,y in zip(unit(d),branchdir)))<.01:
                    axis=unit(d);reach=max(main['nominal_in'],e['nominal_in'])*2.4
                    ports=[[round(start[k]+sign*axis[k]*reach,5) for k in range(3)] for sign in [-1,1]]
                    ports.append([round(start[k]+branchdir[k]*reach,5) for k in range(3)])
                    add(e['id']+'-tee','tee',e['system'],at=start,ports=ports,
                        diameters=[main['nominal_in'],main['nominal_in'],e['nominal_in']],nominal_in=main['nominal_in'],
                        route_id=e['id'],main_route_id=main['id'],role='representative branch tee')
                    found=True;break
            if found:break
    # Explicit dimensional/connection contract for verification, not just counts.
    return dict(fixtures=fixtures,supply_connections=contract,mixed_outlets=devices,
        expected_supply_ports={'CW':5,'HW':4},expected_stops=5,expected_mixers=2,
        scope='Primary bathroom domestic-water supplies only; drainage and venting are not included.',
        hardware_basis='Elbows, tees, flexible connector dimensions, five stops and two mixer bodies are representative; not a manufacturer schedule or verified installed assembly.',
        heights_in={'CW_overhead':102,'HW_overhead':100,'HWC_overhead':98,'lav_stop':26,'wc_stop':14,'shower_mixer':48,'tub_mixer':24,'shower_head':80},
        height_status='assumed')
