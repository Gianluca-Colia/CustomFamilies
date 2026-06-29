# install_ae.ps1 - installs the AEOP "After Effects -> TouchDesigner" pieces for
# the Custom families plugin. Runs entirely in the CURRENT USER context, so it
# needs NO administrator rights and shows NO UAC prompt.
#
# GUARD: if After Effects is NOT installed, the script does NOTHING and exits.
#
# When AE IS present it installs:
#   1) AELayerSpout.aex -> %APPDATA%\Adobe\Common\Plug-ins\7.0\MediaCore\
#        This Common MediaCore folder is SHARED by every installed AE version
#        (24, 25, 26, ...), so one copy covers them all - no admin, and no
#        double-load (copying into each version's own Program Files\Plug-ins
#        would make AE load the effect twice -> conflict).
#   2) PlayerDebugMode = 1 (HKCU, CSXS 9..12) so the unsigned CEP panel can load.
#   3) CEP panel com.aeop.nullosc -> %APPDATA%\Adobe\CEP\extensions\
#
# All source paths derive from $PSScriptRoot, so it works wherever the AEOP
# package is installed (...\Custom families\AEOP\AE plugins\). Idempotent. The
# C++ operators (.dll) are NOT handled here - the TD operators read them in place
# from ...\AEOP\Dll\.
#
# Call with a single line, e.g. from the Custom families installer:
#   powershell -NonInteractive -NoProfile -ExecutionPolicy Bypass -File "install_ae.ps1"

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path     # ...\AEOP\AE plugins

function Log($m) { Write-Output "[install_ae] $m" }

# Detect every installed After Effects version. Registry first (survives custom
# install locations), then the default Program Files\Adobe folder as a fallback.
function Get-AEInstalls {
    $names = @()
    # Prefer human-readable Program Files folder names ("Adobe After Effects 2026").
    $pf = Join-Path $env:ProgramFiles 'Adobe'
    if (Test-Path $pf) {
        foreach ($d in (Get-ChildItem $pf -Directory -Filter 'Adobe After Effects*' -ErrorAction SilentlyContinue)) {
            $names += ($d.Name -replace '^Adobe After Effects\s*', '')
        }
    }
    # Registry fallback only when nothing was found under Program Files (covers
    # AE installed to a custom location). Avoids listing the same version twice.
    if ($names.Count -eq 0) {
        foreach ($rr in @('HKLM:\SOFTWARE\Adobe\After Effects',
                          'HKLM:\SOFTWARE\WOW6432Node\Adobe\After Effects')) {
            if (Test-Path $rr) {
                foreach ($k in (Get-ChildItem $rr -ErrorAction SilentlyContinue)) {
                    $ip = (Get-ItemProperty $k.PSPath -ErrorAction SilentlyContinue).InstallPath
                    if ($ip -and (Test-Path $ip)) { $names += $k.PSChildName }
                }
            }
        }
    }
    return ($names | Sort-Object -Unique)
}

try {
    # --- GUARD: do nothing unless AE is installed -------------------------
    $versions = @(Get-AEInstalls)
    if ($versions.Count -eq 0) {
        Log "After Effects not detected - nothing to do."
        exit 0
    }
    Log ("After Effects detected: " + ($versions -join ', ') +
         "  (one shared MediaCore install covers all of them)")

    # --- 1) Effect .aex -> per-user shared MediaCore (no admin) -----------
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
