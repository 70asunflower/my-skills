@echo off
rem Remotion 缓存的无头 Chrome，2x 截图。用法:
rem   shoot.bat <file:///D:/tmp/mini.html> <D:\path\out.png> "2000,1090"
rem 窗口尺寸必须带引号——cmd 会把逗号拆成两个参数（踩过: Malformed window size）。
set CHROME=D:\Project\Zcode\college-promo\node_modules\.remotion\chrome-headless-shell\win64\chrome-headless-shell-win64\chrome-headless-shell.exe
%CHROME% --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=2 --default-background-color=FFFFFFFF --window-size=%3 --screenshot=%2 %1
