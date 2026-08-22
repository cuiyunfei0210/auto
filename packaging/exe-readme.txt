把整个 WallpaperStudio 文件夹拷到电脑上任意位置。

打开方法
1. 进入 WallpaperStudio 文件夹
2. 双击 WallpaperStudio.exe
3. 会弹出「壁纸工坊」程序窗口，不再打开系统浏览器
4. 用完关窗口，或点网页里的「退出程序」

第一次如果提示缺 WebView2
- 安装 Microsoft Edge WebView2：https://go.microsoft.com/fwlink/p/?LinkId=2124703
- 一般装了 Edge 的 Windows 已经自带

注意
- 发给别人时：把整个 WallpaperStudio 文件夹打成 zip 再发（_internal 必须在）。不要只发一个 exe。微信/QQ 常会拦 exe。对方解压到桌面后再打开。
- 不要把你用过的 data\config.json 一起发出去也行；新版本会忽略别人电脑的 C:\Users\... 路径。若对方仍报错，让他删掉 data\config.json 再打开。
- 上传壁纸站仍用内置 Chromium（在后台填登录表），操作界面在程序窗口里
- 不要只拷一个 exe，同目录的其它文件也要一起带走
- 不要直接双击压缩包里的程序（WinRAR 临时目录跑起来会出问题）
- 如果弹出 Failed to load Python DLL / python312.dll / 找不到指定的模块：先删掉整个 WallpaperStudio 文件夹，再解压 GitHub 的 client-Windows。exe 必须和 _internal 在同一层。也可以先双击「打开壁纸工坊.bat」检查。还不行就安装 VC++：https://aka.ms/vs/17/release/vc_redist.x64.exe ，并看杀毒软件有没有隔离 dll
- 配置和图片在 exe 旁边的 data 文件夹。源图请放进 data\source（或「文件夹」页显示的实际读取目录），子文件夹里的图也会算
- 同一台电脑只能开一份。如果再双击 exe 没有新窗口，多半已经在跑，请到任务栏点「壁纸工坊」
- 如果提示已经在运行，但看不到窗口：打开任务管理器，结束 WallpaperStudio.exe，再重新双击
- 用完关窗口即可。日志在 data\studio.log
- 跳过二创时不会把源图拷进输出目录。开始二创前会清空输出目录里的旧图，本轮张数会和源图一致
- gpt-image-2 原生只能出 1024×1024 / 1536×1024 / 1024×1536。出图尺寸填 1920×1080 / 2K / 4K 时会放大到该尺寸；CQwall 最少要 1920×1080
- 根据图片写标题：newxxt 填 gpt-5.4-mini。aipixapi 这组 Key 只有 gpt-image-2，写标题会走 newxxt
