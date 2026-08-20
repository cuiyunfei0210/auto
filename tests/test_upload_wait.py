from pathlib import Path

import pytest

from wallpaper_studio.models import SiteProfile
from wallpaper_studio.uploader import _is_failure_text, _wait_file_accepted


def test_failure_text_detects_upload_errors():
    assert _is_failure_text("Upload failed")
    assert _is_failure_text("Please agree to the Creator Certification Agreement")
    assert not _is_failure_text("Uploaded")


async def test_file_wait_uses_hidden_image_field_not_legal_copy(tmp_path: Path):
    pytest.importorskip("playwright")
    try:
        from playwright.async_api import async_playwright
    except Exception:
        pytest.skip("playwright is not available")

    page_path = tmp_path / "cqwall.html"
    page_path.write_text(
        """<!doctype html>
<html><body>
  <div id="layer-cca" style="display:none">
    <p>Uploaded and published voluntarily by registered creators and platform users;</p>
  </div>
  <input id="wallImage" value="">
  <script>
    setTimeout(function () {
      document.getElementById('wallImage').value = '/uploads/wallpaper/demo.png';
    }, 150);
  </script>
</body></html>
""",
        encoding="utf-8",
    )

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=True)
        except Exception:
            pytest.skip("chromium is not installed; run playwright install chromium")
        page = await browser.new_page()
        await page.goto(page_path.resolve().as_uri())
        site = SiteProfile(file_uploaded_text="Uploaded", navigation_timeout_ms=4000)
        await _wait_file_accepted(page, site)
        await browser.close()
