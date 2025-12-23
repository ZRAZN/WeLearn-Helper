"""
任务进度管理器
负责保存和恢复任务进度
"""
import json
import os
import time
from typing import Dict, List, Optional, Any
from core.logger import get_logger

logger = get_logger("TaskProgress")


class TaskProgress:
    """任务进度管理类"""
    
    def __init__(self, progress_file: str = "task_progress.json"):
        """
        初始化任务进度管理器
        
        Args:
            progress_file: 进度文件路径
        """
        self.progress_file = progress_file
        self.progress_data = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """加载进度数据"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载进度文件失败: {str(e)}")
                return {}
        return {}
    
    def _save_progress(self) -> bool:
        """保存进度数据"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存进度文件失败: {str(e)}")
            return False
    
    def save_task_progress(
        self, 
        task_id: str, 
        task_type: str,
        cid: str,
        uid: str,
        classid: str,
        unit_indices: List[int],
        current_units: List[Dict],
        completed_units: List[int],
        completed_courses: Dict[int, List[str]],  # 单元索引 -> 已完成课程ID列表
        task_config: Dict[str, Any]
    ) -> bool:
        """
        保存任务进度
        
        Args:
            task_id: 任务唯一ID
            task_type: 任务类型 (刷作业/刷时长)
            cid: 课程ID
            uid: 用户ID
            classid: 班级ID
            unit_indices: 所有单元索引列表
            current_units: 单元详细信息
            completed_units: 已完成的单元索引列表
            completed_courses: 每个单元已完成的课程ID列表
            task_config: 任务配置参数
        
        Returns:
            bool: 保存是否成功
        """
        try:
            self.progress_data[task_id] = {
                "task_type": task_type,
                "cid": cid,
                "uid": uid,
                "classid": classid,
                "unit_indices": unit_indices,
                "current_units": current_units,
                "completed_units": completed_units,
                "completed_courses": completed_courses,
                "task_config": task_config,
                "last_update_time": time.time(),
                "status": "paused"  # paused, completed
            }
            return self._save_progress()
        except Exception as e:
            logger.error(f"保存任务进度失败: {str(e)}")
            return False
    
    def mark_task_completed(self, task_id: str) -> bool:
        """
        标记任务为已完成
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 操作是否成功
        """
        if task_id in self.progress_data:
            self.progress_data[task_id]["status"] = "completed"
            self.progress_data[task_id]["completion_time"] = time.time()
            return self._save_progress()
        return False
    
    def clear_task_progress(self, task_id: str) -> bool:
        """
        清除指定任务的进度
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 操作是否成功
        """
        if task_id in self.progress_data:
            del self.progress_data[task_id]
            return self._save_progress()
        return False
    
    def get_incomplete_tasks(self) -> List[Dict]:
        """
        获取所有未完成的任务
        
        Returns:
            List[Dict]: 未完成的任务列表
        """
        incomplete_tasks = []
        for task_id, task_data in self.progress_data.items():
            if task_data.get("status") == "paused":
                # 格式化时间戳
                last_update_time = task_data.get("last_update_time", 0)
                if last_update_time:
                    import datetime
                    last_update_time_str = datetime.datetime.fromtimestamp(last_update_time).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    last_update_time_str = "未知"
                
                incomplete_tasks.append({
                    "task_id": task_id,
                    "last_update_time_str": last_update_time_str,
                    **task_data
                })
        return incomplete_tasks
    
    def get_task_progress(self, task_id: str) -> Optional[Dict]:
        """
        获取指定任务的进度
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[Dict]: 任务进度数据，如果不存在则返回None
        """
        return self.progress_data.get(task_id)
    
    def generate_task_id(self, cid: str, uid: str, task_type: str) -> str:
        """
        生成任务ID
        
        Args:
            cid: 课程ID
            uid: 用户ID
            task_type: 任务类型
        
        Returns:
            str: 任务ID
        """
        return f"{task_type}_{cid}_{uid}_{int(time.time())}"