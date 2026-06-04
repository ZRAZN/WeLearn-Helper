"""
通用视频背景工具
"""
import os
import sys
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout
from PyQt5.QtCore import QUrl, QSizeF, Qt


def get_app_path():
    """获取应用路径"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_video_path(video_name='ui b.mp4'):
    """获取视频文件路径"""
    app_path = get_app_path()
    video_path = os.path.join(app_path, video_name)
    if not os.path.exists(video_path):
        internal_path = os.path.join(app_path, '_internal')
        if os.path.exists(os.path.join(internal_path, video_name)):
            video_path = os.path.join(internal_path, video_name)
    return video_path if os.path.exists(video_path) else None


def setup_video_background(widget, video_name='ui b.mp4', video_width=1520, video_height=855):
    """为窗口设置视频背景
    
    Args:
        widget: 要设置背景的窗口控件
        video_name: 视频文件名
        video_width: 视频宽度
        video_height: 视频高度
    
    Returns:
        tuple: (graphics_view, content_container, video_player) 或 None
    """
    video_path = get_video_path(video_name)
    
    # 创建图形场景和视图
    graphics_scene = QGraphicsScene()
    graphics_view = QGraphicsView(graphics_scene)
    graphics_view.setStyleSheet("background: black; border: none;")
    graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    graphics_view.viewport().setStyleSheet("background: black;")
    
    # 创建视频项 - 设置为窗口大小
    video_item = QGraphicsVideoItem()
    video_item.setSize(QSizeF(widget.width(), widget.height()))
    graphics_scene.addItem(video_item)
    
    # 创建内容容器 - 设置为窗口大小
    content_container = QWidget()
    content_container.setStyleSheet("background: transparent;")
    content_container.setGeometry(0, 0, widget.width(), widget.height())
    content_proxy = graphics_scene.addWidget(content_container)
    content_proxy.setZValue(1)
    
    # 播放视频
    video_player = None
    if video_path:
        try:
            video_player = QMediaPlayer()
            video_player.setVideoOutput(video_item)
            video_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
            video_player.setVolume(0)
            video_player.mediaStatusChanged.connect(
                lambda s, vp=video_player: (vp.setPosition(0), vp.play()) if s == QMediaPlayer.MediaStatus.EndOfMedia else None
            )
            video_player.play()
        except Exception as e:
            print(f"设置视频背景失败: {e}")
    
    return graphics_view, content_container, video_player
