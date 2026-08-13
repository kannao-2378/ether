# 一键重启 dev-server 并打开浏览器（无窗口执行）
$port = 8001
$projectDir = "e:\All file\trae\zuopinji\brand-portfolio"
$url = "http://127.0.0.1:$port"

# 1. 停止占用 8001 端口的旧进程
$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    $conns.OwningProcess | Sort-Object -Unique | ForEach-Object {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 500
}

# 2. 后台启动 dev-server（隐藏窗口，独立进程持续运行）
Start-Process node -ArgumentList "dev-server.mjs" -WindowStyle Hidden -WorkingDirectory $projectDir

# 3. 等待服务就绪（轮询端口，最多 5 秒）
$ready = $false
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Milliseconds 500
    $check = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($check) { $ready = $true; break }
}

# 4. 打开默认浏览器
Start-Process $url
