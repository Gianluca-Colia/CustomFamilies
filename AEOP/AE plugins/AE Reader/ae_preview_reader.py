#!/usr/bin/env python3
"""AE playback time -> TouchDesigner OSC bridge (UI Automation, no screenshots).

After Effects freezes all scripting (ExtendScript/CEP/AEGP) during a RAM
preview, so no SDK reports the *playback* frame ("red bar") live. BUT After
Effects exposes its Composition viewer time display through the Windows UI
Automation / accessibility tree, and that value keeps updating during playback.

We read that control's value directly - no screen capture, no pixel
coordinates, resolution-independent, and AE does not need to be in front. The
control is located by walking AE's UIA tree (window class "AE_CApplication*",
a timecode-shaped Name under the "AE Composition" panel), so it works on any
machine without calibration.

  AE plays -> UIA reads viewer timecode "H:MM:SS:FF"
           -> frame = ((H*3600+MM*60+SS)*fps)+FF
           -> /ae/playhead OSC -> CHOP (v11) -> moves the Null

Usage:
  python ae_preview_reader.py            # run the live bridge
  python ae_preview_reader.py --probe    # list timecode controls and exit

Requires: uiautomation  (pip install uiautomation)
"""

import argparse
import re
import socket
import struct
import sys
import time

import uiautomation as auto

# --- Configuration ---------------------------------------------------------
FPS = 24.0                 # comp frame rate (AE timecode last field = frames)
# Send to a local multicast group so MANY TouchDesigner CHOP nodes can all
# receive the same stream (each picks its own Null). Must match the CHOP's
# "Multicast Group" parameter. Use "127.0.0.1" for plain single-node unicast.
TD_HOST = "239.255.42.99"
TD_PORT = 7000
OUTPUT_HZ = 90             # rate of the smooth playhead we send to TD
INTERP_LAG = 0.28          # render AE's motion this far behind real time, so we
                           # interpolate between known samples instead of
                           # extrapolating ahead (>= AE's ~0.25s redraw gap).
                           # Lower = less latency but may stutter; higher =
                           # smoother but more delay. Set to AE's coarse interval.

# AE timecode, e.g. "0:00:03:18" (":" normal, ";" drop-frame).
TIMECODE_RE = re.compile(r"^\s*(\d+)[:;](\d\d)[:;](\d\d)[:;](\d\d)\s*$")

# --- OSC --------------------------------------------------------------------
def _osc_string(s):
    b = s.encode("ascii", "ignore") + b"\x00"
    if len(b) % 4:
        b += b"\x00" * (4 - len(b) % 4)
    return b

def osc_playhead_message(frame):
    """/ae/playhead  ,f  frame   (the CHOP's single, authoritative time source)."""
    return (_osc_string("/ae/playhead") + _osc_string(",f")
            + struct.pack(">f", float(frame)))

# --- UI Automation ----------------------------------------------------------
def find_ae_window():
    root = auto.GetRootControl()
    for w in root.GetChildren():
        try:
            cls = w.ClassName or ""
        except Exception:
            cls = ""
        if cls.startswith("AE_CApplication"):
            return w
    return None

def find_timecode_control(ae):
    """Return the first viewer control whose Name is a timecode, or None.

    Preference: one whose ancestor chain mentions the Composition panel, so we
    don't latch onto a timeline current-time field if both are present.
    """
    best = None
    stack = [(ae, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > 10:
            continue
        for ch in node.GetChildren():
            try:
                name = ch.Name or ""
            except Exception:
                name = ""
            if TIMECODE_RE.match(name):
                if _under_composition(ch):
                    return ch
                best = best or ch
            stack.append((ch, depth + 1))
    return best

def _under_composition(ctrl):
    p = ctrl.GetParentControl()
    for _ in range(6):
        if p is None:
            break
        try:
            if (p.Name or "").startswith("AE Composition"):
                return True
        except Exception:
            pass
        p = p.GetParentControl()
    return False

def parse_frame(text):
    m = TIMECODE_RE.match(text or "")
    if not m:
        return None
    h, mm, ss, ff = (int(g) for g in m.groups())
    return int(round((h * 3600 + mm * 60 + ss) * FPS)) + ff

# --- Modes ------------------------------------------------------------------
def probe():
    ae = find_ae_window()
    if not ae:
        print("After Effects window not found (class AE_CApplication*).")
        return
    print("AE window:", ae.ClassName)
    ctrl = find_timecode_control(ae)
    if not ctrl:
        print("No timecode control found in the UIA tree.")
        return
    print("Timecode control Name:", repr(ctrl.Name),
          "| under Composition:", _under_composition(ctrl))
    print("Sampling 1s...")
    for _ in range(20):
        print("  ", ctrl.Name)
        time.sleep(0.05)

def _is_multicast(host):
    try:
        return 224 <= int(host.split(".")[0]) <= 239
    except Exception:
        return False

def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if _is_multicast(TD_HOST):
        # Emit multicast out the loopback interface and loop it back, so local
        # CHOP nodes (joined on 127.0.0.1) all receive it.
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                        socket.inet_aton("127.0.0.1"))
    ae = find_ae_window()
    if not ae:
        print("After Effects not running? (UIA window AE_CApplication* not found)")
        sys.exit(1)
    ctrl = find_timecode_control(ae)
    if not ctrl:
        print("Could not find the viewer timecode control. Is a comp open?")
        sys.exit(1)
    print(f"AE playback reader (UIA, interpolating, lag={INTERP_LAG*1000:.0f}ms) "
          f"-> {TD_HOST}:{TD_PORT}  ({FPS} fps)  Ctrl-C")

    # AE only redraws the viewer timecode ~4-6x/sec during playback (coarse
    # ~15-frame jumps). To turn that into smooth motion WITHOUT ever passing the
    # real frame (which would force a snap-back / "teleport" when playback
    # stops), we INTERPOLATE between known samples at a fixed time lag instead of
    # extrapolating ahead. The output is AE's exact motion delayed by INTERP_LAG:
    # smooth play, instant loop, and a stop that lands exactly where AE stopped.
    out_period = 1.0 / OUTPUT_HZ
    history = []                 # [(t, frame), ...] oldest -> newest
    raw_prev = None
    prev_change_t = time.perf_counter()
    recent_interval = INTERP_LAG  # EMA of time between raw changes (s)
    samp_since_park = 0
    next_out = time.perf_counter()
    last_sent = None
    play_fps = FPS               # EMA of AE's playback rate (frames/s) while playing
    extrap_until = 0.0           # wall-time deadline: extrapolate FORWARD until this
                                 # instant (set on a loop wrap), so we don't sit on the
                                 # post-wrap frame waiting for the next sparse sample.
    loop_hi = None               # learned loop OUT frame (value just before a wrap)
    loop_lo = None               # learned loop IN  frame (value just after a wrap)
    seen_min = None              # min/max frames actually observed during this play
    seen_max = None              # run (reset on a park) -> robust loop bounds

    def sample_at(T):
        """AE's frame at wall-time T, interpolated between bracketing samples."""
        if not history:
            return None
        if T <= history[0][0]:
            return history[0][1]
        for i in range(len(history) - 1):
            a_t, a_f = history[i]
            b_t, b_f = history[i + 1]
            if a_t <= T < b_t:
                span = b_t - a_t
                if span <= 0:
                    return b_f
                # Only a LARGE backward drop (~the whole loop range) is a loop wrap.
                # A small backward step is just a backward SCRUB and MUST interpolate
                # normally - modelling it as a wrap folds it into a wild spike.
                lo = seen_min if seen_min is not None else b_f
                hi = seen_max if seen_max is not None else a_f
                rng = hi - lo
                if rng > 8.0 and (a_f - b_f) > rng * 0.5:
                    # AE looped somewhere INSIDE this segment - we can't know where,
                    # so MODEL the true motion: keep going forward from a_f and wrap
                    # at the loop bounds. Unwrapping b_f above a_f makes the line
                    # monotonic, so it joins a_f at a_t and b_f at b_t with the wrap
                    # happening mid-segment (no discontinuity at either end).
                    target = b_f + rng                       # unwrap b_f above a_f
                    est = a_f + (target - a_f) * ((T - a_t) / span)
                    while est >= hi:
                        est -= rng                           # fold back into [lo, hi)
                    return est if est > 0.0 else 0.0
                return a_f + (b_f - a_f) * ((T - a_t) / span)
        # T beyond the last sample. Normally HOLD (clean stop). But right after a
        # loop wrap the next sample is ~one sparse interval away, and holding the
        # post-wrap frame is exactly the "freeze dopo" the restart. While inside
        # the post-wrap window, climb FORWARD from the last frame at the measured
        # play rate, capped at ~one expected interval so we never overshoot far.
        last_t, last_f = history[-1]
        if now < extrap_until:
            extra = play_fps * (T - last_t)
            cap = play_fps * max(recent_interval, 0.05) * 1.5
            if extra < 0.0:
                extra = 0.0
            elif extra > cap:
                extra = cap
            return last_f + extra
        return last_f                        # T beyond last sample -> hold (stop/gap)

    while True:
        now = time.perf_counter()
        try:
            text = ctrl.Name
        except Exception:                       # stale ref -> re-find
            ae = find_ae_window()
            ctrl = find_timecode_control(ae) if ae else None
            text = None
        f = parse_frame(text) if text else None

        if f is not None and f != raw_prev:
            dt = now - prev_change_t
            df = (f - raw_prev) if raw_prev is not None else 0
            if dt > 0.6:                     # fresh motion after a park
                recent_interval = 0.03       # start low-lag until we know the cadence
                samp_since_park = 0
                seen_min = float(f)          # forget stale bounds from a prior run
                seen_max = float(f)
            else:
                samp_since_park += 1
                if samp_since_park == 1:
                    recent_interval = dt      # first real interval: scrub (dense) vs play (sparse)
                else:
                    recent_interval = recent_interval * 0.5 + dt * 0.5
            # Observed loop bounds (robust to which exact frame each loop samples).
            if seen_max is None or f > seen_max: seen_max = float(f)
            if seen_min is None or f < seen_min: seen_min = float(f)

            # Classify the change. Three cases must behave differently:
            #  - play step  : small forward increment -> interpolate (smooth play);
            #  - loop WRAP  : backward by ~one loop length during play -> model it;
            #  - SEEK       : the user clicked elsewhere on the timeline -> a DIRECT
            #                 jump that must NOT be swept/interpolated.
            # A seek is any discontinuity too big to be a play step that is also not
            # a loop wrap. play_step caps dt so a long pause before the click doesn't
            # inflate the "expected" motion and hide the jump.
            play_step = play_fps * min(dt, 0.4)
            rng = (seen_max - seen_min) if (seen_max is not None and seen_min is not None) else 0.0
            looks_like_wrap = (df < -2.0 and rng > 8.0 and samp_since_park >= 2
                               and abs(df) >= rng * 0.5)
            is_seek = (abs(df) > play_step + 10.0) and not looks_like_wrap

            if is_seek:
                # Direct jump: reset history to JUST this sample so sample_at returns
                # it immediately (no sweep from the old position), and cancel any
                # pending loop extrapolation.
                extrap_until = 0.0
                history.clear()
                history.append((now, float(f)))
            else:
                # Track AE's forward play rate (frames/s); skip on jumps so a seek
                # can't corrupt the rate estimate.
                if df > 0 and 0.10 < dt < 0.5:   # play cadence only (skip dense scrub)
                    inst = df / dt
                    if 1.0 <= inst <= 240.0:
                        play_fps = play_fps * 0.5 + inst * 0.5
                if looks_like_wrap:
                    extrap_until = now + max(recent_interval, 0.05) * 1.6
                    loop_hi = float(raw_prev)        # learn the loop range so the NEXT
                    loop_lo = float(f)               # wrap can be predicted, not just reacted to
                history.append((now, float(f)))
                if len(history) > 8:
                    del history[0]
            prev_change_t = now
            raw_prev = f

        if now >= next_out:
            next_out = now + out_period
            # Adaptive lag, two regimes:
            #  - dense samples (scrubbing) -> minimal lag, basically realtime;
            #  - sparse samples (playback)  -> full lag, smooth + clean stop.
            if recent_interval < 0.10:
                eff_lag = recent_interval * 0.25     # scrub: track the hand
            else:
                eff_lag = min(INTERP_LAG, recent_interval * 1.2)
            est = sample_at(now - eff_lag)
            if est is not None and (last_sent is None or abs(est - last_sent) > 0.001):
                last_sent = est
                sock.sendto(osc_playhead_message(est), (TD_HOST, TD_PORT))
                print(f"\rframe {est:8.2f} ", end="", flush=True)

        time.sleep(0.002)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--fps", type=float)
    ap.add_argument("--port", type=int)
    args = ap.parse_args()
    if args.fps:
        FPS = args.fps
    if args.port:
        TD_PORT = args.port
    if args.probe:
        probe()
    else:
        run()
