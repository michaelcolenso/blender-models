# Command Reference

## 1. Normal-Python preflight only

```bash
python3 scripts/preflight.py
```

This checks package completeness, Python syntax, expected build functions, CSV row counts, and hashes all handoff files. It does not import `bpy`.

## 2. Full strict Blender build

```bash
blender --background --factory-startup \
  --python scripts/run_build_and_verify.py -- \
  --fail-on-warning
```

## 3. Full strict build + demolition checkpoint renders

```bash
blender --background --factory-startup \
  --python scripts/run_build_and_verify.py -- \
  --fail-on-warning --render-keyframes
```

## 4. Reopen the generated scene and verify persistence

```bash
blender --background output/Meydenbauer_B101_Demolition_v4.blend \
  --python scripts/verify_saved_blend.py -- \
  --fail-on-warning
```

## 5. Build a subset of passes

For debugging only:

```bash
blender --background --factory-startup \
  --python scripts/run_build_and_verify.py -- \
  --passes 1
```

or:

```bash
blender --background --factory-startup \
  --python scripts/run_build_and_verify.py -- \
  --passes 1,2
```

The production handoff acceptance run should use `1,2,3`.

## 6. Custom render resolution

```bash
blender --background --factory-startup \
  --python scripts/run_build_and_verify.py -- \
  --render-keyframes --resolution-x 1920 --resolution-y 1080 --samples 64
```

## Useful diagnostics

```bash
blender --version
python3 --version
sha256sum -c MANIFEST.sha256   # Linux
shasum -a 256 -c MANIFEST.sha256  # macOS may vary by shasum implementation
```
