"""
Shared path resolver for the myfpl_predictor project.

Actual layout:

myfpl_predictor/
├── data/
├── img/
├── models/
├── python/                          
└── Fantasy-Premier-League-master/  

Import this from any script or notebook inside python/ instead of
hardcoding an absolute BASE path.
"""
from pathlib import Path


def find_project_root(marker: str = "data", start: Path | None = None) -> Path:
    """Walk upward from `start` (or cwd) until a folder containing `marker` is found."""
    here = Path(start).resolve() if start else Path.cwd().resolve()
    for folder in [here, *here.parents]:
        if (folder / marker).is_dir():
            return folder
    raise FileNotFoundError(
        f"Could not locate project root -- no '{marker}/' folder found above {here}."
    )


# --- Locate BASE ---
try:
    # Running as a .py script: resolve relative to this file's own folder.
    _here = Path(__file__).resolve().parent
except NameError:
    # Running inside a notebook: __file__ doesn't exist, fall back to cwd.
    _here = None

BASE     = find_project_root(start=_here)
DATA     = BASE / "data"
MODELS   = BASE / "models"
IMG      = BASE / "img"
PYTHON   = BASE / "python"
FPL_REPO = BASE / "Fantasy-Premier-League-master"

if __name__ == "__main__":
    print("Project root :", BASE)
    print("Data folder  :", DATA)
    print("Models folder:", MODELS)
    print("Python folder:", PYTHON)
    print("FPL repo     :", FPL_REPO, "(exists:", FPL_REPO.is_dir(), ")")