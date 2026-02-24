import re
from rich.console import Console
from rich.panel import Panel

console = Console()

DANGEROUS_COMMAND_PATTERNS = [
    (r'\brm\s+(-[^\s]*)?r', "Recursive file deletion"),
    (r'\bsudo\b', "Elevated privileges (sudo)"),
    (r'\bchmod\s+777\b', "World-writable permissions"),
    (r'>\s*/dev/', "Writing to device file"),
    (r'\bmkfs\b', "Filesystem formatting"),
    (r'\bdd\s+if=', "Raw disk operation (dd)"),
    (r':\(\)\s*\{', "Fork bomb pattern"),
    (r'\bkill\s+-9\b', "Force kill process"),
    (r'\bshutdown\b', "System shutdown"),
    (r'\breboot\b', "System reboot"),
    (r'\bcurl\b.*\|\s*(ba)?sh', "Piping remote script to shell"),
    (r'\bwget\b.*\|\s*(ba)?sh', "Piping remote script to shell"),
    (r'>\s*/etc/', "Writing to system config"),
    (r'\bgit\s+push\s+.*--force', "Force push to remote"),
    (r'\bgit\s+reset\s+--hard', "Hard reset (destructive)"),
    (r'\btruncate\b', "File truncation"),
    (r'\bnpm\s+publish\b', "Publishing package to npm"),
    (r'\bpip\s+install\b.*--break-system', "Breaking system packages"),
]

SENSITIVE_WRITE_PATHS = [
    r'\.bashrc$', r'\.bash_profile$', r'\.zshrc$', r'\.profile$',
    r'\.ssh/', r'\.gnupg/', r'\.env$', r'\.gitconfig$',
    r'/etc/', r'/usr/', r'/bin/', r'/sbin/',
]

SENSITIVE_OVERWRITE_PATTERNS = [
    r'\.env$', r'\.env\.local$', r'\.env\.production$',
    r'id_rsa', r'id_ed25519', r'\.pem$', r'\.key$',
]


def _check_sensitive_path(path):
    for pattern in SENSITIVE_WRITE_PATHS:
        if re.search(pattern, path):
            return True, f"Modifying sensitive path: {path}"
    for pattern in SENSITIVE_OVERWRITE_PATTERNS:
        if re.search(pattern, path):
            return True, f"Modifying sensitive file: {path}"
    return False, ""


def check_approval(tool_name, tool_input):
    if tool_name == "run_command":
        command = tool_input.get("command", "")
        for pattern, reason in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, command):
                return True, f"Dangerous command detected: {reason}"
        return False, ""

    if tool_name in ("write_file", "edit_file"):
        path = tool_input.get("path", "")
        return _check_sensitive_path(path)

    if tool_name == "apply_patch":
        patch = tool_input.get("patch", "")
        for line in patch.split("\n"):
            if line.startswith("+++ "):
                path = line[4:].strip()
                if path.startswith("b/"):
                    path = path[2:]
                is_sensitive, reason = _check_sensitive_path(path)
                if is_sensitive:
                    return True, reason
        return False, ""

    return False, ""


def prompt_approval(tool_name, tool_input, reason):
    detail = ""
    if tool_name == "run_command":
        detail = tool_input.get("command", "")
    elif tool_name in ("write_file", "edit_file"):
        detail = tool_input.get("path", "")
    elif tool_name == "apply_patch":
        detail = "(patch content)"

    content = f"[bold yellow]Reason:[/bold yellow] {reason}\n"
    content += f"[bold yellow]Tool:[/bold yellow] {tool_name}\n"
    if detail:
        content += f"[bold yellow]Detail:[/bold yellow] {detail}"

    console.print(
        Panel(
            content,
            title="[bold red]Approval Required[/bold red]",
            border_style="red",
        )
    )

    try:
        console.print("[bold]Allow this operation? [Y/n]:[/bold] ", end="")
        answer = input().strip().lower()
        return answer in ("", "y", "yes")
    except (KeyboardInterrupt, EOFError):
        console.print()
        return False
