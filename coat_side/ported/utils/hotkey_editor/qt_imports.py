"""
Hotkey Editor - Qt Import Helper

Centralized Qt imports with fallback for non-Qt environments.
"""
from __future__ import annotations

HAS_QT: bool = False

try:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QLineEdit,
        QComboBox,
        QTreeWidget,
        QTreeWidgetItem,
        QHeaderView,
        QMessageBox,
        QFileDialog,
        QStatusBar,
        QFrame,
        QSplitter,
        QMenu,
        QDialog,
        QDialogButtonBox,
        QGroupBox,
        QScrollArea,
        QListWidget,
        QListWidgetItem,
        QFormLayout,
        QRadioButton,
        QButtonGroup,
        QCheckBox,
    )
    from PySide6.QtCore import Qt, QTimer, Signal, QEvent
    from PySide6.QtGui import QColor, QBrush, QAction, QKeySequence, QKeyEvent, QIcon, QPixmap, QPainter

    HAS_QT = True
except ImportError:
    # Provide fallback types for type hints
    QMainWindow = object
    QDialog = object
    QWidget = object
