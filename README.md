# blender-models

Dimensionally accurate, provenance-tagged Blender models and quantity takeoffs of occupied-multifamily restoration and defect-repair projects. Each model is built headless (bpy) from a YAML spec in which every element traces to a source or is labeled assumed. Models are coordination and estimating tools, not contract documents.

- **Rules and method:** [INSTRUCTIONS.md](INSTRUCTIONS.md)
- **Step-by-step commands, troubleshooting, build history:** [RUNBOOK.md](RUNBOOK.md)
- **Specs:** `specs/` · **Tools:** `tools/` · **CI:** `.github/workflows/build-models.yaml`

Quick check that the environment works (Python 3.11 only):

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python tools/build.py specs/_sample-bay.yaml --out build
```
