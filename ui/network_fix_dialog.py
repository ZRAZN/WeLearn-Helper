"""
网络诊断与修复工具箱对话框
"""
import os
import sys
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton,
    QGroupBox, QProgressBar, QTextEdit, QCheckBox, QMessageBox
)
from PyQt5.QtGui import QPixmap, QIcon, QColor
from ui.jelly_qml_button import JellyQmlButton as JellyButton

from core.network_fixer import NetworkDiagnostics, NetworkFixer, is_admin


class DiagnosisThread(QThread):
    """诊断线程"""
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)
    
    def run(self):
        self.progress.emit("正在诊断网络状态...")
        diag = NetworkDiagnostics()
        results = diag.diagnose_all()
        self.finished.emit(results)


class FixThread(QThread):
    """修复线程"""
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)
    
    def __init__(self, items_to_fix):
        super().__init__()
        self.items_to_fix = items_to_fix
    
    def run(self):
        self.progress.emit("正在执行修复...")
        fixer = NetworkFixer()
        
        # 根据选择的项目执行对应修复
        results = []
        for item in self.items_to_fix:
            self.progress.emit(f"正在修复: {item}...")
            if item == "DNS服务":
                results.append(("刷新DNS", *fixer.flush_dns()))
            elif item == "代理配置":
                results.append(("重置代理", *fixer.reset_proxy()))
            elif item == "HOSTS文件":
                results.append(("修复HOSTS", *fixer.fix_hosts()))
            elif item == "LSP协议":
                results.append(("重置Winsock", *fixer.reset_winsock()))
            elif item == "IP配置":
                results.append(("重置IP/TCP", *fixer.reset_tcp_ip()))
                results.append(("刷新DNS", *fixer.flush_dns()))
                results.append(("重置DHCP", *fixer.reset_dhcp()))
        
        self.finished.emit(results)


class NetworkFixDialog(QDialog):
    """网络修复工具箱对话框"""
    
    def __init__(self, parent=None):
        super().__init__(None)  # 不设置parent，成为独立窗口
        self.setWindowTitle("网络诊断与修复工具箱")
        self.setMinimumSize(450, 600)
        self.resize(450, 600)  # 3:4 比例
        # 完全无边框
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._drag_pos = None
        self.setup_video_background()
        self.init_ui()
        self.diagnosis_results = []
        self.fix_checkboxes = {}
    
    def setup_video_background(self):
        """设置视频背景"""
        from ui.video_background import setup_video_background
        result = setup_video_background(self, 'UI B2.mp4', 450, 600)
        if result:
            self.graphics_view, self.content_container, self.video_player = result
            # 设置为主布局
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            main_layout.addWidget(self.graphics_view)
            
            # 顶部栏（覆盖在graphics_view上面）
            self.top_bar = QWidget(self)
            self.top_bar.setFixedHeight(40)
            self.top_bar.setGeometry(0, 0, 450, 40)
            self.top_bar.setStyleSheet("background: transparent;")
            top_layout = QHBoxLayout(self.top_bar)
            top_layout.setContentsMargins(15, 10, 15, 0)
            top_layout.setSpacing(0)
            top_layout.addStretch()
            
            min_btn = QPushButton()
            min_btn.setFixedSize(12, 12)
            min_btn.setStyleSheet("QPushButton { background-color: #ffbd2e; border: none; border-radius: 6px; } QPushButton:hover { background-color: #ff9500; }")
            min_btn.clicked.connect(self.showMinimized)
            top_layout.addWidget(min_btn)
            top_layout.addSpacing(8)
            
            max_btn = QPushButton()
            max_btn.setFixedSize(12, 12)
            max_btn.setStyleSheet("QPushButton { background-color: #27c93f; border: none; border-radius: 6px; } QPushButton:hover { background-color: #28a745; }")
            max_btn.clicked.connect(self.toggle_maximize)
            top_layout.addWidget(max_btn)
            top_layout.addSpacing(8)
            
            close_btn = QPushButton()
            close_btn.setFixedSize(12, 12)
            close_btn.setStyleSheet("QPushButton { background-color: #ff5f56; border: none; border-radius: 6px; } QPushButton:hover { background-color: #ff3b30; }")
            close_btn.clicked.connect(self.close)
            top_layout.addWidget(close_btn)
            
            self.top_bar.raise_()
            
            # 内容容器覆盖在视频上 - 使用ScrollArea确保内容可滚动
            from PyQt5.QtWidgets import QScrollArea
            self.content_widget = QScrollArea(self)
            self.content_widget.setStyleSheet("background: transparent; border: none;")
            self.content_widget.setGeometry(0, 40, 450, 560)
            self.content_widget.setWidgetResizable(True)
            self.content_widget.raise_()
            self.content_widget.show()
    
    def init_ui(self):
        # 创建内容容器
        content_container = QWidget()
        content_container.setStyleSheet("background: transparent;")
        
        if hasattr(self, 'content_widget'):
            self.content_widget.setWidget(content_container)
        
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(15, 10, 15, 15)
        content_layout.setSpacing(10)
        
        # 标题
        title = QLabel("网络诊断与修复工具箱")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.diagnose_btn = JellyButton("🔍 一键诊断")
        self.diagnose_btn.set_color("#2196F3")
        self.diagnose_btn.clicked.connect(self.start_diagnosis)
        btn_layout.addWidget(self.diagnose_btn)
        
        self.fix_btn = JellyButton("🔧 修复选中项")
        self.fix_btn.set_color("#4CAF50")
        self.fix_btn.setEnabled(False)
        self.fix_btn.clicked.connect(self.start_fix)
        btn_layout.addWidget(self.fix_btn)
        content_layout.addLayout(btn_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        content_layout.addWidget(self.progress_bar)
        
        # 诊断结果区
        result_group = QGroupBox("诊断结果")
        result_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background: transparent;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        result_layout.addWidget(self.result_text)
        
        # 修复选项区（诊断后显示）
        self.fix_options_group = QGroupBox("选择要修复的项目（取消勾选可忽略）")
        self.fix_options_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background: transparent;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        self.fix_options_layout = QVBoxLayout(self.fix_options_group)
        self.fix_options_group.setVisible(False)
        result_layout.addWidget(self.fix_options_group)
        
        content_layout.addWidget(result_group)
        
        # 状态栏
        self.status_label = QLabel('点击"一键诊断"开始检测网络状态')
        self.status_label.setStyleSheet("color: #aaa; font-size: 12px; background: transparent;")
        content_layout.addWidget(self.status_label)
    
    def toggle_maximize(self):
        """切换最大化/还原"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 记录拖动位置"""
        if event.button() == Qt.MouseButton.LeftButton and event.y() < 40:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 窗口拖动"""
        if hasattr(self, '_drag_pos') and self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            if event.y() < 40:
                self.move(event.globalPos() - self._drag_pos)
                event.accept()
    
    def set_background(self):
        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'):
                app_path = sys._MEIPASS
            else:
                app_path = os.path.dirname(sys.executable)
                if not os.path.exists(os.path.join(app_path, 'ZR.ico')):
                    internal_path = os.path.join(app_path, '_internal')
                    if os.path.exists(os.path.join(internal_path, 'ZR.ico')):
                        app_path = internal_path
        else:
            app_path = os.path.dirname(os.path.abspath(__file__))
            app_path = os.path.dirname(app_path)
        
        bg_path = os.path.join(app_path, 'ZR.png')
        if os.path.exists(bg_path):
            pixmap = QPixmap(bg_path)
            from PyQt5.QtGui import QBrush
            palette = self.palette()
            palette.setBrush(self.backgroundRole(), QBrush(pixmap.scaled(
                self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)))
            self.setPalette(palette)
    
    def start_diagnosis(self):
        """开始诊断"""
        self.diagnose_btn.setEnabled(False)
        self.fix_btn.setEnabled(False)
        self.result_text.clear()
        self.fix_options_group.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("正在诊断...")
        
        self.diag_thread = DiagnosisThread()
        self.diag_thread.finished.connect(self.on_diagnosis_finished)
        self.diag_thread.progress.connect(lambda msg: self.status_label.setText(msg))
        self.diag_thread.start()
    
    def on_diagnosis_finished(self, results):
        """诊断完成"""
        self.diagnosis_results = results
        self.progress_bar.setVisible(False)
        self.diagnose_btn.setEnabled(True)
        
        has_errors = False
        html = "<style>table{width:100%} td{padding:5px} .ok{color:green} .warning{color:orange} .error{color:red}</style>"
        html += "<table>"
        
        # 清除旧的复选框
        while self.fix_options_layout.count():
            item = self.fix_options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.fix_checkboxes.clear()
        
        for r in results:
            status = r['status']
            name = r['name']
            if status == 'ok':
                icon = '\u2705'
                cls = 'ok'
            elif status == 'warning':
                icon = '\u26a0\ufe0f'
                cls = 'warning'
                has_errors = True
                # 为有问题的项添加复选框
                cb = QCheckBox(f"{name}: {r['detail']}")
                cb.setChecked(True)
                cb.setStyleSheet("font-size: 12px; padding: 3px;")
                self.fix_options_layout.addWidget(cb)
                self.fix_checkboxes[name] = cb
            else:
                icon = '\u274c'
                cls = 'error'
                has_errors = True
                # 为有问题的项添加复选框
                cb = QCheckBox(f"{name}: {r['detail']}")
                cb.setChecked(True)
                cb.setStyleSheet("font-size: 12px; padding: 3px; color: red;")
                self.fix_options_layout.addWidget(cb)
                self.fix_checkboxes[name] = cb
            
            html += f'<tr><td>{icon}</td><td><b>{name}</b></td><td class="{cls}">{r["detail"]}</td></tr>'
        
        html += "</table>"
        self.result_text.setHtml(html)
        
        if has_errors:
            self.fix_btn.setEnabled(True)
            self.fix_options_group.setVisible(True)
            self.status_label.setText(f"检测到 {len(self.fix_checkboxes)} 个问题，取消勾选可忽略")
        else:
            self.status_label.setText("网络状态正常，无需修复")
    
    def start_fix(self):
        """开始修复选中的项目"""
        # 获取选中的项目
        items_to_fix = []
        for name, cb in self.fix_checkboxes.items():
            if cb.isChecked():
                items_to_fix.append(name)
        
        if not items_to_fix:
            QMessageBox.information(self, "提示", "没有选择需要修复的项目")
            return
        
        # 检查管理员权限
        if not is_admin():
            msg = QMessageBox(self)
            msg.setWindowTitle("需要管理员权限")
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.setText("网络修复需要管理员权限，请以管理员身份运行程序后重试。")
            msg.exec_()
            return
        
        fix_list = "\n".join([f"  • {item}" for item in items_to_fix])
        reply = QMessageBox.question(
            self, "确认修复",
            f"即将修复以下项目：\n{fix_list}\n\n部分修复需要重启电脑生效，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.fix_btn.setEnabled(False)
        self.diagnose_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("正在修复...")
        
        self.fix_thread = FixThread(items_to_fix)
        self.fix_thread.finished.connect(self.on_fix_finished)
        self.fix_thread.start()
    
    def on_fix_finished(self, results):
        """修复完成"""
        self.progress_bar.setVisible(False)
        self.diagnose_btn.setEnabled(True)
        self.fix_btn.setEnabled(True)
        
        if not results:
            self.status_label.setText("没有执行任何修复操作")
            return
        
        html = "<style>table{width:100%} td{padding:5px} .ok{color:green} .error{color:red}</style>"
        html += "<p><b>修复结果：</b></p><table>"
        
        for name, success, msg in results:
            icon = '\u2705' if success else '\u274c'
            cls = 'ok' if success else 'error'
            html += f'<tr><td>{icon}</td><td><b>{name}</b></td><td class="{cls}">{msg}</td></tr>'
        
        html += "</table>"
        self.result_text.setHtml(html)
        self.status_label.setText("修复完成，部分操作需要重启电脑生效")
        
        # 询问是否重启
        needs_restart = any("重启" in msg for _, success, msg in results if success)
        if needs_restart:
            reply = QMessageBox.question(
                self, "需要重启",
                "部分修复操作需要重启电脑才能生效，是否现在重启？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.system("shutdown /r /t 10 /c \"网络修复完成，10秒后重启\"")
