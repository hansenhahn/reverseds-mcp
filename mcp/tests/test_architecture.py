"""Architecture unit tests: enforce the layering contracts (via import-linter)."""
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def test_architecture_contracts() -> None:
    """The import-linter contracts in `pyproject.toml` must all be kept."""
    lint_imports = Path(sys.executable).with_name("lint-imports")
    result = subprocess.run(
        [str(lint_imports)],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
