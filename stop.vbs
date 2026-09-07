' 无窗口一键关闭本地服务器
' 双击此文件即可执行，无 cmd/PowerShell 窗口弹出，操作完自动结束
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File ""e:\All file\trae\zuopinji\brand-portfolio\stop.ps1""", 0, True
