<#
.SYNOPSIS
    Create a Windows Desktop shortcut that launches the TUI Bible application.

.DESCRIPTION
    Writes a .lnk file to the current user's Desktop. The shortcut opens
    scripts\launch_tui.cmd, which installs dependencies and builds the local
    database on first launch and then starts the terminal UI. Delete the
    shortcut like any other Desktop icon to remove it.

.PARAMETER RepoPath
    Path to the checkout. Defaults to the parent of this script's directory.

.PARAMETER ShortcutName
    Label for the Desktop icon (without the .lnk extension).

.PARAMETER IconLocation
    Icon to use, in "path,index" form.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1 -RepoPath "C:\src\TUI Bible" -ShortcutName "TUI Bible Dev"
#>
[CmdletBinding()]
param(
    [string]$RepoPath,
    [string]$ShortcutName = 'TUI Bible',
    [string]$IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
)

$ErrorActionPreference = 'Stop'

# Resolve the default here rather than in param(): Windows PowerShell 5.1 does
# not expose $PSScriptRoot while evaluating parameter defaults.
if ([string]::IsNullOrWhiteSpace($RepoPath)) {
    $RepoPath = Join-Path $PSScriptRoot '..'
}

if (-not (Test-Path -LiteralPath $RepoPath -PathType Container)) {
    throw "Repository path not found: $RepoPath"
}
$RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path

$launcher = Join-Path $RepoPath 'scripts\launch_tui.cmd'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "Launcher not found: $launcher"
}

$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
if ([string]::IsNullOrWhiteSpace($desktop)) {
    throw 'Could not locate the Desktop directory for the current user.'
}
$shortcutPath = Join-Path $desktop "$ShortcutName.lnk"

if (Test-Path -LiteralPath $shortcutPath) {
    Write-Host "Replacing existing shortcut: $shortcutPath"
}

$shell = New-Object -ComObject WScript.Shell
try {
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\cmd.exe'
    $shortcut.Arguments = "/c `"`"$launcher`"`""
    $shortcut.WorkingDirectory = $RepoPath
    $shortcut.IconLocation = $IconLocation
    $shortcut.Description = 'Launch the TUI Bible terminal application'
    $shortcut.Save()
}
finally {
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($shell)
}

Write-Host "Desktop shortcut created: $shortcutPath"
Write-Host "Target: $launcher"
Write-Host "Working directory: $RepoPath"
