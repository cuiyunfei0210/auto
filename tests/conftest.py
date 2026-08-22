from __future__ import annotations

from pathlib import Path

import pytest

from wallpaper_studio.control import clear_stop


@pytest.fixture
def studio_home(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("WALLPAPER_STUDIO_HOME", str(tmp_path))
    clear_stop()
    from wallpaper_studio.server import state as studio_state

    studio_state.running = False
    studio_state.stopping = False
    studio_state.stopped = False
    studio_state.task = None
    studio_state.logs = []
    studio_state.last_error = None
    studio_state.last_result = None
    studio_state.remix_remaining = None
    studio_state.remix_total = None
    return tmp_path
