"""Sites and products: the generic layout every construction project follows.

    projects/<site>/project.yaml                  site metadata (name, address, building type, ...)
    projects/<site>/specs/*.yaml                  spec-driven models (detail | house | room | element)
    projects/<site>/products/<name>/product.yaml  bespoke pipelines (film, viewer, report) and their steps
    projects/<site>/deliverables/<name>/          what gets handed over

No bpy here, so discovery works on machines and CI jobs without Blender.
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from bmodels.paths import BUILD, PROJECTS, ROOT

LEGACY_SPECS = ROOT / "specs"  # pre-site layout; still built until every spec lives under a site


@dataclass
class Product:
    site: "Site"
    name: str
    dir: Path
    meta: dict = field(default_factory=dict)

    @property
    def ref(self):
        return f"{self.site.name}/{self.name}"

    @property
    def deliverable_dirs(self):
        """Declared in product.yaml (`deliverables:` path or list, relative to the product); default deliverables/<name>."""
        d = self.meta.get("deliverables")
        if not d:
            return [self.site.dir / "deliverables" / self.name]
        return [(self.dir / x).resolve() for x in ([d] if isinstance(d, str) else d)]

    @property
    def deliverables(self):
        return self.deliverable_dirs[0]

    @property
    def build(self):
        return BUILD / self.site.name / self.name


@dataclass
class Site:
    name: str
    dir: Path
    meta: dict = field(default_factory=dict)

    @property
    def specs(self):
        return sorted((self.dir / "specs").glob("*.yaml"))

    @property
    def products(self):
        found = sorted(p.parent for p in (self.dir / "products").glob("*/product.yaml"))
        return [Product(self, d.name, d, _yaml(d / "product.yaml")) for d in found]

    @property
    def build(self):
        return BUILD / self.name


def _yaml(path):
    return yaml.safe_load(Path(path).read_text()) or {}


def sites():
    return [Site(p.parent.name, p.parent, _yaml(p)) for p in sorted(PROJECTS.glob("*/project.yaml"))]


def site(name):
    for s in sites():
        if s.name == name:
            return s
    raise SystemExit(f"No site '{name}' (projects/{name}/project.yaml). Sites: {', '.join(s.name for s in sites()) or 'none'}")


def product(ref):
    site_name, _, name = ref.partition("/")
    for p in site(site_name).products:
        if p.name == name:
            return p
    raise SystemExit(f"No product '{ref}'. Products: {', '.join(p.ref for p in site(site_name).products) or 'none'}")


def legacy_specs():
    return sorted(LEGACY_SPECS.glob("*.yaml"))


def all_specs():
    return [sp for s in sites() for sp in s.specs] + legacy_specs()


def site_of(spec_path):
    """The site a spec belongs to, or None for a legacy specs/ file."""
    spec_path = Path(spec_path).resolve()
    for s in sites():
        if spec_path.is_relative_to(s.dir.resolve()):
            return s
    return None


def build_dir(spec_path):
    """Where a spec's outputs go: build/<site>/<spec>/ (legacy specs keep build/<spec>/)."""
    s = site_of(spec_path)
    return (s.build if s else BUILD)


def resolve_specs(targets):
    """Spec files from paths, 'site', or 'site/spec-stem' targets. No targets = every spec."""
    if not targets:
        return all_specs()
    out = []
    for t in targets:
        p = Path(t)
        if p.suffix in (".yaml", ".yml") and p.exists():
            out.append(p)
            continue
        site_name, _, stem = t.partition("/")
        specs = site(site_name).specs
        picked = [sp for sp in specs if not stem or sp.stem == stem]
        if not picked:
            raise SystemExit(f"No spec '{stem}' in {site_name}. Specs: {', '.join(sp.stem for sp in specs) or 'none'}")
        out += picked
    return out
