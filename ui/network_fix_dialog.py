"""
网络诊断与修复工具箱对话框
"""
import os
import sys
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QProgressBar, QTextEdit, QCheckBox, QMessageBox
)
from PyQt5.QtGui import QPixmap, QIcon, QColor

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
    
    def run(self):
        self.progress.emit("正在执行修复...")
        fixer = NetworkFixer()
        results = fixer.reset_all()
        self.finished.emit(results)


class NetworkFixDialog(QDialog):
    """网络修复工具箱对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("网络诊断与修复工具箱")
        self.setMinimumSize(600, 500)
        self.resize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.set_background()
        self.init_ui()
        self.diagnosis_results = []
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("网络诊断与修复工具箱")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 诊断按钮
        btn_layout = QHBoxLayout()
        self.diagnose_btn = QPushButton("🔍 一键诊断")
        self.diagnose_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.diagnose_btn.clicked.connect(self.start_diagnosis)
        btn_layout.addWidget(self.diagnose_btn)
        
        self.fix_btn = QPushButton("🔧 一键修复")
        self.fix_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.fix_btn.setEnabled(False)
        self.fix_btn.clicked.connect(self.start_fix)
        btn_layout.addWidget(self.fix_btn)
        layout.addLayout(btn_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 诊断结果区
        result_group = QGroupBox("诊断结果")
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
        layout.addWidget(result_group)
        
        # 状态栏
        self.status_label = QLabel('点击"一键诊断"开始检测网络状态')
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)
    
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
            palette = self.palette()
            palette.setBrush(self.backgroundRole(), 
                self.palette().brush(self.backgroundRole()) if not pixmap.isNull() else 
                self.palette().brush(self.backgroundRole()))
            from PyQt5.QtGui import QBrush
            palette.setBrush(self.backgroundRole(), QBrush(pixmap.scaled(
                self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)))
            self.setPalette(palette)
    
    def start_diagnosis(self):
        """开始诊断"""
        self.diagnose_btn.setEnabled(False)
        self.fix_btn.setEnabled(False)
        self.result_text.clear()
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
        
        for r in results:
            status = r['status']
            if status == 'ok':
                icon = '✅'
                cls = 'ok'
            elif status == 'warning':
                icon = '⚠️'
                cls = 'warning'
                has_errors = True
            else:
                icon = '❌'
                cls = 'error'
                has_errors = True
            
            html += f'<tr><td>{icon}</td><td><b>{r["name"]}</b></td><td class="{cls}">{r["detail"]}</td></tr>'
        
        html += "</table>"
        self.result_text.setHtml(html)
        
        if has_errors:
            self.fix_btn.setEnabled(True)
            self.status_label.setText('检测到问题，点击"一键修复"进行修复')
        else:
            self.status_label.setText("网络状态正常，无需修复")
    
    def start_fix(self):
        """开始修复"""
        # 检查管理员权限
        if not is_admin():
            msg = QMessageBox(self)
            msg.setWindowTitle("需要管理员权限")
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.setText("网络修复需要管理员权限，请以管理员身份运行程序后重试。")
            msg.exec_()
            return
        
        reply = QMessageBox.question(
            self, "确认修复",
            "即将执行以下修复操作：\n"
            "• 重置 Winsock\n"
            "• 重置 IP/TCP 协议栈\n"
            "• 刷新 DNS 缓存\n"
            "• 重新获取 DHCP 地址\n"
            "• 重置代理配置\n"
            "• 修复 HOSTS 文件\n\n"
            "部分修复需要重启电脑生效，是否继续？",
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
        
        self.fix_thread = FixThread()
        self.fix_thread.finished.connect(self.on_fix_finished)
        self.fix_thread.start()
    
    def on_fix_finished(self, results):
        """修复完成"""
        self.progress_bar.setVisible(False)
        self.diagnose_btn.setEnabled(True)
        
        html = "<style>table{width:100%} td{padding:5px} .ok{color:green} .error{color:red}</style>"
        html += "<p><b>修复结果：</b></p><table>"
        
        for name, success, msg in results:
            icon = '✅' if success else '❌'
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
