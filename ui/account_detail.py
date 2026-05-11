"""
账号详情对话框
用于单个账号的精细化管理：手动选课、单独执行、查看日志
"""
import os
import sys
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QElapsedTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QTextEdit, QMessageBox,
    QComboBox, QSpinBox, QSplitter, QWidget, QProgressBar
)
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor
from PyQt5.QtMultimedia import QSound
from core.api import WeLearnClient
from core.account_manager import Account


# 直接导入workers模块，避免使用ui.workers
import sys
import os

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 直接导入workers模块
import workers
LoginThread = workers.LoginThread
CourseThread = workers.CourseThread
UnitsThread = workers.UnitsThread
TimeStudyThread = workers.TimeStudyThread
StudyThread = workers.StudyThread


class AccountDetailDialog(QDialog):
    """
    账号详情对话框
    提供单个账号的完整控制：登录、选课、参数设置、执行任务
    """
    
    # 信号：状态更新（用于通知主界面刷新）
    status_updated = pyqtSignal(str, str, str)  # username, status, progress
    
    def __init__(self, account: Account, parent=None):
        super().__init__(parent)
        self.account = account
        self.client = WeLearnClient()  # 每个账号独立的会话
        
        # 状态数据
        self.is_logged_in = False
        self.courses = []
        self.current_course = None
        self.current_units = []
        self.uid = ""
        self.classid = ""
        
        # 线程
        self.login_thread = None
        self.course_thread = None
        self.units_thread = None
        self.study_thread = None  # 刷作业/刷时长通用
        

        
        self.init_ui()
        self.setWindowTitle(f"账号管理 - {account.nickname or account.username}")
        self.setMinimumSize(700, 500)
        # 移除右上角的问号帮助按钮，并添加最小化按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint | Qt.WindowMinimizeButtonHint)
        self.set_background()
    
    def showEvent(self, event):
        """对话框显示时自动登录"""
        super().showEvent(event)
        
        # 如果还没有尝试过自动登录，则自动登录
        if not self.auto_login_attempted and not self.is_logged_in:
            self.auto_login_attempted = True
            # 延迟一点时间再执行登录，确保界面完全显示
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, self.do_login)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # ========== 账号信息 ==========
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"<b>用户名:</b> {self.account.username}"))
        info_layout.addWidget(QLabel(f"<b>昵称:</b> {self.account.nickname or '无'}"))
        self.status_label = QLabel(f"<b>状态:</b> {self.account.status}")
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()
        
        self.login_btn = QPushButton("🔐 登录")
        self.login_btn.clicked.connect(self.do_login)
        info_layout.addWidget(self.login_btn)
        
        layout.addLayout(info_layout)
        
        # 标记是否已自动登录
        self.auto_login_attempted = False
        
        # ========== 分割器：左侧课程选择 + 右侧日志 ==========
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：课程和设置
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 课程列表
        course_group = QGroupBox("课程列表")
        course_layout = QVBoxLayout(course_group)
        
        self.refresh_courses_btn = QPushButton("刷新课程")
        self.refresh_courses_btn.setEnabled(False)
        self.refresh_courses_btn.clicked.connect(self.refresh_courses)
        course_layout.addWidget(self.refresh_courses_btn)
        
        self.courses_list = QListWidget()
        self.courses_list.itemClicked.connect(self.on_course_selected)
        course_layout.addWidget(self.courses_list)
        
        left_layout.addWidget(course_group)
        
        # 任务设置
        settings_group = QGroupBox("任务设置")
        settings_layout = QVBoxLayout(settings_group)
        
        # 当前选中课程
        course_info_layout = QHBoxLayout()
        course_info_layout.addWidget(QLabel("目标课程:"))
        self.current_course_label = QLabel("未选择")
        self.current_course_label.setStyleSheet("color: #666; font-style: italic;")
        course_info_layout.addWidget(self.current_course_label)
        course_info_layout.addStretch()
        settings_layout.addLayout(course_info_layout)
        
        # 单元选择（复选框列表）
        unit_group = QGroupBox("选择单元")
        unit_group_layout = QVBoxLayout(unit_group)
        
        # 全选/取消全选按钮
        select_btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_none_btn = QPushButton("取消全选")
        self.select_all_btn.clicked.connect(self.select_all_units)
        self.select_none_btn.clicked.connect(self.select_none_units)
        select_btn_layout.addWidget(self.select_all_btn)
        select_btn_layout.addWidget(self.select_none_btn)
        select_btn_layout.addStretch()
        unit_group_layout.addLayout(select_btn_layout)
        
        # 单元列表
        self.unit_list = QListWidget()
        self.unit_list.setMaximumHeight(120)
        unit_group_layout.addWidget(self.unit_list)
        
        settings_layout.addWidget(unit_group)
        
        # === 模式选择 ===
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["刷作业", "刷时长"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        settings_layout.addLayout(mode_layout)
        
        # === 刷作业设置 ===
        self.homework_widget = QWidget()
        homework_layout = QVBoxLayout(self.homework_widget)
        homework_layout.setContentsMargins(0, 0, 0, 0)
        
        # 第一行：正确率
        homework_row1 = QHBoxLayout()
        homework_row1.addWidget(QLabel("正确率:"))
        self.accuracy_spin = QSpinBox()
        self.accuracy_spin.setRange(0, 100)
        self.accuracy_spin.setValue(100)
        self.accuracy_spin.setSuffix("%")
        homework_row1.addWidget(self.accuracy_spin)
        homework_row1.addStretch()
        homework_layout.addLayout(homework_row1)
        
        # 第二行：并发数
        homework_row2 = QHBoxLayout()
        homework_row2.addWidget(QLabel("并发数:"))
        self.homework_concurrent_spin = QSpinBox()
        self.homework_concurrent_spin.setRange(1, 20)
        self.homework_concurrent_spin.setValue(5)
        self.homework_concurrent_spin.setToolTip("同时处理多少个课程，越高刷得越快")
        homework_row2.addWidget(self.homework_concurrent_spin)
        homework_row2.addStretch()
        homework_layout.addLayout(homework_row2)
        
        settings_layout.addWidget(self.homework_widget)
        
        # === 刷时长设置 ===
        self.time_widget = QWidget()
        time_layout = QVBoxLayout(self.time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        
        # 第一行：单元总时长
        time_row1 = QHBoxLayout()
        time_row1.addWidget(QLabel("单元时长:"))
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 240)  # 最大240小时
        self.time_spin.setValue(3)  # 默认3小时
        self.time_spin.setToolTip("每个单元的总学习时长")
        time_row1.addWidget(self.time_spin)
        
        # 添加时间单位选择
        self.time_unit_combo = QComboBox()
        self.time_unit_combo.addItems(["小时", "分钟"])
        self.time_unit_combo.setCurrentText("小时")  # 默认选择小时
        self.time_unit_combo.currentTextChanged.connect(self.on_time_unit_changed)
        time_row1.addWidget(self.time_unit_combo)
        
        time_row1.addWidget(QLabel("  随机扰动:"))
        self.time_random_spin = QSpinBox()
        self.time_random_spin.setRange(0, 30)
        self.time_random_spin.setValue(5)
        self.time_random_spin.setSuffix(" 分钟")
        self.time_random_spin.setToolTip("随机增减范围，如设5则实际时长为 55~65 分钟")
        time_row1.addWidget(self.time_random_spin)
        time_row1.addStretch()
        time_layout.addLayout(time_row1)
        
        # 第二行：并发数
        time_row2 = QHBoxLayout()
        time_row2.addWidget(QLabel("并发数:"))
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 100)
        self.concurrent_spin.setValue(90)
        self.concurrent_spin.setToolTip("同时刷多少个课程，越高刷得越快")
        time_row2.addWidget(self.concurrent_spin)
        time_row2.addStretch()
        time_layout.addLayout(time_row2)
        
        settings_layout.addWidget(self.time_widget)
        self.time_widget.hide()  # 默认显示刷作业
        
        left_layout.addWidget(settings_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ 开始刷作业")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_study)
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_study)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        left_layout.addLayout(control_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(left_widget)
        
        # 右侧：日志
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 180);
                border: 1px solid rgba(200, 200, 200, 200);
                border-radius: 5px;
                padding: 5px;
                color: #333333;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        log_layout.addWidget(clear_log_btn)
        
        right_layout.addWidget(log_group)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([350, 350])
        layout.addWidget(splitter)
        
        # 底部倒计时栏
        self.countdown_label = QLabel("⏱ 预计剩余: --:--:--")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.7);
                color: #00FF88;
                font-size: 16px;
                font-weight: bold;
                font-family: Consolas, monospace;
                padding: 8px;
                border-radius: 4px;
            }
        """)
        self.countdown_label.setVisible(False)
        layout.addWidget(self.countdown_label)
        
        # 进度跟踪变量
        self.progress_total = 0
        self.progress_current = 0
        self._task_start_time = None
        self._countdown_timer = QTimer()
        self._countdown_timer.timeout.connect(self._update_countdown)
        self._last_progress_time = 0
        self._avg_per_unit = 0
        self._smoothed_remaining = 0
    
    def log(self, message: str):
        """添加日志"""
        # 添加到UI日志
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
        # 同时记录到全局日志系统
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        logger.info(message)
    

    def update_status(self, status: str, progress: str = ""):
        """更新状态并通知主界面"""
        self.account.status = status
        self.account.progress = progress
        self.status_label.setText(f"<b>状态:</b> {status}")
        self.status_updated.emit(self.account.username, status, progress)
    
    def do_login(self):
        """执行登录"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        logger.info(f"开始登录 - 账号: {self.account.username}")
        self.login_btn.setEnabled(False)
        self.login_btn.setText("登录中...")
        self.log("正在登录...")
        self.update_status("登录中")
        
        logger.info(f"创建登录线程 - 账号: {self.account.username}")
        self.login_thread = LoginThread(self.client, self.account.username, self.account.password)
        self.login_thread.login_result.connect(self.on_login_result)
        self.login_thread.start()
    
    def on_login_result(self, success: bool, message: str):
        """登录结果回调"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        self.login_btn.setEnabled(True)
        
        if success:
            self.is_logged_in = True
            self.login_btn.setText("✅ 已登录")
            self.login_btn.setEnabled(False)
            self.refresh_courses_btn.setEnabled(True)
            self.log(f"✅ 登录成功")
            logger.info(f"登录成功 - 账号: {self.account.username}")
            self.update_status("已登录")
            # 自动刷新课程
            self.refresh_courses()
        else:
            self.login_btn.setText("🔐 登录")
            self.log(f"❌ 登录失败: {message}")
            logger.error(f"登录失败 - 账号: {self.account.username}, 错误: {message}")
            self.update_status("登录失败", message)
            msg_box = QMessageBox(QMessageBox.Warning, "登录失败", message)
            # 移除问号帮助按钮
            msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg_box.exec_()
    
    def refresh_courses(self):
        """刷新课程列表"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        logger.info(f"开始获取课程列表 - 账号: {self.account.username}")
        self.refresh_courses_btn.setEnabled(False)
        self.refresh_courses_btn.setText("获取中...")
        self.log("正在获取课程列表...")
        
        logger.info(f"创建课程获取线程 - 账号: {self.account.username}")
        self.course_thread = CourseThread(self.client)
        self.course_thread.course_result.connect(self.on_courses_result)
        self.course_thread.start()
    
    def on_courses_result(self, success: bool, courses: list, message: str):
        """课程列表结果回调"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        self.refresh_courses_btn.setEnabled(True)
        self.refresh_courses_btn.setText("刷新课程")
        
        if success:
            self.courses = courses
            self.courses_list.clear()
            course_names = []
            for course in courses:
                item = QListWidgetItem(f"{course['name']} (进度: {course['per']}%)")
                item.setData(Qt.ItemDataRole.UserRole, course)
                self.courses_list.addItem(item)
                course_names.append(course['name'])
            self.log(f"✅ 获取到 {len(courses)} 门课程")
            logger.info(f"课程列表获取成功 - 账号: {self.account.username}, 课程数量: {len(courses)}, 课程: {', '.join(course_names)}")
        else:
            self.log(f"❌ 获取课程失败: {message}")
            logger.error(f"课程列表获取失败 - 账号: {self.account.username}, 错误: {message}")
            msg_box = QMessageBox(QMessageBox.Warning, "失败", message)
            # 移除问号帮助按钮
            msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg_box.exec_()
    
    def on_course_selected(self, item: QListWidgetItem):
        """选择课程"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        course = item.data(Qt.ItemDataRole.UserRole)
        self.current_course = course
        course_name = course['name']
        course_id = course['cid']
        
        logger.info(f"选择课程 - 账号: {self.account.username}, 课程: {course_name} (ID: {course_id})")
        
        self.current_course_label.setText(course_name)
        self.log(f"选择课程: {course_name}")
        
        # 获取单元信息
        logger.info(f"开始获取单元信息 - 账号: {self.account.username}, 课程ID: {course_id}")
        self.get_units()
    
    def get_units(self):
        """获取单元信息"""
        if not self.current_course:
            return
        
        self.unit_list.clear()
        self.start_btn.setEnabled(False)
        self.log("正在获取单元信息...")
        
        self.units_thread = UnitsThread(self.client, self.current_course['cid'])
        self.units_thread.units_result.connect(self.on_units_result)
        self.units_thread.start()
    
    def on_units_result(self, success: bool, units_data: list, message: str):
        """单元信息结果回调"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        if success and units_data:
            data = units_data[0]
            self.uid = data['uid']
            self.classid = data['classid']
            self.current_units = data['units']
            
            # 填充复选框列表
            self.unit_list.clear()
            unit_names = []
            for i, unit in enumerate(self.current_units):
                unit_name = unit.get('name', f'单元 {i+1}')
                item = QListWidgetItem(f"单元 {i+1}: {unit_name}")
                item.setCheckState(Qt.CheckState.Checked)  # 默认全选
                item.setData(Qt.ItemDataRole.UserRole, i)  # 存储索引
                self.unit_list.addItem(item)
                unit_names.append(unit_name)
            
            self.start_btn.setEnabled(True)
            self.log(f"✅ 获取到 {len(self.current_units)} 个单元")
            logger.info(f"单元列表获取成功 - 账号: {self.account.username}, 课程: {self.current_course['name']}, 单元数量: {len(self.current_units)}, 单元: {', '.join(unit_names)}")
        else:
            self.log(f"❌ 获取单元失败: {message}")
            logger.error(f"单元列表获取失败 - 账号: {self.account.username}, 课程: {self.current_course['name']}, 错误: {message}")
    
    def select_all_units(self):
        """全选单元"""
        for i in range(self.unit_list.count()):
            self.unit_list.item(i).setCheckState(Qt.CheckState.Checked)
    
    def select_none_units(self):
        """取消全选单元"""
        for i in range(self.unit_list.count()):
            self.unit_list.item(i).setCheckState(Qt.CheckState.Unchecked)
    
    def on_mode_changed(self, mode: str):
        """模式切换"""
        if mode == "刷作业":
            self.homework_widget.show()
            self.time_widget.hide()
            self.start_btn.setText("▶️ 开始刷作业")
        else:
            self.homework_widget.hide()
            self.time_widget.show()
            self.start_btn.setText("▶️ 开始刷时长")
    
    def on_time_unit_changed(self, unit: str):
        """时间单位切换"""
        current_value = self.time_spin.value()
        
        if unit == "小时":
            # 从分钟转换为小时
            self.time_spin.setRange(1, 240)  # 最大240小时
            self.time_spin.setValue(max(1, current_value // 60))  # 转换为小时，确保至少1小时
            self.time_random_spin.setSuffix(" 分钟")  # 随机扰动始终以分钟为单位
        else:
            # 从小时转换为分钟
            self.time_spin.setRange(1, 14400)  # 最大14400分钟
            self.time_spin.setValue(max(1, current_value * 60))  # 转换为分钟，确保至少1分钟
            self.time_random_spin.setSuffix(" 分钟")  # 随机扰动始终以分钟为单位
    
    def start_study(self):
        """开始任务"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        logger.info(f"开始执行任务 - 账号: {self.account.username}")
        
        if not self.current_course:
            logger.warning("未选择课程，任务终止")
            msg_box = QMessageBox(QMessageBox.Warning, "警告", "请先选择课程")
            # 移除问号帮助按钮
            msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg_box.exec_()
            return
        
        logger.info(f"已选择课程: {self.current_course['name']} (ID: {self.current_course['cid']})")
        
        # 获取选中的单元
        units_to_process = []
        for i in range(self.unit_list.count()):
            item = self.unit_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                unit_index = item.data(Qt.ItemDataRole.UserRole)
                unit_data = self.current_units[unit_index] if unit_index < len(self.current_units) else {}
                units_to_process.append(unit_index)
                logger.info(f"选中单元: {unit_data.get('name', f'单元 {unit_index+1}')} (索引: {unit_index})")
        
        if not units_to_process:
            logger.warning("未选择任何单元，任务终止")
            msg_box = QMessageBox(QMessageBox.Warning, "警告", "请至少选择一个单元")
            # 移除问号帮助按钮
            msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg_box.exec_()
            return
        
        mode = self.mode_combo.currentText()
        logger.info(f"任务模式: {mode}")
        
        # 添加任务开始前的提醒
        if mode == "刷作业":
            msg_box = QMessageBox(QMessageBox.Information, "任务提醒", 
                                 f"即将开始刷作业任务\n\n课程: {self.current_course['name']}\n选中单元数: {len(units_to_process)} 个\n\n确认要开始吗？")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.Yes)
            # 移除问号帮助按钮
            msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            if msg_box.exec_() != QMessageBox.Yes:
                logger.info("用户取消了刷作业任务")
                return
        else:
            # 获取时间值和单位
            time_value = self.time_spin.value()
            time_unit = self.time_unit_combo.currentText()
            
            # 转换为分钟
            if time_unit == "小时":
                total_minutes = time_value * 60
                time_text = f"{time_value} 小时"
            else:
                total_minutes = time_value
                time_text = f"{time_value} 分钟"
                
            random_range = self.time_random_spin.value()
            concurrent = self.concurrent_spin.value()
            
            # 计算预计完成时间
            estimated_time = total_minutes * len(units_to_process) / concurrent
            hours = int(estimated_time // 60)
            minutes = int(estimated_time % 60)
            seconds = int((estimated_time * 60) % 60)
            
            if hours > 0:
                time_estimate = f"{hours} 小时 {minutes} 分钟 {seconds} 秒"
            else:
                time_estimate = f"{minutes} 分钟 {seconds} 秒"
            
            msg_box = QMessageBox(QMessageBox.Information, "任务提醒", 
                                 f"即将开始刷时长任务\n\n课程: {self.current_course['name']}\n选中单元数: {len(units_to_process)} 个\n每单元时长: {time_text}\n预计完成时间: {time_estimate}\n\n确认要开始吗？")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.Yes)
            # 移除问号帮助按钮
            msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            if msg_box.exec_() != QMessageBox.Yes:
                logger.info("用户取消了刷时长任务")
                return
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_total = 0
        self.progress_current = 0
        self._smoothed_remaining = 0
        
        self._task_start_time = QElapsedTimer()
        self._task_start_time.start()
        self.countdown_label.setText("⏱ 预计剩余: 计算中...")
        self.countdown_label.setVisible(True)
        self._countdown_timer.start(1000)
        
        if mode == "刷作业":
            accuracy_config = self.accuracy_spin.value()
            homework_concurrent = self.homework_concurrent_spin.value()
            logger.info(f"刷作业配置 - 正确率: {accuracy_config}%, 并发数: {homework_concurrent}")
            self.log(f"开始刷作业 (已选 {len(units_to_process)} 个单元, {homework_concurrent} 并发)...")
            self.update_status("运行中")
            
            logger.info(f"创建刷作业线程 - 课程ID: {self.current_course['cid']}, 用户ID: {self.uid}, 班级ID: {self.classid}")
            self.study_thread = StudyThread(
                self.client,
                self.current_course['cid'],
                self.uid,
                self.classid,
                units_to_process,  # 传入单元列表
                accuracy_config,
                self.current_units,
                max_concurrent=homework_concurrent  # 传入并发数
            )
        else:
            # 获取时间值和单位（这些变量在提醒弹窗中已经获取过）
            time_value = self.time_spin.value()
            time_unit = self.time_unit_combo.currentText()
            
            # 转换为分钟
            if time_unit == "小时":
                total_minutes = time_value * 60
            else:
                total_minutes = time_value
                
            random_range = self.time_random_spin.value()
            concurrent = self.concurrent_spin.value()
            
            logger.info(f"刷时长配置 - 每单元时长: {time_value} {time_unit}, 随机范围: ±{random_range} 分钟, 并发数: {concurrent}")
            
            # 根据选择的时间单位显示日志
            if time_unit == "小时":
                self.log(f"开始刷时长 (已选 {len(units_to_process)} 个单元, 每单元 {time_value}±{random_range//60} 小时, {concurrent} 并发)...")
            else:
                self.log(f"开始刷时长 (已选 {len(units_to_process)} 个单元, 每单元 {time_value}±{random_range} 分钟, {concurrent} 并发)...")
                
            self.update_status("运行中")
            
            logger.info(f"创建刷时长线程 - 课程ID: {self.current_course['cid']}, 用户ID: {self.uid}, 班级ID: {self.classid}")
            self.study_thread = TimeStudyThread(
                self.client,
                self.current_course['cid'],
                self.uid,
                self.classid,
                units_to_process,  # 传入单元列表
                total_minutes,     # 每单元总分钟数
                random_range,      # 随机扰动分钟数
                self.current_units,
                max_concurrent=concurrent
            )
        
        logger.info("任务线程创建完成，连接信号并启动")
        self.study_thread.progress_update.connect(self.on_progress_update)
        self.study_thread.study_finished.connect(self.on_study_finished)
        self.study_thread.start()
    
    def stop_study(self):
        """停止任务"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        logger.info(f"用户请求停止任务 - 账号: {self.account.username}, 课程: {self.current_course['name'] if self.current_course else '未选择'}")
        
        if self.study_thread and self.study_thread.isRunning():
            self.log("正在停止任务...")
            logger.info("正在发送停止信号给任务线程")
            
            # 调用线程的stop方法，这会保存进度
            self.study_thread.stop()
            
            # 等待线程结束，最多等待5秒
            self.study_thread.wait(5000)
            
            if self.study_thread.isRunning():
                logger.warning("任务线程在5秒后仍在运行，强制终止")
                self.log("任务未能正常停止，强制终止")
                self.study_thread.terminate()
                self.study_thread.wait(2000)  # 再等待2秒
                
                # 如果仍在运行，使用更强制的方法
                if self.study_thread.isRunning():
                    logger.error("任务线程强制终止失败，使用最终方法")
                    self.log("任务线程无法终止，正在使用最终方法")
                    import os
                    import signal
                    try:
                        # 尝试使用系统信号终止
                        os.kill(self.study_thread.threadId(), signal.SIGTERM)
                    except:
                        pass
            else:
                logger.info("任务线程已正常停止")
                self.log("任务已停止")
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.countdown_label.setVisible(False)
        self._countdown_timer.stop()
        self.log("⏹️ 任务已停止")
        self.update_status("已停止")
    
    def on_progress_update(self, status: str, message: str):
        """进度更新回调"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        if status == "progress_total":
            try:
                self.progress_total = int(message)
                self.progress_bar.setRange(0, self.progress_total)
                self.progress_bar.setValue(0)
            except ValueError:
                pass
            return
        
        if status == "progress_current":
            try:
                self.progress_current = int(message)
                self.progress_bar.setValue(self.progress_current)
                self._update_countdown()
            except ValueError:
                pass
            return
        
        self.log(message)
        logger.debug(f"任务进度更新: {message}")
        self.update_status("运行中", status)
    
    def _update_countdown(self):
        """更新倒计时显示"""
        if self.progress_total <= 0 or self._task_start_time is None:
            return
        
        elapsed = self._task_start_time.elapsed() / 1000.0
        
        if self.progress_current <= 0:
            self.countdown_label.setText("⏱ 预计剩余: 计算中...")
            return
        
        avg_per_unit = elapsed / self.progress_current
        remaining = avg_per_unit * (self.progress_total - self.progress_current)
        
        if self._smoothed_remaining <= 0:
            self._smoothed_remaining = remaining
        else:
            self._smoothed_remaining = self._smoothed_remaining * 0.7 + remaining * 0.3
        
        display_remaining = max(0, self._smoothed_remaining)
        hours = int(display_remaining // 3600)
        minutes = int((display_remaining % 3600) // 60)
        seconds = int(display_remaining % 60)
        
        self.countdown_label.setText(f"⏱ 预计剩余: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def on_study_finished(self, result: dict):
        """任务完成回调"""
        from core.logger import get_logger
        logger = get_logger("AccountDetail")
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self._countdown_timer.stop()
        
        completion_style = """
            QLabel {
                background-color: rgba(76, 175, 80, 0.85);
                color: white;
                font-size: 16px;
                font-weight: bold;
                font-family: Consolas, monospace;
                padding: 8px;
                border-radius: 4px;
            }
        """
        
        if self._task_start_time and self._task_start_time.isValid():
            total_seconds = int(self._task_start_time.elapsed() / 1000)
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            self.countdown_label.setText(f"✅ 任务完成! 总用时: {h:02d}:{m:02d}:{s:02d}")
        else:
            self.countdown_label.setText("✅ 任务已完成!")
        self.countdown_label.setStyleSheet(completion_style)
        self.countdown_label.setVisible(True)
        
        mode = self.mode_combo.currentText()
        if mode == "刷作业":
            msg = f"步骤1成功: {result.get('way1_succeed', 0)}, 失败: {result.get('way1_failed', 0)}\n"
            msg += f"步骤2成功: {result.get('way2_succeed', 0)}, 失败: {result.get('way2_failed', 0)}"
            self.log(f"✅ 刷作业完成！\n{msg}")
            logger.info(f"刷作业任务完成 - 账号: {self.account.username}, 课程: {self.current_course['name']}, 结果: {msg}")
        else:
            completed_units = result.get('completed_units', 0)
            total_units = len(self.current_units) if self.current_units else 0
            self.log(f"✅ 刷时长完成！已完成 {completed_units}/{total_units} 个单元")
            logger.info(f"刷时长任务完成 - 账号: {self.account.username}, 课程: {self.current_course['name']}, 完成单元: {completed_units}/{total_units}")
            

        
        # 播放提示音
        try:
            # 尝试使用系统默认提示音
            import winsound
            winsound.MessageBeep(winsound.MB_OK)
        except Exception as e:
            self.log(f"播放系统提示音失败: {str(e)}")
            # 如果系统提示音失败，尝试使用PyQt5的QSound
            try:
                # 尝试播放系统默认声音
                QSound.play("SystemExclamation")
            except Exception as e2:
                self.log(f"播放QSound提示音也失败: {str(e2)}")
        
        self.update_status("已完成")
        msg_box = QMessageBox(QMessageBox.Information, "完成", "任务已完成！")
        # 移除问号帮助按钮
        msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        msg_box.exec_()
        
        # 清理线程引用
        self.study_thread = None
        logger.debug("任务线程引用已清理")
    
    def closeEvent(self, event):
        """关闭窗口时清理线程"""
        from core.logger import get_logger
        import threading
        import time
        import os
        
        self._countdown_timer.stop()
        
        try:
            import psutil
        except ImportError:
            psutil = None
        
        logger = get_logger("AccountDetail")
        
        logger.info(f"账号详情窗口关闭 - 账号: {self.account.username}")
        logger.info(f"当前进程ID: {os.getpid()}")
        logger.info(f"当前线程ID: {threading.get_ident()}")
        logger.info(f"活动线程数: {threading.active_count()}")
        
        # 记录所有活动线程
        for thread in threading.enumerate():
            logger.info(f"活动线程: {thread.name} (ID: {thread.ident}, 是否运行中: {thread.is_alive()})")
        
        # 记录进程状态
        if psutil is not None:
            try:
                process = psutil.Process(os.getpid())
                logger.info(f"进程状态: {process.status()}")
                logger.info(f"进程内存使用: {process.memory_info().rss / 1024 / 1024:.2f} MB")
                logger.info(f"进程CPU使用率: {process.cpu_percent()}%")
                logger.info(f"进程线程数: {process.num_threads()}")
            except Exception as e:
                logger.error(f"获取进程状态失败: {str(e)}")
        else:
            logger.warning("psutil模块不可用，无法获取详细进程信息")
        
        # 先发送停止信号
        if self.study_thread:
            try:
                logger.info(f"任务线程状态: {self.study_thread.isRunning()}")
                logger.info(f"任务线程是否已停止: {self.study_thread.isFinished()}")
                
                if hasattr(self.study_thread, 'stop'):
                    logger.info("调用线程stop方法")
                    self.study_thread.stop()
                    
                if self.study_thread.isRunning():
                    logger.warning("关闭窗口时发现仍在运行的任务，尝试停止")
                    self.log("正在停止任务...")
                    
                    # 使用quit而不是terminate，确保线程能够正常清理
                    logger.info("调用线程quit方法")
                    self.study_thread.quit()
                    
                    # 增加等待时间，确保线程有足够时间停止
                    logger.info("等待线程停止（3秒）")
                    start_time = time.time()
                    if not self.study_thread.wait(3000):
                        wait_time = time.time() - start_time
                        logger.warning(f"任务线程未能正常停止（等待了{wait_time:.2f}秒），强制终止")
                        self.study_thread.terminate()
                        logger.info("调用线程terminate方法")
                        
                        start_time = time.time()
                        if not self.study_thread.wait(1000):
                            wait_time = time.time() - start_time
                            logger.error(f"强制终止失败（等待了{wait_time:.2f}秒）")
                    
                    # 再次检查，如果还在运行，使用更强制的方式
                    if self.study_thread.isRunning():
                        logger.error("任务线程仍在运行，使用最强制的方式终止")
                        try:
                            # 尝试强制结束线程
                            self.study_thread.terminate()
                            logger.info("再次调用线程terminate方法")
                            # 立即等待，不给线程任何反应时间
                            start_time = time.time()
                            if not self.study_thread.wait(500):
                                wait_time = time.time() - start_time
                                logger.error(f"无法终止任务线程（等待了{wait_time:.2f}秒），程序可能无法正常退出")
                        except Exception as term_error:
                            logger.error(f"强制终止线程时出错: {str(term_error)}")
                
                # 确保线程完全清理
                if self.study_thread:
                    self.study_thread.deleteLater()
                self.study_thread = None
                logger.debug("任务线程已清理")
            except Exception as e:
                logger.error(f"清理任务线程时出错: {str(e)}")
                # 即使出错也要继续清理
                self.study_thread = None
        
        # 关闭客户端连接
        if hasattr(self, 'client') and self.client:
            try:
                # 如果客户端有清理方法，调用它
                if hasattr(self.client, 'close'):
                    self.client.close()
                logger.debug("客户端连接已关闭")
            except Exception as e:
                logger.error(f"关闭客户端连接时出错: {str(e)}")
        
        # 再次记录线程状态
        logger.info(f"关闭后活动线程数: {threading.active_count()}")
        for thread in threading.enumerate():
            logger.info(f"关闭后活动线程: {thread.name} (ID: {thread.ident}, 是否运行中: {thread.is_alive()})")
        
        logger.info(f"账号详情窗口已关闭 - 账号: {self.account.username}")
        event.accept()
    
    def set_background(self):
        # 获取应用程序路径
        if getattr(sys, 'frozen', False):
            # 如果是打包后的应用程序
            if hasattr(sys, '_MEIPASS'):
                # 单文件版本，资源文件在临时目录中
                app_path = sys._MEIPASS
            else:
                # 目录版本
                app_path = os.path.dirname(sys.executable)
                # 检查资源文件是否在根目录
                if not os.path.exists(os.path.join(app_path, 'ZR.ico')):
                    # 如果不在根目录，尝试在_internal目录中查找
                    internal_path = os.path.join(app_path, '_internal')
                    if os.path.exists(os.path.join(internal_path, 'ZR.ico')):
                        app_path = internal_path
        else:
            # 如果是开发环境
            app_path = os.path.dirname(os.path.abspath(__file__))
            app_path = os.path.dirname(app_path)  # 回到项目根目录
        
        # 设置背景图片
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
