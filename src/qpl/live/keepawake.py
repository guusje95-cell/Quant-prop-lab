"""Keep Windows awake while a long job runs, with the screen still allowed to turn off (SetThreadExecutionState with
ES_SYSTEM_REQUIRED, the same mechanism download managers use). No effect on other systems. Released when the process ends."""
import sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def keep_awake(log=print) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        ok = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        if ok:
            log("  (keeping the PC awake while this runs; the screen may turn off)")
        return bool(ok)
    except Exception:
        return False
