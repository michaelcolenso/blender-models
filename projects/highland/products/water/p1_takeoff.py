def refine(roots, calibration, registration, pipe, element, label):
    source = calibration["p1"]["source"]
    architecture_source = calibration["p1"]["architecture_source"]

    def point(sheet, x, y, z=0):
        transform = registration[sheet]
        return [
            round(x * transform["x"]["in_per_working_px"] + transform["x"]["offset_in"], 5),
            round(y * transform["y"]["in_per_working_px"] + transform["y"]["offset_in"], 5),
            z,
        ]

    def p(x, y, system):
        return point("plumbing", x, y, calibration["p1"]["overhead_pipe_in"][system])

    mains = {
        "CW": [(2740, 2428), (3890, 2428), (3890, 2578), (4110, 2578)],
        "HW": [(2740, 2440), (3902, 2440), (3902, 2590), (4110, 2590)],
        "HWC": [(2740, 2452), (3914, 2452), (3914, 2602), (4110, 2602)],
    }
    sizes = {"CW": 1.25, "HW": 1.0, "HWC": 0.5}
    for system, coordinates in mains.items():
        points = [p(x, y, system) for x, y in coordinates]
        roots[f"p1:{system}"] = points[0]
        pipe(
            f"p1-south-corridor-{system}", "p1", system, points, sizes[system], source,
            role="west continuation and south corridor main",
        )
        branch = [points[-1], p(4110, 2720, system)]
        pipe(
            f"p1-unit-107-approach-{system}", "p1", system, branch, sizes[system], source,
            terminal=True, role="Unit 107 service approach; internal routing governed by P4.01",
        )

    for axis, names in (("x", ["6", "7", "8", "9", "10"]), ("y", ["E", "F", "G", "H"])):
        grid = registration["architecture"][axis]
        for name, pixel in zip(grid["names"], grid["working_px"]):
            if axis == "x":
                a = point("architecture", pixel, 450)
                b = point("architecture", pixel, 3700)
                at = point("architecture", pixel, 400)
            else:
                a = point("architecture", 2750, pixel)
                b = point("architecture", 5150, pixel)
                at = point("architecture", 5200, pixel)
            element(
                f"p1-grid-{name}", "p1", "pipe", system="context", points=[a, b],
                nominal_in=0.5, size_status="assumed", size_basis="Grid reference line",
                source=architecture_source,
            )
            label(f"p1-grid-label-{name}", "p1", at, name, 12)

    label("p1-scope", "p1", point("architecture", 2900, 3650), "P1 SOUTH CORRIDOR / UNIT 107 APPROACH", 16)
    label("p1-unit-107", "p1", p(4110, 2770, "CW"), "UNIT 107 / P4.01 CONTINUES", 10)
