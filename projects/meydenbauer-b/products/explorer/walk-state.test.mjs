import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {B103_UNIT_ID, findB103, walkBoundsFromExtents, spawnInBounds, moveWalk} from './walk-state.mjs';

const state = JSON.parse(readFileSync(new URL('../../state/project-state.json', import.meta.url)));
const slab = {minX: 0, maxX: 30, minZ: 0, maxZ: 20};
const pipes = {minX: 10, maxX: 22, minZ: 5, maxZ: 14};

test('walk mode chooses the actual canonical B-103 interval', () => {
  const unit = findB103(state.metadata.timeline);
  assert.equal(unit.element_id, B103_UNIT_ID);
  assert.equal(unit.unit, 'B-103');
  assert.equal(unit.start_day, 0);
  assert.equal(unit.end_day, 19);
  assert.throws(() => findB103({units: []}));
});

test('schematic area pads B-103 mesh extents but cannot leave slab bounds', () => {
  assert.deepEqual(walkBoundsFromExtents(pipes, slab, 2), {
    minX: 8, maxX: 24, minZ: 3, maxZ: 16,
  });
  assert.deepEqual(walkBoundsFromExtents({minX: -1,maxX: 4,minZ: -2,maxZ: 5}, slab, 2), {
    minX: 0.35, maxX: 6, minZ: 0.35, maxZ: 7,
  });
  assert.throws(() => walkBoundsFromExtents(pipes, null));
  assert.throws(() => walkBoundsFromExtents({minX: 40,maxX: 45,minZ: 30,maxZ: 35},slab));
});

test('eye position spawns inside guard and faces its center', () => {
  const bounds = walkBoundsFromExtents(pipes, slab, 2);
  const spawn = spawnInBounds(bounds);
  assert.ok(spawn.x > bounds.minX && spawn.x < bounds.maxX);
  assert.ok(spawn.z > bounds.minZ && spawn.z < bounds.maxZ);
  const forward = moveWalk(spawn, {forward:true}, spawn.yaw, 0.1, bounds);
  const cx = (bounds.minX+bounds.maxX)/2, cz = (bounds.minZ+bounds.maxZ)/2;
  assert.ok(Math.hypot(forward.x-cx, forward.z-cz) < Math.hypot(spawn.x-cx, spawn.z-cz));
});

test('WASD movement is yaw-relative, normalized on diagonals and capped per frame', () => {
  const bounds={minX:-50,maxX:50,minZ:-50,maxZ:50}, origin={x:0,z:0};
  const forward=moveWalk(origin, {forward:true}, 0, 0.1, bounds);
  assert.ok(Math.abs(forward.x)<1e-9 && Math.abs(forward.z+0.22)<1e-9);
  const right=moveWalk(origin,{right:true},0,0.1,bounds);
  assert.ok(Math.abs(right.x-0.22)<1e-9 && Math.abs(right.z)<1e-9);
  const turn=moveWalk(origin,{forward:true},Math.PI/2,0.1,bounds);
  assert.ok(Math.abs(turn.x+0.22)<1e-9 && Math.abs(turn.z)<1e-9);
  const diagonal=moveWalk(origin,{forward:true,right:true},0,0.1,bounds);
  assert.ok(Math.abs(Math.hypot(diagonal.x,diagonal.z)-0.22)<1e-9);
  assert.deepEqual(moveWalk(origin,{},0,0.1,bounds),origin);
  assert.ok(Math.hypot(...Object.values(moveWalk(origin,{forward:true},0,3,bounds)))<=0.221);
});

test('player cannot move across collision guard, regardless of input', () => {
  const bounds=walkBoundsFromExtents(pipes,slab,2);
  let p={x:bounds.minX+0.1,z:bounds.minZ+0.1};
  for(let i=0;i<1000;i++) p=moveWalk(p,{left:true,forward:true},0,0.1,bounds);
  assert.deepEqual(p,{x:bounds.minX,z:bounds.minZ});
  assert.throws(()=>moveWalk(p,{forward:true},0,-1,bounds));
  assert.throws(()=>moveWalk(p,{forward:true},NaN,0.1,bounds));
});
