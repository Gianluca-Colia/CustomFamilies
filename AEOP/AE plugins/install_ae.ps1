# install_ae.ps1 - installs the AEOP "After Effects -> TouchDesigner" pieces for
# the Custom families plugin.
#
# GUARD: if After Effects is NOT installed, the script does NOTHING and exits.
#
# When AE IS present it installs:
#   1) AELayerSpout.aex -> <AE>\Support Files\Plug-ins\ for EVERY installed AE
#      version (the location AE actually scans; the per-user Common\MediaCore
#      folder is NOT reliably loaded). These live under Program Files, so this
#      step self-elevates ONE child (one UAC) that copies the .aex into each
#      detected version's Plug-ins.
#   2) PlayerDebugMode = 1 (HKCU, CSXS 9..12) so the unsigned CEP panel can load.
#   3) CEP panel com.aeop.nullosc -> %APPDATA%\Adobe\CEP\extensions\
# Steps 2 and 3 stay in the CURRENT USER context (HKCU / %APPDATA%).
#
# AV NOTE: the .aex is unsigned, so aggressive antivirus (Avast/AVG, etc.) may
# quarantine it. After copying we VERIFY the file survived; if an AV removed it
# we pop a clear message telling the user which folders to whitelist. We do NOT
# try to add AV exclusions programmatically: a script that edits antivirus
# settings is itself flagged as malware (and gets quarantined). A code-signing
# certificate is the only way to make this fully automatic for all AVs.
#
# Source paths derive from $PSScriptRoot. Idempotent. The C++ operators (.dll)
# are read in place from ...\AEOP\Dll and need no install. A persistent log is
# written next to this script (_install_ae_log.txt) because stdout is lost when
# the script is launched by the TD installer.

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path     # ...\AEOP\AE plugins
$logFile = Join-Path $here '_install_ae_log.txt'

function Log($m) {
    $line = "[install_ae] $m"
    Write-Output $line
    try { Add-Content -LiteralPath $logFile -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $line) } catch {}
}

# Every installed AE: objects { Name; Plugins } where Plugins is the version's
# "Support Files\Plug-ins" folder. Program Files folders first (friendly names),
# registry InstallPath as a fallback for custom install locations. Requiring the
# Plug-ins dir to exist skips leftover/partial version folders.
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
                            if (Test-Path $cand) { $list += [pscustomobject]@{ Name = $k.PSChildName; Plugins = $cand }; break }
                        }
                    }
                }
            }
        }
    }
    return $list
}

# Active third-party AV display name(s) for the guidance message, if any.
function Get-ActiveAV {
    try {
        $avs = Get-CimInstance -Namespace 'root/SecurityCenter2' -ClassName AntiVirusProduct -ErrorAction Stop |
               Where-Object { $_.displayName -and $_.displayName -notmatch 'Windows Defender' }
        if ($avs) { return (($avs | ForEach-Object { $_.displayName }) -join ', ') }
    } catch {}
    return $null
}

try {
    # --- GUARD: do nothing unless AE is installed -------------------------
    $installs = @(Get-AEInstalls)
    if ($installs.Count -eq 0) {
        Log "After Effects not detected - nothing to do."
        exit 0
    }
    Log ("After Effects detected: " + (($installs | ForEach-Object { $_.Name }) -join ', '))

    # --- 1) Effect .aex -> each version's Plug-ins (one elevated copy) -----
    $aex = Join-Path $here 'AELayerSpout.aex'
    if (Test-Path $aex) {
        $dests = @()
        foreach ($ae in $installs) { $dests += (Join-Path $ae.Plugins 'AELayerSpout.aex') }

        # Plain, readable -Command (NOT base64 -EncodedCommand: encoded commands
        # are a malware signature that AV behavior shields flag).
        $inner = (@("`$ErrorActionPreference='SilentlyContinue'") +
                  ($dests | ForEach-Object { "Copy-Item -LiteralPath '$aex' -Destination '$_' -Force -EA SilentlyContinue" })) -join '; '
        Start-Process powershell.exe -Verb RunAs -Wait `
            -ArgumentList '-NoProfile', '-NonInteractive', '-Command', $inner | Out-Null

        # VERIFY: AV (esp. Avast/AVG) can quarantine the unsigned .aex a moment
        # after the copy. Re-check after a short delay; report whatever is missing.
        Start-Sleep -Seconds 4
        $blocked = @($dests | Where-Object { -not (Test-Path -LiteralPath $_) })
        foreach ($o in ($dests | Where-Object { Test-Path -LiteralPath $_ })) { Log "effect -> $o" }

        if ($blocked.Count -gt 0) {
            $av = Get-ActiveAV
            $avTxt = if ($av) { $av } else { 'il tuo antivirus' }
            foreach ($b in $blocked) { Log "BLOCKED by AV ($avTxt): $b" }
            $paths = ($installs | ForEach-Object { $_.Plugins }) -join "`n"
            $msg = "Il plugin di After Effects (AELayerSpout.aex) e' stato bloccato/rimosso da $avTxt.`n`n" +
                   "Aggiungi un'ECCEZIONE per queste cartelle nel tuo antivirus (o in Sicurezza di Windows), poi reinstalla:`n`n" +
                   $paths + "`n" + $here + "`n`n" +
                   "(Il plugin non e' firmato digitalmente: e' un falso positivo.)"
            try { (New-Object -ComObject WScript.Shell).Popup($msg, 0, 'AEOP - Antivirus ha bloccato il plugin', 0x30) | Out-Null } catch {}
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
