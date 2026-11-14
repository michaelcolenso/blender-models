// Plan geometry and collision checks for the P2.1-derived architectural shell.
// Model coordinate basis: x plan feet south; plan y feet west; Three world X/Z metres.
// This is a presentation/collision aid, NOT a surveyed architectural geometry source.
export const FT_M = 0.3048;
export const WALL_HEIGHT_M = 2.7; // visual assumption, not a measured ceiling height
export const DOOR_HEIGHT_M = 2.05; // approximate visualization, not verified
export const GLASS_SILL_M = 0.75;

export const toWorld = ([x, y]) => ({x:x * FT_M, z:y * FT_M});

export function pointInRing(p, ring) {
  let inside=false;
  for(let i=0,j=ring.length-1;i<ring.length;j=i++){
    const a=ring[i], b=ring[j];
    if ((a[1]>p[1]) !== (b[1]>p[1]) &&
        p[0] < (b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]) inside=!inside;
  }
  return inside;
}

export function distanceToSegmentSq(p,a,b) {
  const dx=b[0]-a[0], dy=b[1]-a[1], den=dx*dx+dy*dy;
  const t=den===0?0:Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den));
  return (p[0]-a[0]-t*dx)**2 + (p[1]-a[1]-t*dy)**2;
}

function edgesNear(p, ring, radiusSq) {
  for(let i=0;i<ring.length;i++){
    if(distanceToSegmentSq(p,ring[i],ring[(i+1)%ring.length]) < radiusSq) return true;
  }
  return false;
}

export function wallCollision(worldPosition, walls, radiusM=0.22) {
  const p=[worldPosition.x / FT_M, worldPosition.z / FT_M];
  const rad=radiusM/FT_M, radSq=rad*rad;
  for(const w of walls){
    const outer=w.ring_ft, holes=w.holes_ft||[];
    // Cheap broad-phase; important because some floorplan walls are complex.
    const xs=outer.map(pt=>pt[0]), ys=outer.map(pt=>pt[1]);
    if(p[0]<Math.min(...xs)-rad || p[0]>Math.max(...xs)+rad ||
       p[1]<Math.min(...ys)-rad || p[1]>Math.max(...ys)+rad) continue;
    if(pointInRing(p,outer) && !holes.some(h=>pointInRing(p,h))) return true;
    if(edgesNear(p,outer,radSq) || holes.some(h=>edgesNear(p,h,radSq))) return true;
  }
  return false;
}

// Centerline of an inferred wall gap. The source identifies the gap, but NOT
// which side the hinges are on, which way a door swings, or any hardware.
export function openingAxis(opening, index=0) {
  if(!['door','window'].includes(opening?.kind) || !opening?.ring_ft || opening.ring_ft.length<4) {
    throw Error('Opening must have a plan polygon and kind');
  }
  const ring=opening.ring_ft.slice(0,-1);
  if(ring.length!==4) throw Error('Unsupported opening shape');
  const lengthSq=(a,b)=>(a[0]-b[0])**2+(a[1]-b[1])**2;
  let i=0;
  for(let k=1;k<4;k++) if(lengthSq(ring[k],ring[(k+1)%4])>lengthSq(ring[i],ring[(i+1)%4])) i=k;
  const mean=(a,b)=>[(a[0]+b[0])/2,(a[1]+b[1])/2];
  const start=mean(ring[i],ring[(i+3)%4]);
  const end=mean(ring[(i+1)%4],ring[(i+2)%4]);
  const a=toWorld(start), b=toWorld(end);
  const dx=b.x-a.x, dz=b.z-a.z, length=Math.hypot(dx,dz);
  if(length<0.25) throw Error('Opening too small');
  return {id:index,kind:opening.kind,start:a,end:b,length,
    yaw:Math.atan2(-dz,dx), status:'provisional', source:'P2.1 inferred gap'};
}

export function shellBlocks(position, shell, closedDoors=[], radiusM=0.22) {
  if(wallCollision(position,shell.walls,radiusM)) return true;
  const r2=radiusM**2;
  // Facade glazing can be curving buffered strips, not four-point rectangles.
  const windows=shell.openings.filter(o=>o.kind==='window');
  if(wallCollision(position,windows.map(o=>({ring_ft:o.ring_ft,holes_ft:[]})),radiusM)) return true;
  for(const door of closedDoors){
    if(distanceToSegmentSq([position.x,position.z],
       [door.start.x,door.start.z],[door.end.x,door.end.z])<r2) return true;
  }
  return false;
}

// Resolve each small swept step independently; axis fallback lets players slide
// along walls and door jambs instead of passing through them at low frame rates.
export function resolveShellMovement(from, desired, bounds, shell, closedDoors=[], radiusM=0.22) {
  if(!Number.isFinite(desired.x) || !Number.isFinite(desired.z)) throw Error('Invalid movement');
  const maxStep=0.06;
  const dx=desired.x-from.x,dz=desired.z-from.z;
  const steps=Math.max(1,Math.ceil(Math.hypot(dx,dz)/maxStep));
  let x=from.x,z=from.z;
  const safe=(xx,zz)=>xx>=bounds.minX&&xx<=bounds.maxX&&zz>=bounds.minZ&&zz<=bounds.maxZ&&
    !shellBlocks({x:xx,z:zz},shell,closedDoors,radiusM);
  for(let i=0;i<steps;i++){
    const stepX=dx/steps,stepZ=dz/steps;
    if(safe(x+stepX,z+stepZ)){x+=stepX;z+=stepZ;}
    else if(safe(x+stepX,z)) x+=stepX;
    else if(safe(x,z+stepZ)) z+=stepZ;
  }
  return {x,z};
}

export function findFreeSpawn(bounds,shell,radiusM=0.22) {
  const cx=(bounds.minX+bounds.maxX)/2,cz=(bounds.minZ+bounds.maxZ)/2;
  const candidates=[];
  for(let i=0;i<=16;i++) for(let j=0;j<=16;j++){
    const x=bounds.minX + (i+0.5)/17*(bounds.maxX-bounds.minX);
    const z=bounds.minZ + (j+0.5)/17*(bounds.maxZ-bounds.minZ);
    candidates.push({x,z,d:(x-cx)**2+(z-cz)**2});
  }
  candidates.sort((a,b)=>a.d-b.d);
  const free=candidates.find(p=>!shellBlocks(p,shell,[],radiusM));
  if(!free) throw Error('No collision-free spawn for B-103');
  return {x:free.x,z:free.z,yaw:Math.atan2(-(cx-free.x),-(cz-free.z))};
}
