# 一键启动本地服务器并打开浏览器访问 hub 主入口（无窗口执行）
$port = 8080
$projectDir = "e:\All file\trae\zuopinji\brand-portfolio"
$url = "http://localhost:$port/kan/"

# 1. 停止占用 8080 端口的旧进程
$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    $conns.OwningProcess | Sort-Object -Unique | ForEach-Object {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 500
}

# 2. 后台启动静态服务器（隐藏窗口，独立进程持续运行）
# Ignore the Microsoft Store placeholder and select a real Python interpreter.
$python = Get-Command python -All -ErrorAction Stop |
    Where-Object { $_.Source -notlike '*\Microsoft\WindowsApps\*' } |
    Select-Object -First 1 -ExpandProperty Source

if (-not $python) {
    throw "No usable Python interpreter was found in PATH."
}
Start-Process -FilePath $python -ArgumentList "`"$projectDir\server.py`"", $port -WorkingDirectory $projectDir -WindowStyle Hidden

# 3. 等待服务就绪（轮询端口，最多 5 秒）
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Milliseconds 500
    $check = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($check) { break }
}

# The calling VBS opens the browser after this script exits successfully.
