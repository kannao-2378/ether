# 一键关闭本地服务器（停止占用 8080 端口的进程）
$port = 8080

$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    $conns.OwningProcess | Sort-Object -Unique | ForEach-Object {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Write-Host "server (port $port) stopped" -ForegroundColor Green
} else {
    Write-Host "server not running (port $port idle)" -ForegroundColor Yellow
}
