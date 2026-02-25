import sys
import threading
import time

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

OCTOPUS_LINES = OCTOPUS_FULL.split("\n")
OCTOPUS_HEIGHT = len(OCTOPUS_LINES)

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
_lock = threading.Lock()


def is_awake():
    config = load_config()
    return config.get("octopus_animation", True)


def set_awake(awake):
    config = load_config()
    config["octopus_animation"] = awake
    save_config(config)


def _color_text(text, r, g, b):
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m"


def _pulse_loop():
    sys.stdout.write("\033[?25l")
    for _ in range(OCTOPUS_HEIGHT):
        sys.stdout.write("\n")
    sys.stdout.flush()

    step = 0
    while not _stop_event.is_set():
        r, g, b = COLOR_STEPS[step % len(COLOR_STEPS)]
        step += 1

        sys.stdout.write(f"\033[{OCTOPUS_HEIGHT}A")
        for line in OCTOPUS_LINES:
            colored = _color_text(line, r, g, b)
            sys.stdout.write(f"\r{colored}\033[K\n")
        sys.stdout.flush()

        _stop_event.wait(0.25)


def start_swimming():
    global _swim_thread
    if not is_awake():
        return
    with _lock:
        if _swim_thread is not None and _swim_thread.is_alive():
            return
        _stop_event.clear()
        _swim_thread = threading.Thread(target=_pulse_loop, daemon=True)
        _swim_thread.start()


def stop_swimming():
    global _swim_thread
    with _lock:
        if _swim_thread is None or not _swim_thread.is_alive():
            _swim_thread = None
            return
        _stop_event.set()
        _swim_thread.join(timeout=1.0)
        _swim_thread = None

    sys.stdout.write(f"\033[{OCTOPUS_HEIGHT}A")
    for _ in range(OCTOPUS_HEIGHT):
        sys.stdout.write(f"\r\033[K\n")
    sys.stdout.write(f"\033[{OCTOPUS_HEIGHT}A")

    sys.stdout.write("\033[?25h")
    sys.stdout.flush()
