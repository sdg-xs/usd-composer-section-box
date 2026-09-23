param(
    [string]$KitRoot = 'C:\kit-app-template\_build\windows-x86_64\release\kit'
)
$ErrorActionPreference = 'Stop'
$cache = Join-Path (Split-Path $KitRoot -Parent) 'extscache'
$usd = Get-ChildItem -LiteralPath $cache -Directory -Filter 'omni.usd.libs-*' | Select-Object -First 1
if (-not $usd) { throw "No omni.usd.libs extension found in $cache" }
$pipArchive = Get-ChildItem -LiteralPath $cache -Directory -Filter 'omni.kit.pip_archive-*' | Select-Object -First 1
if (-not $pipArchive) { throw "No omni.kit.pip_archive extension found in $cache" }
$bootstrap = @'
import os, runpy, sys
kit, usd, prebundle, *scripts = sys.argv[1:]
handles = [os.add_dll_directory(kit), os.add_dll_directory(os.path.join(usd, 'bin'))]
sys.path.insert(0, usd)
sys.path.insert(0, prebundle)
for script in scripts:
    runpy.run_path(script, run_name='__main__')
'@
& (Join-Path $KitRoot 'python\python.exe') -c $bootstrap $KitRoot $usd.FullName (Join-Path $pipArchive.FullName 'pip_prebundle') `
    (Join-Path $PSScriptRoot 'tests\verify_model.py') (Join-Path $PSScriptRoot 'tests\verify_selection.py')
exit $LASTEXITCODE
