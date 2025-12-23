import sys
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.main_window import WeLearnUI
from core.logger import logger


def exception_hook(exctype, value, tb):
    """全局异常处理，防止程序闪退"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print(f"未捕获的异常:\n{error_msg}", file=sys.stderr)
    
    # 记录到日志
    logger.critical(f"未捕获的异常:\n{error_msg}")
    
    # 显示错误对话框
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("程序错误")
    msg_box.setText("程序发生错误，但不会退出")
    msg_box.setDetailedText(error_msg)
    msg_box.exec_()


def main():
    # 安装全局异常处理
    sys.excepthook = exception_hook
    
    logger.info("启动WeLearn学习助手")
    
    app = QApplication(sys.argv)
    
    # 设置应用程序退出时清理
    app.aboutToQuit.connect(handle_app_exit)
    
    window = WeLearnUI()
    window.show()
    logger.info("主窗口已显示")
    
    try:
        exit_code = app.exec_()
        logger.info(f"程序退出，退出代码: {exit_code}")
        
        # 确保所有线程都已结束
        import threading
        active_threads = threading.enumerate()
        if len(active_threads) > 1:  # 除了主线程外还有其他线程
            logger.warning(f"程序退出时仍有 {len(active_threads)-1} 个活动线程")
            for thread in active_threads:
                if thread.name != 'MainThread':
                    logger.warning(f"活动线程: {thread.name} (ID: {thread.ident})")
        
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"程序运行时发生异常: {e}")
        logger.exception("异常详情")
        sys.exit(1)


def handle_app_exit():
    """处理应用程序退出事件"""
    logger.info("应用程序退出事件触发，开始清理资源")
    
    # 确保所有线程都已结束
    import threading
    import time
    
    # 获取所有活动线程
    active_threads = threading.enumerate()
    logger.info(f"当前活动线程数量: {len(active_threads)}")
    
    # 等待所有非主线程结束
    for thread in active_threads:
        if (thread.name != 'MainThread' and 
            thread.is_alive() and 
            hasattr(thread, '_target') and 
            not isinstance(thread, threading._DummyThread)):
            logger.info(f"等待线程结束: {thread.name} (ID: {thread.ident})")
            # 最多等待2秒
            thread.join(timeout=2.0)
            if thread.is_alive():
                logger.warning(f"线程 {thread.name} 在2秒后仍在运行")
    
    # 记录最终状态
    final_threads = threading.enumerate()
    if len(final_threads) > 1:
        logger.warning(f"程序退出时仍有 {len(final_threads)-1} 个线程未能正常结束")
    else:
        logger.info("所有线程已正常结束")
    
    logger.info("应用程序退出事件处理完成")

if __name__ == "__main__":
    main()
