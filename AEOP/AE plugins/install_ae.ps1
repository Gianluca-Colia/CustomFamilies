# install_ae.ps1 - installs the AEOP "After Effects -> TouchDesigner" pieces for
# the Custom families plugin. Runs entirely in the CURRENT USER context, so it
# needs NO administrator rights and shows NO UAC prompt:
#
#   1) AELayerSpout.aex -> %APPDATA%\Adobe\Common\Plug-ins\7.0\MediaCore\
#        AE loads effects from this per-user MediaCore folder, so we avoid the
#        admin-only Program Files plug-ins directory entirely.
#   2) PlayerDebugMode = 1 (HKCU, CSXS 9..12) so the unsigned CEP panel can load.
#   3) CEP panel com.aeop.nullosc -> %APPDATA%\Adobe\CEP\extensions\
#
# All paths derive from $PSScriptRoot, so the script works wherever the AEOP
# package is installed (it ships at: ...\Custom families\AEOP\AE plugins\).
# Idempotent: safe to re-run. The C++ operators (.dll) are NOT handled here -
# the TD operators read them in place from ...\AEOP\Dll\.
#
# Call it with a single line, e.g. from the Custom families installer:
#   powershell -NonInteractive -NoProfile -ExecutionPolicy Bypass -File "install_ae.ps1"

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path     # ...\AEOP\AE plugins

function Log($m) { Write-Output "[install_ae] $m" }

try {
    # --- 1) Effect .aex -> per-user MediaCore (no admin) ------------------
    $aex = Join-Path $here 'AELayerSpout.aex'
    if (Test-Path $aex) {
        $mediaCore = Join-Path $env:APPDATA 'Adobe\Common\Plug-ins\7.0\MediaCore'
        New-Item -ItemType Directory -Force -Path $mediaCore | Out-Null
        Copy-Item $aex (Join-Path $mediaCore 'AELayerSpout.aex') -Force
        Log "effect -> $mediaCore"
    } else {
        Log "WARN: AELayerSpout.aex not found at $aex"
    }

    # --- 2) PlayerDebugMode for unsigned CEP (HKCU = current user) --------
    foreach ($v in 9, 10, 11, 12) {
        $key = "HKCU:\Software\Adobe\CSXS.$v"
        New-Item -Path $key -Force | Out-Null
        New-ItemProperty -Path $key -Name 'PlayerDebugMode' -Value '1' -PropertyType String -Force | Out-Null
    }
    Log "PlayerDebugMode=1 (CSXS 9-12)"

    # --- 3) CEP panel -> per-user extensions ------------------------------
    $panelSrc = Join-Path $here 'AE Panel\com.aeop.nullosc'
    if (Test-Path $panelSrc) {
        $dest = Join-Path $env:APPDATA 'Adobe\CEP\extensions\com.aeop.nullosc'
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Copy-Item $panelSrc $dest -Recurse -Force
        Log "panel -> $dest"
    } else {
        Log "WARN: panel source not found at $panelSrc"
    }

    Log "DONE. Restart After Effects to load the effect + panel (Window > Extensions > AE -> Touchdesigner)."
    exit 0
} catch {
    Log "ERROR: $($_.Exception.Message)"
    exit 1
}
