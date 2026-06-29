/* AE Null OSC panel - bake only.
 *
 * While connected, the panel watches the Null layers' keyframes/values and AUTO
 * RE-BAKES (/ae/null_bake) whenever they change (debounced), so the per-frame
 * data in TouchDesigner is always current. No manual Bake, no mode switch.
 *
 * It does NOT send the playhead frame. The current frame (parked AND during
 * playback) is supplied by the external UI-Automation reader
 * (AE Reader/ae_preview_reader.py -> /ae/playhead), which is the single source
 * of time. Streaming the frame from here too would fight that signal.
 *
 * Requires the manifest CEFCommandLine flags --enable-nodejs --mixed-context.
 */
(function () {
    "use strict";

    var nodeRequire = (typeof require === "function") ? require
                     : (typeof cep_node !== "undefined" ? cep_node.require : null);
    var dgram = nodeRequire ? nodeRequire("dgram") : null;
    var child_process = nodeRequire ? nodeRequire("child_process") : null;
    var fs = nodeRequire ? nodeRequire("fs") : null;
    var path = nodeRequire ? nodeRequire("path") : null;

    // --- UI-Automation playhead reader (external Python process) -----------
    // Connect launches it, Disconnect stops it, so the whole pipeline is one
    // button. The reader streams AE's playback frame (/ae/playhead) to TD.
    //
    // The reader ships INSIDE the Custom families package. Its location is derived
    // dynamically from %LOCALAPPDATA% (the one constant we can rely on across PCs /
    // usernames) - never a developer's absolute disk path, which would silently
    // point future installs/debug at the wrong file.
    //   %LOCALAPPDATA%\Derivative\TouchDesigner099\Custom families\AEOP\AE plugins\AE Reader\
    var AEOP_ROOT = (function () {
        var la = (typeof process !== "undefined" && process.env) ? process.env.LOCALAPPDATA : null;
        if (!la || !path) return null;
        return path.join(la, "Derivative", "TouchDesigner099", "Custom families", "AEOP");
    })();
    var READER_DIR    = (AEOP_ROOT && path) ? path.join(AEOP_ROOT, "AE plugins", "AE Reader") : null;
    var READER_SCRIPT = (READER_DIR && path) ? path.join(READER_DIR, "ae_preview_reader.py") : null;
    var READER_LOG    = (READER_DIR && path) ? path.join(READER_DIR, "_reader_log.txt") : null;
    var readerProc = null;

    // Resolve a Python interpreter without hardcoding a user/version: glob the
    // per-user Python install locations (newest first), then fall back to PATH.
    function pickPython() {
        var cands = [];
        var la = (typeof process !== "undefined" && process.env) ? process.env.LOCALAPPDATA : null;
        if (fs && path && la) {
            var roots = [path.join(la, "Python"), path.join(la, "Programs", "Python")];
            for (var r = 0; r < roots.length; r++) {
                try {
                    var subs = fs.readdirSync(roots[r]).sort().reverse();   // newest version first
                    for (var s = 0; s < subs.length; s++) {
                        cands.push(path.join(roots[r], subs[s], "pythonw.exe"));
                        cands.push(path.join(roots[r], subs[s], "python.exe"));
                    }
                } catch (e) {}
            }
        }
        for (var i = 0; i < cands.length; i++) {
            try { if (fs && fs.existsSync(cands[i])) return cands[i]; } catch (e) {}
        }
        return "pythonw";   // on PATH (needs: pip install uiautomation)
    }

    // Kill any stray reader instances so we never run two senders on port 7000.
    function killStrayReaders(done) {
        if (!child_process) { if (done) done(); return; }
        var ps = "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" " +
                 "| Where-Object { $_.CommandLine -like '*ae_preview_reader*' } " +
                 "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }";
        try {
            child_process.execFile("powershell.exe",
                ["-NonInteractive", "-NoProfile", "-Command", ps],
                function () { if (done) done(); });
        } catch (e) { if (done) done(); }
    }

    function startReader() {
        if (!child_process || !READER_SCRIPT) return;
        killStrayReaders(function () {
            var io = "ignore";
            try { if (fs && READER_LOG) { var fd = fs.openSync(READER_LOG, "w"); io = ["ignore", fd, fd]; } }
            catch (e) {}
            try {
                readerProc = child_process.spawn(pickPython(), [READER_SCRIPT],
                    { detached: true, stdio: io, windowsHide: true });
                readerProc.on("exit", function () { readerProc = null; });
                readerProc.unref();
            } catch (e) { readerProc = null; }
        });
    }

    function stopReader() {
        if (readerProc) { try { readerProc.kill(); } catch (e) {} readerProc = null; }
        killStrayReaders();
    }

    function evalScript(script, cb) {
        if (typeof window.__adobe_cep__ !== "undefined")
            window.__adobe_cep__.evalScript(script, cb || function () {});
        else if (cb) cb("EvalScript error.");
    }

    // --- OSC encoding (big-endian) ----------------------------------------
    function oscPadLen(n) { return (n + 4) & ~3; }

    function oscString(str) {
        var raw = Buffer.from(String(str), "binary");
        var buf = Buffer.alloc(oscPadLen(raw.length), 0);
        raw.copy(buf, 0);
        return buf;
    }

    function oscMessage(address, args) {
        var parts = [oscString(address)];
        var tags = ",";
        for (var i = 0; i < args.length; i++) tags += args[i].t;
        parts.push(oscString(tags));
        for (var j = 0; j < args.length; j++) {
            var a = args[j];
            if (a.t === "s") parts.push(oscString(a.v));
            else if (a.t === "i") { var bi = Buffer.alloc(4); bi.writeInt32BE(a.v | 0, 0); parts.push(bi); }
            else { var bf = Buffer.alloc(4); bf.writeFloatBE(a.v, 0); parts.push(bf); }
        }
        return Buffer.concat(parts);
    }

    function buildBakeMessage(project, comp, name, type, index, frame, numFrames, v) {
        var args = [
            { t: "s", v: project }, { t: "s", v: comp }, { t: "s", v: name }, { t: "s", v: type },
            { t: "i", v: index }, { t: "i", v: frame }, { t: "i", v: numFrames }
        ];
        for (var k = 0; k < 17; k++) args.push({ t: "f", v: v[k] });
        return oscMessage("/ae/layer_bake", args);
    }

    // Live (non-baked) transform of a single static layer at the current time.
    function buildLiveMessage(project, comp, name, type, index, v) {
        var args = [
            { t: "s", v: project }, { t: "s", v: comp }, { t: "s", v: name }, { t: "s", v: type },
            { t: "i", v: index }
        ];
        for (var k = 0; k < 17; k++) args.push({ t: "f", v: v[k] });
        return oscMessage("/ae/layer", args);
    }

    // --- State -------------------------------------------------------------
    var sock = null;
    var frameTimer = null;
    var liveTimer = null;        // fast realtime stream of static-layer transforms
    var liveBusy = false;        // guard so AEOP_live() calls don't pile up
    var connected = false;

    var SIG_INTERVAL_MS = 500;   // how often to check for changes
    var DEBOUNCE_MS = 500;       // wait for edits to settle before re-baking
    var LIVE_INTERVAL_MS = 40;   // ~25 Hz realtime overlay for static layers
    var lastSigCheck = 0;
    var lastSig = null;          // most recently observed signature
    var bakedSig = null;         // signature that is currently baked into TD
    var pendingSince = 0;        // when the current (unbaked) signature appeared
    var baking = false;

    var $ = function (id) { return document.getElementById(id); };
    function setStatus(txt) { $("status").textContent = txt; }

    // OSC transport is FIXED (multicast 239.255.42.99:7000), shared under the
    // hood with the TD CHOP/TOP. No UI - the host/port fields were removed.
    function getHostPort() {
        return { host: "239.255.42.99", port: 7000 };
    }

    // Send a big list of datagrams in paced batches.
    function pacedSend(buffers, host, port, onDone) {
        var i = 0;
        (function step() {
            var end = Math.min(i + 200, buffers.length);
            for (; i < end; i++) sock.send(buffers[i], 0, buffers[i].length, port, host);
            if (i < buffers.length) setTimeout(step, 5);
            else if (onDone) onDone();
        })();
    }

    function doBake(onDone) {
        if (baking) { if (onDone) onDone(); return; }
        baking = true;
        var hp = getHostPort();
        evalScript("AEOP_bake()", function (res) {
            var data;
            try { data = JSON.parse(res); }
            catch (err) { baking = false; setStatus("Bake parse error."); if (onDone) onDone(); return; }
            if (data.error || !data.layers || !data.layers.length) {
                baking = false; setStatus("Connected. No layers in the active comp."); if (onDone) onDone(); return;
            }
            var buffers = [];
            for (var n = 0; n < data.layers.length; n++) {
                var nl = data.layers[n];
                for (var f = 0; f < nl.frames.length; f++)
                    buffers.push(buildBakeMessage(data.project, data.comp, nl.name, nl.type, nl.index, f, data.numFrames, nl.frames[f]));
            }
            pacedSend(buffers, hp.host, hp.port, function () {
                baking = false;
                setStatus("Connected & synced: " + data.layers.length + " layer(s) x " + data.numFrames +
                          " frames -> " + hp.host + ":" + hp.port + "\nBaked. Re-bakes automatically on edit. (Playhead via UIA reader.)");
                if (onDone) onDone();
            });
        });
    }

    // Continuous tick: periodically check whether the animation changed and a
    // re-bake is due. The current FRAME is NOT sent from here anymore - the
    // external UI-Automation reader (ae_preview_reader.py) is the single source
    // of the playhead, because it tracks AE both parked and during playback.
    // Streaming the CTI from here would fight that signal (CTI sits at 0 during
    // play) and yank the value back to 0.
    function tick() {
        if (!sock) return;

        var now = Date.now();
        if (now - lastSigCheck < SIG_INTERVAL_MS) return;
        lastSigCheck = now;

        evalScript("AEOP_signature()", function (sig) {
            if (!connected) return;
            if (sig !== bakedSig) {
                if (sig !== lastSig) {           // still changing - reset debounce
                    lastSig = sig;
                    pendingSince = Date.now();
                } else if (Date.now() - pendingSince >= DEBOUNCE_MS) {
                    // settled - re-bake
                    var target = sig;
                    doBake(function () { bakedSig = target; });
                }
            }
        });
    }

    // Fast realtime overlay: stream the current transform of every STATIC layer
    // (no keyframes) so moving a static null updates TD with ~40 ms latency
    // instead of waiting for the signature poll + debounce + re-bake. Skipped
    // while a bake is running (they share AE's single script engine) and while
    // AE is playing back (scripting is frozen then - the samples simply go stale
    // and the CHOP falls back to the baked value, which is identical for statics).
    function sendLive() {
        if (!sock || !connected || baking || liveBusy) return;
        liveBusy = true;
        var hp = getHostPort();
        evalScript("AEOP_live()", function (res) {
            liveBusy = false;
            if (!connected || !sock) return;
            var data;
            try { data = JSON.parse(res); } catch (e) { return; }
            if (!data.layers || !data.layers.length) return;
            for (var n = 0; n < data.layers.length; n++) {
                var nl = data.layers[n];
                var buf = buildLiveMessage(data.project, data.comp, nl.name, nl.type, nl.index, nl.v);
                sock.send(buf, 0, buf.length, hp.port, hp.host);
            }
        });
    }

    function connect() {
        if (!dgram) { setStatus("Node.js / dgram unavailable. Check manifest flags."); return; }
        sock = dgram.createSocket({ type: "udp4", reuseAddr: true });
        sock.on("error", function (e) { setStatus("Socket error: " + e.message); });
        sock.bind(0, function () {
            try {
                sock.setMulticastTTL(1);
                sock.setMulticastLoopback(true);
                sock.setMulticastInterface("127.0.0.1");  // emit out loopback so local CHOPs receive
            } catch (e) {}
            connected = true;
            lastSig = null; bakedSig = null; lastSigCheck = 0;
            setStatus("Connected. Purging cache, starting reader & baking...");
            // Purge AE's caches on connect so the render/Spout pipeline starts
            // clean (forces a fresh render pass the TOP can record). Then start
            // the playhead reader and bake.
            evalScript("app.purge(PurgeTarget.ALL_CACHES);", function () {
                startReader();
                doBake(function () {
                    evalScript("AEOP_signature()", function (sig) { bakedSig = sig; lastSig = sig; });
                });
            });
            frameTimer = setInterval(tick, 66);   // ~15 Hz (re-bake polling)
            // Realtime static-layer streaming is handled by the AEGP plugin's idle
            // hook (it fires during drags; CEP evalScript cannot - AE's script engine
            // is busy mid-drag). Left here disabled in case a CEP-only fallback is
            // ever needed: liveTimer = setInterval(sendLive, LIVE_INTERVAL_MS);
        });

        var btn = $("toggle");
        btn.textContent = "Disconnect";
        btn.className = "on";
    }

    function disconnect() {
        connected = false;
        if (frameTimer) { clearInterval(frameTimer); frameTimer = null; }
        if (liveTimer) { clearInterval(liveTimer); liveTimer = null; }
        if (sock) { try { sock.close(); } catch (e) {} sock = null; }
        stopReader();
        var btn = $("toggle");
        btn.textContent = "Connect to TD";
        btn.className = "off";
        setStatus("Disconnected.");
    }

    $("toggle").addEventListener("click", function () {
        if (connected) disconnect(); else connect();
    });
})();
