# Installs the "AE Null OSC" CEP panel into After Effects for development.
#  1) Enables loading of unsigned CEP extensions (PlayerDebugMode) for the
#     CSXS runtime versions AE might use.
#  2) Copies the extension folder into the per-user CEP extensions directory.
# Re-run after editing the panel files. Restart After Effects to pick it up,
# then open it from:  Window > Extensions > AE Null OSC
$ErrorActionPreference = 'Stop'

$src = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'com.aeop.nullosc'
if (-not (Test-Path $src)) { Write-Error "Source not found: $src"; exit 1 }

# 1) PlayerDebugMode = 1 for CSXS 9..12 (covers AE CC2019 .. 2025+)
foreach ($v in 9, 10, 11, 12) {
    $key = "HKCU:\Software\Adobe\CSXS.$v"
    New-Item -Path $key -Force | Out-Null
    New-ItemProperty -Path $key -Name 'PlayerDebugMode' -Value '1' -PropertyType String -Force | Out-Null
    Write-Output "PlayerDebugMode=1 -> $key"
}

# 2) Copy into the per-user CEP extensions folder
$dest = Join-Path $env:APPDATA 'Adobe\CEP\extensions\com.aeop.nullosc'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Copy-Item $src $dest -Recurse -Force
Write-Output "INSTALLED panel -> $dest"
Write-Output "Restart After Effects, then: Window > Extensions > AE -> Touchdesigner"
