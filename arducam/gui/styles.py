"""Shared styles for the Clean Light GUI theme."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

CARD_STYLE = """
    QFrame {
        background: white;
        border-radius: 10px;
        border: none;
    }
"""

SLIDER_STYLE = """
    QSlider::groove:horizontal {
        background: #f0f0f2;
        height: 4px;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        background: #007aff;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }
    QSlider::handle:horizontal:disabled {
        background: #c0c0c0;
    }
    QSlider::sub-page:horizontal {
        background: #007aff;
        border-radius: 2px;
    }
    QSlider::sub-page:horizontal:disabled {
        background: #d0d0d0;
    }
"""

COMBO_STYLE = """
    QComboBox {
        background: #f0f0f2;
        border: none;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        color: #1d1d1f;
    }
    QComboBox::drop-down {
        border: none;
        padding-right: 6px;
    }
    QComboBox QAbstractItemView {
        background: white;
        border: 1px solid #d1d1d6;
        border-radius: 6px;
        selection-background-color: #007aff;
        selection-color: white;
    }
"""

# Controls panel uses larger combo padding
COMBO_STYLE_LARGE = COMBO_STYLE.replace("padding: 4px 10px", "padding: 8px 12px").replace(
    "font-size: 12px", "font-size: 13px"
)

SPIN_STYLE = """
    QSpinBox {
        background: #f0f0f2; border: none; border-radius: 6px;
        padding: 4px 8px; font-size: 12px; color: #1d1d1f;
        min-width: 50px;
    }
    QSpinBox::up-button, QSpinBox::down-button { width: 16px; }
"""

BTN_PRIMARY = """
    QPushButton {
        background: #007aff; color: white; border: none;
        border-radius: 8px; padding: 10px; font-size: 13px; font-weight: 500;
    }
    QPushButton:hover { background: #0066d6; }
    QPushButton:pressed { background: #004ea8; }
    QPushButton:disabled { background: #a0c4ff; }
"""

BTN_SECONDARY = """
    QPushButton {
        background: white; color: #1d1d1f; border: 1px solid #d1d1d6;
        border-radius: 8px; padding: 10px; font-size: 13px;
    }
    QPushButton:hover { background: #f0f0f2; }
    QPushButton:pressed { background: #e0e0e2; }
    QPushButton:disabled { color: #c0c0c0; }
"""

BTN_RECORD = """
    QPushButton {
        background: #ff3b30; color: white; border: none;
        border-radius: 8px; padding: 10px; font-size: 13px; font-weight: 500;
    }
    QPushButton:hover { background: #e0352b; }
    QPushButton:pressed { background: #c02e25; }
"""

BTN_RECORD_STOP = """
    QPushButton {
        background: white; color: #ff3b30; border: 2px solid #ff3b30;
        border-radius: 8px; padding: 10px; font-size: 13px; font-weight: 500;
    }
    QPushButton:hover { background: #fff0f0; }
"""

PILL_STYLE_ACTIVE = """
    QPushButton {
        background: #007aff; color: white; border: none;
        border-radius: 8px; padding: 3px 12px; font-size: 11px; font-weight: 500;
    }
"""

PILL_STYLE_INACTIVE = """
    QPushButton {
        background: transparent; color: #86868b; border: none;
        border-radius: 8px; padding: 3px 12px; font-size: 11px;
    }
"""

PANEL_BG = "background: #f5f5f7;"

STATUS_BAR_STYLE = "QStatusBar { background: #e8e8ed; color: #1d1d1f; font-size: 12px; }"

LIVE_VIEW_STYLE = "background-color: #1a1a1a; color: #86868b; border-radius: 10px; font-size: 14px;"

REC_STATUS_IDLE = "font-size: 11px; color: #86868b;"
REC_STATUS_ACTIVE = "font-size: 11px; color: #ff3b30; font-weight: 500;"

CARD_PADDING = 14


def section_label(text: str) -> QLabel:
    """Uppercase section header label."""
    label = QLabel(text)
    label.setStyleSheet(
        "font-size: 11px; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px;"
    )
    return label


def small_label(text: str) -> QLabel:
    """Small gray inline label."""
    label = QLabel(text)
    label.setStyleSheet("font-size: 11px; color: #86868b;")
    return label


def value_label(text: str, enabled: bool = True) -> QLabel:
    """Right-aligned value display label."""
    label = QLabel(text)
    label.setMinimumWidth(36)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    _apply_value_label_style(label, enabled)
    return label


def _apply_value_label_style(label: QLabel, enabled: bool) -> None:
    color = "#1d1d1f" if enabled else "#c0c0c0"
    label.setStyleSheet(f"font-size: 13px; color: {color}; font-weight: 500;")


def set_value_label_enabled(label: QLabel, enabled: bool) -> None:
    """Update a value label's visual enabled/disabled state."""
    _apply_value_label_style(label, enabled)


def card() -> tuple[QFrame, QVBoxLayout]:
    """White rounded card container with standard-padded layout."""
    c = QFrame()
    c.setStyleSheet(CARD_STYLE)
    c.setFrameShape(QFrame.Shape.NoFrame)
    layout = QVBoxLayout(c)
    p = CARD_PADDING
    layout.setContentsMargins(p, p, p, p)
    return c, layout
