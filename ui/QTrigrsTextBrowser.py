from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QRect, QSize, QRegExp
from PyQt5.QtGui import QPainter, QColor, QSyntaxHighlighter, QTextCharFormat, QFont
from PyQt5.QtWidgets import QWidget, QPlainTextEdit


# 语法高亮器
class TrigrsHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.highlighting_rules = []

        # 关键字格式 - 蓝色
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(0, 0, 255))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            'title', 'tx', 'nmax', 'mmax', 'nzon', 'rizero',
            'nzs', 'zmin', 'uww', 'nper', 'K-sat', 'Theta-sat', 'Theta-res',
            'Z-P-Fs', 'zmax', 'depth',
            'czmax', 'deepz', 'crizero', 'slomin', 'slomax',
            'c', 'phi', 'uws', 'diffus', 'ks', 'ths', 'thr', 'alp',
            'cri', 'capt', 'slofil', 'elevfil', 'zonfil',
            'zfil', 'depfil', 'rizerofil', 'rifil', 'nxtfil', 'ndxfil',
            'dscfil', 'wffil', 'folder', 'suffix', 'ridoc',
            'outp', 'el_or_dep', 'flag', 'spcg', 'nout', 'ksav', 'lskip',
            'lany', 'llus', 'lps0', 'flowdir', 'bkgrof', 'lasc', 'lpge0',
            'lgcapf', 'lgcap', 'deepz', 'deepwat',
            'zones', 'rifil[]', 'T', 'F', 'xmdv', 'ijz', 'alpha', 'psi0',
            'gener', 'slope', 'hydro', 'tif', 'asc', 'txt',
            'zero', 'flow', 'hydr', 'relh', 't', 'dif'
        ]
        for pattern in keywords:
            self.highlighting_rules.append((QRegExp(pattern), keyword_format))

        # 数字格式 - 红色
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(255, 0, 0))
        self.highlighting_rules.append((QRegExp(r'\b\d+\.?\d*[eE]?[+-]?\d*\b'), number_format))

        # 文件路径格式 - 绿色
        file_format = QTextCharFormat()
        file_format.setForeground(QColor(0, 150, 0))
        file_format.setFontItalic(True)
        self.highlighting_rules.append((QRegExp(r'Data/[\w/\.]+'), file_format))

        # 注释格式 - 灰色
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((QRegExp(r'#.*'), comment_format))

        # 标题格式 - 紫色加粗
        title_format = QTextCharFormat()
        title_format.setForeground(QColor(128, 0, 128))
        title_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegExp(r'^[A-Za-z].*:$'), title_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)


# 行号区域
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)


# 自定义文本编辑器
class TrigrsTextBrowser(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.line_number_area = LineNumberArea(self)
        self.highlighter = TrigrsHighlighter(self.document())
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width()
        # 设置字体
        font = QFont("Consolas", 10)
        self.setFont(font)

    def line_number_area_width(self):
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                                self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(240, 240, 240))  # 行号区域背景色

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(100, 100, 100))
                painter.drawText(0, int(top), self.line_number_area.width() - 5,
                                 self.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def set_init_trigrs(self):
        """
        设置初始化Tr_in
        """
        _translate = QtCore.QCoreApplication.translate
        self.setPlainText(_translate("TrigrsMainWindow", "工程名称\n"
                                                         "\n"
                                                         "tx, nmax, mmax, zones \n"
                                                         "\n"
                                                         "nzs, zmin, uww, nper, t\n"
                                                         "\n"
                                                         "最大深度zmax, 地下水深度depth, 初始入渗率rizero, 最小坡度(°), 最大坡度(°)\n"
                                                         "\n"
                                                         "区域, 1\n"
                                                         "粘聚力c, 内摩擦角φ, 岩土体重度uws, 扩散系数diffus, 饱和导水率K-sat, "
                                                         "饱和体积含水率Theta-sat, 残余体积含水率Theta-res, Alpha\n"
                                                         "\n"
                                                         "cri(1), cri(2), ..., cri(nper)\n"
                                                         "\n"
                                                         "capt(1), capt(2), ..., capt(n), capt(n+1)\n"
                                                         "\n"
                                                         "坡度栅格(slofil)  \n"
                                                         "\n"
                                                         "高程栅格 (elevfil)\n"
                                                         "\n"
                                                         "属性分区栅格 (zonfil)\n"
                                                         "\n"
                                                         "最大深度栅格 (zfil) \n"
                                                         "\n"
                                                         "初始地下水位深度栅格 (depfil)\n"
                                                         "\n"
                                                         "初始入渗率栅格 (rizerofil)\n"
                                                         "\n"
                                                         "各时段降雨强度文件列表 (rifil[])\n"
                                                         "\n"
                                                         "D8流向受体像元编号 (nxtfil)\n"
                                                         "\n"
                                                         "定义径流计算顺序的像元列表文件 (ndxfil)\n"
                                                         "\n"
                                                         "所有径流受体像元列表文件名 (dscfil)\n"
                                                         "\n"
                                                         "径流权重因子列表文件名 (wffil)\n"
                                                         "\n"
                                                         "输出网格文件存储文件夹 (folder)\n"
                                                         "\n"
                                                         "输出文件名标识代码 (suffix)\n"
                                                         "\n"
                                                         "保存径流栅格文件？ 输入T或F\n"
                                                         "F\n"
                                                         "保存最小安全系数栅格？ 输入T或F\n"
                                                         "F\n"
                                                         "保存最小安全系数对应深度栅格？ 输入T或F\n"
                                                         "F\n"
                                                         "保存最小安全系数对应深度处的压力水头栅格？ 输入T或F\n"
                                                         "F\n"
                                                         "保存计算的地下水位深度或高程栅格？ 输入T或F\n"
                                                         "F\n"
                                                         "保存非饱和带底部通量栅格？ 输入T或F\n"
                                                         "F\n"
                                                         "保存压力水头和安全系数列表 (\"flag\")？ (-9 稀疏 xmdv, -8 降采样 "
                                                         "xmdv, -7 完整 xmdv, -6 稀疏 ijz, -5 降采样 ijz, -4 完整 ijz, -3 "
                                                         "Z-P-Fs-饱和度列表, -2 详细 Z-P-Fs, -1 Z-P-Fs 列表, 0 无)。"
                                                         "输入 flag 值，后跟降采样间隔 (整数)。\n"
                                                         "0,1\n"
                                                         "保存输出栅格和/或 ijz/xmdv 文件的次数\n"
                                                         "\n"
                                                         "输出栅格和/或 ijz / xmdv 文件的时间\n"
                                                         "\n"
                                                         "跳过其他时间步？ 输入 T 或 F\n"
                                                         "F\n"
                                                         "使用可充填孔隙度的解析解？ 输入 T 或 F\n"
                                                         "T\n"
                                                         "估算上升地下水位区（即非饱和带下部）的正压力水头？ 输入 T 或 F\n"
                                                         "T\n"
                                                         "使用 psi0=-1/alpha？ 输入 T 或 F (False 选择默认值 psi0=0)\n"
                                                         "F\n"
                                                         "记录质量平衡结果？ 输入 T 或 F\n"
                                                         "T\n"
                                                         "流向 (输入 \"gener\", \"slope\", 或 \"hydro\")\n"
                                                         "gener\n"
                                                         "在瞬态入渗率中添加稳态背景通量以防止在零入渗期间变得比初始条件更干燥？\n"
                                                         "T\n"
                                                         "指定输出网格文件的扩展名。\n"
                                                         "tif\n"
                                                         "在计算安全系数时忽略负压力水头（仅限饱和入渗）？ 输入 T 或 F\n"
                                                         "F\n"
                                                         "在非饱和入渗选项中，计算压力水头时忽略毛细上升带高度？ 输入 T 或 F\n"
                                                         "F\n"
                                                         "SCOOPS ijz 输出中深层压力水头估算参数：地表以下的深度"
                                                         "（正值，使用负值取消此选项），"
                                                         "压力选项（输入 \'zero\', \'flow\', \'hydr\', 或 \'relh\'）\n"
                                                         "0,zero\n"
                                                         ""))
