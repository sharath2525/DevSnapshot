"""DevSnapshot's restrained graphite and indigo visual system."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle


class DevSnapshotStyle(QProxyStyle):
    """Fusion-based style with an unmistakable radio selection state."""

    def __init__(self) -> None:
        super().__init__("Fusion")

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if element != QStyle.PrimitiveElement.PE_IndicatorRadioButton:
            super().drawPrimitive(element, option, painter, widget)
            return

        checked = bool(option.state & QStyle.StateFlag.State_On)
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        size = min(option.rect.width(), option.rect.height(), 16)
        left = option.rect.x() + (option.rect.width() - size) / 2
        top = option.rect.y() + (option.rect.height() - size) / 2
        circle = QRectF(left + 1, top + 1, size - 2, size - 2)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        border = QColor("#716cf0" if checked else "#656977")
        if not enabled:
            border = QColor("#41444f")
        painter.setPen(QPen(border, 1.5))
        painter.setBrush(QColor("#0c0e13"))
        painter.drawEllipse(circle)
        if checked:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#716cf0" if enabled else "#4a477f"))
            painter.drawEllipse(circle.adjusted(4, 4, -4, -4))
        painter.restore()

DARK_STYLESHEET = """
QWidget {
    color: #e9eaf0;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow, QDialog, QWidget#appShell { background: #0a0b0f; }
QWidget#content, QLabel { background: transparent; }
QLabel#productTitle { color: #f7f7fa; font-size: 22pt; font-weight: 700; }
QLabel#title { color: #f7f7fa; font-size: 20pt; font-weight: 700; }
QLabel#dialogTitle { color: #f7f7fa; font-size: 16pt; font-weight: 700; }
QLabel#completeHeading { color: #f7f7fa; font-size: 14pt; font-weight: 650; }
QLabel#tagline { color: #9699a7; font-size: 10pt; }
QLabel#cardTitle { color: #f3f3f7; font-size: 12pt; font-weight: 650; }
QLabel#sectionTitle {
    color: #9b9ead;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.8px;
}
QLabel#metric { color: #f7f7fa; font-size: 15pt; font-weight: 650; }
QLabel#statusTitle { color: #eaf8f2; font-size: 13pt; font-weight: 650; }
QLabel#contentsSummary {
    color: #c7c6fb;
    background: #171626;
    border: 1px solid #34315d;
    border-radius: 7px;
    padding: 8px 10px;
}
QLabel#muted { color: #9295a2; }
QLabel#emptyState {
    color: #a5a7b2;
    background: #0e1015;
    border: 1px dashed #30333e;
    border-radius: 8px;
    padding: 14px;
}
QLabel#success { color: #65d6ad; font-size: 11pt; font-weight: 600; }
QLabel#warning {
    color: #e7c67d;
    background: #211c12;
    border: 1px solid #4b3c20;
    border-radius: 7px;
    padding: 7px 9px;
}
QLabel#pill {
    color: #76d9b5;
    background: #10241e;
    border: 1px solid #245143;
    border-radius: 10px;
    padding: 5px 10px;
    font-size: 8pt;
    font-weight: 700;
}
QLabel#footer { color: #616572; font-size: 8.5pt; }
QLabel#settingsStatus {
    color: #bbb9f5;
    background: #151522;
    border: 1px solid #302e52;
    border-radius: 7px;
    padding: 8px 10px;
}
QFrame#card {
    background: #12141a;
    border: 1px solid #272a34;
    border-radius: 12px;
}
QFrame#actionCard {
    background: #14151e;
    border: 1px solid #34325b;
    border-radius: 12px;
}
QFrame#pathRow {
    background: #0d0f14;
    border: 1px solid #242731;
    border-radius: 9px;
}
QFrame#modeCard {
    background: #111319;
    border: 1px solid #292c36;
    border-radius: 10px;
}
QFrame#modeCard[selected="true"] {
    background: #171625;
    border: 1px solid #625de0;
}
QFrame#customPanel {
    background: #0e1015;
    border: 1px solid #282b35;
    border-radius: 10px;
}
QStackedWidget#modePages { background: transparent; border: 0; }
QRadioButton#modeOption { color: #f2f2f7; font-size: 11pt; font-weight: 650; }
QCheckBox::indicator { width: 16px; height: 16px; }
QPushButton {
    background: #191c24;
    border: 1px solid #343844;
    border-radius: 8px;
    padding: 8px 14px;
    color: #e3e4ea;
    font-weight: 550;
}
QPushButton:hover { background: #222530; border-color: #4b4f5e; }
QPushButton:pressed { background: #13151b; }
QPushButton:disabled { color: #565a66; background: #12141a; border-color: #242731; }
QPushButton#primary {
    background: #625de0;
    border-color: #716cf0;
    color: white;
    font-size: 11pt;
    font-weight: 700;
    padding: 12px 22px;
}
QPushButton#primary:hover { background: #716cf0; border-color: #8985f5; }
QPushButton#secondary { background: #171a22; padding: 9px 14px; }
QPushButton#compact { min-width: 58px; padding: 7px 11px; }
QPushButton#quiet { background: transparent; border-color: #373a47; padding: 5px 9px; }
QPushButton#danger { color: #ffb5b5; border-color: #66383e; }
QPushButton#chip {
    color: #c9c7fa;
    background: #181724;
    border: 1px solid #3c395f;
    border-radius: 10px;
    padding: 4px 8px;
    font-size: 8.5pt;
}
QLineEdit#pathField {
    color: #dedfe6;
    background: transparent;
    border: 0;
    padding: 0;
    selection-background-color: #5d58ce;
}
QLineEdit, QListWidget, QPlainTextEdit {
    background: #0b0d12;
    border: 1px solid #292d38;
    border-radius: 8px;
    padding: 7px;
    selection-background-color: #4f4ab7;
}
QListWidget#historyList { outline: 0; padding: 4px; }
QListWidget::item {
    padding: 10px 9px;
    border-bottom: 1px solid #242730;
    border-radius: 5px;
}
QListWidget::item:hover { background: #191c25; }
QListWidget::item:selected { background: #29264f; color: #f7f7fb; }
QCheckBox { spacing: 8px; }
QProgressBar {
    background: #0b0d12;
    border: 1px solid #292d38;
    border-radius: 5px;
    height: 10px;
    text-align: center;
}
QProgressBar::chunk { background: #716cf0; border-radius: 4px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical {
    background: #373a46;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #1b1e26; color: #ffffff; border: 1px solid #3d414e; }
"""
