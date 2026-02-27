from pathlib import Path
import tomllib

# Read version from pyproject.toml
_pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
with open(_pyproject_path, "rb") as f:
    _pyproject_data = tomllib.load(f)
    __version__: str = _pyproject_data["project"]["version"]
