from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from wallpaper_studio.files import sanitize_filename, unique_path
from wallpaper_studio.storage import data_dir

demo_router = APIRouter()

DEMO_USERS = {
    "demo1": "123123",
    "demo2": "123123",
    "demo3": "123123",
}

SESSIONS: dict[str, str] = {}


def reset_demo_sessions() -> None:
    SESSIONS.clear()

LOGIN_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>示例壁纸站 · 登录</title>
  <link rel="stylesheet" href="/static/studio.css"/>
</head>
<body class="demo-body">
  <main class="demo-card">
    <p class="eyebrow">Demo Wallpaper Site</p>
    <h1>登录后上传壁纸</h1>
    <p class="muted">演示账号 demo1 / demo2 / demo3，密码都是 123123。</p>
    {error}
    <form method="post" action="/demo/login" class="stack">
      <label>账号<input id="username" name="username" autocomplete="username" required></label>
      <label>密码<input id="password" name="password" type="password" autocomplete="current-password" required></label>
      <button type="submit">登录</button>
    </form>
  </main>
</body>
</html>
"""

UPLOAD_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>示例壁纸站 · 上传</title>
  <link rel="stylesheet" href="/static/studio.css"/>
</head>
<body class="demo-body">
  <main class="demo-card wide">
    <div class="row-between">
      <div>
        <p class="eyebrow">当前账号 {user}</p>
        <h1>上传壁纸</h1>
      </div>
      <a class="ghost" href="/demo/logout">退出</a>
    </div>
    {flash}
    <form id="upload-form" method="post" action="/demo/upload" enctype="multipart/form-data" class="stack">
      <label>图片文件<input id="file" name="file" type="file" accept="image/*" required></label>
      <label>标题<input id="title" name="title" placeholder="壁纸标题" required></label>
      <label>分类
        <select id="category" name="category">
          <option>风景</option>
          <option>抽象</option>
          <option>动漫</option>
          <option>其他</option>
        </select>
      </label>
      <button id="submit-upload" type="submit">发布上传</button>
    </form>
    <h2>本账号已上传</h2>
    <ul class="upload-list">{items}</ul>
  </main>
</body>
</html>
"""


def _uploads_dir(username: str) -> Path:
    path = data_dir() / "demo_uploads" / username
    path.mkdir(parents=True, exist_ok=True)
    return path


def _current_user(request: Request) -> str | None:
    token = request.cookies.get("demo_session")
    if not token:
        return None
    return SESSIONS.get(token)


def _login_html(error: str = "") -> str:
    block = f'<p class="error">{error}</p>' if error else ""
    return LOGIN_PAGE.replace("{error}", block)


@demo_router.get("/demo/login", response_class=HTMLResponse)
async def demo_login_page(request: Request) -> HTMLResponse:
    if _current_user(request):
        return RedirectResponse("/demo/upload", status_code=302)
    return HTMLResponse(_login_html())


@demo_router.post("/demo/login")
async def demo_login(username: str = Form(...), password: str = Form(...)):
    expected = DEMO_USERS.get(username.strip())
    if expected is None or expected != password:
        return HTMLResponse(_login_html("账号或密码不对"), status_code=401)
    token = secrets.token_hex(16)
    SESSIONS[token] = username.strip()
    response = RedirectResponse("/demo/upload", status_code=303)
    response.set_cookie("demo_session", token, httponly=True)
    return response


@demo_router.get("/demo/logout")
async def demo_logout():
    response = RedirectResponse("/demo/login", status_code=303)
    response.delete_cookie("demo_session")
    return response


@demo_router.get("/demo/upload", response_class=HTMLResponse)
async def demo_upload_page(request: Request):
    user = _current_user(request)
    if not user:
        return RedirectResponse("/demo/login", status_code=302)
    flash = request.query_params.get("ok")
    flash_html = '<p class="success">上传成功</p>' if flash else ""
    items = []
    for path in sorted(_uploads_dir(user).glob("*"), reverse=True):
        if path.suffix == ".txt":
            continue
        meta = path.with_suffix(path.suffix + ".txt")
        title = path.stem
        if meta.exists():
            title = meta.read_text(encoding="utf-8").splitlines()[0]
        items.append(f"<li><strong>{title}</strong> · {path.name}</li>")
    html = (
        UPLOAD_PAGE.replace("{user}", user)
        .replace("{flash}", flash_html)
        .replace("{items}", "".join(items) or "<li class='muted'>还没有上传</li>")
    )
    return HTMLResponse(html)


@demo_router.post("/demo/upload")
async def demo_upload(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form(""),
):
    user = _current_user(request)
    if not user:
        return RedirectResponse("/demo/login", status_code=302)
    raw = await file.read()
    if not raw:
        return HTMLResponse("empty file", status_code=400)
    stem = sanitize_filename(title or Path(file.filename or "wallpaper").stem)
    folder = _uploads_dir(user)
    suffix = Path(file.filename or "image.png").suffix or ".png"
    dest = unique_path(folder, stem, suffix.lower())
    dest.write_bytes(raw)
    dest.with_suffix(dest.suffix + ".txt").write_text(
        f"{stem}\ncategory={category}\noriginal={file.filename}\n",
        encoding="utf-8",
    )
    return RedirectResponse("/demo/upload?ok=1", status_code=303)


@demo_router.get("/demo/api/uploads/{username}")
async def demo_uploads_api(username: str):
    folder = _uploads_dir(username)
    items = []
    for path in sorted(folder.glob("*")):
        if path.name.endswith(".txt"):
            continue
        items.append({"file": path.name, "title": path.stem})
    return JSONResponse({"username": username, "items": items})
