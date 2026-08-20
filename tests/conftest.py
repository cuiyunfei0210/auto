from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def studio_home(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("WALLPAPER_STUDIO_HOME", str(tmp_path))
    return tmp_path
