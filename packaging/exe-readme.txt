把整个 WallpaperStudio 文件夹拷到电脑上任意位置。

打开方法
1. 进入 dist\WallpaperStudio
2. 双击 WallpaperStudio.exe
3. 等浏览器自动打开 http://127.0.0.1:8765
4. 用完前不要关闭黑色窗口，关掉就等于退出

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
- 配置和图片在 exe 旁边的 data 文件夹。源图请放进 data\source（或「文件夹」页显示的实际读取目录），子文件夹里的图也会算
- 同一台电脑只能开一份。如果再双击 exe 没有新窗口，多半已经在跑，浏览器会打开 http://127.0.0.1:8765；也可在任务管理器里结束 WallpaperStudio.exe 后再开
- 中转站 /v1/images 报 image_generation / tools 错时，程序会自动改走对话画图；对话模型用该站实际有的模型
