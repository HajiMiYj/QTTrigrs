"""
QTTrigrs 的栅格文件选择控件。

原 PyQGIS 版用 ``QgsMapLayerComboBox`` 从工程已加载图层中选取栅格；
独立程序没有 QGIS 工程，因此改为“行编辑 + 浏览按钮”的组合，直接到磁盘上
选择栅格文件。功能上等价：得到的是写入 ``tr_in.txt`` / ``tpx_in.txt`` 的
真实磁盘路径。
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QToolButton,
    QWidget,
)

_ICONS_DIR = Path(__file__).resolve().parents[1] / "resources" / "icons"


def _icon(name: str) -> QIcon:
    path = _ICONS_DIR / name
    if path.is_file():
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon
    return QIcon()

#: 允许作为栅格输入的扩展名（与官方 TRIGRS 常用格式一致）
RASTER_FILTER = (
    "栅格文件 (*.tif *.tiff *.asc *.txt *.img *.vrt *.bil *.hdr *.nc);;"
    "所有文件 (*)"
)


class RasterPathEdit(QWidget):
    """
    一个只读的路径输入框 + “浏览”按钮。

    用户在行编辑里看到选中的文件路径，点按钮弹文件对话框；也可以把
    TopoIndex 产物路径直接 ``setPath`` 回填进来。
    """

    #: 选中/回填的路径发生变化时发出（参数是当前路径字符串）
    pathChanged = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None,
                 filter: str = RASTER_FILTER):
        super().__init__(parent)
        self._filter = filter

        self._line = QLineEdit(self)
        self._line.setReadOnly(True)
        self._line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._line.setPlaceholderText("（未选择）")
        self._line.textChanged.connect(self.pathChanged)

        self._button = QToolButton(self)
        self._button.setIcon(_icon("browse.png"))
        self._button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self._button.setToolTip("选择文件")
        self._button.setFixedWidth(26)
        self._button.clicked.connect(self._browse)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._line)
        layout.addWidget(self._button)

    # ------------------------------------------------------------------ API
    def path(self) -> str:
        """当前选中的文件路径（空串表示未选择）。"""
        return self._line.text().strip()

    def setPath(self, path: str | os.PathLike) -> None:
        """回填路径（例如导入工程 / 运行 TopoIndex 后自动填入产物）。"""
        text = "" if path is None else str(path)
        if text != self._line.text():
            self._line.setText(text)

    def setPlaceholderText(self, text: str) -> None:
        self._line.setPlaceholderText(text)

    def lineEdit(self) -> QLineEdit:
        return self._line

    # ------------------------------------------------------------- 内部实现
    def _browse(self) -> None:
        current = self.path()
        start = str(Path(current).parent) if current else str(Path.home())
        chosen, _ = QFileDialog.getOpenFileName(self, "选择栅格文件", start,
                                                self._filter)
        if chosen:
            self._line.setText(chosen)
            self._line.setToolTip(chosen)
