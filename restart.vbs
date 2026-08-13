' 无窗口一键重启 dev-server 并打开浏览器
' 双击此文件即可执行，无 cmd/PowerShell 窗口弹出，操作完自动结束
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File ""e:\All file\trae\zuopinji\brand-portfolio\restart.ps1""", 0, False
