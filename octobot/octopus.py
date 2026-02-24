import sys
import threading
import shutil

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

SWIM_FRAMES = [
    [
        "     ___",
        "    /o o\\",
        "   ( =^= )",
        " ~~~\\___/~~~",
        "  ~/~ ~/~ ~/~",
    ],
    [
        "     ___",
        "    /o o\\",
        "   ( =^= )",
        " ~~~\\___/~~~",
        " ~/~ ~/~ ~/~ ",
    ],
    [
        "     ___",
        "    /o o\\",
        "   ( =^= )",
        " ~~~\\___/~~~",
        "~ ~/~ ~/~ ~/~",
    ],
]

SPRITE_HEIGHT = 5
SPRITE_WIDTH = 14

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


def _swim_loop():
    term_width = shutil.get_terminal_size((80, 24)).columns
    pos = -SPRITE_WIDTH
    frame_idx = 0

    sys.stdout.write("\033[?25l")
    for _ in range(SPRITE_HEIGHT):
        sys.stdout.write("\n")
    sys.stdout.flush()

    while not _stop_event.is_set():
        frame = SWIM_FRAMES[frame_idx % len(SWIM_FRAMES)]
        frame_idx += 1

        sys.stdout.write(f"\033[{SPRITE_HEIGHT}A")

        for line in frame:
            if pos >= 0:
                padded = " " * pos + line
            else:
                clip = -pos
                if clip < len(line):
                    padded = line[clip:]
                else:
                    padded = ""

            padded = padded[:term_width]
            sys.stdout.write(f"\r{padded}\033[K\n")

        sys.stdout.flush()

        pos += 1
        if pos > term_width:
            pos = -SPRITE_WIDTH
            term_width = shutil.get_terminal_size((80, 24)).columns

        _stop_event.wait(0.15)


def start_swimming():
    global _swim_thread
    if not is_awake():
        return
    with _lock:
        if _swim_thread is not None and _swim_thread.is_alive():
            return
        _stop_event.clear()
        _swim_thread = threading.Thread(target=_swim_loop, daemon=True)
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

    sys.stdout.write(f"\033[{SPRITE_HEIGHT}A")
    for _ in range(SPRITE_HEIGHT):
        sys.stdout.write(f"\r\033[K\n")
    sys.stdout.write(f"\033[{SPRITE_HEIGHT}A")

    sys.stdout.write("\033[?25h")
    sys.stdout.flush()
