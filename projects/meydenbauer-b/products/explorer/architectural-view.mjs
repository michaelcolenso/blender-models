import * as THREE from 'three';
import {FT_M, WALL_HEIGHT_M, DOOR_HEIGHT_M, GLASS_SILL_M, openingAxis} from './architectural-state.mjs';

// Read-only Three.js interpretation of the already-extracted P2.1 architectural base.
// Doors/hinges/heights are presentation assumptions; wall footprints & opening gaps
// are source-derived and retain provisional status in the canonical project documents.
const planPoint = ([x,y]) => new THREE.Vector2(x*FT_M,-y*FT_M);
const makeLoop = ring => ring.map(planPoint);
const wallMaterial = new THREE.MeshStandardMaterial({
  color:0xe4dfd1,roughness:0.82,transparent:true,opacity:1,side:THREE.DoubleSide,
});
const doorMaterial = new THREE.MeshStandardMaterial({
  color:0x9b7d56,roughness:0.75,side:THREE.DoubleSide,
});
const glassMaterial = new THREE.MeshStandardMaterial({
  color:0x8bb9c9,roughness:0.18,metalness:0.12,
  transparent:true,opacity:0.34,depthWrite:false,side:THREE.DoubleSide,
});

export function buildArchitecturalView(shell,floorY){
  const group=new THREE.Group();
  group.name='P2.1 architectural shell · provisional';
  group.visible=false;

  for(let i=0;i<shell.walls.length;i++){
    const wall=shell.walls[i];
    if(wall.ring_ft.length<4) continue;
    const shape=new THREE.Shape(makeLoop(wall.ring_ft));
    for(const hole of wall.holes_ft||[]){
      if(hole.length>=4) shape.holes.push(new THREE.Path(makeLoop(hole)));
    }
    const geometry=new THREE.ExtrudeGeometry(shape,{
      depth:WALL_HEIGHT_M,bevelEnabled:false,steps:1,curveSegments:1,
    });
    geometry.rotateX(-Math.PI/2);
    const mesh=new THREE.Mesh(geometry,wallMaterial);
    mesh.name='P2.1 wall footprint '+i+' · provisional';
    mesh.position.y=floorY;
    mesh.userData={basis:'P2.1 paired linework',status:'provisional'};
    group.add(mesh);
  }

  const doors=[];
  for(let i=0;i<shell.openings.length;i++){
    const o=shell.openings[i];
    if(o.kind==='door'){
      const axis=openingAxis(o,i);
      const hinge=new THREE.Group();
      hinge.name='P2.1 door gap '+i+' · assumed swing';
      hinge.position.set(axis.start.x,floorY,axis.start.z);
      const panel=new THREE.Mesh(
        new THREE.BoxGeometry(Math.max(0.15,axis.length-0.035),DOOR_HEIGHT_M,0.045),doorMaterial,
      );
      panel.position.set(axis.length/2,DOOR_HEIGHT_M/2,0);
      panel.name='Door panel · illustrative';
      hinge.add(panel);
      hinge.rotation.y=axis.yaw+Math.PI*0.42;
      group.add(hinge);
      doors.push({...axis,root:hinge,open:true,targetYaw:axis.yaw+Math.PI*0.42});
    } else {
      // Glazing includes long curved facade gaps; extrude each *original plan footprint*
      // rather than reducing the gap to an invented axis-aligned rectangle.
      const shape=new THREE.Shape(makeLoop(o.ring_ft));
      const geometry=new THREE.ExtrudeGeometry(shape,{
        depth:1.35,bevelEnabled:false,steps:1,curveSegments:1,
      });
      geometry.rotateX(-Math.PI/2);
      const pane=new THREE.Mesh(geometry,glassMaterial);
      pane.position.y=floorY+GLASS_SILL_M;
      pane.name='P2.1 glazing footprint '+i+' · provisional';
      group.add(pane);
    }
  }

  function display(active,xray){
    group.visible=active;
    wallMaterial.opacity=xray?0.18:1;
    wallMaterial.depthWrite=!xray;
    glassMaterial.opacity=xray?0.12:0.34;
  }

  function animate(dt){
    const k=Math.min(1,Math.max(0,dt)*9);
    for(const door of doors){
      door.root.rotation.y += (door.targetYaw-door.root.rotation.y)*k;
    }
  }

  function nearestDoor(position,forward,range=2.2){
    let best=null,score=Infinity;
    for(const door of doors){
      const cx=(door.start.x+door.end.x)/2,cz=(door.start.z+door.end.z)/2;
      const dx=cx-position.x,dz=cz-position.z,dist=Math.hypot(dx,dz);
      if(dist>range || dist<0.0001) continue;
      const dot=(dx*forward.x+dz*forward.z)/dist;
      if(dot<0.2) continue;
      const s=dist-0.5*dot;
      if(s<score){score=s;best=door;}
    }
    return best;
  }

  function toggleDoor(door){
    if(!door)return false;
    door.open=!door.open;
    door.targetYaw=door.yaw + (door.open?Math.PI*0.42:0);
    return door.open;
  }

  return {group,doors,display,animate,nearestDoor,toggleDoor};
}
