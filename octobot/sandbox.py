import io
import ast
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

BANNED_DUNDER_ATTRS = {
    "__import__", "__builtins__", "__subclasses__", "__bases__", "__mro__",
    "__globals__", "__code__", "__closure__", "__func__", "__self__",
    "__dict__", "__class__", "__module__", "__qualname__",
    "__init_subclass__", "__set_name__", "__del__",
    "__getattr__", "__getattribute__", "__setattr__", "__delattr__",
    "__reduce__", "__reduce_ex__",
}

BANNED_NAMES = {
    "__import__", "eval", "exec", "compile", "open",
    "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "hasattr",
    "type", "super", "classmethod", "staticmethod", "property",
    "breakpoint", "exit", "quit",
    "memoryview", "bytearray", "bytes",
    "__build_class__",
}

SANDBOX_TIMEOUT = 30


class SandboxTimeout(Exception):
    pass


class SandboxSecurityError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise SandboxTimeout("Code execution timed out (30s limit)")


def _validate_ast(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxSecurityError(f"Syntax error: {e}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            raise SandboxSecurityError(f"Import statements are not allowed")

        if isinstance(node, ast.ImportFrom):
            raise SandboxSecurityError(f"Import statements are not allowed")

        if isinstance(node, ast.Attribute):
            attr_name = node.attr
            if attr_name.startswith("__") and attr_name.endswith("__"):
                if attr_name in BANNED_DUNDER_ATTRS:
                    raise SandboxSecurityError(f"Access to '{attr_name}' is not allowed")
            if attr_name in ("system", "popen", "call", "Popen", "check_output", "check_call"):
                raise SandboxSecurityError(f"Access to '{attr_name}' is not allowed")
            if attr_name in ("rmtree", "move"):
                raise SandboxSecurityError(f"Access to '{attr_name}' is not allowed")

        if isinstance(node, ast.Name):
            if node.id in BANNED_NAMES:
                raise SandboxSecurityError(f"Use of '{node.id}' is not allowed")

        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in BANNED_NAMES:
                raise SandboxSecurityError(f"Calling '{func.id}' is not allowed")


def _wrap_tool_handler(handler_func):
    def wrapper(**kwargs):
        return handler_func(kwargs)

    wrapper.__name__ = getattr(handler_func, '__name__', 'tool')
    wrapper.__doc__ = None
    wrapper.__globals__ = {}
    wrapper.__module__ = None
    return wrapper


class _SafeToolWrapper:
    __slots__ = ('_fn',)

    def __init__(self, fn):
        object.__setattr__(self, '_fn', fn)

    def __call__(self, **kwargs):
        return object.__getattribute__(self, '_fn')(kwargs)

    def __repr__(self):
        return f"<tool>"

    def __getattr__(self, name):
        raise SandboxSecurityError(f"Cannot access attributes on tool functions")


def execute_code(code, tool_handlers):
    try:
        _validate_ast(code)
    except SandboxSecurityError as e:
        return {"error": f"Security violation: {e}"}

    namespace = {"__builtins__": {}}
    namespace.update(SAFE_BUILTINS)

    captured_output = io.StringIO()

    def safe_print(*args, **kwargs):
        kwargs.pop("file", None)
        kwargs.pop("flush", None)
        print(*args, file=captured_output, **kwargs)

    namespace["print"] = safe_print

    for tool_name, handler_func in tool_handlers.items():
        namespace[tool_name] = _SafeToolWrapper(handler_func)

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
    except SandboxSecurityError as e:
        return {"error": f"Security violation: {e}"}
    except Exception as e:
        tb = traceback.format_exc()
        lines = tb.split("\n")
        relevant = [l for l in lines if not l.strip().startswith("File \"<") or "sandbox" not in l]
        return {"error": f"{type(e).__name__}: {e}", "traceback": "\n".join(relevant[-5:])}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        captured_output.close()
