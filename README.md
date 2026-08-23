# 壁纸工坊

本地小工具：对文件夹里的图片做二创（可选），然后用浏览器**模拟网页上传**。  
**一个账号的数量传完，才登录下一个账号。** 同一台电脑只能开一份。

## Windows 怎么打开

电脑上先安装 [Python 3.11+](https://www.python.org/downloads/windows/)，安装时勾选 **Add python.exe to PATH**。

然后**双击**下面任意一个文件：

- `打开壁纸工坊.bat`
- `start.bat`

第一次会自动创建环境、安装组件和 Chromium。装完后会弹出 **壁纸工坊程序窗口**，不再打开系统浏览器。  
用 `打开壁纸工坊.bat` 时，用完之前不要关掉那个黑色命令行窗口。  
打包好的 `WallpaperStudio.exe` **没有黑色窗口**，界面就在程序里；用完关窗口，或点「退出程序」。  
如果窗口打不开：到任务管理器结束 `WallpaperStudio.exe`，重新打开。不要反复双击。

也可以自己打包成桌面 exe，步骤如下。

## 做成桌面 exe

在 **Windows 电脑**上操作（Linux/Mac 打不出 Windows 的 exe）。

1. 先安装 [Python 3.11+](https://www.python.org/downloads/windows/)，勾选 **Add python.exe to PATH**。
2. 把整个项目文件夹放到电脑上，例如 `D:\wallpaper-studio`。
3. （建议）**先双击一次** `打开壁纸工坊.bat`，等它装完。不是必须，但能提前把 Chromium 装好。
4. **双击** `build-windows.bat`，等几分钟，不要关窗口。
5. 结束后会自动打开文件夹  
   `项目目录\dist\WallpaperStudio\`
6. **双击** `WallpaperStudio.exe`。会弹出程序窗口，不依赖系统浏览器。  
   用完关窗口即可。

以后日常使用只需要第 6 步。可以把 `dist\WallpaperStudio` 整个文件夹拷到桌面；**不要只拷一个 exe**，同目录文件要一起带着。

配置和图片在 exe 旁边的 `data` 文件夹里。

如果提示缺少 WebView2，安装 [Edge WebView2 运行库](https://go.microsoft.com/fwlink/p/?LinkId=2124703)（装了 Edge 的电脑一般已经有）。

## GitHub 自动打包（和 Actions 里的 Build client app 一样）

代码一推送到 GitHub，就会自动跑工作流 **Build client app**：

1. 打开仓库 → 点 **Actions**
2. 左侧点 **Build client app**
3. 点进带绿色勾的那一次
4. 拉到页面底部 **Artifacts**，下载 `client-Windows`
5. 解压后打开 `WallpaperStudio\WallpaperStudio.exe`（也可以先双击同目录的 `打开壁纸工坊.bat`）

如果弹出 **Failed to load Python DLL / python312.dll / 找不到指定的模块**：说明 `_internal` 不完整。请删掉桌面上的整个 `WallpaperStudio` 文件夹，重新解压 `client-Windows`，保证 exe 和 `_internal` 在同一层。不要只拷 exe，也不要从压缩包里直接打开。还不行就安装 [VC++ 运行库](https://aka.ms/vs/17/release/vc_redist.x64.exe)。

**一定要先解压整个文件夹**，再双击 exe。不要直接在压缩包里打开，也不要从 WinRAR 的临时目录运行。  
如果提示找不到 `chrome-headless-shell.exe`，说明用的是旧包（没带浏览器）。请重新下载最新一次绿色勾的 `client-Windows`。

也可以在 Actions 页面右上角 **Run workflow** 手动再打一次包。
Windows / Linux / macOS 都会各打一份。

## 能做什么

- 跳过二创，直接选本地文件夹上传
- 对接中转站 API（默认 `https://api.newxxt.top`，生图 `gpt-image-2`，起名 `gpt-5.4-mini`）做图生图
- 也可以换成 `https://www.aipixapi.art/` 生图（这组 Key 只有 gpt-image-2，写标题仍走 newxxt）
- 多账号队列：每个账号可设上传数量、间隔和独立代理
- 用 Chromium 打开登录页、填表、选文件、点发布（不调壁纸站后台接口）
- 代理可选。默认 **一个账号一个出口 IP**，代理不够或两个账号填了同一个代理时会拒绝开跑；关掉代理也能正常上传
- 自带示例壁纸站，方便先把流程跑通

## 安装（手动，可选）

如果双击 bat 失败，可在项目目录打开命令行：

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -e .
playwright install chromium
python run.py
```

## 建议的试用步骤

1. 把几张图放进 `data/source`（或在界面里填写源文件夹）
2. 任务模式选 **跳过二创，直接上传源文件夹**
3. 账号页默认已填 CQwall 邮箱 `ari-ihcot@linshi-mail.com`
4. 点「开始任务」
5. 打开 [示例站上传页](http://127.0.0.1:8765/demo/login) 查看两个账号各自收到的图

对真实壁纸站：默认已对接 [CQwall](https://www.cqwall.com/)，账号页预填 `ari-ihcot@linshi-mail.com`。分类默认风景（值为 9）。当前分类：1 动物 / 2 军事 / 3 汽车 / 4 电影 / 5 时代 / 6 明星 / 7 宇宙 / 8 美女 / 9 风景 / 10 动漫 / 17 游戏 / 18 都市。程序不限制图片宽高。

中转站默认 [api.newxxt.top](https://api.newxxt.top/)，也可以用 [aipixapi.art](https://www.aipixapi.art/)。不要填 `xbhuiz.com`（那条线路不能生图）。接口地址不要带 `/v1`。账号队列里不要填中转站邮箱。

## 二创

在「二创 API」可选中转站模板。默认是 `https://api.newxxt.top`：生图用 `gpt-image-2`，根据图片写标题用 `gpt-5.4-mini`。OpenCode 配置里的 `gpt-5.x` 是对话模型，不要填进生图模型。

`https://www.aipixapi.art` 这组 Key 只有 `gpt-image-2`，适合生图；写标题会改走 newxxt。`xmapi.site` 同样是生图为主。

`gpt-image-2` 会先按原图走 `/v1/images/edits` 改图，不会先打后台那种不带原图的文生图。newxxt 的改图通道有时会报 `image_generation` tools 错；后台测小狗只证明文生图通了。改图失败后会先识图（写出士兵/人物等真实主体），再走带 `quality` 的文生图，避免军事原图变成风景。还不行会改走 aipixapi 生图，标题仍用 newxxt 对话 Key。newxxt 请把「生图」Key 填进生图栏，「对话」Key 填进对话栏。

`gpt-image-2` 只能原生出 `1024x1024` / `1536x1024` / `1024x1536`。出图尺寸填 `1920x1080`、`2K`、`4K` 时，会先按最接近的原生尺寸出图，再放大到你填的宽高。CQwall 最少要 1920×1080，推荐填 `1920x1080`。

文件名提示词会走 `/v1/chat/completions`，并根据图片内容识图起名。newxxt 填 `gpt-5.4-mini`。`gpt-image-2` 不能写标题。

跳过二创时直接上传源文件夹，不会再把源图拷进输出目录。开始二创前会清空输出目录里的旧图，所以本轮二创张数会和源图一致。

## 出口 IP

每个账号应走不同代理，避免多个账号落在同一个 IP：

1. 打开「账号」页，勾选 **启用代理，按账号切换出口**
2. 保持 **禁止多个账号共用同一个代理**
3. 在账号行填写该账号的代理，或在代理池里按账号数量准备同样多的地址（一行一个）
4. 格式示例：`http://user:pass@1.2.3.4:8080` 或 `socks5://2.2.2.2:1080`

不启用代理时程序仍可运行，但本机所有账号会表现为同一个出口。

## 命令

```bash
python run.py
python run.py --web
python run.py --no-browser
python run.py --once
pytest
```

默认打开程序窗口。`--web` 用系统浏览器调试；`--no-browser` 只开后台服务；`--once` 按当前配置跑一轮，不打开界面。
