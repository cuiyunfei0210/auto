把整个 WallpaperStudio 文件夹拷到电脑上任意位置。

打开方法
1. 进入 dist\WallpaperStudio
2. 双击 WallpaperStudio.exe
3. 等浏览器自动打开 http://127.0.0.1:8765
4. 用完请在网页里点「退出程序」。打包版没有黑色窗口

第一次如果提示缺浏览器
- 回到项目目录，先双击「打开壁纸工坊.bat」一次
  （会给当前 Windows 用户安装 Chromium）
- 然后再双击 WallpaperStudio.exe

注意
- 发给别人时：把整个 WallpaperStudio 文件夹打成 zip 再发（_internal 必须在）。不要只发一个 exe。微信/QQ 常会拦 exe。对方解压到桌面后再打开。
- 不要把你用过的 data\config.json 一起发出去也行；新版本会忽略别人电脑的 C:\Users\... 路径。若对方仍报错，让他删掉 data\config.json 再打开。
- 上传网页需要 Chromium。新打包会把浏览器打进 _internal；若仍提示找不到浏览器，请安装 Microsoft Edge
- 不要只拷一个 exe，同目录的其它文件也要一起带走
- 不要直接双击压缩包里的程序（WinRAR 临时目录跑起来会出问题）
- 如果弹出 Failed to load Python DLL / python312.dll / 找不到指定的模块：先删掉整个 WallpaperStudio 文件夹，再解压 GitHub 的 client-Windows。exe 必须和 _internal 在同一层。也可以先双击「打开壁纸工坊.bat」检查。还不行就安装 VC++：https://aka.ms/vs/17/release/vc_redist.x64.exe ，并看杀毒软件有没有隔离 dll
- 配置和图片在 exe 旁边的 data 文件夹。源图请放进 data\source（或「文件夹」页显示的实际读取目录），子文件夹里的图也会算
- 同一台电脑只能开一份。如果再双击 exe 没有新窗口，多半已经在跑，浏览器会打开 http://127.0.0.1:8765
- 如果提示已经在运行，但网页打不开：打开任务管理器，结束 WallpaperStudio.exe，再重新双击。新版本也会自动清掉卡死的旧进程
- 浏览器要等一两秒再刷新；如果先跳出无法访问，等界面起来即可
- 用完请点网页上的「退出程序」。日志在 data\studio.log
- 跳过二创时不会把源图拷进输出目录。开始二创前会清空输出目录里的旧图，本轮张数会和源图一致
- gpt-image-2 只能原生出 1024×1024 / 1536×1024 / 1024×1536，程序不再放大
- 根据图片写标题：newxxt 填 gpt-5.4-mini。aipixapi 这组 Key 只有 gpt-image-2，写标题会走 newxxt
- 中转站 /v1/images 报 image_generation / tools 错时，程序会自动改走对话画图；对话模型用该站实际有的模型
