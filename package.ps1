$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$manifest = Get-Content (Join-Path $PSScriptRoot 'config\extension.toml') -Raw
$version = [regex]::Match($manifest, '(?m)^version = "([^"]+)"').Groups[1].Value
if (-not $version) { throw 'No extension version found.' }
$outputDirectory = Join-Path $PSScriptRoot 'dist'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$archivePath = Join-Path $outputDirectory "section.box-$version.zip"
$stream = [System.IO.File]::Open($archivePath, [System.IO.FileMode]::Create)
$archive = [System.IO.Compression.ZipArchive]::new($stream, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    $files = @(
        Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'section_box') -File -Filter '*.py'
        Get-Item -LiteralPath (Join-Path $PSScriptRoot 'config\extension.toml')
        Get-Item -LiteralPath (Join-Path $PSScriptRoot 'data\icon.svg'), (Join-Path $PSScriptRoot 'data\icon_active.svg')
    )
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($PSScriptRoot.Length + 1).Replace('\', '/')
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, "section.box/$relative") | Out-Null
    }
} finally {
    $archive.Dispose()
    $stream.Dispose()
}
Write-Output $archivePath
