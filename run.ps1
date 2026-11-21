$ErrorActionPreference = 'Stop'
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { throw '未找到 Python 启动器。请先安装 Python 3.12 和 trcc-linux。' }
& $python.Source -3.12 (Join-Path $PSScriptRoot 'run_zh.py')
exit $LASTEXITCODE
