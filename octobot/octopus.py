import threading

from rich.text import Text
from rich.live import Live
from rich.console import Console

from .config import load_config, save_config

OCTOPUS_FULL = """\
⠀⠀⠀⠀⠀⠀⢀⣀⣠⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣷⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⠀⠀⠀⣠⣶⣾⣷⣶⣄⠀⠀⠀⠀⠀
⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⠀⠀⢰⣿⠟⠉⠻⣿⣿⣷⠀⠀⠀⠀
⠀⠀⠀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⢷⣄⠘⠿⠀⠀⠀⢸⣿⣿⡆⠀⠀⠀
⠀⠀⠀⠀⠈⠿⣿⣿⣿⣿⣿⣀⣸⣿⣷⣤⣴⠟⠀⠀⠀⠀⢀⣼⣿⣿⠁⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠈⠙⣛⣿⣿⣿⣿⣿⣿⣿⣿⣦⣀⣀⣀⣴⣾⣿⣿⡟⠀⠀⠀⠀
⠀⠀⠀⢀⣠⣴⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⠋⣠⣤⣀⠀⠀
⠀⠀⣴⣿⣿⣿⠿⠟⠛⠛⢛⣿⣿⣿⣿⣿⣿⣧⡈⠉⠁⠀⠀⠀⠈⠉⢻⣿⣧⠀
⠀⣼⣿⣿⠋⠀⠀⠀⠀⢠⣾⣿⣿⠟⠉⠻⣿⣿⣿⣦⣄⠀⠀⠀⠀⠀⣸⣿⣿⠃
⠀⣿⣿⡇⠀⠀⠀⠀⠀⣿⣿⡿⠃⠀⠀⠀⠈⠛⢿⣿⣿⣿⣿⣶⣿⣿⣿⡿⠋⠀
⠀⢿⣿⣧⡀⠀⣶⣄⠘⣿⣿⡇⠀⠀⠠⠶⣿⣶⡄⠈⠙⠛⠻⠟⠛⠛⠁⠀⠀⠀
⠀⠈⠻⣿⣿⣿⣿⠏⠀⢻⣿⣿⣄⠀⠀⠀⣸⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⣿⣿⣿⣶⣾⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠛⠛⠛⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀"""

COLOR_STEPS = [
    (255, 140, 0),
    (230, 130, 30),
    (200, 120, 60),
    (170, 120, 100),
    (130, 130, 150),
    (90, 150, 200),
    (0, 170, 240),
    (0, 191, 255),
    (0, 170, 240),
    (90, 150, 200),
    (130, 130, 150),
    (170, 120, 100),
    (200, 120, 60),
    (230, 130, 30),
]

_stop_event = threading.Event()
_swim_thread = None
_live = None
_lock = threading.Lock()


def is_awake():
    config = load_config()
    return config.get("octopus_animation", True)


def set_awake(awake):
    config = load_config()
    config["octopus_animation"] = awake
    save_config(config)


def _make_frame(step):
    r, g, b = COLOR_STEPS[step % len(COLOR_STEPS)]
    text = Text(OCTOPUS_FULL)
    text.stylize(f"rgb({r},{g},{b})")
    return text


def _pulse_loop(live):
    step = 0
    while not _stop_event.is_set():
        live.update(_make_frame(step))
        step += 1
        _stop_event.wait(0.25)


def start_swimming():
    global _swim_thread, _live
    if not is_awake():
        return
    with _lock:
        if _swim_thread is not None and _swim_thread.is_alive():
            return
        _stop_event.clear()
        console = Console()
        _live = Live(_make_frame(0), console=console, refresh_per_second=8, transient=True)
        _live.start()
        _swim_thread = threading.Thread(target=_pulse_loop, args=(_live,), daemon=True)
        _swim_thread.start()


def stop_swimming():
    global _swim_thread, _live
    with _lock:
        if _swim_thread is None or not _swim_thread.is_alive():
            _swim_thread = None
            if _live:
                try:
                    _live.stop()
                except Exception:
                    pass
                _live = None
            return
        _stop_event.set()
        _swim_thread.join(timeout=1.0)
        _swim_thread = None
        if _live:
            try:
                _live.stop()
            except Exception:
                pass
            _live = None
