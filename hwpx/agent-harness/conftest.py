"""Root conftest — pre-import python-hwpx before pytest discovers cli_anything.hwpx."""
import importlib
import sys

# Force-load the real python-hwpx package BEFORE pytest's collection
# imports cli_anything.hwpx which would shadow it via __init__.py traversal.
if "hwpx" not in sys.modules:
    # Find the real hwpx from site-packages
    import importlib.util
    spec = importlib.util.find_spec("hwpx")
    if spec and spec.origin and "site-packages" in spec.origin:
        real_hwpx = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(real_hwpx)
        sys.modules["hwpx"] = real_hwpx
