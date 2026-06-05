"""
基于QML的毛玻璃果冻按钮
PyQt5自带QML支持，无需额外安装
"""
import os
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtQml import QQmlEngine


class JellyQmlButton(QWidget):
    """
    基于QML的果冻按钮
    - 半透明毛玻璃
    - 按压果冻形变
    - 丝滑弹性回弹
    - 顶部弧面高光
    """
    clicked = pyqtSignal()
    
    def __init__(self, text="按钮", color="#4CAF50", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(45)
        self.setMinimumWidth(100)
        self._text = text
        self._color = color
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建QML视图
        self.qml_view = QQuickWidget()
        self.qml_view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.qml_view.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        
        # 设置透明背景
        self.qml_view.setClearColor(Qt.GlobalColor.transparent)
        
        layout.addWidget(self.qml_view)
        
        # 加载QML
        qml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'JellyButton.qml')
        self.qml_view.setSource(QUrl.fromLocalFile(qml_path))
        
        # 连接信号
        root = self.qml_view.rootObject()
        if root:
            root.clicked.connect(self._on_clicked)
            root.setProperty("text", text)
            root.setProperty("btnColor", color)
    
    def _on_clicked(self):
        self.clicked.emit()
    
    def setText(self, text):
        self._text = text
        root = self.qml_view.rootObject()
        if root:
            root.setProperty("text", text)
    
    def text(self):
        return self._text
    
    def set_color(self, color):
        """设置颜色"""
        self._color = color
        root = self.qml_view.rootObject()
        if root:
            root.setProperty("btnColor", color)
    
    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        root = self.qml_view.rootObject()
        if root:
            root.setEnabled(enabled)
