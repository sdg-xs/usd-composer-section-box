param(
    [string]$KitRoot = 'C:\kit-app-template\_build\windows-x86_64\release\kit'
)
$ErrorActionPreference = 'Stop'
$cache = Join-Path (Split-Path $KitRoot -Parent) 'extscache'
$usd = Get-ChildItem -LiteralPath $cache -Directory -Filter 'omni.usd.libs-*' | Select-Object -First 1
if (-not $usd) { throw "No omni.usd.libs extension found in $cache" }
$bootstrap = @'
import os, runpy, sys
kit, usd, script = sys.argv[1:]
handles = [os.add_dll_directory(kit), os.add_dll_directory(os.path.join(usd, 'bin'))]
sys.path.insert(0, usd)
runpy.run_path(script, run_name='__main__')
'@
& (Join-Path $KitRoot 'python\python.exe') -c $bootstrap $KitRoot $usd.FullName (Join-Path $PSScriptRoot 'tests\verify_model.py')
exit $LASTEXITCODE
