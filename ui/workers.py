from PyQt5.QtCore import QThread, pyqtSignal
import random
from core.api import WeLearnClient

class LoginThread(QThread):
    """登录线程"""

    login_result = pyqtSignal(bool, str)

    def __init__(self, client: WeLearnClient, username, password):
        super().__init__()
        self.client = client
        self.username = username
        self.password = password

    def run(self):
        success, message = self.client.login(self.username, self.password)
        self.login_result.emit(success, message)


class CourseThread(QThread):
    """获取课程线程"""

    course_result = pyqtSignal(bool, list, str)

    def __init__(self, client: WeLearnClient):
        super().__init__()
        self.client = client

    def run(self):
        success, courses, message = self.client.get_courses()
        self.course_result.emit(success, courses, message)


class UnitsThread(QThread):
    """获取单元线程"""

    units_result = pyqtSignal(bool, list, str)

    def __init__(self, client: WeLearnClient, cid):
        super().__init__()
        self.client = client
        self.cid = cid

    def run(self):
        success, data, message = self.client.get_course_info(self.cid)
        if success:
            self.units_result.emit(True, [data], message)
        else:
            self.units_result.emit(False, [], message)


class StudyThread(QThread):
    """学习线程"""

    progress_update = pyqtSignal(str, str)
    study_finished = pyqtSignal(dict)

    def __init__(
        self, client: WeLearnClient, cid, uid, classid, unit_idx, accuracy_config, current_units, max_concurrent=5
    ):
        super().__init__()
        self.client = client
        self.cid = cid
        self.uid = uid
        self.classid = classid
        self.unit_idx = unit_idx
        self.accuracy_config = accuracy_config
        self.current_units = current_units
        self.max_concurrent = max_concurrent  # 最大并发数
        self._stop_flag = False



    def process_single_course(self, course):
        """处理单个课程的作业"""
        from core.logger import get_logger
        logger = get_logger("StudyThread")
        
        if self._stop_flag:
            logger.debug("检测到停止标志，跳过课程")
            return 0, 0, 0, 0  # way1_succeed, way1_failed, way2_succeed, way2_failed
        
        course_location = course.get("location", "未知课程")
        is_visible = course.get("isvisible") != "false"
        is_complete = "未" not in course.get("iscomplete", "")
        
        logger.info(f"处理课程: {course_location}, 可见: {is_visible}, 已完成: {is_complete}")
        
        if not is_visible:
            logger.debug(f"跳过不可见课程: {course_location}")
            self.progress_update.emit("skip", f"[跳过] {course_location}")
            return 0, 0, 0, 0
        
        if is_complete:
            logger.debug(f"跳过已完成课程: {course_location}")
            self.progress_update.emit("completed", f"[已完成] {course_location}")
            return 0, 0, 0, 0
        
        # 处理未完成的课程
        logger.info(f"开始处理未完成课程: {course_location}")
        self.progress_update.emit("start", f"[进行] {course_location}")
        
        if isinstance(self.accuracy_config, tuple):
            accuracy = str(
                random.randint(
                    self.accuracy_config[0], self.accuracy_config[1]
                )
            )
        else:
            accuracy = str(self.accuracy_config)
        
        logger.info(f"提交课程进度: {course_location}, 正确率: {accuracy}%")
        w1_s, w1_f, w2_s, w2_f = self.client.submit_course_progress(
            self.cid, self.uid, self.classid, course["id"], accuracy
        )
        
        status_msg = f"[完成] {course_location} - 正确率: {accuracy}%"
        status_msg += " (步骤1:成功)" if w1_s else " (步骤1:失败)"
        status_msg += " (步骤2:成功)" if w2_s else " (步骤2:失败)"
        
        logger.info(f"课程处理完成: {course_location}, 步骤1: {'成功' if w1_s else '失败'}, 步骤2: {'成功' if w2_s else '失败'}")
        self.progress_update.emit("finish", status_msg)
        
        return w1_s, w1_f, w2_s, w2_f
    def process_unit(self, unit_index):
        from core.logger import get_logger
        from concurrent.futures import ThreadPoolExecutor, as_completed
        logger = get_logger("StudyThread")
        
        logger.info(f"开始处理单元 {unit_index + 1}")
        way1_succeed, way1_failed, way2_succeed, way2_failed = 0, 0, 0, 0

        try:
            logger.info(f"获取单元 {unit_index + 1} 的课程详情")
            success, leaves, message = self.client.get_sco_leaves(
                self.cid, self.uid, self.classid, unit_index
            )
            if not success:
                logger.error(f"获取单元 {unit_index + 1} 详情失败: {message}")
                self.progress_update.emit("error", f"获取单元详情失败: {message}")
                return 0, 0, 0, 0

            logger.info(f"单元 {unit_index + 1} 包含 {len(leaves)} 个课程，使用 {self.max_concurrent} 个线程并发处理")
            
            # 过滤出需要处理的课程（可见且未完成）
            courses_to_process = []
            for i, course in enumerate(leaves):
                course_location = course.get("location", "未知课程")
                is_visible = course.get("isvisible") != "false"
                is_complete = "未" not in course.get("iscomplete", "")
                
                logger.info(f"课程 {i+1}: {course_location}, 可见: {is_visible}, 已完成: {is_complete}")
                
                if is_visible and not is_complete:
                    courses_to_process.append(course)
                elif not is_visible:
                    logger.debug(f"跳过不可见课程: {course_location}")
                    self.progress_update.emit("skip", f"[跳过] {course_location}")
                else:
                    logger.debug(f"跳过已完成课程: {course_location}")
                    self.progress_update.emit("completed", f"[已完成] {course_location}")
            
            if not courses_to_process:
                logger.info(f"单元 {unit_index + 1} 没有需要处理的课程")
                return 0, 0, 0, 0
            
            logger.info(f"单元 {unit_index + 1} 有 {len(courses_to_process)} 个课程需要处理")
            
            # 使用线程池并发处理课程
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                futures = {
                    executor.submit(self.process_single_course, course): course 
                    for course in courses_to_process
                }
                
                for future in as_completed(futures):
                    if self._stop_flag:
                        logger.info("检测到停止标志，取消所有未完成的任务")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    w1_s, w1_f, w2_s, w2_f = future.result()
                    way1_succeed += w1_s
                    way1_failed += w1_f
                    way2_succeed += w2_s
                    way2_failed += w2_f

        except Exception as e:
            logger.error(f"处理单元 {unit_index + 1} 时发生错误: {str(e)}")
            self.progress_update.emit(
                "error", f"处理单元 {unit_index + 1} 时发生错误: {str(e)}"
            )

        logger.info(f"单元 {unit_index + 1} 处理完成 - 步骤1成功: {way1_succeed}, 失败: {way1_failed}, 步骤2成功: {way2_succeed}, 失败: {way2_failed}")
        return way1_succeed, way1_failed, way2_succeed, way2_failed

    def run(self):
        from core.logger import get_logger
        logger = get_logger("StudyThread")
        
        logger.info(f"刷作业线程开始运行 - 课程ID: {self.cid}, 用户ID: {self.uid}, 班级ID: {self.classid}")
        logger.info(f"日志记录器已初始化，日志级别: {logger.level}")
        
        total_way1_succeed, total_way1_failed = 0, 0
        total_way2_succeed, total_way2_failed = 0, 0
        self._stop_flag = False

        try:
            # unit_idx 现在是一个列表
            unit_indices = self.unit_idx if isinstance(self.unit_idx, list) else [self.unit_idx]
            logger.info(f"开始处理 {len(unit_indices)} 个单元")
            
            for unit_index in unit_indices:
                if self._stop_flag:
                    logger.info("检测到停止标志，终止任务执行")
                    break
                

                    
                logger.info(f"开始处理单元 {unit_index + 1}")
                self.progress_update.emit(
                    "unit_start", f"\n=== 开始处理第 {unit_index + 1} 单元 ==="
                )
                result = self.process_unit(unit_index)
                total_way1_succeed += result[0]
                total_way1_failed += result[1]
                total_way2_succeed += result[2]
                total_way2_failed += result[3]
                
                logger.info(f"单元 {unit_index + 1} 处理完成 - 步骤1成功: {result[0]}, 失败: {result[1]}, 步骤2成功: {result[2]}, 失败: {result[3]}")
                self.progress_update.emit(
                    "unit_finish", f"=== 第 {unit_index + 1} 单元处理完成 ===\n"
                )
                


            result = {
                "way1_succeed": total_way1_succeed,
                "way1_failed": total_way1_failed,
                "way2_succeed": total_way2_succeed,
                "way2_failed": total_way2_failed,
            }
            
            logger.info(f"刷作业任务完成 - 总计步骤1成功: {total_way1_succeed}, 失败: {total_way1_failed}, 步骤2成功: {total_way2_succeed}, 失败: {total_way2_failed}")
            self.study_finished.emit(result)

        except Exception as e:
            logger.error(f"刷作业过程中发生错误: {str(e)}")
            self.progress_update.emit("error", f"学习过程中发生错误: {str(e)}")
    
    def stop(self):
        """停止学习"""
        from core.logger import get_logger
        logger = get_logger("StudyThread")
        
        logger.info("收到停止刷作业任务请求")
        self._stop_flag = True
        
        # 立即尝试终止线程
        if self.isRunning():
            logger.info("尝试立即终止刷作业线程")
            self.terminate()


class TimeStudyThread(QThread):
    """刷时长线程 - 支持多单元并行刷时长，充分利用并发数，支持任务进度保存和恢复"""

    progress_update = pyqtSignal(str, str)
    study_finished = pyqtSignal(dict)

    def __init__(
        self, client: WeLearnClient, cid, uid, classid, unit_idx, 
        total_minutes, random_range, current_units, max_concurrent=10
    ):
        super().__init__()
        self.client = client
        self.cid = cid
        self.uid = uid
        self.classid = classid
        self.unit_idx = unit_idx  # 单元索引列表
        self.total_minutes = total_minutes  # 每单元总分钟数
        self.random_range = random_range    # 随机扰动分钟数
        self.current_units = current_units
        self.max_concurrent = max_concurrent
        self._stop_flag = False
        
        # 进度跟踪
        self.completed_units = []
        self.completed_courses = {}
        self.unit_course_data = {}  # 存储每个单元的课程数据
        self.unit_course_times = {}  # 存储每个单元的课程时长



    def calculate_unit_time(self, unit_index, course_count):
        """计算单元总时间和每课程时间"""
        # 添加随机扰动
        actual_minutes = self.total_minutes + random.randint(-self.random_range, self.random_range)
        actual_minutes = max(1, actual_minutes)  # 确保至少1分钟
        total_seconds = actual_minutes * 60
        
        # 平分到每个课程
        per_course_time = total_seconds // course_count if course_count > 0 else total_seconds
        
        # 存储时间信息
        self.unit_course_times[unit_index] = {
            "actual_minutes": actual_minutes,
            "per_course_seconds": per_course_time
        }
        
        return actual_minutes, per_course_time

    def study_single_course(self, course_data):
        """处理单个课程"""
        from core.logger import get_logger
        logger = get_logger("TimeStudyThread")
        
        if self._stop_flag:
            logger.debug("检测到停止标志，跳过课程")
            return False, None
        
        unit_index, chapter = course_data
        course_id = chapter["id"]
        course_location = chapter.get("location", "未知课程")
        

        
        # 获取当前单元的课程时长
        if unit_index not in self.unit_course_times:
            logger.error(f"单元 {unit_index + 1} 的时长信息未计算")
            return False, None
            
        per_course_time = self.unit_course_times[unit_index]["per_course_seconds"]
        
        # 将秒转换为更友好的时间格式显示
        minutes = per_course_time // 60
        seconds = per_course_time % 60
        
        if minutes >= 60:
            hours = minutes // 60
            mins = minutes % 60
            if mins > 0:
                if seconds > 0:
                    time_str = f"{hours}小时{mins}分{seconds}秒"
                else:
                    time_str = f"{hours}小时{mins}分钟"
            else:
                if seconds > 0:
                    time_str = f"{hours}小时{seconds}秒"
                else:
                    time_str = f"{hours}小时"
        else:
            if minutes > 0:
                time_str = f"{minutes}分{seconds}秒" if seconds > 0 else f"{minutes}分钟"
            else:
                time_str = f"{seconds}秒"
        
        logger.info(f"开始刷课程时长: 单元{unit_index + 1} - {course_location}, 时长: {time_str}")
        self.progress_update.emit(
            "start", f"[单元{unit_index + 1}] {course_location} - {time_str}"
        )
        
        logger.debug(f"调用simulate_time方法: 课程ID={course_id}, 时长={per_course_time}秒")
        success = self.client.simulate_time(self.cid, self.uid, course_id, per_course_time)
        
        if success:
            logger.info(f"课程时长刷取成功: 单元{unit_index + 1} - {course_location}")
            self.progress_update.emit(
                "finish", f"[完成] 单元{unit_index + 1} - {course_location}"
            )
            

        else:
            logger.error(f"课程时长刷取失败: 单元{unit_index + 1} - {course_location}")
            self.progress_update.emit("error", f"[失败] 单元{unit_index + 1} - {course_location}")
        
        return success, course_id if success else None



    def _prepare_all_courses(self):
        """准备所有单元的课程数据"""
        from core.logger import get_logger
        logger = get_logger("TimeStudyThread")
        
        all_courses = []
        
        # 获取所有单元的课程
        for unit_index in self.unit_idx:
            if self._stop_flag:
                break
                

                
            logger.info(f"获取单元 {unit_index + 1} 的课程详情")
            success, leaves, message = self.client.get_sco_leaves(
                self.cid, self.uid, self.classid, unit_index
            )
            
            if not success:
                logger.error(f"单元 {unit_index + 1}: 获取失败 - {message}")
                self.progress_update.emit("error", f"单元 {unit_index + 1}: 获取失败 - {message}")
                continue
            
            # 过滤可见的课程
            visible_chapters = [ch for ch in leaves if ch.get("isvisible") != "false"]
            logger.info(f"单元 {unit_index + 1}: 发现 {len(visible_chapters)} 个可见课程")
            
            if not visible_chapters:
                logger.info(f"单元 {unit_index + 1}: 没有可刷的课程")
                self.progress_update.emit("skip", f"单元 {unit_index + 1}: 没有可刷的课程")
                continue
            
            # 计算当前单元的课程时长
            actual_minutes, per_course_seconds = self.calculate_unit_time(unit_index, len(visible_chapters))
            
            # 格式化时间显示
            if actual_minutes >= 60:
                hours = actual_minutes // 60
                mins = actual_minutes % 60
                if mins > 0:
                    total_time_str = f"{hours}小时{mins}分钟"
                else:
                    total_time_str = f"{hours}小时"
            else:
                total_time_str = f"{actual_minutes}分钟"
            
            per_course_mins = per_course_seconds // 60
            if per_course_mins >= 60:
                hours = per_course_mins // 60
                mins = per_course_mins % 60
                if mins > 0:
                    per_course_str = f"{hours}小时{mins}分钟"
                else:
                    per_course_str = f"{hours}小时"
            else:
                per_course_str = f"{per_course_mins}分钟"
            
            logger.info(f"单元 {unit_index + 1}: 每课程时长 {per_course_str}，单元总时长 {total_time_str}")
            self.progress_update.emit(
                "info", f"单元 {unit_index + 1}: 发现 {len(visible_chapters)} 个课程，每课程时长 {per_course_str}，单元总时长 {total_time_str}"
            )
            
            # 存储单元课程数据
            self.unit_course_data[unit_index] = visible_chapters
            
            # 添加到总课程列表
            for chapter in visible_chapters:
                all_courses.append((unit_index, chapter))
        
        return all_courses

    def run(self):
        from core.logger import get_logger
        from concurrent.futures import ThreadPoolExecutor, as_completed
        logger = get_logger("TimeStudyThread")
        
        logger.info(f"刷时长线程开始运行 - 课程ID: {self.cid}, 用户ID: {self.uid}, 班级ID: {self.classid}, 每单元时长: {self.total_minutes}分钟, 随机范围: ±{self.random_range}分钟, 最大并发: {self.max_concurrent}")
        
        total_success, total_fail = 0, 0
        self._stop_flag = False

        try:
            # 准备所有单元的课程数据
            all_courses = self._prepare_all_courses()
            
            if not all_courses:
                logger.info("没有找到可刷的课程")
                self.progress_update.emit("info", "没有找到可刷的课程")
                result = {
                    "way1_succeed": 0,
                    "way1_failed": 0,
                    "way2_succeed": 0,
                    "way2_failed": 0,
                }
                self.study_finished.emit(result)
                return
            
            logger.info(f"总共发现 {len(all_courses)} 个课程，开始多单元并发处理")
            self.progress_update.emit("info", f"总共发现 {len(all_courses)} 个课程，开始多单元并发处理...")
            
            # 多单元并发处理所有课程
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                # 提交所有课程任务
                futures = {
                    executor.submit(self.study_single_course, course_data): course_data 
                    for course_data in all_courses
                }
                
                # 处理完成的任务
                completed_count = 0
                for future in as_completed(futures):
                    if self._stop_flag:
                        logger.info("检测到停止标志，取消所有未完成的任务")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    success, course_id = future.result()
                    if success:
                        total_success += 1
                    else:
                        total_fail += 1
                    
                    completed_count += 1
                    # 更新进度
                    progress_percent = int(completed_count / len(all_courses) * 100)
                    self.progress_update.emit("progress", f"进度: {completed_count}/{len(all_courses)} ({progress_percent}%)")
            

            
            logger.info(f"刷时长任务完成 - 总计成功: {total_success}, 失败: {total_fail}")
            result = {
                "way1_succeed": total_success,
                "way1_failed": total_fail,
                "way2_succeed": total_success,
                "way2_failed": total_fail,
            }
            self.study_finished.emit(result)

        except Exception as e:
            logger.error(f"刷时长过程中发生错误: {str(e)}")
            self.progress_update.emit("error", f"刷时长过程中发生错误: {str(e)}")
    
    def stop(self):
        """停止刷时长"""
        from core.logger import get_logger
        logger = get_logger("TimeStudyThread")
        
        logger.info("收到停止刷时长任务请求")
        self._stop_flag = True
        
        # 立即尝试终止线程
        if self.isRunning():
            logger.info("尝试立即终止刷时长线程")
            self.terminate()

