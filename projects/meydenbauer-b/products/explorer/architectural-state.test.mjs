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
