from PyQt5.QtWidgets import QTableWidget
from src.memory_helper import update_memory_table
import struct
import logging

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
        self.first_values = {}    # 首次搜索的值 {地址: 值}
        self.prev_values = {}     # 上次搜索的值 {地址: 值}
        self.current_values = {}  # 当前搜索的值 {地址: 值}
        self.logger = logging.getLogger('game_cheater')

    def create_memory_table(self):
        """创建内存表格"""
        from src.ui_helper import create_memory_table
        self.memory_table = create_memory_table()
        return self.memory_table

    def update_results(self, results, memory_reader, status_callback):
        """更新搜索结果"""
        self.search_results = results

        # 读取新的当前值
        new_values = {}
        for addr in results:
            try:
                if memory_reader.current_value_type == 'double':
                    data = memory_reader.read_memory(addr, 8)
                else:
                    data = memory_reader.read_memory(addr, 4)

                if data:
                    if memory_reader.current_value_type == 'int32':
                        value = int.from_bytes(data, 'little', signed=True)
                    elif memory_reader.current_value_type == 'float':
                        value = struct.unpack('<f', data)[0]
                    else:  # double
                        value = struct.unpack('<d', data)[0]
                    new_values[addr] = value

            except Exception as e:
                self.logger.debug(f"读取地址 {hex(addr)} 的值失败: {str(e)}")
                continue

        # 更新历史值
        if self.is_first_search:
            # 首次搜索：设置首次值和当前值，清空先前值
            self.first_values = new_values.copy()
            self.current_values = new_values.copy()
            self.prev_values.clear()
        else:
            # 非首次搜索：先保存当前值到先前值，再更新当前值
            self.prev_values = self.current_values  # 保存当前值到先前值
            self.current_values = new_values  # 更新当前值

        # 更新内存表格
        if self.memory_table:
            update_memory_table(self.memory_table, results, memory_reader, status_callback,
                              self.first_values, self.prev_values, self.current_values)

        self.last_results = results
        self.is_first_search = False

    def clear(self):
        """清空搜索结果"""
        self.search_results = []
        self.last_results = None
        self.first_values.clear()
        self.prev_values.clear()
        self.current_values.clear()
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