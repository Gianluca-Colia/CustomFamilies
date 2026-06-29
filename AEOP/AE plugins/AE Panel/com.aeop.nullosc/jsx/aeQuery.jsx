/* aeQuery.jsx - runs inside After Effects (ExtendScript).
 *
 * AEOP_collect() walks every composition in the open project, finds the Null
 * layers, samples their transform at the composition's CURRENT time (the
 * playhead / CTI) and returns the whole lot as a JSON string. The CEP panel
 * parses this string and turns each entry into an OSC message.
 *
 * ExtendScript has no native JSON, so we serialize by hand.
 */

function AEOP__esc(s) {
    s = String(s);
    var out = "";
    for (var i = 0; i < s.length; i++) {
        var c = s.charAt(i);
        if (c === '"' || c === '\\') out += '\\' + c;
        else if (c === '\n') out += '\\n';
        else if (c === '\r') out += '\\r';
        else if (c === '\t') out += '\\t';
        else out += c;
    }
    return out;
}

function AEOP__num(n) {
    if (n === null || n === undefined || isNaN(n)) return "0";
    return String(n);
}

// Project name, URI-DECODED. ExtendScript's File.name returns the name
// percent-encoded (spaces as %20), but the AEGP C++ plugin sends it decoded.
// Both must agree or the CHOP keys them as two different projects. decodeURI is
// idempotent for plain names, so it's safe either way.
function AEOP__projName(proj) {
    var n = (proj && proj.file) ? proj.file.name : "Untitled";
    try { n = decodeURI(n); } catch (e) {}
    return n;
}

// Safe property read: returns the valueAtTime array, or a default if the
// property is missing on this layer.
function AEOP__val(layer, name, t, def) {
    try {
        var tr = layer.property("ADBE Transform Group");
        var p = tr ? tr.property(name) : null;
        if (!p) p = layer.property(name);
        if (!p) return def;
        var v = p.valueAtTime(t, false);
        return v;
    } catch (e) {
        return def;
    }
}

function AEOP__arr(v, i, def) {
    if (v === null || v === undefined) return def;
    if (v instanceof Array) return (v.length > i) ? v[i] : def;
    return (i === 0) ? v : def;   // scalar property
}

// Classify an AE layer into a short type tag that the C++ operators filter on.
// Order matters: adjustment layers are solids with a flag, nulls are AVLayers
// with a flag, so test the specific flags before the generic source checks.
function AEOP__layerType(layer) {
    try {
        if (layer instanceof ShapeLayer)  return "shape";
        if (layer instanceof TextLayer)   return "text";
        if (layer instanceof CameraLayer) return "camera";
        if (layer instanceof LightLayer)  return "light";
        if (layer.nullLayer === true)       return "null";
        if (layer.adjustmentLayer === true) return "adjustment";
        var src = layer.source;
        if (src && src.mainSource && (src.mainSource instanceof SolidSource)) return "solid";
        if (src) return "footage";
    } catch (e) {}
    return "av";
}

function AEOP_collect() {
    var proj = app.project;
    var projName = AEOP__projName(proj);

    var entries = [];

    if (proj) {
        for (var ci = 1; ci <= proj.numItems; ci++) {
            var item = proj.item(ci);
            if (!(item instanceof CompItem)) continue;

            var comp = item;
            var t = comp.time;   // CURRENT playhead time of this comp (seconds)

            for (var li = 1; li <= comp.numLayers; li++) {
                var layer = comp.layer(li);
                var ltype = AEOP__layerType(layer);

                var threeD = false;
                try { threeD = (layer.threeDLayer === true); } catch (e) {}

                var pos    = AEOP__val(layer, "ADBE Position",      t, [0, 0, 0]);
                var scale  = AEOP__val(layer, "ADBE Scale",         t, [100, 100, 100]);
                var opacity= AEOP__val(layer, "ADBE Opacity",       t, 100);
                var anchor = AEOP__val(layer, "ADBE Anchor Point",  t, [0, 0, 0]);

                var rx = 0, ry = 0, rz = 0, ox = 0, oy = 0, oz = 0;
                if (threeD) {
                    rx = AEOP__val(layer, "ADBE Rotate X", t, 0);
                    ry = AEOP__val(layer, "ADBE Rotate Y", t, 0);
                    rz = AEOP__val(layer, "ADBE Rotate Z", t, 0);
                    var orient = AEOP__val(layer, "ADBE Orientation", t, [0, 0, 0]);
                    ox = AEOP__arr(orient, 0, 0);
                    oy = AEOP__arr(orient, 1, 0);
                    oz = AEOP__arr(orient, 2, 0);
                } else {
                    // 2D: single Rotation maps to Z.
                    rz = AEOP__val(layer, "ADBE Rotate Z", t, 0);
                }

                var e = "{";
                e += '"project":"' + AEOP__esc(projName) + '",';
                e += '"comp":"'    + AEOP__esc(comp.name) + '",';
                e += '"layer":"'   + AEOP__esc(layer.name) + '",';
                e += '"type":"'    + AEOP__esc(ltype) + '",';
                e += '"index":'    + AEOP__num(layer.index) + ',';
                e += '"tx":' + AEOP__num(AEOP__arr(pos, 0, 0)) + ',';
                e += '"ty":' + AEOP__num(AEOP__arr(pos, 1, 0)) + ',';
                e += '"tz":' + AEOP__num(AEOP__arr(pos, 2, 0)) + ',';
                e += '"sx":' + AEOP__num(AEOP__arr(scale, 0, 100)) + ',';
                e += '"sy":' + AEOP__num(AEOP__arr(scale, 1, 100)) + ',';
                e += '"sz":' + AEOP__num(AEOP__arr(scale, 2, 100)) + ',';
                e += '"rx":' + AEOP__num(rx) + ',';
                e += '"ry":' + AEOP__num(ry) + ',';
                e += '"rz":' + AEOP__num(rz) + ',';
                e += '"ox":' + AEOP__num(ox) + ',';
                e += '"oy":' + AEOP__num(oy) + ',';
                e += '"oz":' + AEOP__num(oz) + ',';
                e += '"opacity":' + AEOP__num(opacity) + ',';
                e += '"ax":' + AEOP__num(AEOP__arr(anchor, 0, 0)) + ',';
                e += '"ay":' + AEOP__num(AEOP__arr(anchor, 1, 0)) + ',';
                e += '"az":' + AEOP__num(AEOP__arr(anchor, 2, 0)) + ',';
                e += '"time":' + AEOP__num(t);
                e += "}";
                entries.push(e);
            }
        }
    }

    return "[" + entries.join(",") + "]";
}


// AEOP_bake() - samples EVERY frame of the active comp for each Null layer and
// returns the whole animation as JSON. The panel turns this into /ae/null_bake
// OSC messages so TouchDesigner can store it and play it back at full rate.
// Runs while the timeline is parked (sampling valueAtTime does not move the CTI).
function AEOP_bake() {
    var proj = app.project;
    var projName = AEOP__projName(proj);

    var comp = (proj) ? proj.activeItem : null;
    if (!(comp instanceof CompItem)) {
        if (proj) {
            for (var ci = 1; ci <= proj.numItems; ci++) {
                if (proj.item(ci) instanceof CompItem) { comp = proj.item(ci); break; }
            }
        }
    }
    if (!(comp instanceof CompItem)) return '{"error":"no active comp"}';

    var fdur = comp.frameDuration;
    var numFrames = Math.round(comp.duration / fdur);

    var out = '{"project":"' + AEOP__esc(projName) + '",';
    out += '"comp":"' + AEOP__esc(comp.name) + '",';
    out += '"frameRate":' + AEOP__num(comp.frameRate) + ',';
    out += '"numFrames":' + numFrames + ',';
    out += '"layers":[';

    var first = true;
    for (var li = 1; li <= comp.numLayers; li++) {
        var layer = comp.layer(li);
        var ltype = AEOP__layerType(layer);
        var threeD = false;
        try { threeD = (layer.threeDLayer === true); } catch (e) {}

        if (!first) out += ',';
        first = false;
        out += '{"name":"' + AEOP__esc(layer.name) + '","type":"' + AEOP__esc(ltype) +
               '","index":' + AEOP__num(layer.index) + ',"frames":[';

        for (var f = 0; f < numFrames; f++) {
            var t = f * fdur;
            var pos     = AEOP__val(layer, "ADBE Position",     t, [0, 0, 0]);
            var scale   = AEOP__val(layer, "ADBE Scale",        t, [100, 100, 100]);
            var opacity = AEOP__val(layer, "ADBE Opacity",      t, 100);
            var anchor  = AEOP__val(layer, "ADBE Anchor Point", t, [0, 0, 0]);
            var rx = 0, ry = 0, rz = 0, ox = 0, oy = 0, oz = 0;
            if (threeD) {
                rx = AEOP__val(layer, "ADBE Rotate X", t, 0);
                ry = AEOP__val(layer, "ADBE Rotate Y", t, 0);
                rz = AEOP__val(layer, "ADBE Rotate Z", t, 0);
                var orient = AEOP__val(layer, "ADBE Orientation", t, [0, 0, 0]);
                ox = AEOP__arr(orient, 0, 0); oy = AEOP__arr(orient, 1, 0); oz = AEOP__arr(orient, 2, 0);
            } else {
                rz = AEOP__val(layer, "ADBE Rotate Z", t, 0);
            }

            if (f > 0) out += ',';
            out += '[' +
                AEOP__num(AEOP__arr(pos, 0, 0)) + ',' + AEOP__num(AEOP__arr(pos, 1, 0)) + ',' + AEOP__num(AEOP__arr(pos, 2, 0)) + ',' +
                AEOP__num(AEOP__arr(scale, 0, 100)) + ',' + AEOP__num(AEOP__arr(scale, 1, 100)) + ',' + AEOP__num(AEOP__arr(scale, 2, 100)) + ',' +
                AEOP__num(rx) + ',' + AEOP__num(ry) + ',' + AEOP__num(rz) + ',' +
                AEOP__num(ox) + ',' + AEOP__num(oy) + ',' + AEOP__num(oz) + ',' +
                AEOP__num(opacity) + ',' +
                AEOP__num(AEOP__arr(anchor, 0, 0)) + ',' + AEOP__num(AEOP__arr(anchor, 1, 0)) + ',' + AEOP__num(AEOP__arr(anchor, 2, 0)) + ',' +
                AEOP__num(t) +
            ']';
        }
        out += ']}';
    }
    out += ']}';
    return out;
}


// True if the layer has ANY keyframe on a transform property. Such layers are
// animated and go through the baked timeline; layers with NO keyframes are
// "static" and are streamed live (instant, no bake/debounce gap).
function AEOP__hasAnyKeys(layer) {
    var props = ["ADBE Anchor Point", "ADBE Position", "ADBE Scale",
                 "ADBE Rotate X", "ADBE Rotate Y", "ADBE Rotate Z",
                 "ADBE Orientation", "ADBE Opacity"];
    var tr = null;
    try { tr = layer.property("ADBE Transform Group"); } catch (e) {}
    if (!tr) return false;
    for (var p = 0; p < props.length; p++) {
        var pr = null;
        try { pr = tr.property(props[p]); } catch (e) {}
        if (pr && pr.numKeys > 0) return true;
    }
    return false;
}

// AEOP_live() - lightweight realtime overlay. Samples the CURRENT-time transform
// of every STATIC layer (no keyframes) in the active comp. The panel streams
// these as /ae/layer messages at ~25 Hz so moving a static null updates TD
// immediately, without waiting for the signature poll + debounce + re-bake.
// Animated layers are skipped here (they come through AEOP_bake).
function AEOP_live() {
    var proj = app.project;
    var projName = AEOP__projName(proj);
    var comp = AEOP__activeComp();
    if (!comp) return '{"error":"no comp"}';
    var t = comp.time;

    var out = '{"project":"' + AEOP__esc(projName) + '","comp":"' + AEOP__esc(comp.name) + '","layers":[';
    var first = true;
    for (var li = 1; li <= comp.numLayers; li++) {
        var layer = comp.layer(li);
        if (AEOP__hasAnyKeys(layer)) continue;   // animated -> baked path

        var ltype = AEOP__layerType(layer);
        var threeD = false;
        try { threeD = (layer.threeDLayer === true); } catch (e) {}

        var pos     = AEOP__val(layer, "ADBE Position",     t, [0, 0, 0]);
        var scale   = AEOP__val(layer, "ADBE Scale",        t, [100, 100, 100]);
        var opacity = AEOP__val(layer, "ADBE Opacity",      t, 100);
        var anchor  = AEOP__val(layer, "ADBE Anchor Point", t, [0, 0, 0]);
        var rx = 0, ry = 0, rz = 0, ox = 0, oy = 0, oz = 0;
        if (threeD) {
            rx = AEOP__val(layer, "ADBE Rotate X", t, 0);
            ry = AEOP__val(layer, "ADBE Rotate Y", t, 0);
            rz = AEOP__val(layer, "ADBE Rotate Z", t, 0);
            var orient = AEOP__val(layer, "ADBE Orientation", t, [0, 0, 0]);
            ox = AEOP__arr(orient, 0, 0); oy = AEOP__arr(orient, 1, 0); oz = AEOP__arr(orient, 2, 0);
        } else {
            rz = AEOP__val(layer, "ADBE Rotate Z", t, 0);
        }

        if (!first) out += ',';
        first = false;
        out += '{"name":"' + AEOP__esc(layer.name) + '","type":"' + AEOP__esc(ltype) +
               '","index":' + AEOP__num(layer.index) + ',"v":[' +
            AEOP__num(AEOP__arr(pos, 0, 0)) + ',' + AEOP__num(AEOP__arr(pos, 1, 0)) + ',' + AEOP__num(AEOP__arr(pos, 2, 0)) + ',' +
            AEOP__num(AEOP__arr(scale, 0, 100)) + ',' + AEOP__num(AEOP__arr(scale, 1, 100)) + ',' + AEOP__num(AEOP__arr(scale, 2, 100)) + ',' +
            AEOP__num(rx) + ',' + AEOP__num(ry) + ',' + AEOP__num(rz) + ',' +
            AEOP__num(ox) + ',' + AEOP__num(oy) + ',' + AEOP__num(oz) + ',' +
            AEOP__num(opacity) + ',' +
            AEOP__num(AEOP__arr(anchor, 0, 0)) + ',' + AEOP__num(AEOP__arr(anchor, 1, 0)) + ',' + AEOP__num(AEOP__arr(anchor, 2, 0)) + ',' +
            AEOP__num(t) +
        ']}';
    }
    out += ']}';
    return out;
}

// Active comp helper.
function AEOP__activeComp() {
    var proj = app.project;
    var comp = (proj) ? proj.activeItem : null;
    if (!(comp instanceof CompItem)) {
        if (proj) {
            for (var ci = 1; ci <= proj.numItems; ci++) {
                if (proj.item(ci) instanceof CompItem) { comp = proj.item(ci); break; }
            }
        }
    }
    return (comp instanceof CompItem) ? comp : null;
}

// AEOP_frame() - lightweight: the active comp's current playhead frame, so TD
// can follow AE's timeline by indexing the baked clip.
function AEOP_frame() {
    var proj = app.project;
    var projName = AEOP__projName(proj);
    var comp = AEOP__activeComp();
    if (!comp) return '{"error":"no comp"}';
    var fdur = comp.frameDuration;
    var frame = comp.time / fdur;
    var numFrames = Math.round(comp.duration / fdur);
    return '{"project":"' + AEOP__esc(projName) + '","comp":"' + AEOP__esc(comp.name) +
           '","frame":' + AEOP__num(frame) + ',"numFrames":' + numFrames + '}';
}

// AEOP_signature() - a compact string that changes when the comp STRUCTURE or
// any KEYFRAMES change (layer added/removed/renamed, keyframe added/moved/edited).
// Static transform values are deliberately NOT included: they are handled by the
// live stream (AEOP_live), so dragging a static null does not trigger a full
// re-bake. The panel compares this between polls and re-bakes only when it differs.
function AEOP_signature() {
    var comp = AEOP__activeComp();
    if (!comp) return "";
    var s = comp.name + "|" + comp.numLayers + "|" + comp.duration + "|" + comp.frameDuration + "|";
    var props = ["ADBE Anchor Point", "ADBE Position", "ADBE Scale",
                 "ADBE Rotate X", "ADBE Rotate Y", "ADBE Rotate Z",
                 "ADBE Orientation", "ADBE Opacity"];
    for (var li = 1; li <= comp.numLayers; li++) {
        var layer = comp.layer(li);
        s += li + ":" + layer.name + ":" + AEOP__layerType(layer) + ";";
        var tr = null;
        try { tr = layer.property("ADBE Transform Group"); } catch (e) {}
        if (!tr) continue;
        for (var p = 0; p < props.length; p++) {
            var pr = null;
            try { pr = tr.property(props[p]); } catch (e) {}
            if (!pr) continue;
            // Only keyframes count toward the bake signature. A property with no
            // keys is static and is streamed live, so its value is omitted here.
            try {
                if (pr.numKeys > 0) {
                    s += props[p] + "#k" + pr.numKeys + ":";
                    for (var k = 1; k <= pr.numKeys; k++)
                        s += pr.keyTime(k).toFixed(4) + "=" + String(pr.keyValue(k)) + ",";
                    s += ";";
                }
            } catch (e) {}
        }
    }
    return s;
}
