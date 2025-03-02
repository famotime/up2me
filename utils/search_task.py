from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from utils.memory_helper import update_memory_table
from utils.search_thread import SearchThread
import struct
import logging

class SearchTask:
    """搜索任务类，用于管理单个搜索任务的状态"""
    def __init__(self, name="新任务"):
        self.name = name
        self.display_name = name  # 添加显示名称属性，初始与name相同
        self.memory_table = None
        self.search_results = []
        self.value = None
        self.value_type = None
        self.compare_type = None
        self.is_first_search = True
        self.last_results = None  # 上次搜索结果
        self.first_values = {}    # 首次搜索的值 {地址: 值}
        self.prev_values = {}     # 上次搜索的值 {地址: 值}
        self.current_values = {}  # 当前搜索的值 {地址: 值}
        self.logger = logging.getLogger('game_cheater')
        self.search_thread = None  # 每个任务拥有自己的搜索线程
        self.is_searching = False  # 标记任务是否正在搜索
        self.memory_reader = None  # 保存memory_reader引用

    def create_memory_table(self):
        """创建内存表格"""
        from utils.ui_helper import create_memory_table
        self.memory_table = create_memory_table()
        return self.memory_table

    def start_search(self, memory_reader, status_callback):
        """开始搜索"""
        # 如果已经有搜索线程在运行，则停止它
        if self.is_searching and self.search_thread and self.search_thread.isRunning():
            self.stop_search()
            return False

        # 保存memory_reader引用
        self.memory_reader = memory_reader

        # 注册任务到memory_reader
        memory_reader.register_task(self)

        # 创建并启动搜索线程
        search_params = self.get_search_params()
        self.search_thread = SearchThread(memory_reader, search_params)
        self.search_thread.finished.connect(lambda results: self._on_search_completed(results, memory_reader, status_callback))
        self.search_thread.progress.connect(status_callback)
        self.is_searching = True
        self.search_thread.start()
        return True

    def stop_search(self):
        """停止搜索"""
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.stop()
            self.search_thread.wait()
            self.search_thread = None
            self.is_searching = False

            # 从memory_reader中注销任务
            if hasattr(self, 'memory_reader') and self.memory_reader:
                self.memory_reader.unregister_task(self)

            return True
        return False

    def _on_search_completed(self, results, memory_reader, status_callback):
        """搜索完成的回调函数"""
        self.logger.info(f"搜索任务 '{self.name}' 完成，找到 {len(results)} 个结果")
        # 保存memory_reader引用，用于后续操作
        self.memory_reader = memory_reader

        # 注意：先前值的更新已经在SearchThread中处理，这里不需要重复

        self.update_results(results)
        self.is_searching = False
        self.search_thread = None

    def update_results(self, addresses):
        """更新搜索结果"""
        try:
            if not self.memory_table:
                self.logger.error("更新搜索结果失败：内存表格未初始化")
                return False

            if not addresses:
                self.logger.debug("没有找到匹配的地址")
                self.memory_table.setRowCount(0)
                return True

            # 保存搜索结果
            self.search_results = addresses
            self.last_results = addresses

            # 保存原始值类型，避免影响其他任务
            if not self.memory_reader:
                self.logger.error("更新搜索结果失败：内存读取器未初始化")
                return False

            original_value_type = self.memory_reader.current_value_type
            self.memory_reader.current_value_type = self.value_type

            try:
                # 使用memory_helper中的update_memory_table函数更新表格
                from utils.memory_helper import update_memory_table

                # 更新内存表格
                update_memory_table(
                    self.memory_table,
                    addresses,
                    self.memory_reader,
                    None,  # 不使用状态回调
                    self.first_values,
                    self.prev_values,
                    self.current_values,
                    self.value_type
                )

                self.logger.debug(f"成功更新搜索结果: {len(addresses)} 个地址")
                return True
            except Exception as e:
                self.logger.error(f"更新搜索结果失败: {str(e)}")
                import traceback
                self.logger.debug(traceback.format_exc())
                return False
            finally:
                # 恢复原始值类型，避免影响其他任务
                self.memory_reader.current_value_type = original_value_type
        except Exception as e:
            self.logger.error(f"更新搜索结果时发生未处理异常: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False

    def clear(self):
        """清空搜索结果"""
        # 如果正在搜索，先停止搜索
        if self.is_searching:
            self.stop_search()

        # 清空所有搜索相关数据
        self.search_results = []
        self.last_results = None
        self.first_values.clear()
        self.prev_values.clear()
        self.current_values.clear()
        self.value = None
        self.compare_type = None
        # 不要清除 value_type，因为它是任务的基本属性

        # 确保完全清空表格
        if self.memory_table:
            self.memory_table.setRowCount(0)

            # 如果有内存读取器，确保更新内存表格
            if hasattr(self, 'memory_reader') and self.memory_reader:
                try:
                    from utils.memory_helper import update_memory_table
                    # 保存原始值类型，避免影响其他任务
                    original_value_type = self.memory_reader.current_value_type
                    try:
                        # 更新内存表格（空表格）
                        update_memory_table(
                            self.memory_table,
                            [],
                            self.memory_reader,
                            task_value_type=self.value_type
                        )
                    finally:
                        # 恢复原始值类型，避免影响其他任务
                        self.memory_reader.current_value_type = original_value_type
                except Exception as e:
                    self.logger.error(f"清空内存表格失败: {str(e)}")

        # 重置搜索状态
        self.is_first_search = True

    def get_search_params(self):
        """获取搜索参数"""
        return {
            'value': self.value,
            'value_type': self.value_type,
            'compare_type': self.compare_type,
            'last_results': self.last_results,
            'is_first_search': self.is_first_search
        }