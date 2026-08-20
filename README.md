# 壁纸工坊

本地小工具：对文件夹里的图片做二创（可选），然后用浏览器**模拟网页上传**。  
**一个账号的数量传完，才登录下一个账号。** 同一台电脑只能开一份。

## Windows 怎么打开

电脑上先安装 [Python 3.11+](https://www.python.org/downloads/windows/)，安装时勾选 **Add python.exe to PATH**。

然后**双击**下面任意一个文件：

- `打开壁纸工坊.bat`
- `start.bat`

第一次会自动创建环境、安装组件和 Chromium。装完后浏览器会打开 `http://127.0.0.1:8765`。  
**用完之前不要关掉那个黑色命令行窗口**，关掉就等于退出程序。

也可以自己打包成桌面 exe，步骤如下。

## 做成桌面 exe

在 **Windows 电脑**上操作（Linux/Mac 打不出 Windows 的 exe）。

1. 先安装 [Python 3.11+](https://www.python.org/downloads/windows/)，勾选 **Add python.exe to PATH**。
2. 把整个项目文件夹放到电脑上，例如 `D:\wallpaper-studio`。
3. （建议）**先双击一次** `打开壁纸工坊.bat`，等它装完。不是必须，但能提前把 Chromium 装好。
4. **双击** `build-windows.bat`，等几分钟，不要关窗口。
5. 结束后会自动打开文件夹  
   `项目目录\dist\WallpaperStudio\`
6. **双击** `WallpaperStudio.exe`。浏览器会打开 `http://127.0.0.1:8765`。  
   黑色窗口不要关。

以后日常使用只需要第 6 步。可以把 `dist\WallpaperStudio` 整个文件夹拷到桌面；**不要只拷一个 exe**，同目录文件要一起带着。

配置和图片在 exe 旁边的 `data` 文件夹里。

## 能做什么

- 跳过二创，直接选本地文件夹上传
- 对接中转站 API（`https://api.newxxt.top`）做图生图，并按提示词生成标题
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
3. 账号保持默认的 `demo1` / `demo2`（密码 `123123`）
4. 点「开始任务」
5. 打开 [示例站上传页](http://127.0.0.1:8765/demo/login) 查看两个账号各自收到的图

对真实壁纸站：默认已对接 [CQwall](https://www.cqwall.com/)。在「账号」页填写邮箱和密码；图片需 **不小于 1920×1080**。分类默认风景（值为 9）。

账号密码只保存在本机 `data/config.json`，不要提交到 git。

## 二创

在「二创 API」填中转站地址和 API Key（只保存在本机 `data/config.json`）。  
当前部分中转站的 `/v1/images/edits` 通道可能不可用，这时用跳过二创即可。

文件名提示词会走 `/v1/chat/completions`，用生成的标题作为上传标题。

## 出口 IP

每个账号应走不同代理，避免多个账号落在同一个 IP：

1. 打开「账号」页，勾选 **启用代理，按账号切换出口**
2. 保持 **禁止多个账号共用同一个代理**
3. 在账号行填写该账号的代理，或在代理池里按账号数量准备同样多的地址（一行一个）
4. 格式示例：`http://user:pass@1.2.3.4:8080` 或 `socks5://2.2.2.2:1080`

不启用代理时程序仍可运行，但本机所有账号会表现为同一个出口。

## 命令

```bash
python run.py --no-browser
python run.py --once
pytest
```

`--once` 按当前配置跑一轮，不打开界面。
