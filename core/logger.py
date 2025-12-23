"""
日志管理器
提供程序运行日志记录功能
"""
import os
import sys
import logging
from datetime import datetime


class Logger:
    """日志管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger('WeLearnV4')
        self.logger.setLevel(logging.DEBUG)
        
        # 确定日志文件路径
        if getattr(sys, 'frozen', False):
            # 如果是打包后的可执行程序
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller打包
                app_dir = os.path.dirname(sys.executable)
            else:
                # 其他打包方式
                app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        else:
            # 源代码运行
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 创建logs目录（如果不存在）
        logs_dir = os.path.join(app_dir, "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
        
        # 设置日志文件路径（按日期）
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(logs_dir, f"WeLearnV4_{today}.log")
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到日志器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 记录启动日志
        self.logger.info("=" * 50)
        self.logger.info("WeLearn学习助手V4.6.5 启动")
        self.logger.info(f"日志文件路径: {log_file}")
        self.logger.info("=" * 50)
    
    def debug(self, message):
        """记录调试信息"""
        self.logger.debug(message)
    
    def info(self, message):
        """记录一般信息"""
        self.logger.info(message)
    
    def warning(self, message):
        """记录警告信息"""
        self.logger.warning(message)
    
    def error(self, message):
        """记录错误信息"""
        self.logger.error(message)
    
    def critical(self, message):
        """记录严重错误信息"""
        self.logger.critical(message)
    
    def exception(self, message):
        """记录异常信息（包含堆栈跟踪）"""
        self.logger.exception(message)


# 创建全局日志实例
logger = Logger()

def get_logger(name=None):
    """获取日志记录器
    
    Args:
        name: 日志记录器名称，如果为None则返回默认记录器
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    if name:
        return logging.getLogger(name)
    return logger.logger