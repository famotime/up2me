import json
from pathlib import Path
import time
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
import struct

class TestUtils:
    @staticmethod
    def load_test_config():
        """加载测试配置"""
        config_path = Path(__file__).parent / 'test_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def wait(ms):
        """等待指定的毫秒数"""
        QTest.qWait(ms)

    @staticmethod
    def simulate_search(window, value, value_type, compare_type):
        """模拟搜索操作"""
        print(f"\n模拟搜索: 值={value}, 类型={value_type}, 比较={compare_type}")

        # 设置搜索值
        window.search_input.clear()
        window.search_input.setText(value)

        # 设置值类型
        index = window.type_combo.findText(value_type)
        if index >= 0:
            window.type_combo.setCurrentIndex(index)

        # 设置比较类型
        index = window.compare_combo.findText(compare_type)
        if index >= 0:
            window.compare_combo.setCurrentIndex(index)

        # 触发搜索
        window._on_search_clicked()
        TestUtils.wait(1000)  # 等待搜索完成

    @staticmethod
    def simulate_add_address(window, address, name, value, value_type):
        """模拟添加地址操作"""
        print(f"\n模拟添加地址: 地址={address}, 名称={name}, 值={value}, 类型={value_type}")

        initial_rows = window.result_table.rowCount()

        # 创建新的地址对话框
        dialog = window.AddressDialog(window)

        # 设置对话框的值
        dialog.address_input.setText(address)
        dialog.name_input.setText(name)
        dialog.value_input.setText(value)

        # 设置值类型
        if value_type == '整数':
            dialog.type_int.setChecked(True)
        elif value_type == '浮点':
            dialog.type_float.setChecked(True)
        elif value_type == '双精度':
            dialog.type_double.setChecked(True)

        # 模拟确认
        dialog.accept()
        TestUtils.wait(500)

        return window.result_table.rowCount() > initial_rows

    @staticmethod
    def simulate_lock_address(window, row):
        """模拟锁定地址操作"""
        print(f"\n模拟锁定地址: 行={row}")
        if row < window.result_table.rowCount():
            lock_item = window.result_table.item(row, 4)  # 锁定列
            if lock_item:
                lock_item.setText("是")
                TestUtils.wait(500)
                return True
        return False

    @staticmethod
    def verify_memory_value(window, addr, expected_value, value_type):
        """验证内存值"""
        print(f"\n验证内存值: 地址={addr}, 期望值={expected_value}, 类型={value_type}")
        size = 4  # 默认大小
        if value_type == '双精度':
            size = 8

        value = window.memory_reader.read_memory(int(addr, 16), size)
        if not value:
            return False

        try:
            if value_type == '整数':
                actual = int.from_bytes(value, 'little', signed=True)
                return actual == int(expected_value)
            elif value_type == '浮点':
                actual = struct.unpack('<f', value)[0]
                return abs(actual - float(expected_value)) < 1e-6
            elif value_type == '双精度':
                actual = struct.unpack('<d', value)[0]
                return abs(actual - float(expected_value)) < 1e-6
        except:
            return False

        return False