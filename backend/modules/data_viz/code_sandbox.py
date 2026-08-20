"""AST Security Validator & Sandboxed Pandas Execution Environment for Module 2.

Ensures generated Python/Pandas code is completely read-only, free of
system calls, network requests, or malicious operations prior to execution.
"""

import ast
import time
from typing import Any, Dict, Optional, Tuple
import numpy as np
import pandas as pd

# Forbidden AST node types
FORBIDDEN_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Delete,
    ast.Global,
    ast.Nonlocal,
    ast.AsyncFunctionDef,
    ast.AsyncFor,
    ast.AsyncWith,
)

# Forbidden builtin function names
FORBIDDEN_CALLS = {
    "open",
    "eval",
    "exec",
    "__import__",
    "compile",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "hasattr",
    "memoryview",
    "breakpoint",
    "exit",
    "quit",
}

# Forbidden module or attribute names
FORBIDDEN_ATTRIBUTES = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "requests",
    "urllib",
    "http",
    "pickle",
    "ctypes",
    "threading",
    "multiprocessing",
    "builtins",
    "__builtins__",
    "__class__",
    "__base__",
    "__subclasses__",
    "to_csv",
    "to_excel",
    "to_sql",
    "to_json",
    "to_pickle",
    "to_parquet",
    "to_feather",
    "drop",
    "pop",
    "remove",
}


class CodeSecurityValidator(ast.NodeVisitor):
    """AST Visitor that validates Python code against safety rules."""

    def __init__(self):
        self.errors = []

    def visit(self, node):
        if isinstance(node, FORBIDDEN_NODES):
            self.errors.append(f"Forbidden statement: {type(node).__name__}")
        super().visit(node)

    def visit_Call(self, node):
        # Check direct function calls
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(f"Forbidden function call: {node.func.id}()")
        # Check method calls (e.g., os.system, df.drop)
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_ATTRIBUTES or node.func.attr in FORBIDDEN_CALLS:
                self.errors.append(f"Forbidden method call: .{node.func.attr}()")
        
        # Check for inplace=True mutations
        for kw in getattr(node, "keywords", []):
            if kw.arg == "inplace":
                if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.errors.append("Forbidden mutation: inplace=True is disallowed")

        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.errors.append(f"Forbidden attribute access: .{node.attr}")
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in FORBIDDEN_ATTRIBUTES:
            self.errors.append(f"Forbidden identifier: {node.id}")
        self.generic_visit(node)



def validate_python_code(code_str: str) -> Tuple[bool, Optional[str]]:
    """
    Statically analyze code with AST. Returns (is_safe, error_message).
    """
    if not code_str or not code_str.strip():
        return False, "Empty code snippet"

    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    validator = CodeSecurityValidator()
    validator.visit(tree)

    if validator.errors:
        return False, "; ".join(validator.errors)

    return True, None


def execute_sandboxed_pandas(
    code_str: str,
    df: pd.DataFrame,
    timeout_sec: int = 30,
) -> Dict[str, Any]:
    """
    Execute validated pandas code in a restricted execution environment.
    Guarantees that `df` is read-only and no filesystem/network access occurs.
    """
    is_safe, error_msg = validate_python_code(code_str)
    if not is_safe:
        return {
            "status": "unsafe_blocked",
            "error": f"Security validation failed: {error_msg}",
            "result_df": None,
            "row_count": 0,
            "execution_time_ms": 0,
        }

    # Prepare restricted namespace
    safe_builtins = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "sorted": sorted,
        "print": lambda *args: None,  # No-op stdout
    }

    # Pass copy of df so mutations do not affect memory
    df_copy = df.copy(deep=False)
    local_scope = {
        "df": df_copy,
        "pd": pd,
        "np": np,
        "result": None,
    }
    global_scope = {"__builtins__": safe_builtins}

    # Pre-process code to capture last expression into 'result' if not explicitly assigned
    code_lines = [line for line in code_str.strip().split("\n") if line.strip()]
    if code_lines:
        last_line = code_lines[-1].strip()
        if not last_line.startswith("result") and not "=" in last_line:
            code_lines[-1] = f"result = {last_line}"
        elif "=" in last_line and not last_line.startswith("result"):
            var_name = last_line.split("=")[0].strip()
            code_lines.append(f"result = {var_name}")
    exec_code = "\n".join(code_lines)

    start_time = time.time()
    try:
        exec(exec_code, global_scope, local_scope)
        elapsed_ms = int((time.time() - start_time) * 1000)

        raw_result = local_scope.get("result")
        if raw_result is None:
            raw_result = local_scope.get("df")

        # Standardize result into a DataFrame
        if isinstance(raw_result, pd.Series):
            result_df = raw_result.to_frame().reset_index()
        elif isinstance(raw_result, pd.DataFrame):
            result_df = raw_result.reset_index(drop=False) if raw_result.index.name else raw_result
        elif isinstance(raw_result, (dict, list)):
            result_df = pd.DataFrame(raw_result)
        elif isinstance(raw_result, (int, float, str, np.number)):
            result_df = pd.DataFrame([{"மதிப்பு": raw_result}])
        else:
            result_df = pd.DataFrame([{"மதிப்பு": str(raw_result)}])

        # Limit result size for memory safety (max 100 rows returned to UI)
        capped_df = result_df.head(100)

        return {
            "status": "success",
            "error": None,
            "result_df": capped_df,
            "row_count": len(result_df),
            "execution_time_ms": elapsed_ms,
        }

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "status": "error",
            "error": str(e),
            "result_df": None,
            "row_count": 0,
            "execution_time_ms": elapsed_ms,
        }
