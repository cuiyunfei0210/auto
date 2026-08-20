from __future__ import annotations

from collections.abc import Callable, Awaitable
from pathlib import Path

from wallpaper_studio.browser import (
    browser_context_options,
    chromium_launch_attempts,
    click_even_if_offscreen,
    configure_playwright_env,
)
from wallpaper_studio.models import Account, AccountBatch, SiteProfile
from wallpaper_studio.sites import map_category

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
        configure_playwright_env()
        self._playwright = await async_playwright().start()
        if proxy:
            self.log(f"当前代理：{proxy}")
        launch_error: Exception | None = None
        for launch_kwargs in chromium_launch_attempts(self.site.headless, proxy):
            channel = launch_kwargs.get("channel")
            try:
                self._browser = await self._playwright.chromium.launch(**launch_kwargs)
                if channel:
                    self.log(f"未找到内置 Chromium，已改用系统浏览器（{channel}）")
                launch_error = None
                break
            except Exception as exc:  # noqa: BLE001 - try Edge/Chrome before failing
                launch_error = exc
                continue
        if self._browser is None:
            raise RuntimeError(
                "找不到上传用的浏览器。"
                "请重新下载解压完整的 WallpaperStudio 文件夹，或在这台电脑安装 Microsoft Edge / Google Chrome。"
                f" 原始错误：{launch_error}"
            ) from launch_error
        self._context = await self._browser.new_context(**browser_context_options())
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.site.navigation_timeout_ms)
        self.log("正在打开登录页…")
        await self._page.goto(self.site.login_url, wait_until="domcontentloaded")
        if self.site.open_login_selector:
            self.log("正在打开登录窗口…")
            await click_even_if_offscreen(
                self._page.locator(self.site.open_login_selector).first,
                self.site.navigation_timeout_ms,
            )
            await self._page.locator(self.site.username_selector).first.wait_for(state="visible")
        await self._page.locator(self.site.username_selector).first.fill(account.username)
        await self._page.locator(self.site.password_selector).first.fill(account.password)
        await click_even_if_offscreen(
            self._page.locator(self.site.login_button_selector).first,
            self.site.navigation_timeout_ms,
        )
        if self.site.login_success_text:
            await self._page.get_by_text(self.site.login_success_text, exact=False).first.wait_for()
        else:
            await self._page.wait_for_load_state("domcontentloaded")
            error = self._page.locator(".error")
            if await error.count():
                raise RuntimeError(f"登录失败：{await error.first.inner_text()}")
        if self.site.logged_in_selector:
            await self._page.locator(self.site.logged_in_selector).first.wait_for()
        self.log(f"账号 {account.username} 登录完成")

    async def upload_image(self, image: Path, title: str, category: str) -> None:
        if self._page is None:
            raise RuntimeError("uploader has not started an account")
        page = self._page
        await page.goto(self.site.upload_url, wait_until="domcontentloaded")
        if self.site.open_upload_selector:
            await click_even_if_offscreen(
                page.locator(self.site.open_upload_selector).first,
                self.site.navigation_timeout_ms,
            )
            if self.site.title_selector:
                await page.locator(self.site.title_selector).first.wait_for(state="visible")
        await page.locator(self.site.file_input_selector).first.set_input_files(str(image))
        if self.site.file_uploaded_text:
            await page.get_by_text(self.site.file_uploaded_text, exact=False).first.wait_for()
        if self.site.title_selector:
            await page.locator(self.site.title_selector).first.fill(title)
        raw_category = category or self.site.category_value
        mapped = map_category(raw_category)
        choices = [item for item in (raw_category, mapped) if item]
        if self.site.category_selector and choices:
            locator = page.locator(self.site.category_selector).first
            tag = await locator.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                selected = False
                for item in dict.fromkeys(choices):
                    try:
                        await locator.select_option(value=item, timeout=2000)
                        selected = True
                        break
                    except Exception:
                        try:
                            await locator.select_option(label=item, timeout=2000)
                            selected = True
                            break
                        except Exception:
                            continue
                if not selected:
                    raise RuntimeError(f"无法选择分类：{raw_category}")
            else:
                await locator.fill(mapped or raw_category)
        if self.site.agree_selector:
            await _check_agreements(page, self.site.agree_selector)
        await click_even_if_offscreen(
            page.locator(self.site.submit_selector).first,
            self.site.navigation_timeout_ms,
        )
        await _wait_upload_result(page, self.site)
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


async def _check_agreements(page, selector: str) -> None:
    locators = page.locator('input[name="remember"]')
    count = await locators.count()
    for index in range(count):
        box = locators.nth(index)
        try:
            await box.check(force=True)
        except Exception:
            continue
    target = page.locator(selector).first
    try:
        await target.check(force=True)
    except Exception:
        nearby = page.locator("#layer-upload .layui-form-checkbox").first
        if await nearby.count():
            await nearby.click()


async def _wait_upload_result(page, site: SiteProfile) -> None:
    if site.success_text:
        await page.get_by_text(site.success_text, exact=False).first.wait_for(
            timeout=site.navigation_timeout_ms
        )
        return
    msg = page.locator(".layui-layer-msg, .layui-layer-dialog").last
    try:
        await msg.wait_for(timeout=site.navigation_timeout_ms)
        text = (await msg.inner_text()).strip()
    except Exception:
        return
    lowered = text.lower()
    if any(token in lowered for token in ["fail", "error", "please", "失败", "错误"]):
        raise RuntimeError(f"上传未成功：{text}")


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
