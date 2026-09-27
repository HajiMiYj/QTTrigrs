"""集中式日志捕获：Python ``print`` 与 Fortran ``write(*,*)`` 统一进入缓冲区。

背景
----
TopoIndex 的 f2py 内核（官方产物）内部用 ``write(*,*)`` 往控制台打印，
这个输出走的是 C 运行时 stdout（fd 1），``redirect_stdout`` 拦不住它。
本模块在**后台线程**里把 fd 1/2 重定向到临时文件，把 Fortran 输出也接进来，
和 Python 的 print 一起进入同一个缓冲区；运行结束后一次性 flush 并落盘，
不再每个函数各处理各的日志。

用法::

    capture = LogCapture(on_line=queue.put)
    capture.redirect_fd()
    try:
        with redirect_stdout(capture), redirect_stderr(capture):
            run(...)
    finally:
        capture.restore_fd()
    text = capture.getvalue()
"""
from __future__ import annotations

import io
import os
import sys
import tempfile


class LogCapture:
    """把控制台输出捕获到一个字符串缓冲区。"""

    def __init__(self, on_line=None):
        self._buffer = io.StringIO()
        self._on_line = on_line
        self._line_buf = ""
        self._fd = None
        self._fd_path = None
        self._saved = []

    # ------------------------------------------------------- redirect_stdout 接口
    def write(self, text: str) -> int:
        text = "" if text is None else str(text)
        if text:
            self._buffer.write(text)
            if self._on_line is not None:
                self._line_buf += text
                while "\n" in self._line_buf:
                    line, self._line_buf = self._line_buf.split("\n", 1)
                    self._on_line(line)
        return len(text)

    def flush(self) -> None:
        if self._on_line is not None and self._line_buf:
            self._on_line(self._line_buf)
            self._line_buf = ""

    # ------------------------------------------------------- fd 重定向（Fortran write）
    def redirect_fd(self) -> None:
        """把 fd 1/2 重定向到临时文件，捕获 Fortran 的 write(*,*)。"""
        if os.name != "nt" or not hasattr(os, "dup2"):
            return
        try:
            fd, path = tempfile.mkstemp(prefix="qtqtgrs_", suffix=".log")
            self._fd = fd
            self._fd_path = path
            self._saved = [os.dup(1), os.dup(2)]
            os.dup2(fd, 1)
            os.dup2(fd, 2)
        except OSError:
            self._saved = []
            if self._fd is not None:
                try:
                    os.close(self._fd)
                except OSError:
                    pass
                self._fd = None

    def restore_fd(self) -> None:
        """恢复 fd 1/2，并把临时文件里捕获的 Fortran 输出合并回缓冲区。"""
        if not self._saved:
            return
        try:
            # 先刷新 C 运行时 + Python 的缓冲，确保内容写到临时文件
            try:
                import ctypes
                ctypes.CDLL("msvcrt").fflush(None)
            except Exception:
                pass
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception:
                pass
        except Exception:
            pass

        try:
            for idx, saved in enumerate(self._saved):
                os.dup2(saved, 1 + idx)
                os.close(saved)
        except Exception:
            pass
        self._saved = []

        try:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            if self._fd_path and os.path.exists(self._fd_path):
                with open(self._fd_path, "rb") as fh:
                    content = fh.read().decode("utf-8", "replace")
                if content:
                    self._buffer.write(content)
                    if self._on_line is not None:
                        for line in content.splitlines():
                            self._on_line(line)
                try:
                    os.unlink(self._fd_path)
                except OSError:
                    pass
        except Exception:
            pass
        self._fd_path = None

    def getvalue(self) -> str:
        return self._buffer.getvalue()
