"""
QTTrigrs 界面的控制器（纯 PyQt5，无 QGIS 依赖）。

本模块把 ``QTrigrsWindow.ui`` 生成的界面与 :mod:`trigrs` /
:mod:`topoindex` 两个计算内核连接起来。

与原 PyQGIS 版的差异
--------------------
1. **栅格一律从磁盘文件选择**（``RasterPathEdit`` 行编辑 + 浏览按钮），
   不再使用 ``QgsMapLayerComboBox``；降雨强度栅格同样放在表格单元格里。
2. **界面控件与输入文件一一对应**。写出与读回都由
   :mod:`trigrs.TrigrsInputFile` / :mod:`topoindex.TopoIndexInputFile`
   完成，界面本身不拼接任何文件文本，因此界面显示的内容与写入磁盘的内容
   永远一致，且与 USGS 官方 ``tr_in.txt`` / ``tpx_in.txt`` 逐字兼容。
3. **工程文件就是官方输入文件**（``tr_in.txt`` / ``tpx_in.txt``），可直接
   用原版程序打开。文件路径绑定以 ``#`` 注释块附在文件末尾：官方程序会忽略
   它，本模块读回时用它恢复“哪个控件对应哪个文件”。
4. 运行 TRIGRS / TopoIndex 后不再把结果自动载入 QGIS 工程，而是在日志中
   列出生成的文件（TopoIndex 的径流文件仍会自动回填到对应输入框）。
"""
from __future__ import annotations

import contextlib
import os
import queue
import sys
import threading
import traceback
from functools import wraps
from pathlib import Path

from PyQt5.QtCore import Qt, QSignalBlocker, QSize, QTimer
from PyQt5.QtGui import QIcon, QImage, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStyle,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from trigrs.TrigrsInputFile import (
    SOIL_COLUMNS,
    TrigrsInput,
    TrigrsInputError,
    append_annotations,
    build_tr_in,
    looks_like_tr_in,
    parse_annotations,
    parse_tr_in,
    write_tr_in,
)
from trigrs.TrigrsInputFile import validate as validate_trigrs
from topoindex.TopoIndexInputFile import (
    MAX_SUFFIX,
    TopoIndexInput,
    TopoIndexInputError,
    append_annotations as append_topo_annotations,
    build_tpx_in,
    looks_like_tpx_in,
    parse_annotations as parse_topo_annotations,
    parse_tpx_in,
    write_tpx_in,
)
from topoindex.TopoIndexInputFile import validate as validate_topoindex
from log_control import LogCapture
from run_control import StopRequested
from .about_dialog import show_about, show_topoindex_params, show_trigrs_params
from .file_picker import RasterPathEdit
from .QTrigrsTextBrowser import TrigrsTextBrowser
from .QTrigrsWindow import Ui_TrigrsMainWindow

# 下拉框取值，顺序与 .ui 中的条目一一对应
WATER_TABLE_MODES = ("depth", "eleva")
FLOW_DIRS = ("gener", "slope", "hydro")
DEEPWAT_MODES = ("zero", "flow", "hydr", "relh")
FLAG_VALUES = (0, -1, -2, -3, -4, -5, -6, -7, -8, -9)

#: 文件占位控件 -> (文件名标签, 中文名, 归属模块)
#: 归属模块用于分别校验：TopoIndex 只看 DEM 与流向，其余属于 TRIGRS。
#: 控件名与 QTrigrsWindow.ui 中的占位 QWidget 一一对应。
RASTER_LAYER_FIELDS = (
    ("slopeLayerWidget", "slopeLayerFileLabel", "坡度栅格", "trigrs"),
    ("elevLayerWidget", "elevLayerFileLabel", "高程栅格", "trigrs"),
    ("zoneLayerWidget", "zoneLayerFileLabel", "属性分区栅格", "trigrs"),
    ("zmaxLayerWidget", "zmaxLayerFileLabel", "最大深度栅格", "trigrs"),
    ("depthLayerWidget", "depthLayerFileLabel", "地下水位深度栅格", "trigrs"),
    ("rizeroLayerWidget", "rizeroLayerFileLabel", "初始入渗率栅格", "trigrs"),
    ("nxtLayerWidget", "nxtLayerFileLabel", "下游单元编号栅格", "trigrs"),
    ("topoDemLayerWidget", "topoDemLayerFileLabel", "DEM 高程栅格", "topoindex"),
    ("topoDirLayerWidget", "topoDirLayerFileLabel", "流向栅格", "topoindex"),
)

#: TRIGRS 必需栅格（少一个都不能运行）
TRIGRS_REQUIRED_LAYERS = {
    "slopeLayerWidget": "坡度栅格 slofil",
    "elevLayerWidget": "高程栅格 elevfil",
}

#: 可选栅格：给了就用，没给则由对应的标量值兜底
TRIGRS_OPTIONAL_LAYERS = {
    "zoneLayerWidget": "属性分区栅格 zonfil",
    "zmaxLayerWidget": "最大深度栅格 zfil",
    "depthLayerWidget": "地下水位深度栅格 depfil",
    "rizeroLayerWidget": "初始入渗率栅格 rizerofil",
    "nxtLayerWidget": "下游单元编号栅格 nxtfil",
}

#: TopoIndex 必需栅格
TOPOINDEX_REQUIRED_LAYERS = {
    "topoDemLayerWidget": "TopoIndex 的 DEM 栅格",
}


def _project_root() -> Path:
    """
    返回 QTTrigrs 项目根目录（``trigrs`` 包与 ``lib`` 所在的目录）。

    ``ui/trigrs_controller.py`` -> ``ui`` -> 项目根目录。
    """
    return Path(__file__).resolve().parents[1]


def same_path(a: str | os.PathLike, b: str | os.PathLike) -> bool:
    """
    比较两个路径是否指向同一个文件。

    兼容 Windows 正/反斜杠混用、大小写差异以及 8.3 短名，因此官方文件里的
    ``C:/x/y.tif`` 与本机记录的 ``C:\\x\\y.tif`` 能匹配上。
    """
    if not a or not b:
        return False
    pa, pb = Path(str(a)), Path(str(b))
    try:
        if pa.exists() and pb.exists():
            return os.path.samefile(pa, pb)
    except OSError:
        pass
    na = os.path.normcase(os.path.normpath(os.path.abspath(str(pa))))
    nb = os.path.normcase(os.path.normpath(os.path.abspath(str(pb))))
    return na == nb


def resolve_project_path(value: str, base: Path | None) -> str:
    """
    把工程文件里的路径解析成绝对路径。

    官方文件里常见相对路径（``Data/tutorial/slope.asc``），此时按输入文件所在
    目录解析；绝对路径原样返回（只统一分隔符）。
    """
    text = str(value or "").strip()
    if not text:
        return ""
    path = Path(text)
    if path.is_absolute():
        return str(path)
    if base is not None:
        return str(Path(base) / path)
    return str(path)


def _to_float(text: str, label: str, default: float | None = None) -> float:
    text = (text or "").strip()
    if not text:
        if default is not None:
            return default
        raise TrigrsInputError(f"{label} 不能为空")
    try:
        return float(text)
    except ValueError as exc:
        raise TrigrsInputError(f"{label} 不是合法数字：{text!r}") from exc


def _split_floats(text: str, label: str) -> list[float]:
    parts = [p for p in str(text).replace("，", ",").replace(";", ",").split(",") if p.strip()]
    if not parts:
        raise TrigrsInputError(f"{label} 不能为空")
    values = []
    for part in parts:
        try:
            values.append(float(part.strip()))
        except ValueError as exc:
            raise TrigrsInputError(f"{label} 中含有非法数字：{part!r}") from exc
    return values


def _batch_ui_update(method):
    """Do not collect partially rebuilt tables from synchronous Qt callbacks."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        previous = getattr(self, "_updating_ui", False)
        self._updating_ui = True
        try:
            result = method(self, *args, **kwargs)
        finally:
            self._updating_ui = previous
        if not previous:
            self._refresh_trigrs_preview()
            self._refresh_topo_preview()
        return result
    return wrapped


class _QueueSink:
    """把 print 输出按行写入队列，供主线程定时刷新到日志。"""

    def __init__(self, outq: queue.Queue):
        self._q = outq
        self._buf = ""

    def write(self, text: str) -> int:
        if text:
            self._buf += text
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                if line:
                    self._q.put(line)
        return len(text)

    def flush(self) -> None:
        if self._buf:
            self._q.put(self._buf)
            self._buf = ""


class _BasePanel(QMainWindow):
    """公共逻辑：日志、进程内执行、预览文本框、菜单栏与工具栏。"""

    run_title = "计算"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_TrigrsMainWindow()
        container = QWidget()
        self.ui.setupUi(container)
        self.setCentralWidget(container)

        self._worker: threading.Thread | None = None
        self._outq: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._on_finished_cb = None
        self._run_log_text = ""
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)
        self._poll_timer.timeout.connect(self._poll_worker)

        self._log_lines: list[str] = []
        # 日志刷新做节流：计算内核可能每秒产出成百上千行（tqdm 进度条、
        # 逐单元信息），如果每来一块就整篇 setPlainText，界面会把时间全花在
        # 重排重绘上。这里先攒着，由定时器统一刷新。
        self._log_pending: list[str] = []
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(150)
        self._log_timer.setSingleShot(True)
        self._log_timer.timeout.connect(self._flush_log)

        self.trigrs_browser = TrigrsTextBrowser()
        self.trigrs_browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ui.previewTrinLayout.addWidget(self.trigrs_browser)

        self.topo_browser = TrigrsTextBrowser()
        self.topo_browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ui.previewTopoLayout.addWidget(self.topo_browser)

    # ------------------------------------------------------------------ 图标
    def _icon(self, name: str, fallback=None) -> QIcon:
        """加载 ``resources/icons/<name>``，缺失时回退到 Qt 标准图标。"""
        path = _project_root() / "resources" / "icons" / name
        if path.is_file():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
        if fallback is not None:
            return self.style().standardIcon(fallback)
        return QIcon()

    # ------------------------------------------------------------------ 日志
    def log(self, message: str) -> None:
        """把消息加入待显示队列（由定时器节流刷新，避免高频重绘）。"""
        text = "" if message is None else str(message)
        for line in text.splitlines() or [""]:
            self._log_pending.append(line)
        if not self._log_timer.isActive():
            self._log_timer.start()

    def _flush_log(self) -> None:
        if not self._log_pending:
            return
        self._log_lines.extend(self._log_pending)
        self._log_pending = []
        if len(self._log_lines) > 5000:
            self._log_lines = self._log_lines[-5000:]
        self.ui.logPlainTextEdit.setPlainText("\n".join(self._log_lines))
        bar = self.ui.logPlainTextEdit.verticalScrollBar()
        bar.setValue(bar.maximum())

    def log_now(self, message: str) -> None:
        """立即刷新日志（用于少量关键消息，例如开始/结束）。"""
        self.log(message)
        self._flush_log()

    def clear_log(self) -> None:
        self._log_timer.stop()
        self._log_lines = []
        self._log_pending = []
        self.ui.logPlainTextEdit.clear()

    def report_problems(self, title: str, problems: list[str]) -> None:
        self.log(f"---- {title} ----")
        for item in problems:
            self.log(f"  - {item}")
        QMessageBox.warning(self, title, "\n".join(problems))

    def _ask(self, title: str, text: str, yes: str, no: str = "否") -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        yes_button = box.addButton(yes, QMessageBox.AcceptRole)
        box.addButton(no, QMessageBox.RejectRole)
        box.exec_()
        return box.clickedButton() is yes_button

    # ------------------------------------------------------- 进程内执行内核
    def _start_inprocess(self, target, on_finished, *args) -> None:
        if self._worker is not None and self._worker.is_alive():
            QMessageBox.information(self, self.run_title,
                                    "已有任务正在运行，请先等待完成或点击停止。")
            return
        self.clear_log()
        self.log("任务已启动（进程内运行）。")
        self._flush_log()

        self._outq = queue.Queue()
        self._stop_event = threading.Event()
        self._on_finished_cb = on_finished
        self._worker = threading.Thread(
            target=self._run_in_thread, args=(target, args), daemon=True)
        self._set_running(True)
        self._poll_timer.start()
        self._worker.start()

    def _run_in_thread(self, target, args) -> None:
        code = 0
        capture = LogCapture(on_line=self._outq.put)
        capture.redirect_fd()
        try:
            with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
                target(*args)
        except StopRequested:
            code = 3
            self._outq.put("已停止。")
        except Exception as exc:  # noqa: BLE001 - 引擎异常统一在这里兜底
            code = 2
            self._outq.put(f"程序执行出现错误: {exc}")
            self._outq.put(traceback.format_exc().rstrip("\n"))
        finally:
            try:
                capture.flush()
                capture.restore_fd()
                self._run_log_text = capture.getvalue()
            finally:
                self._outq.put(("__done__", code))

    def _poll_worker(self) -> None:
        while True:
            try:
                item = self._outq.get_nowait()
            except queue.Empty:
                return
            if isinstance(item, tuple) and len(item) == 2 and item[0] == "__done__":
                self._poll_timer.stop()
                self._worker = None
                self._set_running(False)
                code = item[1]
                if code == 3:
                    self.log("任务已停止。")
                else:
                    self.log(f"任务结束，退出码 {code}。")
                self._flush_log()
                callback = self._on_finished_cb
                self._on_finished_cb = None
                if callback is not None and code != 3:
                    callback(code)
                return
            self.log(item)

    def _set_running(self, running: bool) -> None:
        """运行期间禁用“检查 / 运行”，启用“停止”。"""
        for name in ("_act_run_topo", "_act_run_trigrs",
                     "_act_check_topo", "_act_check_trigrs"):
            action = getattr(self, name, None)
            if action is not None:
                action.setEnabled(not running)
        stop = getattr(self, "_act_stop", None)
        if stop is not None:
            stop.setEnabled(running)

    def stop_process(self) -> None:
        if self._worker is None or not self._worker.is_alive():
            return
        self.log("正在请求停止任务（进程内计算无法立即中断，将在当前步骤结束后停止）……")
        self._stop_event.set()

    def closeEvent(self, event):  # noqa: N802 - Qt 命名
        self.shutdown()
        super().closeEvent(event)

    def shutdown(self) -> None:
        self._poll_timer.stop()
        if self._worker is not None and self._worker.is_alive():
            self._stop_event.set()
            self._worker.join(timeout=3)
            self._worker = None


class TrigrsPanel(_BasePanel):
    """TRIGRS + TopoIndex 一体化面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QTTrigrs")
        self._project_path: str | None = None
        self._file_pickers: dict[str, RasterPathEdit] = {}
        self._rain_file_pickers: dict[int, RasterPathEdit] = {}
        self._setup_menu_and_toolbar()

        # 独立程序没有 QGIS 的“工程图层”概念，隐藏“刷新栅格”按钮
        if hasattr(self.ui, "refreshLayersButton"):
            self.ui.refreshLayersButton.setVisible(False)

        self._updating_ui = True
        self._build_file_pickers()
        self._build_soil_table()
        self._build_rain_table()
        self._updating_ui = False
        self._connect_signals()
        self._refresh_trigrs_preview()
        self._refresh_topo_preview()
        self.log("QTTrigrs 已就绪。栅格文件请点右侧“…”按钮从磁盘选择。")

    # ------------------------------------------------------- 菜单栏与 Action 面板
    def _switch_view(self, widget) -> None:
        """切换到指定视图页。"""
        if widget is not None and hasattr(self.ui, "TrigrsMainWidget"):
            self.ui.TrigrsMainWidget.setCurrentWidget(widget)

    def _setup_menu_and_toolbar(self) -> None:
        """
        菜单栏 + 三条主工具栏（工程 / TopoIndex / TRIGRS）。

        * 工具栏按 **工程 → TopoIndex → TRIGRS** 排列，两个模型的操作彻底分开
          （TopoIndex 排在 TRIGRS 前面：先做地形指数，再跑 TRIGRS）；
        * 菜单栏除“视图”外，另有 **检查参数** 与 **运行** 两个菜单，同样区分两个模型；
        * 工具栏按钮一律纯图标 + hover tooltip。
        """
        ui = self.ui

        # 窗口图标
        self.setWindowIcon(self._icon("app.png"))

        # ---------------- 公共 Action ----------------
        def make(icon: str, fallback, text: str, tip: str, slot) -> QAction:
            action = QAction(self._icon(icon, fallback), text, self)
            action.setToolTip(tip)
            action.setStatusTip(tip)
            action.triggered.connect(slot)
            return action

        self._act_new = make("new.png", QStyle.SP_FileIcon, "新建工程", "清空参数与文件选择", self.new_project)
        self._act_import = make("open.png", QStyle.SP_DialogOpenButton, "导入工程…",
                                "导入 tr_in.txt / tpx_in.txt，并恢复栅格选择", self.import_project)
        self._act_export = make("save.png", QStyle.SP_DialogSaveButton, "导出工程…",
                                "导出为官方 tr_in.txt / tpx_in.txt", self.export_project)

        self._act_view_topo = make("topoindex.png", None, "TopoIndex 地形指数",
                                   "切换到 TopoIndex 页", lambda: self._switch_view(ui.TopoIndexWidget))
        self._act_view_trigrs = make("trigrs.png", None, "TRIGRS 模型",
                                     "切换到 TRIGRS 页", lambda: self._switch_view(ui.TrigrsWidget))
        self._act_view_preview = make("preview_input.png", None, "输入文件预览",
                                      "查看将写出的 tr_in.txt / tpx_in.txt",
                                      lambda: self._switch_view(ui.previewWidget))
        self._act_view_result = make("preview_result.png", None, "结果预览",
                                     "浏览输出目录里的结果文件",
                                     lambda: self._switch_view(ui.resultPreviewWidget))

        self._act_preview_topo = make("preview_input.png", QStyle.SP_FileDialogContentsView,
                                      "生成 tpx_in.txt 预览", "刷新并查看 tpx_in.txt",
                                      self._on_preview_topo)
        self._act_preview_trigrs = make("preview_input.png", QStyle.SP_FileDialogContentsView,
                                        "生成 tr_in.txt 预览", "刷新并查看 tr_in.txt",
                                        self._on_preview_trigrs)

        self._act_check_topo = make("check_topo.png", QStyle.SP_DialogApplyButton,
                                    "检查 TopoIndex 参数…", "校验 TopoIndex 参数",
                                    self._on_check_topoindex)
        self._act_check_trigrs = make("check_trigrs.png", QStyle.SP_DialogApplyButton,
                                      "检查 TRIGRS 参数…", "校验 TRIGRS 参数",
                                      self._on_check_trigrs)

        self._act_run_topo = make("run_topo.png", QStyle.SP_MediaPlay, "运行 TopoIndex",
                                  "运行 TopoIndex（进程内后台线程）", self.run_topoindex)
        self._act_run_trigrs = make("run_trigrs.png", QStyle.SP_MediaPlay, "开始计算（TRIGRS）",
                                    "运行 TRIGRS（进程内后台线程）", self.run_trigrs)
        self._act_stop = make("stop.png", QStyle.SP_MediaStop, "停止",
                              "停止当前计算（在当前步骤结束后停止）", self.stop_process)
        self._act_stop.setEnabled(False)

        self._act_about = make("app.png", QStyle.SP_MessageBoxInformation, "关于 QTTrigrs…",
                               "程序简介与官方作者署名致谢", self._show_about)
        self._act_help_topo = make("topoindex.png", None, "TopoIndex 参数说明…",
                                   "tpx_in.txt 全部参数与产物", self._show_topoindex_help)
        self._act_help_trigrs = make("trigrs.png", None, "TRIGRS 参数说明…",
                                     "tr_in.txt 全部参数与输出文件", self._show_trigrs_help)

        # ---------------- 菜单栏 ----------------
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction(self._act_new)
        file_menu.addAction(self._act_import)
        file_menu.addAction(self._act_export)
        file_menu.addSeparator()
        file_menu.addAction(self._act_preview_topo)
        file_menu.addAction(self._act_preview_trigrs)
        file_menu.addSeparator()
        quit_act = QAction("退出(&Q)", self)
        quit_act.setShortcut(QKeySequence("Ctrl+Q"))
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        view_menu = menubar.addMenu("视图(&V)")
        for action in (self._act_view_topo, self._act_view_trigrs,
                       self._act_view_preview, self._act_view_result):
            view_menu.addAction(action)

        # 检查参数：分别对应 TopoIndex 与 TRIGRS
        check_menu = menubar.addMenu("检查参数(&C)")
        check_menu.addAction(self._act_check_topo)
        check_menu.addAction(self._act_check_trigrs)

        # 运行：分别对应 TopoIndex 与 TRIGRS
        run_menu = menubar.addMenu("运行(&R)")
        run_menu.addAction(self._act_run_topo)
        run_menu.addSeparator()
        run_menu.addAction(self._act_run_trigrs)
        run_menu.addSeparator()
        run_menu.addAction(self._act_stop)

        # 帮助：三项各弹一个对话框
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction(self._act_about)
        help_menu.addSeparator()
        help_menu.addAction(self._act_help_topo)
        help_menu.addAction(self._act_help_trigrs)

        # ---------------- 主工具栏：每条独立、可拖动 / 可浮动 ----------------
        # 工程
        tb_project = self._add_toolbar("工程")
        tb_project.addAction(self._act_new)
        tb_project.addAction(self._act_import)
        tb_project.addAction(self._act_export)

        # 视图（放在“工程”后面）
        tb_view = self._add_toolbar("视图")
        tb_view.addAction(self._act_view_topo)
        tb_view.addAction(self._act_view_trigrs)
        tb_view.addAction(self._act_view_preview)
        tb_view.addAction(self._act_view_result)

        # TopoIndex（排在 TRIGRS 前面）
        tb_topo = self._add_toolbar("TopoIndex")
        tb_topo.addAction(self._act_check_topo)
        tb_topo.addAction(self._act_run_topo)
        tb_topo.addAction(self._act_stop)

        # TRIGRS
        tb_trigrs = self._add_toolbar("TRIGRS")
        tb_trigrs.addAction(self._act_check_trigrs)
        tb_trigrs.addAction(self._act_run_trigrs)
        tb_trigrs.addAction(self._act_stop)

        # ---------------- 摘掉 .ui 里页面内那一排旧工具栏 ----------------
        # 只把按钮 setVisible(False) 会留下一条空白：布局本身仍然占着一行的高度。
        # 所以先把整条布局从页面布局里移除，再隐藏其中的控件。
        for layout_name, parent_name in (("toolBarLayout", "trigrsTabLayout"),
                                         ("topoToolBarLayout", "topoIndexTabLayout")):
            inner = getattr(ui, layout_name, None)
            outer = getattr(ui, parent_name, None)
            if inner is not None and outer is not None:
                outer.removeItem(inner)

        for name in ("newProjectButton", "loadProjectButton", "saveProjectButton",
                     "refreshLayersButton", "previewInputButton", "checkProjectButton",
                     "runProjectButton", "stopProjectButton", "toolBarLine",
                     "topoLoadProjectButton", "topoSaveProjectButton",
                     "topoPreviewInputButton", "topoRunButton", "topoToolBarLine"):
            widget = getattr(ui, name, None)
            if widget is not None:
                widget.setVisible(False)

        # 其余仍是纯图标按钮（结果预览、文件选择等）
        for btn, (name, fallback, tip) in {
            ui.resultRefreshButton: ("browse.png", QStyle.SP_BrowserReload, "刷新结果文件列表"),
            ui.ndxfilButton: ("browse.png", QStyle.SP_DirOpenIcon, "选择径流计算顺序单元列表"),
            ui.dscfilButton: ("browse.png", QStyle.SP_DirOpenIcon, "选择下游受体单元列表"),
            ui.wffilButton: ("browse.png", QStyle.SP_DirOpenIcon, "选择径流权重因子列表"),
            ui.outputFolderButton: ("browse.png", QStyle.SP_DirOpenIcon, "选择输出文件夹"),
            ui.topoOutputFolderButton: ("browse.png", QStyle.SP_DirOpenIcon, "选择 TopoIndex 结果保存位置"),
        }.items():
            if btn is None:
                continue
            btn.setIcon(self._icon(name, fallback))
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setToolTip(tip)
            btn.setText("")

    def _add_toolbar(self, title: str) -> QToolBar:
        """
        新建一条主工具栏。

        每条工具栏都是 **可拖动、可浮动（可分离）** 的：按住左侧拖动柄可以把它
        拖到窗口任意一边，或拖出窗口变成浮动小面板（再拖回去即还原）。
        """
        toolbar = QToolBar(title, self)
        toolbar.setObjectName(f"toolbar_{title}")
        toolbar.setMovable(True)
        toolbar.setFloatable(True)
        toolbar.setAllowedAreas(Qt.AllToolBarAreas)
        toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        return toolbar

    def _show_about(self) -> None:
        """“关于 QTTrigrs”：程序简介与官方作者署名致谢。"""
        show_about(self)

    def _show_topoindex_help(self) -> None:
        """“TopoIndex 参数说明”对话框。"""
        show_topoindex_params(self)

    def _show_trigrs_help(self) -> None:
        """“TRIGRS 参数说明”对话框。"""
        show_trigrs_params(self)

    # ------------------------------------------------------- 文件选择控件构建
    def _build_file_pickers(self) -> None:
        """
        在每个占位 QWidget 里放一个 :class:`RasterPathEdit`。

        用代码而不是 .ui 创建，避免 pyuic5 需要额外的自定义控件导入。
        """
        for widget_name, path_label_name, label, _owner in RASTER_LAYER_FIELDS:
            container = getattr(self.ui, widget_name, None)
            if container is None:
                continue
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            picker = RasterPathEdit(container)
            picker.setPlaceholderText(f"（未选择 {label}）")
            layout.addWidget(picker)
            self._file_pickers[widget_name] = picker
            # 文件名不再显示，这个标签只在文件不存在时提示，统一用警示色
            path_label = getattr(self.ui, path_label_name, None)
            if path_label is not None:
                path_label.setStyleSheet("QLabel { color: #c0392b; }")
            picker.pathChanged.connect(
                lambda _path, w=widget_name, p=path_label_name: self._update_path_label(w, p))
            picker.pathChanged.connect(self._refresh_trigrs_preview)
            picker.pathChanged.connect(self._refresh_topo_preview)
            self._update_path_label(widget_name, path_label_name)

    def _update_path_label(self, widget_name: str, path_label_name: str) -> None:
        """
        在文件选择控件旁边补状态提示。

        不再显示文件名（完整路径已经写在行编辑里，再显示一遍文件名又乱又难看）；
        只在文件不存在时给出“（文件不存在）”警告，帮助发现路径失效。
        """
        label = getattr(self.ui, path_label_name, None)
        if label is None:
            return
        picker = self._file_pickers.get(widget_name)
        path = picker.path() if picker is not None else ""
        if path and not Path(path).exists():
            label.setText("（文件不存在）")
            label.setToolTip(path)
            label.show()
        else:
            # 隐藏（而不是只清空文字），否则空标签仍占位，会把输入框挤窄、对不齐
            label.setText("")
            label.setToolTip("")
            label.hide()

    # ------------------------------------------------------------- 文件读写
    def layer_path(self, widget_name: str) -> str:
        """该控件当前对应的栅格路径。"""
        picker = self._file_pickers.get(widget_name)
        return picker.path() if picker is not None else ""

    def _collect_layer_problems(self, for_topoindex: bool = False) -> tuple[list[str], list[str]]:
        """
        检查栅格文件选择情况。

        :param for_topoindex: 为 True 时只检查 TopoIndex 需要的文件，
            这样即使 TRIGRS 的栅格还没选完，也能先单独运行 TopoIndex。
        :return: ``(errors, warnings)``

        只有真正缺不了的栅格才算错误。TRIGRS 里 zmax / depth / rizero / cri
        都是“标量或栅格”二选一，因此这些栅格缺失只是提示，由标量兜底即可。
        """
        errors: list[str] = []
        warnings: list[str] = []

        def describe(widget_name: str) -> str:
            picker = self._file_pickers.get(widget_name)
            path = picker.path() if picker is not None else ""
            if not path:
                return "未选择"
            if not Path(path).exists():
                return "文件不存在"
            return ""

        required = dict(TOPOINDEX_REQUIRED_LAYERS) if for_topoindex else dict(TRIGRS_REQUIRED_LAYERS)
        for widget_name, label in required.items():
            reason = describe(widget_name)
            if reason == "未选择":
                errors.append(f"未选择{label}")
            elif reason:
                errors.append(f"{label}{reason}")

        if not for_topoindex:
            for widget_name, label in TRIGRS_OPTIONAL_LAYERS.items():
                reason = describe(widget_name)
                if reason:
                    warnings.append(f"{label}{reason}（将改用对应的标量值/留空）")
        else:
            reason = describe("topoDirLayerWidget")
            if reason and reason != "未选择":
                warnings.append(f"TopoIndex 的流向栅格{reason}")

        if not for_topoindex:
            for row in range(self.ui.nperSpinBox.value()):
                if not self.rain_layer_path(row):
                    warnings.append(
                        f"第 {row + 1} 期未选择降雨强度栅格，"
                        f"将使用表格里的 cri({row + 1}) 作为全图均匀降雨强度")

        return errors, warnings

    # ------------------------------------------------------------- 初始化表格
    def _make_cell(self, text: str = "") -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    @_batch_ui_update
    def _build_soil_table(self) -> None:
        table = self.ui.soilTableWidget
        count = self.ui.zoneCountSpinBox.value()
        table.setRowCount(count)
        table.setVerticalHeaderLabels([f"zone {i}" for i in range(1, count + 1)])
        defaults = ["1.6e4", "30", "1.8e4", "4.4e-4", "4.4e-6", "0.3", "0.06", "-1"]
        for row in range(count):
            for col in range(len(SOIL_COLUMNS)):
                table.setItem(row, col, self._make_cell(defaults[col]))
        table.resizeColumnsToContents()

    @_batch_ui_update
    def _build_rain_table(self) -> None:
        table = self.ui.rainTableWidget
        nper = self.ui.nperSpinBox.value()
        table.setRowCount(nper + 1)
        table.setVerticalHeaderLabels([f"cri {i}" for i in range(1, nper + 1)] + ["capt 终点"])
        for row in range(nper):
            table.setItem(row, 0, self._make_cell("2.0e-6" if row == 0 else "0"))
            table.setItem(row, 1, self._make_cell("0"))
            table.setCellWidget(row, 2, self._make_rain_file_picker(row))
        last = nper
        table.setItem(last, 0, self._make_cell(""))
        table.setItem(last, 1, self._make_cell("3600"))
        table.setCellWidget(last, 2, None)
        table.resizeColumnsToContents()

    def _make_rain_file_picker(self, row: int) -> RasterPathEdit:
        """降雨强度栅格：表格单元格里的文件选择控件。"""
        picker = RasterPathEdit()
        picker.setPlaceholderText(f"（未选择第 {row + 1} 期降雨栅格）")
        picker.pathChanged.connect(
            lambda _path, r=row: self._on_rain_layer_changed(r))
        self._rain_file_pickers[row] = picker
        picker.setToolTip("未选择降雨强度栅格")
        return picker

    def _on_rain_layer_changed(self, row: int) -> None:
        picker = self._rain_file_pickers.get(row)
        path = picker.path() if picker is not None else ""
        if picker is not None:
            picker.setToolTip(path or f"未选择第 {row + 1} 期降雨栅格")
        self._refresh_trigrs_preview()

    def rain_layer_path(self, row: int) -> str:
        picker = self._rain_file_pickers.get(row)
        return picker.path() if picker is not None else ""

    def rain_layer_paths(self, nper: int) -> list[str]:
        return [self.rain_layer_path(row) for row in range(nper)]

    # ----------------------------------------------------------------- 信号
    def _connect_signals(self) -> None:
        ui = self.ui

        ui.zoneCountSpinBox.valueChanged.connect(self._on_zone_count_changed)
        ui.nperSpinBox.valueChanged.connect(self._on_nper_changed)

        ui.newProjectButton.clicked.connect(self.new_project)
        ui.loadProjectButton.clicked.connect(self.import_project)
        ui.saveProjectButton.clicked.connect(self.export_project)
        ui.previewInputButton.clicked.connect(self._on_preview_trigrs)
        ui.checkProjectButton.clicked.connect(self._on_check_trigrs)
        ui.runProjectButton.clicked.connect(self.run_trigrs)
        ui.stopProjectButton.clicked.connect(self.stop_process)

        ui.topoSaveProjectButton.clicked.connect(self.export_topoindex_project)
        ui.topoLoadProjectButton.clicked.connect(self.import_project)

        # 三个列表文件不是栅格，保留文件选择
        ui.ndxfilButton.clicked.connect(
            lambda: self._pick_text_file(ui.ndxfilLineEdit, "选择径流计算顺序单元列表"))
        ui.dscfilButton.clicked.connect(
            lambda: self._pick_text_file(ui.dscfilLineEdit, "选择下游受体单元列表"))
        ui.wffilButton.clicked.connect(
            lambda: self._pick_text_file(ui.wffilLineEdit, "选择径流权重因子列表"))
        ui.outputFolderButton.clicked.connect(self._pick_output_folder)

        ui.topoPreviewInputButton.clicked.connect(self._on_preview_topo)
        ui.topoRunButton.clicked.connect(self.run_topoindex)
        ui.topoOutputFolderButton.clicked.connect(self._pick_topo_output_folder)

        trigrs_live_widgets = (
            ui.projectTitleLineEdit, ui.txSpinBox, ui.nmaxSpinBox, ui.mmaxSpinBox,
            ui.nzsSpinBox, ui.zminLineEdit, ui.uwwLineEdit, ui.tLineEdit,
            ui.zmaxLineEdit, ui.depthLineEdit, ui.rizeroLineEdit,
            ui.minSlopeLineEdit, ui.maxSlopeLineEdit,
            ui.ndxfilLineEdit, ui.dscfilLineEdit, ui.wffilLineEdit,
            ui.outputFolderLineEdit, ui.suffixLineEdit,
            ui.rodocCheckBox, ui.fsMinCheckBox, ui.zfMinCheckBox, ui.pMinCheckBox,
            ui.waterTableCheckBox, ui.waterTableModeComboBox,
            ui.infiltrationCheckBox, ui.basalFluxCheckBox,
            ui.flagComboBox, ui.spcgSpinBox, ui.noutSpinBox, ui.tsavLineEdit,
            ui.lskipCheckBox, ui.lanyCheckBox, ui.llusCheckBox, ui.lps0CheckBox,
            ui.massBalanceCheckBox, ui.flowDirComboBox, ui.bkgrofCheckBox,
            ui.extensionComboBox, ui.lpge0CheckBox, ui.igcapfCheckBox,
            ui.deepzLineEdit, ui.deepwatComboBox,
        )
        for widget in trigrs_live_widgets:
            for signal_name in ("textChanged", "currentIndexChanged", "valueChanged",
                                "stateChanged"):
                signal = getattr(widget, signal_name, None)
                if signal is not None:
                    signal.connect(self._refresh_trigrs_preview)

        topo_live_widgets = (
            ui.topoHeadingLineEdit, ui.topoPowerLineEdit, ui.topoSuffixLineEdit,
            ui.topoDirectionSchemeComboBox, ui.topoIterSpinBox, ui.topoExtensionComboBox,
            ui.topoListNeighborCheckBox, ui.topoGridNeighborCheckBox,
            ui.topoGridIndexCheckBox, ui.topoListIndexCheckBox,
            ui.topoGridDirectionCheckBox, ui.topoRidgeCheckBox,
            ui.topoRidgeSparseCheckBox,
        )
        for widget in topo_live_widgets:
            for signal_name in ("textChanged", "currentIndexChanged", "valueChanged",
                                "stateChanged"):
                signal = getattr(widget, signal_name, None)
                if signal is not None:
                    signal.connect(self._refresh_topo_preview)

        ui.soilTableWidget.itemChanged.connect(self._refresh_trigrs_preview)
        ui.rainTableWidget.itemChanged.connect(self._refresh_trigrs_preview)

        # 结果预览
        ui.resultRefreshButton.clicked.connect(self._refresh_results)
        ui.resultFileListWidget.currentItemChanged.connect(self._preview_result_file)

    # -------------------------------------------------------------- 结果预览
    def _result_dirs(self) -> list[Path]:
        """候选结果目录：TRIGRS 输出文件夹 + TopoIndex 输出目录。"""
        dirs: list[Path] = []
        try:
            folder = self.ui.outputFolderLineEdit.text().strip()
            if folder:
                dirs.append(Path(folder))
        except Exception:
            pass
        try:
            folder = self.ui.topoOutputFolderLineEdit.text().strip()
            if folder:
                dirs.append(Path(folder))
        except Exception:
            pass
        if self._project_path:
            dirs.append(Path(self._project_path).parent)
        return dirs

    def _refresh_results(self) -> None:
        """扫描结果目录，把生成的栅格 / 列表 / 日志列出来。"""
        ui = self.ui
        ui.resultFileListWidget.clear()
        seen: set[str] = set()
        patterns = ("TR*.asc", "TR*.tif", "TI*.txt", "TRlist_*.txt",
                    "TR_ijz_*.txt", "TrigrsLog.txt", "TopoIndexLog.txt")
        found: list[Path] = []
        for folder in self._result_dirs():
            if not folder.is_dir():
                continue
            for pattern in patterns:
                try:
                    for path in sorted(folder.glob(pattern)):
                        key = os.path.normcase(str(path))
                        if key in seen:
                            continue
                        seen.add(key)
                        found.append(path)
                except OSError:
                    continue
        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for path in found:
            ui.resultFileListWidget.addItem(f"{path.name}  —  {path.parent}")
        self.ui.resultFolderLabel.setText(
            "；".join(str(d) for d in self._result_dirs() if d.is_dir()) or "未设置输出目录")
        self.log(f"结果刷新完成：共 {len(found)} 个文件。")

    def _render_raster_thumbnail(self, path: Path, max_size: int = 520):
        """把栅格渲染成灰度缩略图（QPixmap），NODATA 显示为黑色。"""
        import numpy as np
        import rasterio

        with rasterio.open(path) as src:
            arr = src.read(1).astype(np.float64)
            nd = src.nodata
        h, w = arr.shape
        if nd is not None:
            valid = arr != nd
        else:
            valid = np.ones(arr.shape, dtype=bool)
        vals = arr[valid]
        if vals.size == 0:
            return None
        vmin, vmax = float(vals.min()), float(vals.max())
        if vmax <= vmin:
            vmax = vmin + 1.0
        norm = np.zeros(arr.shape, dtype=np.uint8)
        norm[valid] = ((arr[valid] - vmin) / (vmax - vmin) * 255.0).astype(np.uint8)
        img = QImage(norm.tobytes(), w, h, w, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(img)
        if max(pixmap.width(), pixmap.height()) > max_size:
            pixmap = pixmap.scaled(max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pixmap

    def _preview_result_file(self, item) -> None:
        """预览选中的结果文件：文本显示内容，栅格显示头部/统计 + 图像缩略图。"""
        ui = self.ui
        if item is None:
            return
        text = item.text()
        name = text.split("  —  ")[0].strip()
        parent = text.split("  —  ", 1)[1].strip() if "  —  " in text else ""
        path = Path(parent) / name if parent else Path(name)
        ui.resultPreviewImageLabel.clear()
        if not path.is_file():
            ui.resultPreviewTextEdit.setPlainText(f"文件不存在：{path}")
            return
        ext = path.suffix.lower()
        if ext in (".asc", ".tif", ".tiff"):
            try:
                import numpy as np
                import rasterio
                with rasterio.open(path) as src:
                    arr = src.read(1).astype(np.float64)
                    nd = src.nodata
                    lines = [
                        f"栅格文件：{path}",
                        f"尺寸：{src.width} x {src.height}（{src.count} 波段）",
                        f"驱动：{src.driver}，数据类型：{src.dtypes[0]}",
                        f"投影：{src.crs.to_wkt() if src.crs else '无'}",
                        f"仿射：{src.transform}",
                        f"NODATA：{nd}",
                    ]
                if nd is not None:
                    valid = arr != nd
                    vals = arr[valid]
                else:
                    vals = arr.ravel()
                if vals.size:
                    lines += [
                        f"有效单元：{int(vals.size)}",
                        f"最小值：{float(vals.min()):.6g}",
                        f"最大值：{float(vals.max()):.6g}",
                        f"均值：{float(vals.mean()):.6g}",
                        f"标准差：{float(vals.std()):.6g}",
                    ]
                ui.resultPreviewTextEdit.setPlainText("\n".join(lines))
                pixmap = self._render_raster_thumbnail(path)
                if pixmap is not None:
                    ui.resultPreviewImageLabel.setPixmap(pixmap)
                else:
                    ui.resultPreviewImageLabel.setText("（栅格无有效数据，无法渲染）")
            except Exception as exc:
                ui.resultPreviewTextEdit.setPlainText(f"无法读取栅格：{exc}")
        elif ext in (".txt",):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    head = "".join(f.readline() for _ in range(200))
                ui.resultPreviewTextEdit.setPlainText(
                    head + (f"\n……（文件过大，仅显示前 200 行，共 {path.stat().st_size:,} 字节）"
                             if path.stat().st_size > 64 * 1024 else ""))
            except Exception as exc:
                ui.resultPreviewTextEdit.setPlainText(f"无法读取文本：{exc}")
        else:
            ui.resultPreviewTextEdit.setPlainText(
                f"暂不支持预览该类型文件：{ext}\n路径：{path}")

    # -------------------------------------------------------------- 表格联动
    @_batch_ui_update
    def _on_zone_count_changed(self, count: int) -> None:
        table = self.ui.soilTableWidget
        previous = table.rowCount()
        table.setRowCount(count)
        table.setVerticalHeaderLabels([f"zone {i}" for i in range(1, count + 1)])
        defaults = ["1.6e4", "30", "1.8e4", "4.4e-4", "4.4e-6", "0.3", "0.06", "-1"]
        for row in range(previous, count):
            for col in range(len(SOIL_COLUMNS)):
                table.setItem(row, col, self._make_cell(defaults[col]))
        self._refresh_trigrs_preview()

    @_batch_ui_update
    def _on_nper_changed(self, nper: int) -> None:
        table = self.ui.rainTableWidget
        blocker = QSignalBlocker(table)
        table.setRowCount(nper + 1)
        table.setVerticalHeaderLabels([f"cri {i}" for i in range(1, nper + 1)] + ["capt 终点"])
        for row in range(nper):
            if table.item(row, 0) is None:
                table.setItem(row, 0, self._make_cell("2.0e-6"))
            if table.item(row, 1) is None:
                table.setItem(row, 1, self._make_cell("0"))
            if table.cellWidget(row, 2) is None:
                table.setCellWidget(row, 2, self._make_rain_file_picker(row))
        last = nper
        if table.item(last, 1) is None or not table.item(last, 1).text().strip():
            table.setItem(last, 1, self._make_cell("3600"))
        table.setCellWidget(last, 2, None)
        # 超出范围的降雨下拉框要丢掉，否则会一直堆在内存里
        for row in list(self._rain_file_pickers):
            if row >= nper:
                self._rain_file_pickers.pop(row, None)
        del blocker
        self._refresh_trigrs_preview()

    # ------------------------------------------------------------ 文件选择
    def _pick_text_file(self, line_edit, title: str) -> None:
        start = line_edit.text().strip() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, title, start,
                                              "文本文件 (*.txt);;所有文件 (*)")
        if path:
            line_edit.setText(path)
            self._refresh_trigrs_preview()

    def _pick_output_folder(self) -> None:
        start = self.ui.outputFolderLineEdit.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹", start)
        if path:
            self.ui.outputFolderLineEdit.setText(path)
            self._refresh_trigrs_preview()

    def _pick_topo_output_folder(self) -> None:
        start = self.ui.topoOutputFolderLineEdit.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "选择 TopoIndex 结果保存位置", start)
        if path:
            self.ui.topoOutputFolderLineEdit.setText(path)
            self._refresh_topo_preview()

    # ------------------------------------------------------------- 参数收集
    def collect_trigrs_input(self) -> TrigrsInput:
        """把界面内容读成 :class:`TrigrsInput`（界面与文件字段一一对应）。"""
        ui = self.ui
        zones = ui.zoneCountSpinBox.value()
        nper = ui.nperSpinBox.value()
        nout = ui.noutSpinBox.value()

        soil: list[list[float]] = []
        for row in range(zones):
            values = []
            for col in range(len(SOIL_COLUMNS)):
                cell = ui.soilTableWidget.item(row, col)
                text = cell.text() if cell is not None else ""
                values.append(_to_float(text, f"zone {row + 1} 的 {SOIL_COLUMNS[col]}", 0.0))
            soil.append(values)

        cri = [_to_float(ui.rainTableWidget.item(r, 0).text(), f"cri({r + 1})", 0.0)
               for r in range(nper)]
        capt = []
        for row in range(nper + 1):
            cell = ui.rainTableWidget.item(row, 1)
            capt.append(_to_float(cell.text() if cell else "", f"capt({row + 1})", 0.0))
        rifil = self.rain_layer_paths(nper)

        tsav = _split_floats(ui.tsavLineEdit.text(), "tsav")
        if len(tsav) != nout:
            if len(tsav) < nout:
                tsav = tsav + [tsav[-1] if tsav else 0.0] * (nout - len(tsav))
            else:
                tsav = tsav[:nout]

        return TrigrsInput(
            title=ui.projectTitleLineEdit.text().strip() or "TRIGRS project",
            tx=ui.txSpinBox.value(),
            nmax=ui.nmaxSpinBox.value(),
            mmax=ui.mmaxSpinBox.value(),
            zones=zones,
            nzs=ui.nzsSpinBox.value(),
            zmin=_to_float(ui.zminLineEdit.text(), "zmin", 0.0),
            uww=_to_float(ui.uwwLineEdit.text(), "uww", 9.8e3),
            nper=nper,
            t=_to_float(ui.tLineEdit.text(), "t", 0.0),
            zmax=_to_float(ui.zmaxLineEdit.text(), "zmax", 0.0),
            depth=_to_float(ui.depthLineEdit.text(), "depth", 0.0),
            rizero=_to_float(ui.rizeroLineEdit.text(), "rizero", 0.0),
            slomin=_to_float(ui.minSlopeLineEdit.text(), "最小坡度", 0.0),
            slomax=_to_float(ui.maxSlopeLineEdit.text(), "最大坡度", 90.0),
            soil=soil,
            cri=cri,
            capt=capt,
            rifil=rifil,
            slofil=self.layer_path("slopeLayerWidget"),
            elevfil=self.layer_path("elevLayerWidget"),
            zonfil=self.layer_path("zoneLayerWidget"),
            zfil=self.layer_path("zmaxLayerWidget"),
            depfil=self.layer_path("depthLayerWidget"),
            rizerofil=self.layer_path("rizeroLayerWidget"),
            nxtfil=self.layer_path("nxtLayerWidget"),
            ndxfil=ui.ndxfilLineEdit.text().strip(),
            dscfil=ui.dscfilLineEdit.text().strip(),
            wffil=ui.wffilLineEdit.text().strip(),
            folder=self._output_folder(),
            suffix=ui.suffixLineEdit.text().strip(),
            rodoc=ui.rodocCheckBox.isChecked(),
            save_fs_min=ui.fsMinCheckBox.isChecked(),
            save_zf_min=ui.zfMinCheckBox.isChecked(),
            save_p_min=ui.pMinCheckBox.isChecked(),
            save_water_table=ui.waterTableCheckBox.isChecked(),
            water_table_mode=WATER_TABLE_MODES[ui.waterTableModeComboBox.currentIndex()],
            save_infiltration=ui.infiltrationCheckBox.isChecked(),
            save_basal_flux=ui.basalFluxCheckBox.isChecked(),
            flag=FLAG_VALUES[ui.flagComboBox.currentIndex()],
            spcg=ui.spcgSpinBox.value(),
            nout=nout,
            tsav=tsav,
            lskip=ui.lskipCheckBox.isChecked(),
            lany=ui.lanyCheckBox.isChecked(),
            llus=ui.llusCheckBox.isChecked(),
            lps0=ui.lps0CheckBox.isChecked(),
            log_mass_balance=ui.massBalanceCheckBox.isChecked(),
            flowdir=FLOW_DIRS[ui.flowDirComboBox.currentIndex()],
            bkgrof=ui.bkgrofCheckBox.isChecked(),
            # 索引 0 = asc（lasc 真，官方含义），1 = tif。绝不输出 .txt：
            # .txt 会让 Ssvgrd 拿不到驱动，产生非法的栅格文件。
            lasc=ui.extensionComboBox.currentIndex() == 0,
            lpge0=ui.lpge0CheckBox.isChecked(),
            igcapf=ui.igcapfCheckBox.isChecked(),
            deepz=_to_float(ui.deepzLineEdit.text(), "deepz", -50.0),
            deepwat=DEEPWAT_MODES[ui.deepwatComboBox.currentIndex()],
        )

    def _output_folder(self) -> str:
        folder = self.ui.outputFolderLineEdit.text().strip()
        if not folder:
            return ""
        return folder if folder.endswith(("/", "\\")) else folder + os.sep

    def collect_topoindex_input(self) -> TopoIndexInput:
        """把界面内容读成 :class:`TopoIndexInput`。"""
        ui = self.ui
        heading = ui.topoHeadingLineEdit.text().strip()
        return TopoIndexInput(
            title=heading or "TopoIndex",
            heading=heading or "TopoIndex project",
            aif=1 if ui.topoDirectionSchemeComboBox.currentIndex() == 0 else 2,
            pwr=_to_float(ui.topoPowerLineEdit.text(), "pwr", -1.0),
            itmax=ui.topoIterSpinBox.value(),
            demfil=self.layer_path("topoDemLayerWidget"),
            dirfil=self.layer_path("topoDirLayerWidget"),
            save_list_downslope=ui.topoListNeighborCheckBox.isChecked(),
            save_grid_downslope=ui.topoGridNeighborCheckBox.isChecked(),
            save_grid_index=ui.topoGridIndexCheckBox.isChecked(),
            save_list_index=ui.topoListIndexCheckBox.isChecked(),
            save_grid_direction=ui.topoGridDirectionCheckBox.isChecked(),
            save_grid_ridge=ui.topoRidgeCheckBox.isChecked(),
            ridge_sparse=ui.topoRidgeSparseCheckBox.isChecked(),
            suffix=ui.topoSuffixLineEdit.text().strip()[:MAX_SUFFIX],
        )

    # ---------------------------------------------------------------- 预览
    def _refresh_trigrs_preview(self, *args) -> None:
        if getattr(self, "_updating_ui", False):
            return
        try:
            text = build_tr_in(self.collect_trigrs_input())
        except (TrigrsInputError, ValueError) as exc:
            text = f"参数尚不完整，暂时无法生成 tr_in.txt：\n{exc}\n"
        self.trigrs_browser.setPlainText(text)

    def _refresh_topo_preview(self, *args) -> None:
        if getattr(self, "_updating_ui", False):
            return
        try:
            data = self.collect_topoindex_input()
            text = append_topo_annotations(build_tpx_in(data), {"topo_raster_ext": self._raster_extension()})
            if not self.ui.topoOutputFolderLineEdit.text().strip():
                self.ui.topoOutputFolderLineEdit.setText(data.output_folder)
        except (TopoIndexInputError, ValueError) as exc:
            text = f"参数尚不完整，暂时无法生成 tpx_in.txt：\n{exc}\n"
        self.topo_browser.setPlainText(text)

    def _on_preview_trigrs(self) -> None:
        self._refresh_trigrs_preview()
        self.ui.TrigrsMainWidget.setCurrentWidget(self.ui.previewWidget)
        self.ui.previewTabWidget.setCurrentWidget(self.ui.previewTrinWidget)
        self.log("已刷新 tr_in.txt 预览。")

    def _on_preview_topo(self) -> None:
        self._refresh_topo_preview()
        self.ui.TrigrsMainWidget.setCurrentWidget(self.ui.previewWidget)
        self.ui.previewTabWidget.setCurrentWidget(self.ui.previewTopoWidget)
        self.log("已刷新 tpx_in.txt 预览。")

    # ---------------------------------------------------------------- 路径
    def _project_dir(self) -> Path:
        """
        输入/工程文件的默认目录。

        不依赖 TRIGRS 参数（TopoIndex 允许先单独运行），只用与自身无关的信息：
        已打开的工程文件所在目录 → TopoIndex 的 DEM 目录 → TRIGRS 输出文件夹
        → 用户主目录。
        """
        if self._project_path:
            return Path(self._project_path).parent

        dem = self.layer_path("topoDemLayerWidget")
        if dem:
            parent = Path(dem).parent
            if str(parent) not in ("", "."):
                return parent

        folder = self.ui.outputFolderLineEdit.text().strip()
        if folder:
            return Path(folder)

        return Path.home()

    # ------------------------------------------------- 文件绑定注解（导入导出）
    def _layer_bindings(self) -> dict[str, str]:
        """
        返回“控件名 = 磁盘路径”的文件绑定。

        这是工程文件与界面之间的桥梁：换一台机器打开工程时，官方参数照旧生效，
        文件选择则靠这份绑定在当前界面里重新定位。
        """
        bindings = {name: self.layer_path(name) for name, _p, _l, _o in RASTER_LAYER_FIELDS}
        for row in range(self.ui.nperSpinBox.value()):
            bindings[f"rifil[{row}]"] = self.rain_layer_path(row)
        bindings["topo_raster_ext"] = self._raster_extension()
        return {k: v for k, v in bindings.items() if v}

    def _apply_file_paths(self, wanted: dict[str, str]) -> None:
        """
        把“控件名 -> 磁盘路径”写回对应控件。

        文件不存在时也照常写入（这样导出的 tr_in.txt 仍引用原路径），
        并在日志里逐条提示，供用户随后修正。
        """
        missing: list[str] = []
        for key, target in wanted.items():
            if key.startswith("rifil["):
                row = int(key[len("rifil["):-1])
                picker = self._rain_file_pickers.get(row)
            else:
                picker = self._file_pickers.get(key)
            if picker is None:
                continue
            text = str(target or "").strip()
            picker.setPath(text)
            if text and not Path(text).exists():
                missing.append(f"{key} -> {text}")

        if missing:
            self.log("以下文件在磁盘上不存在，请重新选择：")
            for item in missing:
                self.log(f"  - {item}")

    def _set_file_path(self, key: str, path: str | os.PathLike) -> None:
        """把某个控件直接设置为指定文件路径。"""
        if key.startswith("rifil["):
            picker = self._rain_file_pickers.get(int(key[len("rifil["):-1]))
        else:
            picker = self._file_pickers.get(key)
        if picker is not None:
            picker.setPath(path)

    # ------------------------------------------------------------ 导入 / 导出
    def export_project(self) -> None:
        """导出工程：选择写成 TRIGRS 还是 TopoIndex 输入文件。"""
        box = QMessageBox(self)
        box.setWindowTitle("导出工程")
        box.setText("工程以官方输入文件格式导出，可用原版程序直接打开。\n"
                    "请选择导出类型：")
        trigrs_button = box.addButton("TRIGRS 输入文件 (tr_in.txt)", QMessageBox.AcceptRole)
        topo_button = box.addButton("TopoIndex 输入文件 (tpx_in.txt)", QMessageBox.AcceptRole)
        box.addButton("取消", QMessageBox.RejectRole)
        box.exec_()
        clicked = box.clickedButton()
        if clicked is trigrs_button:
            self.export_trigrs_project()
        elif clicked is topo_button:
            self.export_topoindex_project()

    def export_trigrs_project(self) -> None:
        """把界面上的 TRIGRS 参数导出为 tr_in.txt（附文件绑定注释块）。"""
        try:
            data = self.collect_trigrs_input()
            text = build_tr_in(data)
        except (TrigrsInputError, ValueError) as exc:
            QMessageBox.warning(self, "无法导出", f"TRIGRS 参数尚不完整：\n{exc}")
            return

        default = self._default_export_path("tr_in.txt")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 TRIGRS 输入文件", default,
            "TRIGRS 输入文件 (tr_in.txt);;文本文件 (*.txt)")
        if not path:
            return
        try:
            target = Path(path)
            target.write_text(append_annotations(text, self._layer_bindings()),
                              encoding="utf-8", newline="\n")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        self._project_path = str(target)
        self.log(f"TRIGRS 输入文件已导出：{target}")

    def export_topoindex_project(self) -> None:
        """把界面上的 TopoIndex 参数导出为 tpx_in.txt（附文件绑定注释块）。"""
        try:
            data = self.collect_topoindex_input()
            text = build_tpx_in(data)
        except (TopoIndexInputError, ValueError) as exc:
            QMessageBox.warning(self, "无法导出", f"TopoIndex 参数尚不完整：\n{exc}")
            return

        default = self._default_export_path("tpx_in.txt")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 TopoIndex 输入文件", default,
            "TopoIndex 输入文件 (tpx_in.txt);;文本文件 (*.txt)")
        if not path:
            return
        try:
            target = Path(path)
            target.write_text(append_topo_annotations(text, self._layer_bindings()),
                              encoding="utf-8", newline="\n")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        self._project_path = str(target)
        self.log(f"TopoIndex 输入文件已导出：{target}")

    def _default_export_path(self, filename: str) -> str:
        if self._project_path and Path(self._project_path).name.lower() == filename.lower():
            return self._project_path
        return str(self._project_dir() / filename)

    def import_project(self) -> None:
        """
        导入工程。

        自动识别 ``tr_in.txt`` / ``tpx_in.txt``；参数会被写回界面，文件末尾的
        文件绑定注释块会被用来恢复文件选择。缺失的文件会逐条汇报。
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "导入 TRIGRS / TopoIndex 工程", str(self._project_dir()),
            "输入文件 (tr_in.txt tpx_in.txt *.txt);;所有文件 (*)")
        if not path:
            return
        self._import_project_file(Path(path))

    def _import_project_file(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            QMessageBox.critical(self, "导入失败", f"无法读取文件：\n{exc}")
            return

        base = path.parent
        try:
            if looks_like_tpx_in(path):
                data = parse_tpx_in(path)
                info = parse_topo_annotations(text)
                kind = "TopoIndex (tpx_in.txt)"
                self._apply_topoindex_input(data, base, info)
            elif looks_like_tr_in(path):
                data = parse_tr_in(path)
                info = parse_annotations(text)
                kind = "TRIGRS (tr_in.txt)"
                self._apply_trigrs_input(data, base, info)
            else:
                QMessageBox.warning(
                    self, "无法识别",
                    "该文件既不像 tpx_in.txt 也不像 tr_in.txt。\n"
                    "请选择本模块或原版程序生成的输入文件。")
                return
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", f"无法解析输入文件：\n{exc}")
            return

        self._project_path = str(path)
        self.log(f"已导入 {kind}：{path}")
        self._warn_about_missing_referenced_files(data, kind)

    def _warn_about_missing_referenced_files(self, data, kind: str) -> None:
        """
        参数里引用的磁盘文件若不存在，逐条列出。

        这一步很重要：输入文件里存的是路径，换机器后即使文件都补齐了，
        也可能有某个输入的栅格早已被删除。
        """
        missing: list[str] = []
        if isinstance(data, TrigrsInput):
            pairs = [
                ("坡度栅格 slofil", data.slofil),
                ("高程栅格 elevfil", data.elevfil),
                ("属性分区栅格 zonfil", data.zonfil),
                ("最大深度栅格 zfil", data.zfil),
                ("地下水位深度栅格 depfil", data.depfil),
                ("初始入渗率栅格 rizerofil", data.rizerofil),
                ("径流受体栅格 nxtfil", data.nxtfil),
                ("顺序列表 ndxfil", data.ndxfil),
                ("下游列表 dscfil", data.dscfil),
                ("权重列表 wffil", data.wffil),
            ]
            pairs += [(f"降雨强度栅格 rifil({i})", p)
                      for i, p in enumerate(data.rifil, start=1)]
        else:
            pairs = [("DEM 栅格 demfil", data.demfil), ("流向栅格 dirfil", data.dirfil)]

        for label, value in pairs:
            text = str(value or "").strip()
            if text and not Path(text).exists():
                missing.append(f"{label}：{text}")

        if missing:
            self.log("以下参数引用的文件在磁盘上不存在：")
            for item in missing:
                self.log(f"  - {item}")
            QMessageBox.information(
                self, "部分引用的文件不存在",
                "输入文件里引用了下面这些文件，但磁盘上找不到：\n\n"
                + "\n".join(missing[:15])
                + ("\n……" if len(missing) > 15 else "")
                + "\n\n相关文件选择框会保留原路径，请重新指定文件。")

    # ------------------------------------------------- 参数写回界面（导入用）
    @_batch_ui_update
    def _apply_trigrs_input(self, data: TrigrsInput, base: Path | None = None,
                            info: dict[str, str] | None = None) -> None:
        ui = self.ui

        ui.projectTitleLineEdit.setText(data.title)
        ui.topoExtensionComboBox.setCurrentIndex(
            1 if (info or {}).get("topo_raster_ext", "asc") == "tif" else 0)

        # 分区数与土壤参数
        ui.zoneCountSpinBox.setValue(int(data.zones))
        self._on_zone_count_changed(int(data.zones))
        for row, values in enumerate(data.soil):
            if row >= ui.soilTableWidget.rowCount():
                break
            for col, value in enumerate(values):
                ui.soilTableWidget.setItem(row, col, self._make_cell(repr(value)))

        # 降雨时段与参数
        ui.nperSpinBox.setValue(int(data.nper))
        self._on_nper_changed(int(data.nper))
        for row in range(min(data.nper, ui.rainTableWidget.rowCount())):
            ui.rainTableWidget.setItem(row, 0, self._make_cell(repr(data.cri[row])))
            ui.rainTableWidget.setItem(row, 1, self._make_cell(repr(data.capt[row])))
        if ui.rainTableWidget.rowCount() > data.nper:
            ui.rainTableWidget.setItem(data.nper, 1, self._make_cell(repr(data.capt[-1])))

        # 其余标量
        ui.txSpinBox.setValue(int(data.tx))
        ui.nmaxSpinBox.setValue(int(data.nmax))
        ui.mmaxSpinBox.setValue(int(data.mmax))
        ui.nzsSpinBox.setValue(int(data.nzs))
        ui.zminLineEdit.setText(repr(data.zmin))
        ui.uwwLineEdit.setText(repr(data.uww))
        ui.tLineEdit.setText(repr(data.t))
        ui.zmaxLineEdit.setText(repr(data.zmax))
        ui.depthLineEdit.setText(repr(data.depth))
        ui.rizeroLineEdit.setText(repr(data.rizero))
        ui.minSlopeLineEdit.setText(repr(data.slomin))
        ui.maxSlopeLineEdit.setText(repr(data.slomax))

        ui.ndxfilLineEdit.setText(resolve_project_path(data.ndxfil, base))
        ui.dscfilLineEdit.setText(resolve_project_path(data.dscfil, base))
        ui.wffilLineEdit.setText(resolve_project_path(data.wffil, base))
        # folder 是“相对输入文件所在目录”的路径，不能按普通相对路径拼接，
        # 否则 Data/tutorial/export/ 会被拼成 <base>/Data/tutorial/export。
        ui.outputFolderLineEdit.setText(resolve_project_path(data.folder, base).rstrip("/\\"))
        ui.suffixLineEdit.setText(data.suffix)

        ui.rodocCheckBox.setChecked(data.rodoc)
        ui.fsMinCheckBox.setChecked(data.save_fs_min)
        ui.zfMinCheckBox.setChecked(data.save_zf_min)
        ui.pMinCheckBox.setChecked(data.save_p_min)
        ui.waterTableCheckBox.setChecked(data.save_water_table)
        ui.waterTableModeComboBox.setCurrentIndex(
            WATER_TABLE_MODES.index(data.water_table_mode)
            if data.water_table_mode in WATER_TABLE_MODES else 0)
        ui.infiltrationCheckBox.setChecked(data.save_infiltration)
        ui.basalFluxCheckBox.setChecked(data.save_basal_flux)
        ui.flagComboBox.setCurrentIndex(
            FLAG_VALUES.index(data.flag) if data.flag in FLAG_VALUES else 0)
        ui.spcgSpinBox.setValue(int(data.spcg))
        ui.noutSpinBox.setValue(int(data.nout))
        ui.tsavLineEdit.setText(", ".join(repr(v) for v in data.tsav))
        ui.lskipCheckBox.setChecked(data.lskip)
        ui.lanyCheckBox.setChecked(data.lany)
        ui.llusCheckBox.setChecked(data.llus)
        ui.lps0CheckBox.setChecked(data.lps0)
        ui.massBalanceCheckBox.setChecked(data.log_mass_balance)
        ui.flowDirComboBox.setCurrentIndex(
            FLOW_DIRS.index(data.flowdir) if data.flowdir in FLOW_DIRS else 0)
        ui.bkgrofCheckBox.setChecked(data.bkgrof)
        ui.extensionComboBox.setCurrentIndex(0 if data.lasc else 1)  # T->asc, F->tif
        ui.lpge0CheckBox.setChecked(data.lpge0)
        ui.igcapfCheckBox.setChecked(data.igcapf)
        ui.deepzLineEdit.setText(repr(data.deepz))
        ui.deepwatComboBox.setCurrentIndex(
            DEEPWAT_MODES.index(data.deepwat) if data.deepwat in DEEPWAT_MODES else 1)

        # Every input binding is replaced, including empty paths. Partial annotation
        # blocks must not leave unrelated selections from the previous project.
        wanted = {name: resolve_project_path(getattr(data, field), base) for name, field in (
            ("slopeLayerWidget", "slofil"), ("elevLayerWidget", "elevfil"),
            ("zoneLayerWidget", "zonfil"), ("zmaxLayerWidget", "zfil"),
            ("depthLayerWidget", "depfil"), ("rizeroLayerWidget", "rizerofil"),
            ("nxtLayerWidget", "nxtfil"))}
        for row in range(int(data.nper)):
            wanted[f"rifil[{row}]"] = resolve_project_path(data.rifil[row], base)
        for key, value in (info or {}).items():
            if key in wanted or key in self._file_pickers:
                wanted[key] = resolve_project_path(value, base)
        self._apply_file_paths(wanted)
        self._refresh_trigrs_preview()

    @_batch_ui_update
    def _apply_topoindex_input(self, data: TopoIndexInput, base: Path | None = None,
                               info: dict[str, str] | None = None) -> None:
        ui = self.ui
        ui.topoHeadingLineEdit.setText(data.heading)
        ui.topoDirectionSchemeComboBox.setCurrentIndex(0 if data.aif == 1 else 1)
        ui.topoPowerLineEdit.setText(repr(data.pwr))
        ui.topoIterSpinBox.setValue(int(data.itmax))
        ui.topoListNeighborCheckBox.setChecked(data.save_list_downslope)
        ui.topoGridNeighborCheckBox.setChecked(data.save_grid_downslope)
        ui.topoGridIndexCheckBox.setChecked(data.save_grid_index)
        ui.topoListIndexCheckBox.setChecked(data.save_list_index)
        ui.topoGridDirectionCheckBox.setChecked(data.save_grid_direction)
        ui.topoRidgeCheckBox.setChecked(data.save_grid_ridge)
        ui.topoRidgeSparseCheckBox.setChecked(data.ridge_sparse)
        ui.topoSuffixLineEdit.setText(data.suffix)
        ui.topoExtensionComboBox.setCurrentIndex(
            1 if (info or {}).get("topo_raster_ext", "asc") == "tif" else 0)

        wanted: dict[str, str] = {}
        if info:
            for name in ("topoDemLayerWidget", "topoDirLayerWidget"):
                if info.get(name):
                    wanted[name] = resolve_project_path(info[name], base)
        if not wanted:
            wanted = {
                "topoDemLayerWidget": resolve_project_path(data.demfil, base),
                "topoDirLayerWidget": resolve_project_path(data.dirfil, base),
            }
        self._apply_file_paths(wanted)
        self._refresh_topo_preview()

    # ---------------------------------------------------------------- 工程
    @_batch_ui_update
    def new_project(self, *args) -> None:
        # 按钮/菜单的 clicked/triggered 会传一个 checked 布尔参数，这里忽略
        self._project_path = None
        for picker in self._file_pickers.values():
            picker.setPath("")
        self._rain_file_pickers = {}
        for widget_name, path_label_name, _label, _owner in RASTER_LAYER_FIELDS:
            self._update_path_label(widget_name, path_label_name)

        ui = self.ui
        ui.projectTitleLineEdit.setText("")
        ui.topoHeadingLineEdit.setText("")
        ui.topoSuffixLineEdit.setText("")
        ui.topoExtensionComboBox.setCurrentIndex(0)
        ui.topoPowerLineEdit.setText("-1")
        ui.topoIterSpinBox.setValue(10)
        ui.zoneCountSpinBox.setValue(1)
        ui.nperSpinBox.setValue(1)
        ui.noutSpinBox.setValue(1)
        ui.tsavLineEdit.setText("0")
        ui.ndxfilLineEdit.setText("")
        ui.dscfilLineEdit.setText("")
        ui.wffilLineEdit.setText("")
        ui.outputFolderLineEdit.setText("")
        ui.suffixLineEdit.setText("")

        self._build_soil_table()
        ui.rainTableWidget.setRowCount(0)   # 重新生成本期降雨行与文件选择控件
        self._build_rain_table()
        self._refresh_trigrs_preview()
        self._refresh_topo_preview()
        self.log("已新建空白工程。")

    def _report_check(self, title: str, errors: list[str], warnings: list[str]) -> bool:
        """输出检查结果，返回是否通过（没有错误即通过）。"""
        self.log(f"---- {title} ----")
        if errors:
            for item in errors:
                self.log(f"  [错误] {item}")
        if warnings:
            for item in warnings:
                self.log(f"  [提示] {item}")
        if not errors and not warnings:
            self.log("  通过")
        return not errors

    def _show_check_summary(self, groups: list[tuple[str, list[str], list[str]]]) -> bool:
        """把若干组检查结果汇总展示，返回是否有任何错误。"""
        all_errors = [e for _t, errs, _w in groups for e in errs]
        if not all_errors:
            lines: list[str] = []
            for title, _errs, warns in groups:
                if warns:
                    lines.append(f"{title}（提示 {len(warns)} 条，不影响运行）：")
                    lines.extend(f"  · {w}" for w in warns)
            if lines:
                QMessageBox.information(self, "参数检查",
                                        "参数检查通过。\n\n" + "\n".join(lines))
            else:
                QMessageBox.information(self, "参数检查", "参数检查通过。")
            return False
        parts: list[str] = []
        for title, errs, warns in groups:
            if errs:
                parts.append(f"{title}：\n  " + "\n  ".join(errs))
            if warns:
                parts.append(f"{title}（提示）：\n  " + "\n  ".join(warns))
        QMessageBox.warning(self, "参数检查发现问题", "\n\n".join(parts))
        return True

    # ---------------------------------------------------------------- 校验
    def _on_check_trigrs(self) -> None:
        """只检查 TRIGRS 参数。"""
        self.clear_log()
        try:
            trigrs_data = self.collect_trigrs_input()
            layer_errs, layer_warns = self._collect_layer_problems()
            errs, warns = validate_trigrs(trigrs_data)
            trigrs_errors = layer_errs + errs
            trigrs_warnings = layer_warns + warns
        except TrigrsInputError as exc:
            trigrs_errors = [str(exc)]
            trigrs_warnings = []
        self._report_check("TRIGRS 参数检查", trigrs_errors, trigrs_warnings)
        self._show_check_summary([("TRIGRS", trigrs_errors, trigrs_warnings)])

    def _on_check_topoindex(self) -> None:
        """只检查 TopoIndex 参数。"""
        self.clear_log()
        try:
            topo_data = self.collect_topoindex_input()
            layer_errs, layer_warns = self._collect_layer_problems(for_topoindex=True)
            errs, warns = validate_topoindex(topo_data)
            topo_errors = layer_errs + errs
            topo_warnings = layer_warns + warns
        except TopoIndexInputError as exc:
            topo_errors = [str(exc)]
            topo_warnings = []
        self._report_check("TopoIndex 参数检查", topo_errors, topo_warnings)
        self._show_check_summary([("TopoIndex", topo_errors, topo_warnings)])

    # ---------------------------------------------------------------- 运行
    def write_tr_in_file(self, path: str | os.PathLike | None = None) -> Path:
        """写给 TRIGRS 用的输入文件（含文件绑定注释块）。"""
        target = Path(path) if path else self._project_dir() / "tr_in.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(append_annotations(build_tr_in(self.collect_trigrs_input()),
                                             self._layer_bindings()),
                          encoding="utf-8", newline="\n")
        return target

    def write_tpx_in_file(self, path: str | os.PathLike | None = None) -> Path:
        """写给 TopoIndex 用的输入文件（含文件绑定注释块）。"""
        target = Path(path) if path else self._project_dir() / "tpx_in.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            append_topo_annotations(build_tpx_in(self.collect_topoindex_input()),
                                    self._layer_bindings()),
            encoding="utf-8", newline="\n")
        return target

    def run_trigrs(self) -> None:
        """运行 TRIGRS；只涉及 TRIGRS 自身的参数，与 TopoIndex 无关。"""
        self.clear_log()
        try:
            data = self.collect_trigrs_input()
        except TrigrsInputError as exc:
            self.report_problems("无法运行", [str(exc)])
            return
        layer_errs, layer_warns = self._collect_layer_problems()
        errs, warns = validate_trigrs(data)
        for item in layer_warns + warns:
            self.log(f"[提示] {item}")
        if layer_errs or errs:
            self.report_problems("运行前检查未通过", layer_errs + errs)
            return
        try:
            tr_in = self.write_tr_in_file()
        except Exception as exc:
            QMessageBox.critical(self, "写入输入文件失败", str(exc))
            return

        self.log(f"tr_in.txt 已写入：{tr_in}")
        output_dir = data.folder.rstrip("/\\") or str(tr_in.parent)
        output_path = Path(output_dir)
        if not output_path.is_absolute():
            output_path = tr_in.parent / output_path
        before = self._result_snapshot(output_path)
        self._start_inprocess(
            self._run_trigrs_target,
            lambda code: self._after_trigrs(code, output_path, before),
            tr_in, output_path / "TrigrsLog.txt",
        )

    def _run_trigrs_target(self, tr_in: Path, log_path: Path) -> None:
        """在后台线程内运行 TRIGRS（进程内，无子进程）。"""
        from trigrs.Trigrs import trigrs
        from trigrs.TrigrsModule.Grids import grids
        from trigrs.TrigrsModule.InputVars import input_vars
        from trigrs.TrigrsModule.ModelVars import model_vars

        # 进程内反复运行时，模块级单例需重置到初始状态
        grids.__init__()
        input_vars.__init__()
        model_vars.__init__()
        trigrs(str(tr_in), str(log_path), self._stop_event)

    @staticmethod
    def _result_snapshot(folder: Path) -> dict[Path, tuple[int, int]]:
        result = {}
        for pattern in ("TR*.asc", "TR*.tif"):
            for path in folder.glob(pattern):
                stat = path.stat()
                result[path] = (stat.st_mtime_ns, stat.st_size)
        return result

    def _after_trigrs(self, code: int, folder: Path, before: dict) -> None:
        if code != 0:
            self.log(f"TRIGRS 退出码 {code}，请查看上方错误信息。")
            return
        try:
            changed = [path for path, stamp in self._result_snapshot(folder).items()
                       if before.get(path) != stamp]
            self.log("TRIGRS 计算完成。本次生成/更新的结果文件：")
            for path in sorted(changed):
                self.log(f"  - {path}")
            if not changed:
                self.log(f"未发现本次生成的 ASC/TIF 栅格，请检查输出选项。目录：{folder}")
        except Exception as exc:
            self.log(f"结果文件已生成，但列举失败：{exc}；目录：{folder}")
        try:
            self._refresh_results()
        except Exception:
            pass

    def run_topoindex(self) -> None:
        """
        运行 TopoIndex。

        只校验 TopoIndex 自己的参数，因此可以在 TRIGRS 参数尚未填完时先算。
        """
        self.clear_log()
        try:
            data = self.collect_topoindex_input()
        except TopoIndexInputError as exc:
            self.report_problems("无法运行 TopoIndex", [str(exc)])
            return
        layer_errs, layer_warns = self._collect_layer_problems(for_topoindex=True)
        errs, warns = validate_topoindex(data)
        for item in layer_warns + warns:
            self.log(f"[提示] {item}")
        if layer_errs or errs:
            self.report_problems("TopoIndex 运行前检查未通过", layer_errs + errs)
            return
        try:
            tpx_in = self.write_tpx_in_file()
        except Exception as exc:
            QMessageBox.critical(self, "写入输入文件失败", str(exc))
            return

        self.log(f"tpx_in.txt 已写入：{tpx_in}")
        raster_ext = self._raster_extension()
        output_folder = self.ui.topoOutputFolderLineEdit.text().strip()
        self._start_inprocess(
            self._run_topoindex_target,
            self._after_topoindex,
            tpx_in, raster_ext, output_folder,
        )

    def _run_topoindex_target(self, tpx_in: Path, raster_ext: str, result_dir: str) -> None:
        """在后台线程内运行 TopoIndex（进程内，无子进程）。"""
        from topoindex.topoindex import topoindex_main

        os.environ["TRIGRS_RASTER_EXT"] = raster_ext
        topoindex_main(True, str(tpx_in), self._stop_event, result_dir or None)

    def _raster_extension(self) -> str:
        """TopoIndex 页独立选择的栅格格式，默认 ASC。"""
        return "asc" if self.ui.topoExtensionComboBox.currentIndex() == 0 else "tif"

    def _warn_about_legacy_txt_products(self, folder: Path) -> None:
        """
        提示目录里遗留的旧版「栅格」.txt 文件。

        早期版本会把栅格产物（TIdscelGrid / TIcelindxGrid / TIflodirGrid /
        TIridge_crest）写成 .txt，现在统一写 .asc / .tif。列表类产物
        （TIdsneiList / TIdscelList / TIwfactorList / TIcelindxList）本来就是
        .txt，是合法产物，不在提示范围内。
        """
        patterns = ("TIdscelGrid_*.txt", "TIcelindxGrid_*.txt",
                    "TIflodirGrid_*.txt", "TIridge_crest_*.txt")
        try:
            stale: list[str] = []
            for pattern in patterns:
                stale.extend(p.name for p in folder.glob(pattern)
                             if p.is_file() and p.stat().st_size > 1024)
            stale = sorted(set(stale))
        except OSError:
            return
        if not stale:
            return
        self.log("注意：目录中存在早期版本留下的栅格 .txt 文件（旧版把栅格写成了 .txt，不是合法栅格格式）：")
        for name in stale[:10]:
            self.log(f"  - {name}")
        self.log("  这些文件不会被使用，建议删除；"
                 "本次运行的栅格产物是 .asc / .tif。")

    def _after_topoindex(self, code: int) -> None:
        if code != 0:
            self.log(f"TopoIndex 退出码 {code}，未自动填充径流文件。")
            return
        data = self.collect_topoindex_input()
        folder = Path(self.ui.topoOutputFolderLineEdit.text().strip() or data.output_folder)
        suffix = data.suffix

        def first_existing(stem: str, extensions=(".txt",)) -> Path | None:
            """
            找 TopoIndex 的产物，尽量宽容：

            1. 先按当前 suffix 精确匹配（含 Fortran 版单下划线 / 部分 Python 版
               双下划线两种写法）；
            2. 再按 ``<stem>_*.ext`` 通配，取最近修改的那个。
            """
            for candidate_suffix in (f"_{suffix}", f"__{suffix}"):
                for ext in extensions:
                    path = folder / f"{stem}{candidate_suffix}{ext}"
                    if path.exists():
                        return path
            matches: list[Path] = []
            for ext in extensions:
                matches.extend(folder.glob(f"{stem}_*{ext}"))
            if matches:
                matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                return matches[0]
            return None

        text_products = {
            "ndxfil": ("TIcelindxList", "径流计算顺序单元列表 ndxfil"),
            "dscfil": ("TIdscelList", "下游受体单元列表 dscfil"),
            "wffil": ("TIwfactorList", "径流权重因子列表 wffil"),
        }

        found: dict[str, Path] = {}
        missing: list[str] = []
        for name, (stem, label) in text_products.items():
            path = first_existing(stem)
            if path is None:
                missing.append(label)
            else:
                found[name] = path

        if missing:
            self.log("TopoIndex 运行结束，但以下产物没有找到，未自动填充：")
            for item in missing:
                self.log(f"  - {item}")
            self.log(f"  期望目录：{folder}")
            self.log(f"  期望文件名形如：TIcelindxList_{suffix}.txt / "
                     f"TIdscelList_{suffix}.txt / "
                     f"TIwfactorList_{suffix}.txt")
            if suffix == "":
                self.log(f"  提示：当前 suffix 为空，产物文件名会是 "
                         f"TIcelindxList_.txt 这一类。"
                         "建议填写 suffix 以便区分不同方案的产物。")
            self.log("  可能原因：correct_order 未收敛（itmax 太小）。"
                     "请增大 TopoIndex 页的 itmax（顺序修正最大迭代次数）后重试；"
                     "大网格 DEM 通常需要 itmax ≥ 1000。")
            self._warn_about_legacy_txt_products(folder)
            try:
                listing = sorted(p.name for p in folder.iterdir() if p.is_file())
                self.log("  目录中现有文件："
                         + ("、".join(listing[:30]) if listing else "（空）"))
            except OSError as exc:
                self.log(f"  无法列出目录：{exc}")
            self._save_run_log(Path(folder), "TopoIndexLog.txt")
            return

        self.ui.ndxfilLineEdit.setText(str(found["ndxfil"]))
        self.ui.dscfilLineEdit.setText(str(found["dscfil"]))
        self.ui.wffilLineEdit.setText(str(found["wffil"]))

        nxt_path = first_existing("TIdscelGrid", (f".{self._raster_extension()}",))
        if nxt_path is not None:
            self._set_file_path("nxtLayerWidget", nxt_path)
        else:
            self.log("未找到 D8 下游单元编号栅格（TIdscelGrid_*），"
                     "请在“nxtfil”处手动选择对应文件。"
                     "若本次未勾选“保存 D8 下游邻居单元栅格”，TopoIndex 不会生成该栅格。")

        self._refresh_trigrs_preview()
        self.log("已把 TopoIndex 产物填入 TRIGRS 的径流演算文件：")
        for name, path in found.items():
            self.log(f"  {name} = {path}")
        if nxt_path is not None:
            self.log(f"  已填入下游单元编号栅格：{nxt_path.name}")
        self._save_run_log(Path(folder), "TopoIndexLog.txt")
        try:
            self._refresh_results()
        except Exception:
            pass

    def _save_run_log(self, folder: Path, filename: str) -> None:
        """把本次运行的完整日志（控制台 + 缓冲区）一次性落盘。"""
        text = getattr(self, "_run_log_text", "")
        if not text:
            return
        try:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / filename
            path.write_text(text, encoding="utf-8", errors="replace")
            self.log(f"运行日志已保存：{path}")
        except Exception as exc:
            self.log(f"保存运行日志失败：{exc}")
