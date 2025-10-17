from __future__ import annotations

from pathlib import Path
import zipfile

import pytest


@pytest.fixture
def make_skill_zip(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]

    def _make(example_name: str) -> Path:
        src = project_root / "examples" / example_name
        if not src.exists():
            raise FileNotFoundError(f"example {example_name} not found")
        archive = tmp_path / f"{example_name}.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            for file_path in src.rglob("*"):
                if file_path.is_file():
                    arcname = Path(example_name) / file_path.relative_to(src)
                    zf.write(file_path, arcname.as_posix())
        return archive

    return _make
