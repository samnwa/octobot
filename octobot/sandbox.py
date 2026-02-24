import io
import sys
import signal
import traceback


SAFE_BUILTINS = {
    "len": len,
    "range": range,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "frozenset": frozenset,
    "enumerate": enumerate,
    "zip": zip,
    "sorted": sorted,
    "reversed": reversed,
    "min": min,
    "max": max,
    "sum": sum,
    "any": any,
    "all": all,
    "abs": abs,
    "round": round,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "type": type,
    "hasattr": hasattr,
    "getattr": getattr,
    "setattr": setattr,
    "repr": repr,
    "hash": hash,
    "map": map,
    "filter": filter,
    "True": True,
    "False": False,
    "None": None,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "StopIteration": StopIteration,
}

BLOCKED_PATTERNS = [
    "__import__",
    "import ",
    "from ",
    "exec(",
    "eval(",
    "compile(",
    "open(",
    "globals(",
    "locals(",
    "__builtins__",
    "__subclasses__",
    "__bases__",
    "__mro__",
    "os.system",
    "os.popen",
    "subprocess",
    "shutil.rmtree",
]

SANDBOX_TIMEOUT = 30


class SandboxTimeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise SandboxTimeout("Code execution timed out (30s limit)")


def _wrap_tool_handler(handler_func):
    def wrapper(**kwargs):
        return handler_func(kwargs)
    return wrapper


def _check_code_safety(code):
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            return False, f"Blocked pattern detected: '{pattern}'"
    return True, ""


def execute_code(code, tool_handlers):
    safe, reason = _check_code_safety(code)
    if not safe:
        return {"error": reason}

    namespace = {"__builtins__": {}}
    namespace.update(SAFE_BUILTINS)

    namespace["print"] = None
    captured_output = io.StringIO()

    for tool_name, handler_func in tool_handlers.items():
        namespace[tool_name] = _wrap_tool_handler(handler_func)

    def safe_print(*args, **kwargs):
        kwargs.pop("file", None)
        kwargs.pop("flush", None)
        print(*args, file=captured_output, **kwargs)

    namespace["print"] = safe_print

    old_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(SANDBOX_TIMEOUT)

    try:
        exec(code, namespace)

        output = captured_output.getvalue()
        if len(output) > 50000:
            output = output[:50000] + "\n... [truncated]"

        return {"output": output if output else "(no output)", "status": "ok"}

    except SandboxTimeout:
        return {"error": "Code execution timed out (30s limit)"}
    except Exception as e:
        tb = traceback.format_exc()
        lines = tb.split("\n")
        relevant = [l for l in lines if not l.strip().startswith("File \"<") or "sandbox" not in l]
        return {"error": f"{type(e).__name__}: {e}", "traceback": "\n".join(relevant[-5:])}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        captured_output.close()
