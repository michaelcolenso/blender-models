#!/usr/bin/env python3
"""Normal-Python preflight. Does not require Blender."""
from __future__ import annotations
import ast, csv, hashlib, json, py_compile, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/"scripts"/"build_meydenbauer_b101_v4.py"
REPORT=ROOT/"output"/"preflight_report.json"

REQUIRED=[
    BUILD,
    ROOT/"scripts"/"run_build_and_verify.py",
    ROOT/"scripts"/"verify_saved_blend.py",
    ROOT/"data"/"b101_route_controls_calibrated_v2.csv",
    ROOT/"data"/"B101_demolition_fitting_schedule_v4.csv",
    ROOT/"qa"/"B101_fitting_cut_QA_overlay_v4.png",
    ROOT/"qa"/"B101_demolition_plan_overlay_v3.png",
    ROOT/"sources"/"modeling_brief.txt",
]
EXPECTED_FUNCS={"run_pass1","run_pass2","run_pass3","validate_model","build_b101_demolition_model","build_b101_demolition_fittings"}


def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def csv_rows(p):
    with p.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    issues=[]
    for p in REQUIRED:
        if not p.exists() or p.stat().st_size==0:
            issues.append(f"missing_or_empty: {p.relative_to(ROOT)}")

    compile_targets=[BUILD,ROOT/"scripts"/"run_build_and_verify.py",ROOT/"scripts"/"verify_saved_blend.py"]
    for p in compile_targets:
        try: py_compile.compile(str(p),doraise=True)
        except Exception as e: issues.append(f"py_compile_failed {p.name}: {e}")

    funcs=set()
    try:
        tree=ast.parse(BUILD.read_text(encoding="utf-8"))
        funcs={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        missing=sorted(EXPECTED_FUNCS-funcs)
        if missing: issues.append("missing_expected_functions: "+", ".join(missing))
    except Exception as e:
        issues.append(f"ast_parse_failed: {e}")

    route_rows=csv_rows(ROOT/"data"/"b101_route_controls_calibrated_v2.csv")
    fitting_rows=csv_rows(ROOT/"data"/"B101_demolition_fitting_schedule_v4.csv")
    if len(route_rows)<20: issues.append(f"route_control_row_count_suspicious: {len(route_rows)}")
    if len(fitting_rows)<30: issues.append(f"fitting_schedule_row_count_suspicious: {len(fitting_rows)}")

    files={}
    for p in sorted(x for x in ROOT.rglob("*") if x.is_file() and x.name not in {"MANIFEST.sha256","preflight_report.json"}):
        files[str(p.relative_to(ROOT))]={"size":p.stat().st_size,"sha256":sha256(p)}

    report={
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "python_version":sys.version,
        "issues":issues,
        "passed":not issues,
        "route_control_rows":len(route_rows),
        "fitting_schedule_rows":len(fitting_rows),
        "expected_functions_present":sorted(EXPECTED_FUNCS & funcs),
        "files":files,
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="files"},indent=2))
    print(f"PREFLIGHT_REPORT={REPORT}")
    return 0 if not issues else 1

if __name__=="__main__":
    raise SystemExit(main())
