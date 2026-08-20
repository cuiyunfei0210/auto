# 壁纸工坊

本地小工具：对文件夹里的图片做二创（可选），然后用浏览器**模拟网页上传**。  
**一个账号的数量传完，才登录下一个账号。** 同一台电脑只能开一份。

## 能做什么

- 跳过二创，直接选本地文件夹上传
- 对接中转站 API（`https://api.newxxt.top`）做图生图，并按提示词生成标题
- 多账号队列：每个账号可设上传数量和间隔
- 用 Chromium 打开登录页、填表、选文件、点发布（不调壁纸站后台接口）
- 代理可选；关掉也能正常跑；需要时每 5 个账号换一次代理
- 自带示例壁纸站，方便先把流程跑通

## 安装（Windows）

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -e .
playwright install chromium
```

启动：

```bat
python run.py
```

或双击 `start.bat`。浏览器会打开 `http://127.0.0.1:8765`。

## 建议的试用步骤

1. 把几张图放进 `data/source`（或在界面里填写源文件夹）
2. 任务模式选 **跳过二创，直接上传源文件夹**
3. 账号保持默认的 `demo1` / `demo2`（密码 `123123`）
4. 点「开始任务」
5. 打开 [示例站上传页](http://127.0.0.1:8765/demo/login) 查看两个账号各自收到的图

对真实壁纸站：在「网页上传」里改成该站的登录地址、上传地址和 CSS 选择器。标题会使用图片文件名；分类按你填的默认值选择。

## 二创

在「二创 API」填中转站地址和 API Key（只保存在本机 `data/config.json`）。  
当前部分中转站的 `/v1/images/edits` 通道可能不可用，这时用跳过二创即可。

文件名提示词会走 `/v1/chat/completions`，用生成的标题作为上传标题。

## 命令

```bash
python run.py --no-browser
python run.py --once
pytest
```

`--once` 按当前配置跑一轮，不打开界面。
