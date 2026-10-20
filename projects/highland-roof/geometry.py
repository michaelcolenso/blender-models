"""Apply bounded, source-recorded roof/terrace corrections to the saved revision."""
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
I = .0254
TRADES = ("Envelope", "Glazing", "Balconies", "Roof")


def mesh_record(obj):
    return [obj.name, [list(row) for row in obj.matrix_world],
            [list(v.co) for v in obj.data.vertices], [list(p.vertices) for p in obj.data.polygons]]


def inventory():
    result = {}
    for name in TRADES:
        for obj in bpy.data.collections[name].objects:
            if obj.type == "MESH":
                result[obj.name] = hashlib.sha256(json.dumps(mesh_record(obj), separators=(",", ":")).encode()).hexdigest()
    return result


def digest(records):
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def create_mesh(name, vertices, faces, materials, source, basis, collection="Roof"):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.data.collections[collection].objects.link(obj)
    for material in materials:
        data.materials.append(bpy.data.materials[material])
    obj["source"] = source
    obj["basis"] = basis
    obj["status"] = "assumed"
    obj["geometry_revision"] = "03 / roof and terrace geometry"
    return obj


FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def solid(vertices, faces, polygon, bottom, top):
    offset = len(vertices)
    vertices.extend([(p[0]*I, p[1]*I, z*I) for z in (bottom, top) for p in polygon])
    faces.extend([tuple(offset+j for j in face) for face in FACES])


def strip(a, b, width, extend=0):
    a, b = Vector(a), Vector(b)
    u = (b-a).normalized()
    n = Vector((-u.y, u.x))
    a, b = a-u*extend, b+u*extend
    return [a-n*width/2, b-n*width/2, b+n*width/2, a+n*width/2]


def split_roof_edges(polygon, threshold):
    result = []
    for index, (a, b) in enumerate(zip(polygon, polygon[1:]+polygon[:1])):
        cuts = [Vector(a)]
        if (a[1]-threshold)*(b[1]-threshold) < 0:
            t = (threshold-a[1])/(b[1]-a[1])
            cuts.append(Vector((a[0]+t*(b[0]-a[0]), threshold)))
        cuts.append(Vector(b))
        for start, end in zip(cuts, cuts[1:]):
            zone = "north" if (start.y+end.y)/2 > threshold else "south"
            name = f"roof-parapet-{index}" + ("-"+zone if len(cuts) == 3 else "")
            result.append({"name": name, "a": start, "b": end, "zone": zone})
    return result


def apply_geometry(config, spec):
    before = inventory()
    changed_expected = {name for name in before if name.startswith("roof-parapet-")}
    changed_expected |= {name for name in before if any(name.startswith(e["id"]+"-cap-") for e in spec["roof_features"])}
    roof = config["roof_coping"]
    # Correct the two long R5 wall edges whose midpoint classification places
    # part of their top on the wrong side of the retained roof-level split.
    wall_changes = []
    split = spec["north_roof_split_y"]
    for obj in list(bpy.data.collections["Envelope"].objects):
        if obj.type != "MESH" or not obj.name.startswith("wall-R5-"):
            continue
        bounds = [obj.matrix_world@v.co for v in obj.data.vertices]
        if not min(v.y for v in bounds) < split*I < max(v.y for v in bounds):
            continue
        old_top = max(v.z for v in bounds)
        old_material = list(obj.data.materials)
        vertices, faces = [], []
        assert len(obj.data.vertices) % 8 == 0
        for start in range(0, len(obj.data.vertices), 8):
            chunk = [v.co for v in obj.data.vertices[start:start+8]]
            lo = [min(v[k] for v in chunk)/I for k in range(3)]
            hi = [max(v[k] for v in chunk)/I for k in range(3)]
            ys = sorted({lo[1], hi[1], *([split] if lo[1] < split < hi[1] else [])})
            for a, b in zip(ys, ys[1:]):
                top = hi[2]
                if abs(hi[2]*I-old_top) < 1e-4:
                    top = spec["north_roof_plate_z"] if (a+b)/2 > split else spec["roof_plate_z"]
                if top <= lo[2]:
                    continue
                solid(vertices, faces, [(lo[0], a), (hi[0], a), (hi[0], b), (lo[0], b)], lo[2], top)
        data = bpy.data.meshes.new(obj.name+" / split roof header")
        data.from_pydata(vertices, [], faces)
        data.update()
        for mat in old_material:
            data.materials.append(mat)
        obj.data = data
        obj["source"] = "A2.08 roof levels / inherited north_roof_split_y control"
        obj["basis"] = "Split the R5 header at the retained roof-level change; opening geometry and all lower vertices remain governed by the inherited spec. Split position and wall sections remain assumed."
        changed_expected.add(obj.name)
        wall_changes.append(obj.name)

    for obj in list(bpy.data.collections["Roof"].objects):
        if obj.name.startswith("roof-parapet-"):
            bpy.data.objects.remove(obj, do_unlink=True)
    edges = split_roof_edges(spec["polygons"]["r5"], split)
    normals = []
    for edge in edges:
        u = (edge["b"]-edge["a"]).normalized()
        normals.append(Vector((-u.y, u.x)))

    def offset_corner(index, distance):
        current, previous = normals[index], normals[index-1]
        return edges[index]["a"]+(current+previous)*distance/(1+current.dot(previous))

    for index, edge in enumerate(edges):
        datum = (roof["north_top_ft"] if edge["zone"] == "north" else roof["south_top_ft"])-342
        top = datum*12
        base = spec["north_roof_plate_z"] if edge["zone"] == "north" else spec["roof_plate_z"]
        vertices, faces = [], []
        solid(vertices, faces, strip(edge["a"], edge["b"], roof["wall_thickness_in"]), base, top-roof["main_thickness_in"])
        next_index = (index+1) % len(edges)
        half = roof["main_width_in"]/2
        cap = [offset_corner(index, -half), offset_corner(next_index, -half),
               offset_corner(next_index, half), offset_corner(index, half)]
        solid(vertices, faces, cap, top-roof["main_thickness_in"], top)
        obj = create_mesh(edge["name"], vertices, faces, ["concrete"], roof["source"], roof["basis"])
        obj["top_elevation_ft"] = 342+top/12
        obj["datum_status"] = "confirmed"

    for feature in spec["roof_features"]:
        # The inherited tower is a closed solid extending to the control datum.
        # Its wall-body top must sit below the lowered cap to avoid coincident faces.
        body = bpy.data.objects[feature["id"]]
        top = max(v.co.z for v in body.data.vertices)
        for vertex in body.data.vertices:
            if abs(vertex.co.z-top) < 1e-5:
                vertex.co.z = (feature["top"]-roof["tower_cap_thickness_in"])*I
        body["basis"] = feature["basis"]+" Revision 03 body terminates below the cap; documented top applies to the complete capped feature."
        body["datum_applies_to"] = "complete capped feature"
        changed_expected.add(body.name)
        for obj in list(bpy.data.collections["Roof"].objects):
            if not obj.name.startswith(feature["id"]+"-cap-"):
                continue
            index = int(obj.name.rsplit("-", 1)[-1])
            polygon = [Vector(p) for p in feature["polygon"]]
            ns = []
            for a, b in zip(polygon, polygon[1:]+polygon[:1]):
                u = (b-a).normalized()
                ns.append(Vector((-u.y, u.x)))
            def corner(k, distance):
                return polygon[k]+(ns[k]+ns[k-1])*distance/(1+ns[k].dot(ns[k-1]))
            next_index = (index+1) % len(polygon)
            half = roof["tower_cap_width_in"]/2
            cap = [corner(index, -half), corner(next_index, -half),
                   corner(next_index, half), corner(index, half)]
            vertices, faces = [], []
            solid(vertices, faces, cap, feature["top"]-roof["tower_cap_thickness_in"], feature["top"])
            data = bpy.data.meshes.new(obj.name+" / mitered")
            data.from_pydata(vertices, [], faces)
            data.materials.append(bpy.data.materials["concrete"])
            data.update()
            obj.data = data
            obj["basis"] = roof["basis"]
            obj["datum_status"] = "confirmed"
            obj["top_elevation_ft"] = 342+feature["top"]/12

    new_bands = []
    polygon = spec["polygons"]["typical"]
    for band in config["terrace_bands"]:
        for segment in band["segments"]:
            a, b = polygon[segment], polygon[(segment+1) % len(polygon)]
            vertices, faces = [], []
            top = 627+band["height_in"]
            solid(vertices, faces, strip(a, b, spec["wall_thickness"]), 627, top-band["cap_height_in"])
            solid(vertices, faces, strip(a, b, band["cap_width_in"], 1.5), top-band["cap_height_in"], top)
            axis = "x" if abs(a[1]-b[1]) < .01 else "y"
            material = "brick-"+axis if band["finish"] == "brick" else "concrete"
            obj = create_mesh(f"R5 source terrace band / {segment:02}", vertices, faces, [material, "concrete"], band["source"], band["basis"])
            for face in obj.data.polygons:
                face.material_index = int(face.index >= 6)
            obj["height_status"] = "provisional"
            obj["height_uncertainty_in"] = config["vertical_registration"]["height_uncertainty_in"]
            new_bands.append(obj.name)

    # The MN pair is mirrored in A3.01; move only its internal vertical bar.
    divider_changes = []
    windows = config["window_dividers"]
    for rule in windows["rules"]:
        for level in rule["levels"]:
            name = f"south-{level}-{rule['column']}-frames"
            obj = bpy.data.objects[name]
            assert len(obj.data.vertices) == 48
            old = [v.co.copy() for v in obj.data.vertices]
            lo, hi = min(v.x for v in old), max(v.x for v in old)
            current = sum(v.x for v in old[32:40])/8
            target = lo+(hi-lo)*rule["divider_fraction_from_world_min_x"]
            for vertex in obj.data.vertices[32:40]:
                vertex.co.x += target-current
            assert all(obj.data.vertices[i].co == old[i] for i in [*range(32), *range(40,48)])
            obj["source"] = windows["source"]
            obj["basis"] = windows["basis"]
            obj["divider_status"] = windows["status"]
            obj["divider_fraction_from_min_x"] = rule["divider_fraction_from_world_min_x"]
            changed_expected.add(name)
            divider_changes.append(name)

    after = inventory()
    changed = sorted(name for name in before.keys() & after.keys() if before[name] != after[name])
    removed = sorted(before.keys()-after.keys())
    added = sorted(after.keys()-before.keys())
    assert not (set(changed) | set(removed))-changed_expected
    assert all(name.startswith(("roof-parapet-", "R5 source terrace band / ")) for name in added)
    unaffected = {name: value for name, value in before.items() if name not in changed_expected}
    assert all(after.get(name) == value for name, value in unaffected.items())
    report = {"before_meshes": len(before), "after_meshes": len(after),
              "before_inventory_sha256": digest(before), "after_inventory_sha256": digest(after),
              "unchanged_meshes": len(unaffected), "unchanged_inventory_sha256": digest(unaffected),
              "changed_meshes": changed, "removed_meshes": removed, "added_meshes": added,
              "split_wall_headers": wall_changes, "window_dividers": divider_changes, "new_terrace_bands": new_bands,
              "before": before, "after": after,
              "opening_panels_sills_and_other_frames_preserved": all(after[name] == value for name, value in before.items()
                                                if name not in divider_changes and name in {o.name for o in bpy.data.collections["Glazing"].objects})}
    assert report["opening_panels_sills_and_other_frames_preserved"]
    return report
