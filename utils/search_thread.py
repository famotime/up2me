from PyQt5.QtCore import QThread, pyqtSignal, QCoreApplication
import concurrent.futures
import time
import struct
import traceback
import logging

class SearchThread(QThread):
    """搜索线程"""
    progress = pyqtSignal(str, bool)
    # 使用不需要注册的基本类型
    finished = pyqtSignal(object)  # 使用object类型传递Python对象

    def __init__(self, memory_reader, search_params, logger=None):
        super().__init__()
        self.memory_reader = memory_reader
        self.search_params = search_params
        self.logger = logger or logging.getLogger('game_cheater')
        self.is_running = True
        self.thread_id = id(self)

        # 记录线程创建
        self.logger.debug(f"搜索线程 {self.thread_id} 已创建")

        # 进度更新节流控制
        self.last_progress_update = 0
        self.progress_update_interval = 0.1  # 100ms
        self.last_event_process = 0
        self.event_process_interval = 0.05  # 50ms

    def progress_callback(self, message, log=False):
        """进度回调函数"""
        if not self.is_running:
            return

        # 检查消息格式，确保百分比计算正确
        if "正在搜索..." in message and "/" in message:
            try:
                # 提取当前值和总值
                parts = message.split(" ")[1].split("/")
                current = int(parts[0])
                total = int(parts[1].split(" ")[0])

                # 确保current不超过total
                if current > total:
                    current = total

                # 重新计算百分比
                percentage = (current / total * 100) if total > 0 else 0

                # 保留原始消息中的已检查地址数量信息
                if "已检查" in message:
                    checked_info = message.split(" - ")[1]
                    message = f"正在搜索... {current}/{total} ({percentage:.1f}%) - {checked_info}"
                else:
                    message = f"正在搜索... {current}/{total} ({percentage:.1f}%)"
            except (ValueError, IndexError):
                # 如果解析失败，保持原消息不变
                pass

        # 节流进度更新，减少UI卡顿
        current_time = time.time()
        if current_time - self.last_progress_update >= self.progress_update_interval or log:
            # 对于搜索进度信息，强制设置log=False，确保不记录到日志
            if "正在搜索..." in message:
                log = False
            self.progress.emit(message, log)
            self.last_progress_update = current_time

        # 定期处理事件队列，保持UI响应，但频率比进度更新更高
        if current_time - self.last_event_process >= self.event_process_interval:
            QCoreApplication.processEvents()
            self.last_event_process = current_time

    def run(self):
        """运行搜索线程"""
        try:
            # 获取搜索参数
            value = self.search_params.get('value')
            value_type = self.search_params.get('value_type')
            compare_type = self.search_params.get('compare_type')
            last_results = self.search_params.get('last_results')
            is_first_search = self.search_params.get('is_first_search', True)
            task = self.search_params.get('task')  # 获取任务对象

            self.logger.info(f"搜索线程 {self.thread_id} 开始运行: 值={value}, 类型={value_type}, 比较方式={compare_type}")
            if task:
                self.logger.debug(f"关联任务: {task.name}")
            if last_results:
                self.logger.debug(f"上次结果数量: {len(last_results)}")

            # 记录开始时间
            start_time = time.time()

            # 保存原始值类型，避免影响其他任务
            original_value_type = self.memory_reader.current_value_type
            self.logger.debug(f"保存原始值类型: {original_value_type}")

            # 设置当前值类型
            self.memory_reader.current_value_type = value_type
            self.logger.debug(f"设置当前值类型为: {value_type}")

            # 设置搜索线程的运行状态
            self.memory_reader.is_running = True
            self.is_running = True

            try:
                # 转换比较类型
                compare_map = {
                    '精确匹配': 'exact',
                    '大于': 'bigger',
                    '小于': 'smaller',
                    '已改变': 'changed',
                    '未改变': 'unchanged'
                }

                # 对于浮点数和双精度，增加搜索前的日志
                if value_type in ['float', 'double']:
                    self.logger.info(f"开始{value_type}类型搜索: 值={value}, 比较方式={compare_type}")
                    # 记录浮点数的二进制表示，帮助调试
                    if value_type == 'float':
                        binary = struct.pack('<f', float(value))
                        hex_value = ' '.join([f'{b:02x}' for b in binary])
                        self.logger.info(f"浮点数二进制表示: {hex_value}")
                    else:  # double
                        binary = struct.pack('<d', float(value))
                        hex_value = ' '.join([f'{b:02x}' for b in binary])
                        self.logger.info(f"双精度浮点数二进制表示: {hex_value}")

                # 执行搜索
                if is_first_search:
                    self.logger.debug("执行首次搜索")
                    results = self.memory_reader.search_value(
                        value,
                        value_type,
                        compare_map.get(compare_type, 'exact'),
                        None,
                        self.progress_callback
                    )
                else:
                    self.logger.debug("执行后续搜索")
                    results = self.memory_reader.search_value(
                        value,
                        value_type,
                        compare_map.get(compare_type, 'exact'),
                        last_results,
                        self.progress_callback
                    )

                # 对于浮点数和双精度，增加搜索结果的详细日志
                if value_type in ['float', 'double'] and results:
                    self.logger.info(f"{value_type}类型搜索结果: 找到{len(results)}个匹配地址")
                    # 记录前5个结果的值，帮助调试
                    if len(results) > 0:
                        sample_size = min(5, len(results))
                        sample_values = []
                        for i in range(sample_size):
                            addr = results[i]
                            data = self.memory_reader.read_memory(addr, 4 if value_type == 'float' else 8)
                            if data:
                                val = struct.unpack('<f' if value_type == 'float' else '<d', data)[0]
                                sample_values.append(f"{hex(addr)}={val:.10f}")
                        self.logger.info(f"样本值: {', '.join(sample_values)}")

                # 计算搜索耗时
                elapsed_time = time.time() - start_time

                # 更新任务结果
                if task:
                    self.logger.debug(f"更新任务 '{task.name}' 的搜索结果: {len(results)} 个地址")
                    # 确保任务有memory_reader引用
                    if not hasattr(task, 'memory_reader') or task.memory_reader is None:
                        task.memory_reader = self.memory_reader
                        self.logger.debug(f"为任务 '{task.name}' 设置memory_reader引用")

                    # 在调用任务的_on_search_completed方法前，确保先前值已更新
                    if not task.is_first_search and task.current_values:
                        self.logger.debug(f"更新任务 '{task.name}' 的先前值")
                        task.prev_values = task.current_values.copy()
                        task.current_values = {}

                    # 调用任务的_on_search_completed方法，确保传递memory_reader
                    task._on_search_completed(results, self.memory_reader, self.progress_callback)
                    self.logger.debug(f"已调用任务 '{task.name}' 的_on_search_completed方法")

                    # 设置任务状态
                    task.is_first_search = False
                    task.last_results = results

                # 发送完成信号
                self.progress.emit(f"搜索完成: 找到 {len(results)} 个匹配地址 (耗时: {elapsed_time:.2f}秒)", True)
                self.finished.emit(results)
                self.logger.debug(f"搜索线程 {self.thread_id} 完成，找到 {len(results)} 个结果，耗时 {elapsed_time:.2f}秒")
            except Exception as e:
                self.logger.error(f"搜索过程中出错: {str(e)}")
                import traceback
                self.logger.error(f"错误详情: {traceback.format_exc()}")
                self.progress.emit(f"搜索失败: {str(e)}", True)
                self.finished.emit([])
        except Exception as e:
            self.progress.emit(f"搜索失败: {str(e)}", True)
            self.logger.error(f"搜索线程 {self.thread_id} 失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
            self.finished.emit([])
        finally:
            # 恢复原始值类型，避免影响其他任务
            self.memory_reader.current_value_type = original_value_type
            # 重置memory_reader的运行状态
            self.memory_reader.is_running = False

    def stop(self):
        """停止搜索线程"""
        self.is_running = False
        self.memory_reader.is_running = False
        self.logger.debug(f"搜索线程 {self.thread_id} 被请求停止")