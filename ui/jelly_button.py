"""
果冻效果按钮组件 - 最终版
"""
from PyQt5.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QSize
from PyQt5.QtGui import QColor


class JellyButton(QPushButton):
    """带果冻效果的按钮"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._anim = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(35)
        
        # 添加阴影效果
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setOffset(0, 3)
        self.setGraphicsEffect(self.shadow)
        
        self._base_shadow = 3
        self._hover_shadow = 6
        self._press_shadow = 1
    
    def set_jelly_colors(self, base, hover, pressed):
        """设置颜色"""
        self._base_color = base
        self._hover_color = hover
        self._pressed_color = pressed
        self._apply_style(base)
    
    def _apply_style(self, color, padding="10px 20px", shadow_offset=3):
        """应用样式"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: {padding};
                font-size: 13px;
                border-radius: 8px;
                font-weight: bold;
            }}
        """)
        self.shadow.setOffset(0, shadow_offset)
    
    def set_jelly_style(self, base_color="#4CAF50", hover_color="#45a049", press_color="#3d8b40"):
        """设置果冻效果样式"""
        self._base_color = base_color
        self._hover_color = hover_color
        self._pressed_color = press_color
        self._apply_style(base_color)
    
    def enterEvent(self, event):
        """鼠标进入"""
        if not self.isDown():
            self._apply_style(self._hover_color, "12px 22px", self._hover_shadow)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开"""
        if not self.isDown():
            self._apply_style(self._base_color, "10px 20px", self._base_shadow)
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._apply_style(self._pressed_color, "8px 18px", self._press_shadow)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.rect().contains(self.mapFromGlobal(event.globalPos())):
                self._apply_style(self._hover_color, "12px 22px", self._hover_shadow)
            else:
                self._apply_style(self._base_color, "10px 20px", self._base_shadow)
        super().mouseReleaseEvent(event)
