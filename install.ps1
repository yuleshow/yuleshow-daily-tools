param(
    [switch]$NoSystem,
    [switch]$NoPath,
    [switch]$Uninstall,
    [string]$Prefix = (Join-Path $HOME ".local")
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$ScriptsDir = Join-Path $RepoRoot "scripts"
$BinDir = Join-Path $Prefix "bin"
$AppDir = Join-Path $Prefix "share\yuleshow-daily-tools"
$VenvDir = Join-Path $AppDir "venv"
$Marker = "rem yuleshow-daily-tools wrapper"

function Update-UserPath([bool]$Remove) {
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    $entries = @($current -split [regex]::Escape([IO.Path]::PathSeparator) |
        Where-Object { $_ -and $_.TrimEnd('\') -ne $BinDir.TrimEnd('\') })
    if (-not $Remove) {
        $entries = @($BinDir) + $entries
    }
    [Environment]::SetEnvironmentVariable(
        "Path", ($entries -join [IO.Path]::PathSeparator), "User")
}

if ($Uninstall) {
    if (Test-Path $BinDir) {
        Get-ChildItem -LiteralPath $BinDir -Filter "yuleshow-*.cmd" -File |
            ForEach-Object {
                if ((Get-Content -LiteralPath $_.FullName -Raw) -like "*$Marker*") {
                    Remove-Item -LiteralPath $_.FullName
                    Write-Host "Removed $($_.FullName)"
                }
            }
    }
    if (Test-Path $AppDir) {
        Remove-Item -LiteralPath $AppDir -Recurse
        Write-Host "Removed $AppDir"
    }
    Update-UserPath $true
    [Environment]::SetEnvironmentVariable("YULESHOW_DAILY_TOOLS_PYTHON", $null, "User")
    [Environment]::SetEnvironmentVariable("YULESHOW_DAILY_TOOLS_SCRIPTS", $null, "User")
    $env:YULESHOW_DAILY_TOOLS_PYTHON = $null
    $env:YULESHOW_DAILY_TOOLS_SCRIPTS = $null
    $env:Path = (($env:Path -split [regex]::Escape([IO.Path]::PathSeparator) |
        Where-Object { $_ -and $_.TrimEnd('\') -ne $BinDir.TrimEnd('\') }) -join [IO.Path]::PathSeparator)
    Write-Host "Uninstall complete."
    exit 0
}

if (-not (Test-Path $ScriptsDir)) {
    throw "Scripts directory not found: $ScriptsDir"
}

$VersionCheck = "import sys; sys.exit(0 if (3, 9) <= sys.version_info[:2] < (3, 15) else 1)"
$PythonCommand = $null
$PythonArguments = @()
$Python = Get-Command "python.exe" -ErrorAction SilentlyContinue
if ($Python) {
    & $Python.Source -c $VersionCheck
    if ($LASTEXITCODE -eq 0) { $PythonCommand = $Python.Source }
}
if (-not $PythonCommand) {
    $PythonLauncher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($PythonLauncher) {
        foreach ($Version in @("3.14", "3.13", "3.12", "3.11", "3.10", "3.9")) {
            $CandidateArguments = @("-$Version")
            & $PythonLauncher.Source @CandidateArguments -c $VersionCheck
            if ($LASTEXITCODE -eq 0) {
                $PythonCommand = $PythonLauncher.Source
                $PythonArguments = $CandidateArguments
                break
            }
        }
    }
}
if (-not $PythonCommand) {
    throw "Python 3.9 through 3.14 is required by the current dependencies."
}

if (-not $NoSystem) {
    $Winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
    if (-not $Winget) {
        Write-Warning "winget not found. Install system dependencies manually (ffmpeg, GPSBabel, ExifTool, Poppler, ImageMagick, and a MySQL client)."
    } else {
        $Packages = @(
            "Gyan.FFmpeg",
            "GPSBabel.GPSBabel",
            "OliverBetz.ExifTool",
            "oschwartz10612.Poppler",
            "ImageMagick.ImageMagick"
        )
        foreach ($Package in $Packages) {
            & $Winget.Source install --id $Package --exact --silent `
                --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Could not install $Package with winget; install it manually if you use the related tool."
            }
        }
    }
} else {
    Write-Host "Skipping system package installation (-NoSystem)."
}

New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & $PythonCommand @PythonArguments -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Could not create Python virtual environment." }
}
& $VenvPython -m pip install --upgrade pip wheel setuptools
if ($LASTEXITCODE -ne 0) { throw "Could not update pip tooling." }
& $VenvPython -m pip install -r (Join-Path $RepoRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install Python dependencies." }

[Environment]::SetEnvironmentVariable("YULESHOW_DAILY_TOOLS_PYTHON", $VenvPython, "User")
[Environment]::SetEnvironmentVariable("YULESHOW_DAILY_TOOLS_SCRIPTS", $ScriptsDir, "User")
$env:YULESHOW_DAILY_TOOLS_PYTHON = $VenvPython
$env:YULESHOW_DAILY_TOOLS_SCRIPTS = $ScriptsDir
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
foreach ($Script in Get-ChildItem -LiteralPath $ScriptsDir -File) {
    $Target = Join-Path $BinDir ($Script.Name + ".cmd")
    $Content = @"
@echo off
setlocal
$Marker
set "PYTHONIOENCODING=utf-8"
    "%YULESHOW_DAILY_TOOLS_PYTHON%" "%YULESHOW_DAILY_TOOLS_SCRIPTS%\$($Script.Name)" %*
exit /b %errorlevel%
"@
    Set-Content -LiteralPath $Target -Value $Content -Encoding Ascii
    Write-Host "Installed $($Script.Name)"
}

if (-not $NoPath) {
    Update-UserPath $false
    if (($env:Path -split [regex]::Escape([IO.Path]::PathSeparator)) -notcontains $BinDir) {
        $env:Path = "$BinDir$([IO.Path]::PathSeparator)$env:Path"
    }
    Write-Host "Added $BinDir to your user PATH. Open a new terminal to use the commands."
} else {
    Write-Warning "$BinDir is not added to PATH (-NoPath given)."
}
Write-Host "Installation complete. Sources: $ScriptsDir"
