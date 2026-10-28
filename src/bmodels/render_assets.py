"""External render assets referenced by a scene, excluding saved UI paths."""
from pathlib import Path


def scene_asset_paths(bpy, scene):
    # user_map maps an ID to its users. Invert it to walk from this scene to
    # objects, materials, node groups, images, worlds and other referenced IDs.
    dependencies = {}
    for dependency, users in bpy.data.user_map().items():
        for user in users:
            dependencies.setdefault(user, set()).add(dependency)
    pending = [scene]
    visited = set()
    paths = set()
    file_types = (bpy.types.Image, bpy.types.VectorFont, bpy.types.Sound,
                  bpy.types.MovieClip, bpy.types.Volume, bpy.types.CacheFile,
                  bpy.types.Library)
    while pending:
        item = pending.pop()
        if item in visited:
            continue
        visited.add(item)
        pending.extend(dependencies.get(item, ()))
        library = item.library
        if library:
            pending.append(library)
        if isinstance(item, bpy.types.Library) and item.parent:
            pending.append(item.parent)
        if not isinstance(item, file_types):
            continue
        path = item.filepath
        if not path or path == "<builtin>":
            continue
        if getattr(item, "packed_file", None) or getattr(item, "packed_files", None):
            continue
        if isinstance(item, bpy.types.Image) and item.source in ("GENERATED", "VIEWER"):
            continue
        # Indirect libraries and linked textures resolve relative to the
        # library that owns them, rather than the current working directory.
        owner = item.parent if isinstance(item, bpy.types.Library) else library
        paths.add(bpy.path.abspath(path, library=owner))
    return sorted(paths)


def validate_scene_assets(bpy, scene):
    paths = scene_asset_paths(bpy, scene)
    missing = [path for path in paths if not Path(path).is_file()]
    if missing:
        raise ValueError(f"Missing external scene assets (pack or restore them first): {missing}")
    return paths
