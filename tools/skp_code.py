"""Emit SketchUp-connector Python for a detail spec pair (existing + proposed) — scenes toggle them.

The SketchUp connector (Trimble MCP) is only reachable from a Claude chat session, not from CI,
so this script prints the code Claude passes to `build_model`; Claude then adds scenes/camera and
calls `save_model`. Geometry matches tools/detail.py: rect profiles in the section plane (X, Z),
swept along Y with rise = pitch/12 (sheared, plumb faces stay plumb). Parts identical in both
specs go on the "Shared" layer; the rest on "Existing" / "Proposed". Proposed parts are colored
by scope label prefix: NEW / REQ'D / REC.

  python tools/skp_code.py specs/field-parapet-existing.yaml specs/field-parapet-proposed.yaml > build/skp_code.py
"""
import json, sys
import yaml

MAT = {"osb": (184, 148, 97), "membrane": (38, 38, 41), "shingles": (80, 80, 84), "df_lumber": (196, 160, 110),
       "wrb": (237, 237, 242), "siding": (170, 168, 155), "flashing": (90, 84, 78), "pt_lumber": (150, 130, 90),
       "trim": (230, 227, 217), "rigid": (140, 179, 217), "gable_panel": (140, 145, 133)}
SCOPE = {"NEW": (237, 107, 26), "REQ'D": (242, 199, 51), "REC": (64, 133, 224)}

BODY = r'''
L = DATA["L"]; s = DATA["slope"]; step = DATA["step"]
def prism(x0, z0, x1, z1, y0, y1):
    g = GeometryInput()
    P = lambda x, y, z: SUPoint3D(x, y, z + s * y)
    g.set_vertices([P(x0,y0,z0), P(x1,y0,z0), P(x1,y1,z0), P(x0,y1,z0),
                    P(x0,y0,z1), P(x1,y0,z1), P(x1,y1,z1), P(x0,y1,z1)])
    for fv in [[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7],[4,5,6,7],[0,3,2,1]]:
        lp = LoopInput()
        for i in fv: lp.add_vertex_index(i)
        _, g = g.add_face(lp)
    return g
def get_or_create_material(name, r, g, b, a=255):
    existing = {m.get_name(): m for m in model.get_materials()}
    if name in existing: return existing[name]
    m = Material(); m.set_name(name); m.set_color(SUColor(r, g, b, a)); model.add_materials([m]); return m
def paint(ents, mat):
    for f in ents.get_faces():
        f.set_front_material(mat); f.set_back_material(mat)
layers = {}
for nm in ["Shared", "Existing", "Proposed"]:
    ly = Layer(); ly.set_name(nm); layers[nm] = ly
model.add_layers(list(layers.values()))
root = Group(); model.get_entities().add_group(root); root.set_name(DATA["name"])
counts = {}
for it in DATA["items"]:
    x0, z0, x1, z1 = it["rect"]
    Lc = L - step * it["peel"]
    mat = get_or_create_material("c_%d_%d_%d" % tuple(it["color"]), *it["color"])
    tag = {"confirmed": "", "provisional": " [P]", "assumed": " [A]"}.get(it["status"], "")
    name = (it["id"] + " | " + it["label"] + tag)[:120]
    if it["repeat"]:
        w = it["repeat"]["width_in"]; sp = it["repeat"]["spacing_in"]; t = it["repeat"].get("start_in", 0)
        cd = ComponentDefinition(); cd.set_name(it["id"]); model.add_component_definitions([cd])
        cd.get_entities().fill(prism(x0, z0, x1, z1, 0, w), weld_vertices=True); paint(cd.get_entities(), mat)
        holder = Group(); root.get_entities().add_group(holder); holder.set_name(name); holder.set_layer(layers[it["layer"]])
        n = 0
        while t + w <= Lc + 1e-6:
            inst = cd.create_instance(); inst.set_name("%s_%03d" % (it["id"], n + 1))
            inst.set_transform(SUTransformation([1,0,0,0, 0,1,0,0, 0,0,1,0, 0, t, s * t, 1]))
            holder.get_entities().add_instance(inst); t += sp; n += 1
        counts[it["id"]] = n
    else:
        g = Group(); root.get_entities().add_group(g); g.set_name(name); g.set_layer(layers[it["layer"]])
        g.get_entities().fill(prism(x0, z0, x1, z1, 0, Lc), weld_vertices=True); paint(g.get_entities(), mat)
        counts[it["id"]] = 1
bad = []
for g in root.get_entities().get_groups():
    if g.get_entities().get_instances(): continue
    if g.compute_volume() is None: bad.append(g.get_name())
result = {"parts": len(DATA["items"]), "instances": counts, "non_solid": bad}
'''


def main(ex_path, pr_path):
    ex = yaml.safe_load(open(ex_path))["elements"][0]
    pr = yaml.safe_load(open(pr_path))["elements"][0]
    key = lambda c: (c["id"], tuple(c["rect"]), json.dumps(c.get("repeat")))
    exk = {key(c) for c in ex["components"]}; prk = {key(c) for c in pr["components"]}
    items = []
    def add(c, layer, color):
        items.append(dict(id=c["id"], label=c.get("label", c["id"]), status=c["status"], layer=layer,
                          rect=c["rect"], repeat=c.get("repeat"), color=list(color), peel=c.get("peel", 0)))
    for c in ex["components"]:
        add(c, "Shared" if key(c) in prk else "Existing", MAT.get(c.get("material"), (200, 200, 200)))
    for c in pr["components"]:
        if key(c) in exk:
            continue
        lab = c.get("label", "")
        col = next((v for k, v in SCOPE.items() if lab.startswith(k)), MAT.get(c.get("material"), (200, 200, 200)))
        add(c, "Proposed", col)
    data = dict(name=ex["id"].replace("_existing", ""), L=ex["path"]["length_in"],
                slope=ex["path"].get("pitch", 0) / 12.0, step=ex.get("cutaway_step_in", 0), items=items)
    print("DATA = " + repr(data) + "\n" + BODY)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
