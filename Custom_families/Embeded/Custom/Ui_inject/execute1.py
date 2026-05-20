"""
Execute DAT — initial trigger for Custom_operators_watcher.

Make sure `Start` and `Create` toggles are enabled on this Execute DAT.

The sibling DAT `Custom_operators_watcher` exposes an `Update()` method
that rebuilds the `Custom_operator_list` table from the family's
Custom_operators COMP. Custom_operators_watcher is event-driven (OP
Execute DAT), so it only fires on structural changes after first cook —
but the very first table population isn't guaranteed by any event when
the project opens or when the family is freshly installed. This DAT
guarantees that initial population by calling `Update()` once on the
two startup hooks:

- `onCreate`:  fires when this Execute DAT itself is created (i.e. the
               first time the family COMP is loaded into the project).
- `onStart`:   fires every time the project starts.

The call is idempotent: `Update()` clears and rewrites the target
table, so calling it twice in a row is harmless.
"""

WATCHER_NAME = 'Custom_operators_watcher'


def _trigger_initial_update():
    """Look up the sibling watcher DAT and ask it to refresh the table."""
    try:
        watcher = me.parent().op(WATCHER_NAME)
    except Exception:
        watcher = None
    if watcher is None:
        return
    try:
        watcher.module.Update()
    except Exception:
        # If Update() isn't available (older watcher version), try the
        # legacy alias rebuild().
        try:
            watcher.module.rebuild()
        except Exception:
            pass


def onStart():
    _trigger_initial_update()


def onCreate():
    _trigger_initial_update()


def onExit():
    return


def onFrameStart(frame: int):
    return


def onFrameEnd(frame: int):
    return


def onPlayStateChange(state: bool):
    return


def onDeviceChange():
    return


def onProjectPreSave():
    return


def onProjectPostSave():
    return
