from __future__ import annotations

import shutil
import sys
import tempfile
import typing as _typing
from pathlib import Path

import pytest

# ── Compatibilidad Python 3.14 + pydantic ≤ 2.12 ──────────────────────────────────────────────
# Python 3.14.0rc2 eliminó el parámetro `prefer_fwd_module` de `typing._eval_type`.
# Pydantic lo usa; este parche acepta y descarta ese kwarg para que los modelos se creen sin error.
_original_eval_type = getattr(_typing, "_eval_type", None)
if _original_eval_type is not None:
    def _patched_eval_type(tp, globalns, localns, type_params=(), recursive_guard=frozenset(), prefer_fwd_module=None, **kwargs):  # type: ignore[misc]
        return _original_eval_type(tp, globalns, localns, type_params=type_params, recursive_guard=recursive_guard, **kwargs)
    _typing._eval_type = _patched_eval_type  # type: ignore[attr-defined]
# ───────────────────────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def workspace_tmp_path() -> Path:
    base_dir = PROJECT_ROOT / ".tmp_pytest"
    base_dir.mkdir(exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(dir=base_dir))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
