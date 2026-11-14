// Presentation-only movement for a schematic B-103 walkthrough.
// Coordinates are Three.js world metres after glTF's Blender Z-up -> Y-up conversion.
// No project measurements, construction rates or scenario geometry are calculated here.
export const B103_UNIT_ID = 'meydenbauer-b:unit:b-103';
export const EYE_HEIGHT_M = 1.65;
export const WALK_SPEED_MPS = 2.2;
export const PLAYER_RADIUS_M = 0.35;

export function findB103(timeline) {
  const unit = timeline.units.find(u => u.element_id === B103_UNIT_ID);
  if (!unit || unit.start_day !== 0) throw Error('B-103 missing from canonical baseline');
  return unit;
}

function validExtents(extents) {
  return extents && ['minX', 'maxX', 'minZ', 'maxZ'].every(k => Number.isFinite(extents[k]))
    && extents.maxX > extents.minX && extents.maxZ > extents.minZ;
}

// Rough, axis-aligned *navigation guard* inferred from B-103 schematic meshes.
// It is NOT the apartment boundary or wall layout. Stay within the slab massing.
export function walkBoundsFromExtents(unit, slab, padding = 1.8, clearance = PLAYER_RADIUS_M) {
  if (!validExtents(unit) || !validExtents(slab) || padding < 0 || clearance < 0) {
    throw Error('Invalid walk extents');
  }
  const bounds = {
    minX: Math.max(unit.minX - padding, slab.minX + clearance),
    maxX: Math.min(unit.maxX + padding, slab.maxX - clearance),
    minZ: Math.max(unit.minZ - padding, slab.minZ + clearance),
    maxZ: Math.min(unit.maxZ + padding, slab.maxZ - clearance),
  };
  if (!validExtents(bounds) || bounds.maxX - bounds.minX < 2 * clearance
      || bounds.maxZ - bounds.minZ < 2 * clearance) {
    throw Error('No walkable schematic area inside the slab');
  }
  return bounds;
}

export function spawnInBounds(bounds) {
  if (!validExtents(bounds)) throw Error('Invalid walk bounds');
  const x = bounds.minX + (bounds.maxX - bounds.minX) * 0.28;
  const z = bounds.minZ + (bounds.maxZ - bounds.minZ) * 0.28;
  const targetX = (bounds.minX + bounds.maxX) / 2;
  const targetZ = (bounds.minZ + bounds.maxZ) / 2;
  return {x, z, yaw: Math.atan2(-(targetX - x), -(targetZ - z))};
}

export function moveWalk(position, keys, yaw, seconds, bounds, speed = WALK_SPEED_MPS) {
  if (!validExtents(bounds) || !Number.isFinite(seconds) || seconds < 0
      || !Number.isFinite(yaw) || !Number.isFinite(speed) || speed < 0) {
    throw Error('Invalid walk movement');
  }
  const forward = Number(!!keys.forward) - Number(!!keys.backward);
  const strafe = Number(!!keys.right) - Number(!!keys.left);
  const length = Math.hypot(forward, strafe);
  const step = length ? Math.min(seconds, 0.1) * speed / length : 0;
  const x = position.x + (-Math.sin(yaw) * forward + Math.cos(yaw) * strafe) * step;
  const z = position.z + (-Math.cos(yaw) * forward - Math.sin(yaw) * strafe) * step;
  return {
    x: Math.max(bounds.minX, Math.min(bounds.maxX, x)),
    z: Math.max(bounds.minZ, Math.min(bounds.maxZ, z)),
  };
}
