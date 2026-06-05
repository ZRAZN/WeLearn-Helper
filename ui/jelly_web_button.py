"""
基于Web的毛玻璃果冻按钮组件
使用QWebEngineView实现真正的CSS动画效果
"""
import os
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWebChannel import QWebChannel


class WebButtonBridge(QObject):
    """Python与JS的桥接"""
    clicked = pyqtSignal(str)
    
    @pyqtSlot(str)
    def on_button_click(self, text):
        self.clicked.emit(text)


class JellyWebButton(QWidget):
    """
    基于Web的毛玻璃果冻按钮
    - 半透明毛玻璃背景
    - 按压果冻形变
    - 丝滑弹性回弹
    - 顶部弧面高光
    """
    clicked = pyqtSignal()
    
    def __init__(self, text="按钮", color="green", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(45)
        self.setMinimumWidth(100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建Web视图
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 设置透明背景
        page = self.web_view.page()
        page.setBackgroundColor(Qt.GlobalColor.transparent)
        
        # 设置桥接
        self.bridge = WebButtonBridge()
        self.bridge.clicked.connect(self._on_clicked)
        
        channel = QWebChannel()
        channel.registerObject("bridge", self.bridge)
        page.setWebChannel(channel)
        
        layout.addWidget(self.web_view)
        
        # 加载HTML
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_button.html')
        self.web_view.setUrl(QUrl.fromLocalFile(html_path))
        
        # 页面加载完成后设置按钮
        self.web_view.loadFinished.connect(lambda: self._init_button(text, color))
        
        self._text = text
    
    def _init_button(self, text, color):
        """初始化按钮"""
        self._run_js(f'setText("{text}")')
        self._run_js(f'setColor("{color}")')
    
    def _run_js(self, code):
        """执行JS代码"""
        self.web_view.page().runJavaScript(code)
    
    def _on_clicked(self, text):
        """按钮点击回调"""
        self.clicked.emit()
    
    def setText(self, text):
        """设置按钮文字"""
        self._text = text
        self._run_js(f'setText("{text}")')
    
    def text(self):
        """获取按钮文字"""
        return self._text
    
    def setEnabled(self, enabled):
        """设置启用状态"""
        super().setEnabled(enabled)
        self._run_js(f'setEnabled({str(enabled).lower()})')
    
    def set_color(self, color):
        """设置颜色主题: green, red, blue, orange, purple"""
        self._run_js(f'setColor("{color}")')
