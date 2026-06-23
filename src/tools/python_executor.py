"""
Python 代码安全执行工具
用于在沙箱环境中安全执行学生提交的 Python 代码，
捕获标准输出和错误信息，返回执行结果。
支持预设 stdin 输入以模拟 input() 交互。
"""
import subprocess
import tempfile
import os
from langchain.tools import tool


# 安全限制：禁止导入的危险模块
_BLOCKED_MODULES = {
    "os", "subprocess", "sys", "shutil", "socket", "http",
    "urllib", "requests", "ftplib", "telnetlib", "smtplib",
    "ctypes", "multiprocessing", "signal", "importlib",
    "pdb", "code", "compile", "exec", "eval", "__import__",
    "open", "breakpoint",
}

# 执行超时时间（秒）
_EXECUTION_TIMEOUT = 10

# 安全代码前缀：在用户代码前注入，限制危险操作
_SAFETY_PREAMBLE = """
import builtins
_original_import = builtins.__import__
def _safe_import(name, *args, **kwargs):
    blocked = {_blocked}
    top_level = name.split('.')[0]
    if top_level in blocked:
        raise ImportError(f"为了安全，不允许导入模块: {{name}}")
    return _original_import(name, *args, **kwargs)
builtins.__import__ = _safe_import
""".replace("{_blocked}", repr(_BLOCKED_MODULES))

# 常见错误的友好解释映射
_FRIENDLY_ERRORS = {
    "NameError": "你使用了一个还没有定义的名字。就像你想拿一个还没放进盒子的玩具——先创建变量再使用它哦！",
    "TypeError": "你把不同类型的数据混在一起用了。比如把数字和文字直接相加，Python 不知道该怎么做。",
    "SyntaxError": "你的代码语法有误，可能是少了括号、引号没配对，或者缩进不对。仔细检查一下标点符号吧！",
    "IndentationError": "Python 很在意代码前面的空格（缩进）。if、for、def 后面的代码需要统一空 4 个空格哦！",
    "ZeroDivisionError": "数学里不能除以 0，Python 也不行！检查一下除数是不是变成 0 了。",
    "ValueError": "你给的数据类型是对的，但内容不对。比如想把 'abc' 转成数字 int('abc') 就不行。",
    "IndexError": "你访问了列表里不存在的位置。记住列表索引从 0 开始，最后一个位置是 len(列表)-1。",
    "KeyError": "你查找的键在字典里不存在。就像你翻字典查一个不存在的词。先确认键名拼写对不对。",
    "AttributeError": "你对一个东西做了它不会的操作。比如让数字去 .lower() 就不行，那是字符串才有的方法。",
    "ImportError": "你想导入的模块不存在或被禁止了。检查一下模块名拼写是否正确。",
    "FileNotFoundError": "你想打开的文件不存在。检查文件路径和文件名是否正确。",
}


def _get_friendly_error(stderr_text: str) -> str:
    """从 stderr 中提取错误类型并返回友好解释"""
    for err_type, explanation in _FRIENDLY_ERRORS.items():
        if err_type in stderr_text:
            return explanation
    return ""


def run_python_code(code: str, stdin_input: str = "") -> dict:
    """核心执行逻辑（普通函数，供 tool 和 API 共用）。
    
    返回:
        {"success": bool, "output": str, "error": str, "friendly_error": str}
    """
    if not code or not code.strip():
        return {"success": False, "output": "", "error": "代码不能为空", "friendly_error": ""}

    full_code = _SAFETY_PREAMBLE + "\n" + code

    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write(full_code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True,
                text=True,
                timeout=_EXECUTION_TIMEOUT,
                input=stdin_input if stdin_input else None,
                env={"PATH": os.environ.get("PATH", "/usr/bin"), "HOME": "/tmp"},
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            # 过滤安全前缀相关的 traceback 行
            stderr_lines = stderr.split('\n')
            filtered_stderr = []
            skip = False
            for line in stderr_lines:
                if '_safe_import' in line or '_SAFETY_PREAMBLE' in line:
                    skip = True
                    continue
                if skip:
                    if line.strip() == '' or not line.startswith('  '):
                        skip = False
                    else:
                        continue
                filtered_stderr.append(line)
            clean_stderr = '\n'.join(filtered_stderr).strip()

            friendly = _get_friendly_error(clean_stderr) if clean_stderr else ""

            return {
                "success": not bool(clean_stderr),
                "output": stdout,
                "error": clean_stderr,
                "friendly_error": friendly,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"代码执行超时（超过 {_EXECUTION_TIMEOUT} 秒）",
                "friendly_error": "请检查代码中是否有死循环（比如 while True 但没有 break）或过于耗时的操作。",
            }

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    except Exception as e:
        return {"success": False, "output": "", "error": str(e), "friendly_error": ""}


@tool
def execute_python_code(code: str, stdin_input: str = "") -> str:
    """安全执行学生提交的 Python 代码，返回执行结果（标准输出）或错误信息。
    支持通过 stdin_input 参数预设 input() 的输入值。
    
    参数:
        code: 学生提交的 Python 代码字符串
        stdin_input: 可选，如果代码中有 input() 调用，这里提供预设的输入值（多个输入用换行分隔）
    
    返回:
        包含执行结果或错误信息的字符串
    """
    result = run_python_code(code, stdin_input)

    output_parts = []
    if result["output"]:
        output_parts.append(f"📤 程序输出：\n{result['output']}")
    if result["error"]:
        output_parts.append(f"⚠️ 错误信息：\n{result['error']}")
        if result["friendly_error"]:
            output_parts.append(f"\n💡 错误解释：{result['friendly_error']}")
    if not output_parts:
        output_parts.append("✅ 代码执行完成，没有输出内容。")

    return '\n\n'.join(output_parts)
