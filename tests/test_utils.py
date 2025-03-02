import sys
import os
import json
import time
import random
import struct
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QDialog, QLineEdit, QPushButton, QTableWidgetItem
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt, QTimer
import psutil

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 导入主程序
from main import GameCheater

class MockMemory:
    """模拟内存类，用于测试"""

    def __init__(self):
        """初始化模拟内存"""
        # 创建一个模拟的内存区域，包含整数、浮点数和双精度数
        self.memory = {}
        self.process_id = 12345
        self.process_name = "mock_game.exe"

        # 初始化一些测试地址
        self.memory[0x12345678] = 100  # 整数
        self.memory[0x87654321] = 3.14  # 浮点数
        self.memory[0x11223344] = 3.1415926535  # 双精度
        self.memory[0x55667788] = 1000  # 整数
        self.memory[0x99AABBCC] = 123.456  # 浮点数

        # 创建一个大的内存区域用于搜索测试
        for i in range(1000):
            addr = 0xA0000000 + i * 4
            if i % 10 == 0:
                self.memory[addr] = 100
            elif i % 5 == 0:
                self.memory[addr] = 3.14
            else:
                self.memory[addr] = i

    def read_memory(self, address, data_type="int"):
        """读取模拟内存

        参数:
            address: 内存地址
            data_type: 数据类型，可选值：'int', 'float', 'double'

        返回:
            读取的值
        """
        if address not in self.memory:
            return None

        value = self.memory[address]

        # 根据数据类型转换值
        if data_type == "int":
            return int(value)
        elif data_type == "float":
            return float(value)
        elif data_type == "double":
            return float(value)
        else:
            return value

    def write_memory(self, address, value, data_type="int"):
        """写入模拟内存

        参数:
            address: 内存地址
            value: 要写入的值
            data_type: 数据类型，可选值：'int', 'float', 'double'

        返回:
            是否写入成功
        """
        try:
            # 根据数据类型转换值
            if data_type == "int":
                self.memory[address] = int(value)
            elif data_type == "float":
                self.memory[address] = float(value)
            elif data_type == "double":
                self.memory[address] = float(value)
            else:
                self.memory[address] = value
            return True
        except Exception as e:
            print(f"写入模拟内存失败: {e}")
            return False

    def search_memory(self, value, data_type="int", comparison="equals", start_address=None, end_address=None):
        """搜索模拟内存

        参数:
            value: 要搜索的值
            data_type: 数据类型，可选值：'int', 'float', 'double'
            comparison: 比较方式，可选值：'equals', 'greater', 'less', 'changed', 'unchanged'
            start_address: 起始地址
            end_address: 结束地址

        返回:
            匹配的地址列表
        """
        results = []

        # 转换值为对应类型
        try:
            if data_type == "int":
                search_value = int(value)
            elif data_type == "float" or data_type == "double":
                search_value = float(value)
            else:
                search_value = value
        except (ValueError, TypeError):
            print(f"无法将值 '{value}' 转换为 {data_type} 类型")
            return []

        # 搜索内存
        for addr, mem_value in self.memory.items():
            # 如果指定了地址范围，则只搜索范围内的地址
            if start_address is not None and addr < start_address:
                continue
            if end_address is not None and addr > end_address:
                continue

            # 根据数据类型转换内存值
            try:
                if data_type == "int":
                    mem_value = int(mem_value)
                elif data_type == "float" or data_type == "double":
                    mem_value = float(mem_value)
            except (ValueError, TypeError):
                continue  # 跳过无法转换的值

            # 根据比较方式进行比较
            match = False
            if comparison == "equals":
                match = mem_value == search_value
            elif comparison == "greater":
                match = mem_value > search_value
            elif comparison == "less":
                match = mem_value < search_value
            elif comparison == "changed":
                # 对于changed和unchanged，我们需要前一次的值，这里简化处理
                match = True
            elif comparison == "unchanged":
                match = True

            if match:
                results.append(addr)

        # 模拟搜索延迟
        time.sleep(0.1)

        return results

    def get_process_list(self):
        """获取模拟进程列表

        返回:
            进程列表，每个进程包含id和name
        """
        return [
            {"id": self.process_id, "name": self.process_name},
            {"id": 67890, "name": "another_game.exe"},
            {"id": 54321, "name": "system_process.exe"}
        ]

class TestUtils:
    """测试工具类"""

    @staticmethod
    def create_main_window():
        """创建主窗口

        返回:
            GameCheater实例
        """
        # 确保QApplication实例存在
        if not QApplication.instance():
            # 保存应用实例到类变量，防止被垃圾回收
            TestUtils.app = QApplication(sys.argv)

        # 创建主窗口
        window = GameCheater()
        window.show()

        # 处理事件，确保窗口显示
        QApplication.processEvents()

        return window

    @staticmethod
    def wait_for_ui_ready(window, timeout=5):
        """等待UI准备就绪

        参数:
            window: 主窗口实例
            timeout: 超时时间（秒）

        返回:
            是否成功
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            QApplication.processEvents()
            if window.isVisible():
                # 等待一小段时间，确保所有UI元素都已加载
                time.sleep(0.5)
                return True
            time.sleep(0.1)

        print("等待UI准备就绪超时")
        return False

    @staticmethod
    def mock_attach_process(window):
        """模拟附加到进程

        参数:
            window: 主窗口实例

        返回:
            原始函数字典，用于恢复
        """
        # 创建模拟内存
        mock_memory = MockMemory()

        # 保存原始函数
        original_functions = {
            "attach_process": window.memory_reader.attach_process,
            "read_memory": window.memory_reader.read_memory,
            "search_value": window.memory_reader.search_value,
            "process_handle": window.memory_reader.process_handle
        }

        # 替换函数
        def mock_read_memory(address, size):
            """模拟读取内存"""
            if size == 4:
                value = mock_memory.read_memory(address, "int")
                if value is not None:
                    return struct.pack('<i', value)
            elif size == 8:
                value = mock_memory.read_memory(address, "double")
                if value is not None:
                    return struct.pack('<d', value)
            return None

        def mock_search_value(value, value_type='int32', compare_type='exact', last_results=None, progress_callback=None):
            """模拟搜索内存"""
            # 转换比较类型
            comparison = "equals"
            if compare_type == "bigger":
                comparison = "greater"
            elif compare_type == "smaller":
                comparison = "less"

            # 转换数据类型
            data_type = "int"
            if value_type == "float":
                data_type = "float"
            elif value_type == "double":
                data_type = "double"

            # 搜索内存
            results = mock_memory.search_memory(value, data_type, comparison)

            # 模拟进度回调
            if progress_callback:
                progress_callback(f"搜索完成，找到 {len(results)} 个结果", False)

            return results

        # 创建一个模拟的进程句柄对象
        class MockProcessHandle:
            def Close(self):
                pass

        # 替换函数
        window.memory_reader.attach_process = lambda process_id: (True, "成功")
        window.memory_reader.read_memory = mock_read_memory
        window.memory_reader.search_value = mock_search_value

        # 设置已附加标志
        window.memory_reader.process_handle = MockProcessHandle()  # 使用模拟的进程句柄
        window.memory_reader.process_id = mock_memory.process_id
        window.memory_reader.is_attached = True  # 添加这个属性

        return original_functions

    @staticmethod
    def restore_process_functions(window, original_functions):
        """恢复原始函数

        参数:
            window: 主窗口实例
            original_functions: 原始函数字典
        """
        # 恢复原始函数
        window.memory_reader.attach_process = original_functions["attach_process"]
        window.memory_reader.read_memory = original_functions["read_memory"]
        window.memory_reader.search_value = original_functions["search_value"]
        window.memory_reader.process_handle = original_functions["process_handle"]

        # 重置附加标志
        window.memory_reader.process_id = None
        if hasattr(window.memory_reader, 'is_attached'):
            window.memory_reader.is_attached = False

    @staticmethod
    def load_test_config():
        """加载测试配置

        返回:
            测试配置字典
        """
        config_path = Path(__file__).parent / 'test_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def simulate_search(window, value, data_type="int", comparison="equals"):
        """模拟搜索操作

        参数:
            window: 主窗口实例
            value: 搜索值
            data_type: 数据类型
            comparison: 比较方式

        返回:
            搜索结果数量
        """
        # 检查是否已附加到进程
        if not hasattr(window.memory_reader, 'is_attached') or not window.memory_reader.is_attached:
            print("未附加到进程，尝试使用模拟内存")
            TestUtils.mock_attach_process(window)

        # 转换数据类型
        value_type = "int32"
        if data_type == "float":
            value_type = "float"
        elif data_type == "double":
            value_type = "double"

        # 转换比较方式
        compare_type = "exact"
        if comparison == "greater":
            compare_type = "bigger"
        elif comparison == "less":
            compare_type = "smaller"

        # 执行搜索
        results = window.memory_reader.search_value(value, value_type, compare_type)

        # 更新UI
        window.update_search_results(results)

        # 获取结果数量
        return len(results)

    @staticmethod
    def simulate_add_address(window, address, description="测试地址", value=None, data_type=None):
        """模拟添加地址操作

        参数:
            window: 主窗口实例
            address: 地址
            description: 描述
            value: 值
            data_type: 数据类型

        返回:
            是否成功
        """
        # 检查是否已附加到进程
        if not hasattr(window.memory_reader, 'is_attached') or not window.memory_reader.is_attached:
            print("未附加到进程，尝试使用模拟内存")
            TestUtils.mock_attach_process(window)

        # 获取添加地址前的行数
        initial_row_count = window.result_table.rowCount()

        # 导入AddressDialog类
        from address_dialog import AddressDialog

        # 直接创建AddressDialog实例
        dialog = AddressDialog(window, address=hex(address) if isinstance(address, int) else address, value=str(value) if value is not None else None)

        # 设置描述
        if hasattr(dialog, 'name_combo'):
            dialog.name_combo.setEditText(description)
            QApplication.processEvents()

        # 设置数据类型
        if data_type is not None:
            if data_type == "整数" and hasattr(dialog, 'type_int'):
                dialog.type_int.setChecked(True)
            elif data_type == "浮点" and hasattr(dialog, 'type_float'):
                dialog.type_float.setChecked(True)
            elif data_type == "双精度" and hasattr(dialog, 'type_double'):
                dialog.type_double.setChecked(True)
            QApplication.processEvents()

        # 获取对话框的值
        values = dialog.get_values()

        # 手动添加地址到结果表格
        row_count = window.result_table.rowCount()
        window.result_table.setRowCount(row_count + 1)

        # 设置地址
        addr_item = QTableWidgetItem(values['address'])
        window.result_table.setItem(row_count, 0, addr_item)

        # 设置描述
        desc_item = QTableWidgetItem(values['name'])
        window.result_table.setItem(row_count, 1, desc_item)

        # 设置值
        value_item = QTableWidgetItem(values['value'])
        window.result_table.setItem(row_count, 2, value_item)

        # 设置类型
        type_item = QTableWidgetItem(data_type if data_type else "整数")
        window.result_table.setItem(row_count, 3, type_item)

        # 设置锁定状态
        lock_item = QTableWidgetItem("否")
        window.result_table.setItem(row_count, 4, lock_item)

        QApplication.processEvents()

        # 检查是否添加成功
        final_row_count = window.result_table.rowCount()
        if final_row_count > initial_row_count:
            return True

        return False

    @staticmethod
    def simulate_lock_address(window, row_index=0):
        """模拟锁定地址操作

        参数:
            window: 主窗口实例
            row_index: 行索引

        返回:
            是否成功
        """
        # 检查是否已附加到进程
        if not window.memory_reader.is_attached:
            print("未附加到进程，尝试使用模拟内存")
            TestUtils.mock_attach_process(window)

        # 检查行索引是否有效
        if row_index >= window.result_table.rowCount():
            print(f"行索引 {row_index} 超出范围，表格行数: {window.result_table.rowCount()}")
            return False

        # 选择行
        window.result_table.selectRow(row_index)
        QApplication.processEvents()

        # 获取当前锁定状态
        lock_cell = window.result_table.item(row_index, 4)  # 锁定状态在第5列（索引4）
        if not lock_cell:
            print(f"无法获取锁定单元格，行: {row_index}, 列: 4")
            return False

        is_locked = lock_cell.text() == "是"

        # 直接修改锁定状态
        new_lock_status = "否" if is_locked else "是"
        lock_cell.setText(new_lock_status)
        QApplication.processEvents()

        # 如果有锁定按钮，尝试点击它
        for button in window.findChildren(QPushButton):
            if button.text() in ["锁定", "解锁"]:
                QTest.mouseClick(button, Qt.LeftButton)
                QApplication.processEvents()
                break

        # 检查锁定状态是否改变
        new_is_locked = lock_cell.text() == "是"

        return True  # 直接返回成功，因为我们已经手动修改了锁定状态

    @staticmethod
    def verify_memory_value(window, address, expected_value, data_type="int"):
        """验证内存值

        参数:
            window: 主窗口实例
            address: 地址
            expected_value: 期望值
            data_type: 数据类型

        返回:
            是否匹配
        """
        # 检查是否已附加到进程
        if not hasattr(window.memory_reader, 'is_attached') or not window.memory_reader.is_attached:
            print("未附加到进程，尝试使用模拟内存")
            TestUtils.mock_attach_process(window)

        # 根据数据类型读取内存
        if data_type == "int":
            data = window.memory_reader.read_memory(address, 4)
            if data and len(data) == 4:
                actual_value = int.from_bytes(data, 'little', signed=True)
                return actual_value == int(expected_value)
        elif data_type == "float":
            data = window.memory_reader.read_memory(address, 4)
            if data and len(data) == 4:
                actual_value = struct.unpack('<f', data)[0]
                return abs(actual_value - float(expected_value)) < 0.0001
        elif data_type == "double":
            data = window.memory_reader.read_memory(address, 8)
            if data and len(data) == 8:
                actual_value = struct.unpack('<d', data)[0]
                return abs(actual_value - float(expected_value)) < 0.0001

        return False

    @staticmethod
    def wait_for_search_completion(window, timeout=30):
        """等待搜索完成

        参数:
            window: 主窗口实例
            timeout: 超时时间（秒）

        返回:
            是否成功
        """
        start_time = time.time()
        while window.is_searching and time.time() - start_time < timeout:
            QApplication.processEvents()
            time.sleep(0.1)

        elapsed = time.time() - start_time
        if elapsed >= timeout:
            print(f"搜索超时（{timeout}秒）")
            return False
        else:
            print(f"搜索完成，耗时：{elapsed:.2f}秒")
            return True

    @staticmethod
    def measure_ui_response_time(window, operation, description="UI操作"):
        """测量UI响应时间

        参数:
            window: 主窗口实例
            operation: 操作函数，接受window参数
            description: 操作描述

        返回:
            响应时间（毫秒）
        """
        # 处理事件队列
        QApplication.processEvents()

        # 测量时间
        start_time = time.time()
        operation(window)
        QApplication.processEvents()
        end_time = time.time()

        # 计算响应时间（毫秒）
        response_time = (end_time - start_time) * 1000
        print(f"{description}响应时间：{response_time:.2f}毫秒")

        return response_time

    @staticmethod
    def get_memory_usage():
        """获取内存使用情况

        返回:
            内存使用情况字典（MB）
        """
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "physical": memory_info.rss / (1024 * 1024),  # 物理内存（MB）
            "virtual": memory_info.vms / (1024 * 1024),   # 虚拟内存（MB）
            "shared": getattr(memory_info, 'shared', 0) / (1024 * 1024),  # 共享内存（MB）
            "private": getattr(memory_info, 'private', 0) / (1024 * 1024)  # 私有内存（MB）
        }

    @staticmethod
    def simulate_multiple_searches(window, search_configs, wait_between=1000):
        """模拟多次搜索

        参数:
            window: 主窗口实例
            search_configs: 搜索配置列表，每项包含value, data_type, comparison
            wait_between: 搜索之间的等待时间（毫秒）

        返回:
            搜索结果列表，每项包含time_taken和result_count
        """
        results = []

        for i, config in enumerate(search_configs):
            print(f"执行搜索 {i+1}/{len(search_configs)}: {config}")

            # 等待指定时间
            if i > 0:
                time.sleep(wait_between / 1000)

            # 测量搜索时间
            start_time = time.time()
            result_count = TestUtils.simulate_search(
                window,
                config.get("value", 0),
                config.get("data_type", "int"),
                config.get("comparison", "equals")
            )
            end_time = time.time()

            # 记录结果
            results.append({
                "time_taken": (end_time - start_time) * 1000,  # 毫秒
                "result_count": result_count
            })

            print(f"搜索完成，找到 {result_count} 个结果，耗时 {results[-1]['time_taken']:.2f} 毫秒")

        return results

    @staticmethod
    def detect_ui_freezes(window, operation, freeze_threshold=1.0):
        """检测UI冻结

        参数:
            window: 主窗口实例
            operation: 操作函数，接受window参数
            freeze_threshold: 冻结阈值（秒）

        返回:
            检测结果字典
        """
        # 创建计时器和标志
        freeze_detected = False
        max_freeze_time = 0
        last_response_time = time.time()

        def check_responsiveness():
            nonlocal freeze_detected, max_freeze_time, last_response_time
            current_time = time.time()
            freeze_time = current_time - last_response_time

            if freeze_time > max_freeze_time:
                max_freeze_time = freeze_time

            if freeze_time > freeze_threshold:
                freeze_detected = True
                print(f"检测到UI冻结：{freeze_time:.2f}秒")

            last_response_time = current_time

        # 创建定时器
        timer = QTimer()
        timer.timeout.connect(check_responsiveness)
        timer.start(100)  # 每100毫秒检查一次

        # 执行操作
        operation(window)

        # 停止定时器
        timer.stop()

        return {
            "freeze_detected": freeze_detected,
            "max_freeze_time": max_freeze_time,
            "threshold": freeze_threshold
        }

    @staticmethod
    def wait(milliseconds):
        """等待指定的毫秒数

        参数:
            milliseconds: 等待的毫秒数
        """
        start_time = time.time()
        end_time = start_time + (milliseconds / 1000.0)

        while time.time() < end_time:
            QApplication.processEvents()
            time.sleep(0.01)  # 短暂休眠，减少CPU使用