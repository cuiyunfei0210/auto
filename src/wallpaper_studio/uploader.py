from __future__ import annotations

from collections.abc import Callable, Awaitable
from pathlib import Path

from wallpaper_studio.models import Account, AccountBatch, SiteProfile

LogFn = Callable[[str], None]


class BrowserUploader:
    """Playwright-driven login + form upload. One browser per account."""

    def __init__(self, site: SiteProfile, log: LogFn | None = None) -> None:
        self.site = site
        self.log = log or (lambda _message: None)
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def start_account(self, account: Account, proxy: str | None = None) -> None:
        from playwright.async_api import async_playwright

        await self.close()
        self.log(f"登录账号 {account.username}")
        self._playwright = await async_playwright().start()
        launch_kwargs: dict = {"headless": self.site.headless}
        if proxy:
            launch_kwargs["proxy"] = {"server": proxy}
            self.log(f"当前代理：{proxy}")
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.site.navigation_timeout_ms)
        await self._page.goto(self.site.login_url, wait_until="domcontentloaded")
        await self._page.fill(self.site.username_selector, account.username)
        await self._page.fill(self.site.password_selector, account.password)
        await self._page.click(self.site.login_button_selector)
        await self._page.wait_for_load_state("domcontentloaded")
        error = self._page.locator(".error")
        if await error.count():
            raise RuntimeError(f"登录失败：{await error.first.inner_text()}")
        if "login" in (self._page.url or "").lower():
            await self._page.wait_for_timeout(800)
        self.log(f"账号 {account.username} 登录完成")

    async def upload_image(self, image: Path, title: str, category: str) -> None:
        if self._page is None:
            raise RuntimeError("uploader has not started an account")
        page = self._page
        await page.goto(self.site.upload_url, wait_until="domcontentloaded")
        await page.set_input_files(self.site.file_input_selector, str(image))
        if self.site.title_selector:
            await page.fill(self.site.title_selector, title)
        if self.site.category_selector and category:
            locator = page.locator(self.site.category_selector)
            tag = (await locator.evaluate("el => el.tagName.toLowerCase()"))
            if tag == "select":
                try:
                    await locator.select_option(label=category)
                except Exception:
                    await locator.select_option(value=category)
            else:
                await locator.fill(category)
        await page.click(self.site.submit_selector)
        if self.site.success_text:
            await page.get_by_text(self.site.success_text, exact=False).first.wait_for(
                timeout=self.site.navigation_timeout_ms
            )
        self.log(f"已上传 {image.name}（标题：{title}）")

    async def close(self) -> None:
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None


async def upload_batches(
    batches: list[AccountBatch],
    site: SiteProfile,
    log: LogFn | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    uploader: BrowserUploader | None = None,
) -> int:
    """Upload sequentially: finish every image for one account, then switch."""
    import asyncio

    emit = log or (lambda _message: None)
    sleeper = sleep or asyncio.sleep
    client = uploader or BrowserUploader(site, emit)
    uploaded = 0
    try:
        for batch_index, batch in enumerate(batches, start=1):
            emit(
                f"开始账号 {batch.account.username}（{batch_index}/{len(batches)}），"
                f"本账号 {len(batch.images)} 张"
            )
            await client.start_account(batch.account, batch.proxy)
            for image_index, image in enumerate(batch.images, start=1):
                title = image.stem
                await client.upload_image(image, title, site.category_value)
                uploaded += 1
                if image_index < len(batch.images) and batch.account.interval_seconds > 0:
                    emit(f"等待 {batch.account.interval_seconds:.0f} 秒后上传下一张")
                    await sleeper(batch.account.interval_seconds)
            emit(f"账号 {batch.account.username} 已完成，切换下一个账号")
            await client.close()
    finally:
        await client.close()
    return uploaded
