from __future__ import annotations

from collections.abc import Callable, Awaitable
from pathlib import Path

from wallpaper_studio.browser import (
    browser_context_options,
    chromium_launch_attempts,
    click_even_if_offscreen,
    configure_playwright_env,
)
from wallpaper_studio.control import JobStopped
from wallpaper_studio.models import Account, AccountBatch, SiteProfile
from wallpaper_studio.sites import category_choices, map_category

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
                    self.log(f"使用系统浏览器上传（{channel}）")
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
            await self._page.get_by_text(self.site.login_success_text, exact=True).first.wait_for()
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
        file_locator = page.locator(self.site.file_input_selector)
        if await file_locator.count() == 0:
            file_locator = page.locator(
                "#ID-upload-demo-drag input[type=file], input.layui-upload-file"
            )
        await file_locator.first.set_input_files(str(image))
        self.log(f"正在把图片传到网站：{image.name}")
        await _wait_file_accepted(page, self.site)
        if self.site.title_selector:
            await page.locator(self.site.title_selector).first.fill(title)
        raw_category = category or self.site.category_value
        if self.site.category_selector and (raw_category or "").strip():
            await _select_category(page, self.site, raw_category)
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


async def _select_category(page, site: SiteProfile, raw_category: str) -> None:
    choices = category_choices(raw_category)
    locator = page.locator(site.category_selector).first
    try:
        await locator.wait_for(state="attached", timeout=min(8000, site.navigation_timeout_ms))
    except Exception as exc:
        raise RuntimeError(f"找不到分类下拉框：{site.category_selector}") from exc
    tag = await locator.evaluate("el => el.tagName.toLowerCase()")
    if tag != "select":
        await locator.fill(map_category(raw_category) or raw_category)
        return
    try:
        await locator.locator("option").nth(1).wait_for(state="attached", timeout=5000)
    except Exception:
        pass
    for item in choices:
        try:
            await locator.select_option(value=item, timeout=1500, force=True)
            return
        except Exception:
            pass
        try:
            await locator.select_option(label=item, timeout=1500, force=True)
            return
        except Exception:
            continue
    for item in choices:
        changed = await locator.evaluate(
            """(el, value) => {
                const option = [...el.options].find((row) =>
                    row.value === value || (row.textContent || "").trim() === value
                );
                if (!option) return false;
                el.value = option.value;
                el.dispatchEvent(new Event("change", { bubbles: true }));
                el.dispatchEvent(new Event("input", { bubbles: true }));
                return true;
            }""",
            item,
        )
        if changed:
            dd = page.locator(f'#layer-upload dd[lay-value="{item}"]').first
            if await dd.count():
                try:
                    await click_even_if_offscreen(dd, 3000)
                except Exception:
                    pass
            return
    title = page.locator("#layer-upload .layui-form-select .layui-select-title").first
    if await title.count():
        await click_even_if_offscreen(title, 5000)
        for item in choices:
            dd = page.locator(f'#layer-upload .layui-form-select dd[lay-value="{item}"]').first
            if await dd.count():
                await click_even_if_offscreen(dd, 3000)
                return
            by_text = page.locator("#layer-upload .layui-form-select dd", has_text=item).first
            if await by_text.count():
                await click_even_if_offscreen(by_text, 3000)
                return
    available = await locator.evaluate(
        """el => [...el.options].map((row) => ((row.textContent || "").trim() + "/" + row.value)).filter(Boolean).join("，")"""
    )
    raise RuntimeError(
        f"无法选择分类：{raw_category}。"
        f"网站当前选项：{available or '空的'}。"
        "CQwall 的分类是 Layui 下拉框，请到「网页上传」把默认分类改成「风景」或对应中文名后再试。"
    )


async def _visible_layer_messages(page) -> list[str]:
    return await page.evaluate(
        """() => Array.from(document.querySelectorAll('.layui-layer-msg, .layui-layer-dialog'))
            .filter((el) => {
                const st = getComputedStyle(el);
                if (st.display === 'none' || st.visibility === 'hidden') return false;
                const box = el.getBoundingClientRect();
                return box.width > 0 && box.height > 0;
            })
            .map((el) => (el.innerText || '').trim())
            .filter(Boolean)"""
    )


def _is_failure_text(text: str) -> bool:
    lowered = (text or "").lower()
    return any(token in lowered for token in ["fail", "error", "please", "失败", "错误"])


async def _wait_file_accepted(page, site: SiteProfile) -> None:
    """Wait until the wallpaper file actually reached the site.

    CQwall's legal copy contains a hidden paragraph starting with "Uploaded",
    so a substring text wait never becomes visible. Prefer the hidden image
    path field, and only treat an exact visible toast as success.
    """
    timeout = site.navigation_timeout_ms
    expected = (site.file_uploaded_text or "").strip()
    has_image_field = await page.locator("#wallImage").count()
    if not has_image_field and not expected:
        return
    try:
        result = await page.wait_for_function(
            """expected => {
                const value = document.querySelector('#wallImage')?.value;
                if (value) return {ok: true};
                const nodes = Array.from(document.querySelectorAll(
                    '.layui-layer-msg, .layui-layer-dialog'
                ));
                const visible = nodes.filter((el) => {
                    const st = getComputedStyle(el);
                    if (st.display === 'none' || st.visibility === 'hidden') return false;
                    const box = el.getBoundingClientRect();
                    return box.width > 0 && box.height > 0;
                });
                const textOf = (el) => (el.innerText || '').trim();
                const fail = visible.find((el) => /fail|error|失败|错误/i.test(textOf(el)));
                if (fail) return {ok: false, error: textOf(fail)};
                if (expected && visible.some((el) => textOf(el) === expected)) {
                    return {ok: true};
                }
                return false;
            }""",
            arg=expected,
            timeout=timeout,
        )
    except Exception as exc:
        messages = await _visible_layer_messages(page)
        fail = next((item for item in messages if _is_failure_text(item)), None)
        if fail:
            raise RuntimeError(f"图片未上传成功：{fail}") from exc
        raise RuntimeError(
            "图片没有传到网站。CQwall 要求不少于 1920×1080，且必须在创作者中心上传。"
            f" 原始错误：{exc}"
        ) from exc
    payload = await result.json_value()
    if isinstance(payload, dict) and payload.get("ok") is False:
        raise RuntimeError(f"图片未上传成功：{payload.get('error') or 'Upload failed'}")


async def _wait_upload_result(page, site: SiteProfile) -> None:
    if site.success_text:
        await page.get_by_text(site.success_text, exact=True).first.wait_for(
            state="visible",
            timeout=site.navigation_timeout_ms,
        )
        return
    try:
        await page.locator(".layui-layer-msg, .layui-layer-dialog").last.wait_for(
            state="visible",
            timeout=site.navigation_timeout_ms,
        )
    except Exception:
        return
    messages = await _visible_layer_messages(page)
    text = messages[-1] if messages else ""
    if _is_failure_text(text):
        raise RuntimeError(f"上传未成功：{text}")


def _upload_error_text(exc: BaseException) -> str:
    text = str(exc).strip().replace("原始错误：:", "原始错误：")
    return text or "未知错误"


async def upload_batches(
    batches: list[AccountBatch],
    site: SiteProfile,
    log: LogFn | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    uploader: BrowserUploader | None = None,
    stop_check: Callable[[], bool] | None = None,
) -> tuple[int, int]:
    """Upload sequentially: finish every image for one account, then switch.

    One image failing no longer stops the rest of the queue.
    """
    import asyncio

    emit = log or (lambda _message: None)
    sleeper = sleep or asyncio.sleep
    client = uploader or BrowserUploader(site, emit)
    uploaded = 0
    skipped = 0

    def cancelled() -> bool:
        return bool(stop_check and stop_check())

    try:
        for batch_index, batch in enumerate(batches, start=1):
            if cancelled():
                raise JobStopped("已手动停止")
            emit(
                f"开始账号 {batch.account.username}（{batch_index}/{len(batches)}），"
                f"本账号 {len(batch.images)} 张"
            )
            await client.start_account(batch.account, batch.proxy)
            for image_index, item in enumerate(batch.images, start=1):
                if cancelled():
                    raise JobStopped("已手动停止")
                title = item.title
                try:
                    await client.upload_image(item.path, title, item.category or site.category_value)
                    uploaded += 1
                except asyncio.CancelledError:
                    raise
                except JobStopped:
                    raise
                except Exception as exc:  # noqa: BLE001 - skip this file and keep the queue moving
                    skipped += 1
                    emit(f"跳过 {item.path.name}：{_upload_error_text(exc)}")
                    emit("已跳过，继续下一张")
                if image_index < len(batch.images) and batch.account.interval_seconds > 0:
                    if cancelled():
                        raise JobStopped("已手动停止")
                    emit(f"等待 {batch.account.interval_seconds:.0f} 秒后上传下一张")
                    await sleeper(batch.account.interval_seconds)
            emit(f"账号 {batch.account.username} 已完成，切换下一个账号")
            await client.close()
    finally:
        await client.close()
    return uploaded, skipped
