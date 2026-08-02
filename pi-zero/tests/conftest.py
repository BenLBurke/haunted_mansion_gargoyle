import pathlib
import sys

# ota_apply.py is a standalone script (deliberately not part of the gargoyle
# package -- see its docstring), so it needs its own sys.path entry to import.
SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
