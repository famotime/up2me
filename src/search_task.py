from PyQt5.QtWidgets import QTableWidget
from src.memory_helper import update_memory_table

class SearchTask:
    """搜索任务类，用于管理单个搜索任务的状态"""
    def __init__(self, name="新任务"):
        self.name = name
        self.memory_table = None
        self.search_results = []
        self.value = None
        self.value_type = None
        self.compare_type = None
        self.is_first_search = True
        self.last_results = None  # 上次搜索结果

    def create_memory_table(self):
        """创建内存表格"""
        from src.ui_helper import create_memory_table
        self.memory_table = create_memory_table()
        return self.memory_table

    def update_results(self, results, memory_reader, status_callback):
        """更新搜索结果"""
        self.search_results = results
        self.last_results = results  # 保存本次结果为上次结果
        if self.memory_table:
            update_memory_table(self.memory_table, results, memory_reader, status_callback)
        self.is_first_search = False

    def clear(self):
        """清空搜索结果"""
        self.search_results = []
        self.last_results = None
        if self.memory_table:
            self.memory_table.setRowCount(0)
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