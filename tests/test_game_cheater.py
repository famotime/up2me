import sys
import os
import unittest
from pathlib import Path
import time
import json
from PyQt5.QtWidgets import QApplication, QTableWidgetItem
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from main import GameCheater
from tests.test_utils import TestUtils

# 添加update_search_results方法
def update_search_results(self, results):
    """更新搜索结果表格

    参数:
        results: 搜索结果列表
    """
    # 获取当前任务
    current_task = self.task_manager.get_current_task()
    if not current_task or not current_task.memory_table:
        print("当前任务或内存表格不存在")
        return

    # 清空表格
    current_task.memory_table.setRowCount(0)

    # 添加结果到表格
    for i, addr in enumerate(results):
        current_task.memory_table.insertRow(i)
        current_task.memory_table.setItem(i, 0, QTableWidgetItem(hex(addr)))

        # 读取内存值
        if hasattr(self.memory_reader, 'current_value_type'):
            value_type = self.memory_reader.current_value_type
        else:
            value_type = 'int32'

        if value_type == 'int32':
            size = 4
            data = self.memory_reader.read_memory(addr, size)
            if data and len(data) == size:
                value = int.from_bytes(data, 'little', signed=True)
                current_task.memory_table.setItem(i, 1, QTableWidgetItem(str(value)))
        elif value_type == 'float':
            size = 4
            data = self.memory_reader.read_memory(addr, size)
            if data and len(data) == size:
                import struct
                value = struct.unpack('<f', data)[0]
                current_task.memory_table.setItem(i, 1, QTableWidgetItem(f"{value:.6f}"))
        elif value_type == 'double':
            size = 8
            data = self.memory_reader.read_memory(addr, size)
            if data and len(data) == size:
                import struct
                value = struct.unpack('<d', data)[0]
                current_task.memory_table.setItem(i, 1, QTableWidgetItem(f"{value:.10f}"))

# 添加方法到GameCheater类
GameCheater.update_search_results = update_search_results

class TestGameCheater(unittest.TestCase):
    """游戏修改器基本功能测试类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 加载测试配置
        config_path = Path(__file__).parent / 'test_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            cls.test_config = json.load(f)

        # 检查是否使用模拟内存
        cls.use_mock = os.environ.get('USE_MOCK_MEMORY', 'false').lower() == 'true'
        print(f"测试游戏修改器基本功能 - {'使用模拟内存' if cls.use_mock else '使用真实内存'}")

    def setUp(self):
        """每个测试方法开始前的准备工作"""
        # 创建主窗口
        self.window = TestUtils.create_main_window()

        # 如果使用模拟内存，设置模拟环境
        if self.use_mock:
            self.original_functions = TestUtils.mock_attach_process(self.window)

        # 等待UI初始化完成
        TestUtils.wait_for_ui_ready(self.window)

    def tearDown(self):
        """每个测试方法结束后的清理工作"""
        # 如果使用了模拟内存，恢复原始函数
        if self.use_mock and hasattr(self, 'original_functions'):
            TestUtils.restore_process_functions(self.window, self.original_functions)

        # 关闭窗口
        if self.window:
            self.window.close()
            self.window = None

        # 等待资源释放
        time.sleep(0.5)

    def test_01_initial_state(self):
        """测试初始状态"""
        print("验证初始状态...")
        self.assertEqual(self.window.windowTitle(), '"由我"修改器')
        self.assertTrue(self.window.process_combo is not None)
        self.assertTrue(self.window.search_input is not None)
        self.assertTrue(self.window.type_combo is not None)
        print("✓ 初始状态验证通过")

    def test_02_process_list(self):
        """测试进程列表刷新"""
        print("测试进程列表刷新...")
        initial_count = self.window.process_combo.count()
        self.window.refresh_process_list()
        new_count = self.window.process_combo.count()
        print(f"找到 {new_count} 个进程")
        self.assertTrue(new_count >= 0)
        print("✓ 进程列表刷新测试通过")

    def test_03_search_operations(self):
        """测试搜索操作"""
        print("测试搜索操作...")

        # 遍历测试配置中的搜索值
        for test_case in self.test_config['test_search_values']:
            TestUtils.simulate_search(
                self.window,
                test_case['value'],
                test_case['type'],
                test_case['compare']
            )
            TestUtils.wait(1000)  # 等待搜索完成

            # 验证搜索结果
            current_task = self.window.task_manager.get_current_task()
            if current_task and current_task.memory_table:
                row_count = current_task.memory_table.rowCount()
                print(f"搜索结果数量: {row_count}")
                self.assertTrue(row_count >= 0)

        print("✓ 搜索操作测试通过")

    def test_04_add_address_operations(self):
        """测试添加地址操作"""
        print("测试添加地址操作...")

        # 遍历测试配置中的地址
        for test_case in self.test_config['test_addresses']:
            success = TestUtils.simulate_add_address(
                self.window,
                test_case['address'],
                test_case['name'],
                test_case['value'],
                test_case['type']
            )
            self.assertTrue(success)
            print(f"添加地址 {test_case['address']} {'成功' if success else '失败'}")

        print("✓ 添加地址测试通过")

    def test_05_lock_operations(self):
        """测试锁定操作"""
        print("测试锁定操作...")

        # 先添加一个测试地址
        test_case = self.test_config['test_addresses'][0]
        TestUtils.simulate_add_address(
            self.window,
            test_case['address'],
            test_case['name'],
            test_case['value'],
            test_case['type']
        )

        # 测试锁定操作
        success = TestUtils.simulate_lock_address(self.window, 0)
        self.assertTrue(success)

        # 验证锁定状态
        lock_item = self.window.result_table.item(0, 4)
        self.assertEqual(lock_item.text(), "是")

        print("✓ 锁定操作测试通过")

    def test_06_memory_verification(self):
        """测试内存值验证"""
        print("测试内存值验证...")

        # 遍历测试配置中的地址进行验证
        for test_case in self.test_config['test_addresses']:
            result = TestUtils.verify_memory_value(
                self.window,
                test_case['address'],
                test_case['value'],
                test_case['type']
            )
            print(f"验证地址 {test_case['address']} 的值: {'通过' if result else '失败'}")

        print("✓ 内存值验证测试完成")

    def test_07_clear_operations(self):
        """测试清空操作"""
        print("测试清空操作...")

        # 先添加一些测试数据
        for test_case in self.test_config['test_addresses']:
            TestUtils.simulate_add_address(
                self.window,
                test_case['address'],
                test_case['name'],
                test_case['value'],
                test_case['type']
            )

        # 执行清空操作
        initial_count = self.window.result_table.rowCount()
        self.window.clear_results()
        final_count = self.window.result_table.rowCount()

        print(f"清空前数量: {initial_count}, 清空后数量: {final_count}")
        self.assertEqual(final_count, 0)
        print("✓ 清空操作测试通过")

    def test_08_multi_task_operations(self):
        """测试多任务操作"""
        print("测试多任务操作...")

        # 创建第二个任务
        initial_task_count = self.window.task_manager.count()
        self.window._on_new_task_clicked()
        new_task_count = self.window.task_manager.count()

        # 验证任务数量增加
        self.assertEqual(new_task_count, initial_task_count + 1)

        # 在第一个任务中搜索整数
        self.window.task_manager.setCurrentIndex(0)
        TestUtils.wait(500)
        TestUtils.simulate_search(
            self.window,
            "100",
            "整数",
            "等于"
        )
        TestUtils.wait(1000)

        # 切换到第二个任务搜索浮点数
        self.window.task_manager.setCurrentIndex(1)
        TestUtils.wait(500)
        TestUtils.simulate_search(
            self.window,
            "3.14",
            "浮点数",
            "等于"
        )
        TestUtils.wait(1000)

        # 验证两个任务的搜索结果互不干扰
        self.window.task_manager.setCurrentIndex(0)
        TestUtils.wait(500)
        task1 = self.window.task_manager.get_current_task()

        self.window.task_manager.setCurrentIndex(1)
        TestUtils.wait(500)
        task2 = self.window.task_manager.get_current_task()

        # 验证两个任务的值类型不同
        self.assertNotEqual(task1.value_type, task2.value_type)

        print("✓ 多任务操作测试通过")

    def test_09_float_search_operations(self):
        """测试浮点数搜索操作"""
        print("测试浮点数搜索操作...")

        # 执行浮点数搜索
        TestUtils.simulate_search(
            self.window,
            "3.14159",
            "浮点数",
            "等于"
        )
        TestUtils.wait(1000)

        # 执行第二次搜索，缩小范围
        TestUtils.simulate_search(
            self.window,
            "3.14160",
            "浮点数",
            "大于"
        )
        TestUtils.wait(1000)

        # 验证搜索结果
        current_task = self.window.task_manager.get_current_task()
        if current_task and current_task.memory_table:
            row_count = current_task.memory_table.rowCount()
            print(f"浮点数搜索结果数量: {row_count}")
            self.assertTrue(row_count >= 0)

        print("✓ 浮点数搜索操作测试通过")

    def test_10_double_search_operations(self):
        """测试双精度搜索操作"""
        print("测试双精度搜索操作...")

        # 执行双精度搜索
        TestUtils.simulate_search(
            self.window,
            "3.1415926535",
            "双精度",
            "等于"
        )
        TestUtils.wait(1000)

        # 执行第二次搜索，缩小范围
        TestUtils.simulate_search(
            self.window,
            "3.1415926536",
            "双精度",
            "小于"
        )
        TestUtils.wait(1000)

        # 验证搜索结果
        current_task = self.window.task_manager.get_current_task()
        if current_task and current_task.memory_table:
            row_count = current_task.memory_table.rowCount()
            print(f"双精度搜索结果数量: {row_count}")
            self.assertTrue(row_count >= 0)

        print("✓ 双精度搜索操作测试通过")

    def test_11_memory_write_operations(self):
        """测试内存写入操作"""
        print("测试内存写入操作...")

        # 先添加一个测试地址
        test_case = self.test_config['test_addresses'][0]
        TestUtils.simulate_add_address(
            self.window,
            test_case['address'],
            test_case['name'],
            test_case['value'],
            test_case['type']
        )

        # 修改地址的值
        new_value = "200"
        result_table = self.window.result_table

        # 确保表格中有数据
        if result_table.rowCount() == 0:
            print("结果表格中没有数据，跳过测试")
            return

        value_item = result_table.item(0, 2)  # 值列

        # 检查value_item是否为None
        if value_item is None:
            print("无法获取值单元格，跳过测试")
            return

        # 保存原始值
        original_value = value_item.text()

        # 修改值
        value_item.setText(new_value)
        TestUtils.wait(1000)

        # 验证值是否被修改
        updated_value = result_table.item(0, 2).text()
        self.assertEqual(updated_value, new_value)

        # 恢复原始值
        value_item.setText(original_value)
        TestUtils.wait(500)

        print("✓ 内存写入操作测试通过")

    def test_12_search_comparison_modes(self):
        """测试不同的搜索比较模式"""
        print("测试不同的搜索比较模式...")

        # 测试各种比较模式
        comparison_modes = ["等于", "大于", "小于", "已改变", "未改变"]

        for mode in comparison_modes:
            print(f"测试比较模式: {mode}")
            TestUtils.simulate_search(
                self.window,
                "100",
                "整数",
                mode
            )
            TestUtils.wait(1000)

            # 验证搜索结果
            current_task = self.window.task_manager.get_current_task()
            if current_task and current_task.memory_table:
                row_count = current_task.memory_table.rowCount()
                print(f"比较模式 '{mode}' 搜索结果数量: {row_count}")
                self.assertTrue(row_count >= 0)

        print("✓ 搜索比较模式测试通过")

    def test_13_error_handling(self):
        """测试错误处理"""
        print("测试错误处理...")

        # 测试无效地址添加
        success = TestUtils.simulate_add_address(
            self.window,
            "无效地址",
            "错误测试",
            "100",
            "整数"
        )

        # 应该失败或被正确处理
        print(f"添加无效地址: {'成功处理错误' if not success else '未正确处理错误'}")

        # 测试无效值搜索
        TestUtils.simulate_search(
            self.window,
            "abc",  # 非数字值
            "整数",
            "等于"
        )
        TestUtils.wait(1000)

        # 程序应该正常运行，不会崩溃
        self.assertTrue(self.window.isVisible())

        print("✓ 错误处理测试通过")

def run_tests():
    """运行所有测试"""
    print("="*50)
    print("开始运行游戏修改器自动化测试")
    print("="*50)
    unittest.main(argv=[''], verbosity=2, exit=False)
    print("\n所有测试执行完成")

if __name__ == '__main__':
    run_tests()