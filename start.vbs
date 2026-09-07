' 无窗口一键启动服务器并打开浏览器
' 双击此文件即可执行，无 cmd/PowerShell 窗口弹出，操作完自动结束
Set WshShell = CreateObject("WScript.Shell")
Set FileSystem = CreateObject("Scripting.FileSystemObject")
url = "http://localhost:8080/kan/"
exitCode = WshShell.Run("powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""e:\All file\trae\zuopinji\brand-portfolio\start.ps1""", 0, True)

If exitCode = 0 Then
    edgePath = WshShell.ExpandEnvironmentStrings("%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe")
    chromePath = WshShell.ExpandEnvironmentStrings("%ProgramFiles%\Google\Chrome\Application\chrome.exe")

    If FileSystem.FileExists(edgePath) Then
        WshShell.Run """" & edgePath & """ """ & url & """", 1, False
    ElseIf FileSystem.FileExists(chromePath) Then
        WshShell.Run """" & chromePath & """ """ & url & """", 1, False
    Else
        CreateObject("Shell.Application").ShellExecute url
    End If
Else
    MsgBox "Failed to start the local website. Exit code: " & exitCode, vbCritical, "Startup error"
End If
