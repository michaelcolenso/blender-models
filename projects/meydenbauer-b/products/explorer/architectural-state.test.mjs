import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {FT_M,toWorld,pointInRing,openingAxis,wallCollision,shellBlocks,
  resolveShellMovement,findFreeSpawn} from './architectural-state.mjs';

const shell=JSON.parse(readFileSync(new URL('../underslab/meydenbauer-b.shell.json',import.meta.url)));

test('architectural source is the P2.1-derived snapshot, not invented geometry',()=>{
  assert.match(shell.source.sheet,/P2\.1/);
  assert.equal(shell.provenance.walls.status,'provisional');
  assert.equal(shell.provenance.openings.status,'provisional');
  assert.ok(shell.walls.length>40);
  assert.ok(shell.openings.some(o=>o.kind==='door'));
  assert.ok(shell.rooms.some(r=>r.name==='BED ROOM'));
  assert.deepEqual(toWorld([10,20]),{x:10*FT_M,z:20*FT_M});
});

test('point-in-polygon respects an explicit hole and corner radius',()=>{
  const wall={ring_ft:[[0,0],[10,0],[10,10],[0,10]],holes_ft:[[[3,3],[7,3],[7,7],[3,7]]]};
  assert.ok(pointInRing([1,1],wall.ring_ft));
  assert.equal(wallCollision(toWorld([5,5]),[wall],0.1),false);
  assert.equal(wallCollision(toWorld([1,1]),[wall],0.1),true);
  assert.equal(wallCollision(toWorld([2.99,5]),[wall],0.1),true);
  assert.equal(wallCollision(toWorld([-5,5]),[wall],0.1),false);
});

test('opening axes are located on source gaps, no inferred hinges claim',()=>{
  const opening={kind:'door',ring_ft:[[0,0],[3,0],[3,0.5],[0,0.5],[0,0]]};
  const axis=openingAxis(opening,5);
  assert.equal(axis.id,5);
  assert.equal(axis.kind,'door');
  assert.equal(axis.status,'provisional');
  assert.ok(Math.abs(axis.length-3*FT_M)<1e-10);
  assert.ok(Math.abs(axis.start.z-0.25*FT_M)<1e-10);
  assert.throws(()=>openingAxis({kind:'door',ring_ft:[[0,0]]}));
});

test('walls, window panes and closed doors block navigation',()=>{
  const empty={walls:[],openings:[]};
  const d=openingAxis({kind:'door',ring_ft:[[0,0],[3,0],[3,0.5],[0,0.5],[0,0]]});
  assert.equal(shellBlocks(toWorld([1.5,0.25]),empty),false);
  assert.equal(shellBlocks(toWorld([1.5,0.25]),empty,[d]),true);
  assert.equal(shellBlocks(toWorld([1.5,0.25]),{walls:[],openings:[{kind:'window',ring_ft:[[0,0],[3,0],[3,0.5],[0,0.5],[0,0]]}]}),true);
});

test('swept movement does not tunnel through walls; movement slides along walls',()=>{
  const thick={ring_ft:[[1,-10],[2,-10],[2,10],[1,10]],holes_ft:[]};
  const wallset={walls:[thick],openings:[]}, bounds={minX:-10,maxX:10,minZ:-10,maxZ:10};
  const stopped=resolveShellMovement({x:0,z:0},{x:3,z:0},bounds,wallset);
  assert.ok(stopped.x<FT_M,JSON.stringify(stopped));
  const slide=resolveShellMovement({x:0,z:0},{x:3,z:1},bounds,wallset);
  assert.ok(slide.z>0 && slide.x<FT_M);
});

test('source geometry provides a valid collision-free B-103 candidate spawn',()=>{
  const bounds={minX:82*FT_M,maxX:124*FT_M,minZ:5*FT_M,maxZ:55*FT_M};
  const p=findFreeSpawn(bounds,shell);
  assert.ok(p.x>=bounds.minX&&p.x<=bounds.maxX);
  assert.ok(p.z>=bounds.minZ&&p.z<=bounds.maxZ);
  assert.equal(shellBlocks(p,shell),false);
});

test('spawn faces a clear path instead of a nearby wall at the guard center',()=>{
  const bounds={minX:0,maxX:6,minZ:0,maxZ:6};
  const wall={ring_ft:[[9,-1],[10,-1],[10,21],[9,21]]};
  const scene={walls:[wall],openings:[]};
  const p=findFreeSpawn(bounds,scene);
  for(let step=0;step<=60;step++){
    const distance=step*0.05;
    const q={x:p.x-Math.sin(p.yaw)*distance,z:p.z-Math.cos(p.yaw)*distance};
    assert.equal(shellBlocks(q,scene),false,JSON.stringify(q));
    assert.ok(q.x>=0&&q.x<=6&&q.z>=0&&q.z<=6);
  }
});

test('reentry spawn respects doors left closed, and small spaces retain a safe fallback',()=>{
  const empty={walls:[],openings:[]};
  const bounds={minX:0,maxX:0.8,minZ:0,maxZ:0.8};
  const door={start:{x:0.4,z:0},end:{x:0.4,z:0.8}};
  const p=findFreeSpawn(bounds,empty,0.22,[door]);
  assert.equal(shellBlocks(p,empty,[door]),false);
  assert.ok(p.x>=0&&p.x<=0.8&&p.z>=0&&p.z<=0.8);
  assert.throws(()=>findFreeSpawn({minX:0.3,maxX:0.5,minZ:0,maxZ:0.8},empty,0.22,[door]),
    /No collision-free spawn/);
});
