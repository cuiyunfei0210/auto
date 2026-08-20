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
- 必须带上整个 WallpaperStudio 文件夹（里面的 _internal 不能丢）
- 上传网页需要 Chromium。新打包会把浏览器打进 _internal；若仍提示找不到浏览器，请安装 Microsoft Edge
- 不要只拷一个 exe，同目录的其它文件也要一起带走
- 不要直接双击压缩包里的程序（WinRAR 临时目录跑起来会出问题）
- 配置和图片在 exe 旁边的 data 文件夹
- 同一台电脑只能开一份
- 中转站 /v1/images 报 image_generation / tools 错时，程序会自动改走对话画图；对话模型用该站实际有的模型
