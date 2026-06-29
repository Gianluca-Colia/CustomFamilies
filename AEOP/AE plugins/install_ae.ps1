# install_ae.ps1 - installs the AEOP "After Effects -> TouchDesigner" pieces for
# the Custom families plugin.
#
# GUARD: if After Effects is NOT installed, the script does NOTHING and exits.
#
# When AE IS present it installs:
#   1) AELayerSpout.aex -> <AE>\Support Files\Plug-ins\ for EVERY installed AE
#      version (2024, 2025, 2026, ...). This is the location AE actually scans
#      for effects; the per-user Common\MediaCore folder is NOT reliably loaded.
#      These folders live under Program Files, so this ONE step needs admin -
#      the script self-elevates a single child process that copies into all the
#      version folders at once (one UAC prompt). Each version loads only its own
#      copy, so there is no double-load.
#   2) PlayerDebugMode = 1 (HKCU, CSXS 9..12) so the unsigned CEP panel can load.
#   3) CEP panel com.aeop.nullosc -> %APPDATA%\Adobe\CEP\extensions\
# Steps 2 and 3 stay in the CURRENT USER context (HKCU / %APPDATA%), so they are
# never run elevated (which would target the wrong user's hive/profile).
#
# Source paths derive from $PSScriptRoot (...\Custom families\AEOP\AE plugins\).
# Idempotent. The C++ operators (.dll) are NOT handled here - the TD operators
# read them in place from ...\AEOP\Dll\.
#
# Call with a single line, e.g. from the Custom families installer:
#   powershell -NonInteractive -NoProfile -ExecutionPolicy Bypass -File "install_ae.ps1"

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path     # ...\AEOP\AE plugins

function Log($m) { Write-Output "[install_ae] $m" }

# Every installed AE: returns objects { Name; Plugins } where Plugins is the
# version's "Support Files\Plug-ins" folder. Program Files folders first (give
# friendly names like 2026), registry InstallPath as a fallback for custom
# install locations.
function Get-AEInstalls {
    $list = @()
    $pf = Join-Path $env:ProgramFiles 'Adobe'
    if (Test-Path $pf) {
        foreach ($d in (Get-ChildItem $pf -Directory -Filter 'Adobe After Effects*' -ErrorAction SilentlyContinue)) {
            $plug = Join-Path $d.FullName 'Support Files\Plug-ins'
            if (Test-Path $plug) {
                $list += [pscustomobject]@{ Name = ($d.Name -replace '^Adobe After Effects\s*', ''); Plugins = $plug }
            }
        }
    }
    if ($list.Count -eq 0) {
        foreach ($rr in @('HKLM:\SOFTWARE\Adobe\After Effects',
                          'HKLM:\SOFTWARE\WOW6432Node\Adobe\After Effects')) {
            if (Test-Path $rr) {
                foreach ($k in (Get-ChildItem $rr -ErrorAction SilentlyContinue)) {
                    $ip = (Get-ItemProperty $k.PSPath -ErrorAction SilentlyContinue).InstallPath
                    if ($ip) {
                        foreach ($cand in @((Join-Path $ip 'Support Files\Plug-ins'), (Join-Path $ip 'Plug-ins'))) {
                            if (Test-Path $cand) {
                                $list += [pscustomobject]@{ Name = $k.PSChildName; Plugins = $cand }
                                break
                            }
                        }
                    }
                }
            }
        }
    }
    return $list
}

try {
    # --- GUARD: do nothing unless AE is installed -------------------------
    $installs = @(Get-AEInstalls)
    if ($installs.Count -eq 0) {
        Log "After Effects not detected - nothing to do."
        exit 0
    }
    Log ("After Effects detected: " + (($installs | ForEach-Object { $_.Name }) -join ', '))

    # --- 1) Effect .aex -> each version's Plug-ins (admin via 1 UAC) ------
    $aex = Join-Path $here 'AELayerSpout.aex'
    if (Test-Path $aex) {
        $needElevation = @()
        foreach ($ae in $installs) {
            $dest = Join-Path $ae.Plugins 'AELayerSpout.aex'
            try {
                Copy-Item -LiteralPath $aex -Destination $dest -Force -ErrorAction Stop
                Log "effect -> $($ae.Plugins)"
            } catch {
                $needElevation += $ae.Plugins      # Program Files -> needs admin
            }
        }
        if ($needElevation.Count -gt 0) {
            $cmds = foreach ($plug in $needElevation) {
                "Copy-Item -LiteralPath '$aex' -Destination '" + (Join-Path $plug 'AELayerSpout.aex') + "' -Force"
            }
            $script = ($cmds -join '; ')
            $enc = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($script))
            $p = Start-Process powershell.exe -Verb RunAs -Wait -PassThru `
                 -ArgumentList '-NoProfile', '-NonInteractive', '-EncodedCommand', $enc
            if ($p.ExitCode -eq 0) {
                Log ("effect (elevated) -> " + ($needElevation -join ' | '))
            } else {
                Log "WARN: elevated copy returned exit $($p.ExitCode) (UAC declined? AE open?)"
            }
        }
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
