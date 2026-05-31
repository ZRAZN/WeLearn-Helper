"""
账号管理视图
主界面核心组件 - 显示账号列表、状态和操作按钮
"""
import os
import sys
import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QFileDialog, QMessageBox,
    QLineEdit, QDialog, QHeaderView, QAbstractItemView, QFrame
)
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor
from core.account_manager import AccountManager, Account
from core.logger import logger


class AddAccountDialog(QDialog):
    """添加账号对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加账号")
        self.setModal(True)
        self.setMinimumWidth(300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()
        self.set_background()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        self.set_input_transparency(self.username_input)
        layout.addWidget(QLabel("用户名:"))
        layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.set_input_transparency(self.password_input)
        layout.addWidget(QLabel("密码:"))
        layout.addWidget(self.password_input)
        
        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("昵称（可选，方便识别）")
        self.set_input_transparency(self.nickname_input)
        layout.addWidget(QLabel("昵称:"))
        layout.addWidget(self.nickname_input)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def set_input_transparency(self, input_widget):
        """设置输入框为半透明样式"""
        input_widget.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 180);
                border: 1px solid rgba(200, 200, 200, 200);
                border-radius: 5px;
                padding: 5px;
                color: #333333;
            }
            QLineEdit:focus {
                border: 1px solid rgba(100, 150, 255, 200);
                background-color: rgba(255, 255, 255, 200);
            }
        """)
    
    def get_values(self):
        return (
            self.username_input.text().strip(),
            self.password_input.text().strip(),
            self.nickname_input.text().strip()
        )
    
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
            palette.setBrush(self.backgroundRole(), QBrush(pixmap.scaled(
                self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)))
            self.setPalette(palette)
    
    def resizeEvent(self, event):
        self.set_background()
        super().resizeEvent(event)


class AccountView(QWidget):
    """
    账号管理视图
    主界面的核心组件，显示账号列表并提供操作
    """
    
    open_detail_requested = pyqtSignal(Account)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.account_manager = AccountManager()
        self.init_ui()
        self.set_background()
        # 初始化时加载账户数据
        self.refresh_table()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        toolbar_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ 添加账号")
        self.delete_btn = QPushButton("🗑️ 删除选中")
        self.refresh_btn = QPushButton("🔄 刷新列表")
        self.excel_import_btn = QPushButton("批量导入")
        
        self.add_btn.clicked.connect(self.add_account)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.refresh_btn.clicked.connect(self.refresh_table)
        self.excel_import_btn.clicked.connect(self.import_accounts)
        
        toolbar_layout.addWidget(self.add_btn)
        toolbar_layout.addWidget(self.delete_btn)
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.excel_import_btn)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        layout.addWidget(self._create_separator())
        
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(6)
        self.account_table.setHorizontalHeaderLabels([
            '用户名', '昵称', '状态', '目标课程', '进度', '操作'
        ])
        
        header = self.account_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setDefaultSectionSize(100)
        header.resizeSection(0, 150)
        header.resizeSection(3, 180)
        header.setStretchLastSection(True)
        
        self.account_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.account_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.account_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.account_table.itemDoubleClicked.connect(self.open_detail)
        
        layout.addWidget(self.account_table)
        
        layout.addWidget(self._create_separator())
        
        status_layout = QHBoxLayout()
        self.status_label = QLabel("账号数: 0")
        self.running_label = QLabel("运行中: 0")
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.running_label)
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
    
    @staticmethod
    def _create_separator():
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #999; max-height: 2px; margin: 4px 0;")
        return separator
    
    def add_account(self):
        """添加账号"""
        dialog = AddAccountDialog(self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            username, password, nickname = dialog.get_values()
            
            if not username or not password:
                msg_box = QMessageBox(QMessageBox.Warning, "警告", "用户名和密码不能为空")
                # 移除问号帮助按钮
                msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                msg_box.exec_()
                return
            
            # 检查重复账号
            existing = self.account_manager.get_account(username)
            if existing:
                nickname_text = f"（昵称: {existing.nickname}）" if existing.nickname else ""
                msg_box = QMessageBox(QMessageBox.Warning, "重复账号", 
                    f"用户名 '{username}' 已存在 {nickname_text}\n\n是否要用新密码覆盖现有账号？")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                if msg_box.exec_() == QMessageBox.StandardButton.Yes:
                    # 更新密码
                    self.account_manager.update_account_password(username, password)
                    if nickname:
                        self.account_manager.update_account_nickname(username, nickname)
                    self.refresh_table()
                    msg_box = QMessageBox(QMessageBox.Information, "成功", "账号信息已更新")
                    msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                    msg_box.exec_()
                return
            
            if self.account_manager.add_account(username, password, nickname):
                self.refresh_table()
                msg_box = QMessageBox(QMessageBox.Information, "成功", "账号添加成功")
                # 移除问号帮助按钮
                msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                msg_box.exec_()
            else:
                msg_box = QMessageBox(QMessageBox.Warning, "警告", "该账号已存在")
                # 移除问号帮助按钮
                msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                msg_box.exec_()
    
    def import_accounts(self):
        """从文件导入账号"""
        msg_box = QMessageBox(QMessageBox.Information, 
            "批量导入", 
            "请选择Excel文件进行批量导入\n\n"
            "Excel文件格式要求：\n"
            "• 必须包含\"用户名\"和\"密码\"列\n"
            "• 可选包含\"昵称\"列\n"
            "• 支持中英文列名（用户名/username，密码/password，昵称/nickname）"
        )
        # 移除问号帮助按钮
        msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        msg_box.exec_()
        
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel文件 (*.xlsx *.xls)"
        )
        
        if filepath:
            if filepath.endswith(('.xlsx', '.xls')):
                count, error = self.import_from_excel(filepath)
                if error:
                    msg_box = QMessageBox(QMessageBox.Warning, "导入失败", error)
                    # 移除问号帮助按钮
                    msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                    msg_box.exec_()
                else:
                    self.refresh_table()
                    msg_box = QMessageBox(QMessageBox.Information, "导入成功", f"成功导入 {count} 个账号")
                    # 移除问号帮助按钮
                    msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                    msg_box.exec_()
            else:
                msg_box = QMessageBox(QMessageBox.Warning, "文件格式错误", "请选择Excel文件（.xlsx或.xls格式）")
                # 移除问号帮助按钮
                msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                msg_box.exec_()
    
    def import_from_excel(self, filepath):
        """从Excel文件导入账号"""
        try:
            df = pd.read_excel(filepath, engine='openpyxl')
            
            required_columns = ['用户名', '密码']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                english_columns = ['username', 'password']
                missing_english = [col for col in english_columns if col not in df.columns]
                
                if missing_english:
                    return 0, f"Excel文件中缺少必要的列: {', '.join(missing_columns)} 或 {', '.join(english_columns)}"
                
                username_col = 'username'
                password_col = 'password'
                nickname_col = 'nickname' if 'nickname' in df.columns else None
            else:
                username_col = '用户名'
                password_col = '密码'
                nickname_col = '昵称' if '昵称' in df.columns else None
            
            count = 0
            for index, row in df.iterrows():
                username = str(row[username_col]).strip()
                password = str(row[password_col]).strip()
                nickname = str(row[nickname_col]).strip() if nickname_col and pd.notna(row[nickname_col]) else ""
                
                if username and password:
                    if self.account_manager.add_account(username, password, nickname):
                        count += 1
            
            return count, None
            
        except Exception as e:
            return 0, f"读取Excel文件时出错: {str(e)}"
    
    def export_accounts(self):
        """导出账号到文件"""
        if self.account_manager.get_account_count() == 0:
            msg_box = QMessageBox(QMessageBox.Warning, "警告", "没有账号可导出")
            # 移除问号帮助按钮
            msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg_box.exec_()
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存账号文件", "accounts.txt", "文本文件 (*.txt);;CSV文件 (*.csv)"
        )
        
        if filepath:
            success, error = self.account_manager.export_to_file(filepath)
            if success:
                msg_box = QMessageBox(QMessageBox.Information, "成功", "账号导出成功")
                # 移除问号帮助按钮
                msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                msg_box.exec_()
            else:
                msg_box = QMessageBox(QMessageBox.Warning, "导出失败", error)
                # 移除问号帮助按钮
                msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                msg_box.exec_()
    
    def delete_selected(self):
        """删除选中的账号"""
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            msg_box = QMessageBox(QMessageBox.Warning, "警告", "请先选择要删除的账号")
            # 移除问号帮助按钮
            msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg_box.exec_()
            return
        
        msg_box = QMessageBox(QMessageBox.Question, "确认", f"确定要删除选中的 {len(selected_rows)} 个账号吗？")
        # 移除问号帮助按钮
        msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        reply = msg_box.exec_()
        
        if reply == QMessageBox.StandardButton.Yes:
            # 从后往前删，避免索引问题
            for index in sorted(selected_rows, reverse=True):
                row = index.row()
                username = self.account_table.item(row, 0).text()
                self.account_manager.remove_account(username)
            self.refresh_table()
    
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
            palette.setBrush(self.backgroundRole(), QBrush(pixmap.scaled(
                self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)))
            self.setPalette(palette)
    
    def resizeEvent(self, event):
        # 窗口大小改变时重新设置背景
        self.set_background()
        super().resizeEvent(event)
    
    def on_row_double_clicked(self, index):
        """双击行打开详情"""
        row = index.row()
        username = self.account_table.item(row, 0).text()
        account = self.account_manager.get_account(username)
        if account:
            self.open_detail_requested.emit(account)
    
    def refresh_table(self):
        """刷新账号表格"""
        logger.info("用户点击刷新按钮，开始刷新账号列表")
        # 重新从文件加载账号数据
        self.account_manager.load_accounts()
        accounts = self.account_manager.get_all_accounts()
        self.account_table.setRowCount(len(accounts))
        
        running_count = 0
        
        for i, acc in enumerate(accounts):
            # 用户名
            self.account_table.setItem(i, 0, QTableWidgetItem(acc.username))
            # 昵称
            self.account_table.setItem(i, 1, QTableWidgetItem(acc.nickname or "-"))
            # 状态
            status_item = QTableWidgetItem(acc.status)
            if acc.status == "运行中":
                status_item.setForeground(Qt.GlobalColor.blue)
                running_count += 1
            elif acc.status == "已完成":
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif acc.status == "失败":
                status_item.setForeground(Qt.GlobalColor.red)
            self.account_table.setItem(i, 2, status_item)
            # 目标课程
            target_course = getattr(acc, 'target_course_name', None) or "自动"
            self.account_table.setItem(i, 3, QTableWidgetItem(target_course))
            # 进度
            self.account_table.setItem(i, 4, QTableWidgetItem(acc.progress or "-"))
            # 操作按钮
            manage_btn = QPushButton("管理")
            manage_btn.setProperty("username", acc.username)
            manage_btn.clicked.connect(self.on_manage_clicked)
            self.account_table.setCellWidget(i, 5, manage_btn)
        
        # 更新状态栏
        self.status_label.setText(f"账号数: {len(accounts)}")
        self.running_label.setText(f"运行中: {running_count}")
        logger.info(f"账号列表刷新完成，共 {len(accounts)} 个账号，其中 {running_count} 个运行中")
    
    def on_manage_clicked(self):
        """管理按钮点击"""
        btn = self.sender()
        username = btn.property("username")
        account = self.account_manager.get_account(username)
        if account:
            self.open_detail_requested.emit(account)
    
    def open_detail(self, item):
        """双击表格行打开账号详情"""
        row = item.row()
        username_item = self.account_table.item(row, 0)
        if username_item:
            username = username_item.text()
            account = self.account_manager.get_account(username)
            if account:
                self.open_detail_requested.emit(account)
    
    def update_account_status(self, username: str, status: str, progress: str = ""):
        """更新账号状态（供外部调用）"""
        self.account_manager.update_status(username, status, progress)
        self.refresh_table()
