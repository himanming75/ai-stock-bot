import warnings
from .registry import COMPATIBILITY_COMPONENTS,canonical_component
def resolve_legacy_component(name):
    if name not in COMPATIBILITY_COMPONENTS: raise KeyError(name)
    m=COMPATIBILITY_COMPONENTS[name]; warnings.warn(f"{name} is compatibility-only",DeprecationWarning,stacklevel=2); return canonical_component(m["canonical_role"])
