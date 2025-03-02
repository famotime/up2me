import sys
import os
import unittest
import time
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from main import GameCheater
from memory_reader import MemoryReader
from tests.test_utils import TestUtils

class TestPerformance(unittest.TestCase):
    """测试内存读写性能和搜索效率"""

    @classmethod
    def setUpClass(cls):
        """在所有测试开始前运行一次"""
        cls.app = QApplication(sys.argv)
        cls.config = TestUtils.load_test_config()
        print("\n开始性能测试...")

        # 加载测试配置
        config_path = Path(__file__).parent / 'test_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            cls.test_config = json.load(f)

        # 检查是否使用模拟内存
        cls.use_mock = os.environ.get('USE_MOCK_MEMORY', 'false').lower() == 'true'
        print(f"测试性能 - {'使用模拟内存' if cls.use_mock else '使用真实内存'}")

    def setUp(self):
        """每个测试用例开始前运行"""
        self.window = GameCheater()
        self.memory_reader = self.window.memory_reader
        print(f"\n运行测试: {self._testMethodName}")

        # 如果使用模拟内存，设置模拟环境
        if self.use_mock:
            self.original_functions = TestUtils.mock_attach_process(self.window)

        # 等待UI初始化完成
        TestUtils.wait_for_ui_ready(self.window)

    def tearDown(self):
        """每个测试用例结束后运行"""
        # 如果使用了模拟内存，恢复原始函数
        if self.use_mock and hasattr(self, 'original_functions'):
            TestUtils.restore_process_functions(self.window, self.original_functions)

        self.window.close()
        print(f"测试完成: {self._testMethodName}")

    def test_01_memory_read_performance(self):
        """测试内存读取性能"""
        print("测试内存读取性能...")

        # 测试不同大小的内存读取性能
        test_sizes = [4, 16, 64, 256, 1024, 4096]
        test_address = 0x12345678  # 测试地址

        for size in test_sizes:
            # 测量读取时间
            start_time = time.time()
            for _ in range(100):  # 重复100次以获得更准确的测量
                self.memory_reader.read_memory(test_address, size)
            end_time = time.time()

            elapsed = end_time - start_time
            print(f"读取 {size} 字节 x 100次: {elapsed:.6f} 秒 (平均: {elapsed/100:.6f} 秒/次)")

        print("✓ 内存读取性能测试完成")

    def test_02_memory_write_performance(self):
        """测试内存写入性能"""
        print("测试内存写入性能...")

        # 测试不同大小的内存写入性能
        test_sizes = [4, 16, 64, 256, 1024]
        test_address = 0x12345678  # 测试地址

        for size in test_sizes:
            # 创建测试数据
            test_data = bytes([0x55] * size)

            # 测量写入时间
            start_time = time.time()
            for _ in range(100):  # 重复100次以获得更准确的测量
                self.memory_reader.write_memory(test_address, test_data)
            end_time = time.time()

            elapsed = end_time - start_time
            print(f"写入 {size} 字节 x 100次: {elapsed:.6f} 秒 (平均: {elapsed/100:.6f} 秒/次)")

        print("✓ 内存写入性能测试完成")

    def test_03_int_search_performance(self):
        """测试整数搜索性能"""
        print("测试整数搜索性能...")

        # 测量整数搜索时间
        start_time = time.time()
        TestUtils.simulate_search(
            self.window,
            "100",
            "整数",
            "等于"
        )
        TestUtils.wait(100)  # 等待搜索开始

        # 等待搜索完成
        current_task = self.window.task_manager.get_current_task()
        while current_task and current_task.is_searching:
            TestUtils.wait(100)

        end_time = time.time()
        elapsed = end_time - start_time

        # 获取搜索结果数量
        row_count = 0
        if current_task and current_task.memory_table:
            row_count = current_task.memory_table.rowCount()

        print(f"整数搜索耗时: {elapsed:.6f} 秒, 找到 {row_count} 个结果")
        print("✓ 整数搜索性能测试完成")

    def test_04_float_search_performance(self):
        """测试浮点数搜索性能"""
        print("测试浮点数搜索性能...")

        # 测量浮点数搜索时间
        start_time = time.time()
        TestUtils.simulate_search(
            self.window,
            "3.14159",
            "浮点数",
            "等于"
        )
        TestUtils.wait(100)  # 等待搜索开始

        # 等待搜索完成
        current_task = self.window.task_manager.get_current_task()
        while current_task and current_task.is_searching:
            TestUtils.wait(100)

        end_time = time.time()
        elapsed = end_time - start_time

        # 获取搜索结果数量
        row_count = 0
        if current_task and current_task.memory_table:
            row_count = current_task.memory_table.rowCount()

        print(f"浮点数搜索耗时: {elapsed:.6f} 秒, 找到 {row_count} 个结果")
        print("✓ 浮点数搜索性能测试完成")

    def test_05_double_search_performance(self):
        """测试双精度搜索性能"""
        print("测试双精度搜索性能...")

        # 测量双精度搜索时间
        start_time = time.time()
        TestUtils.simulate_search(
            self.window,
            "3.1415926535",
            "双精度",
            "等于"
        )
        TestUtils.wait(100)  # 等待搜索开始

        # 等待搜索完成
        current_task = self.window.task_manager.get_current_task()
        while current_task and current_task.is_searching:
            TestUtils.wait(100)

        end_time = time.time()
        elapsed = end_time - start_time

        # 获取搜索结果数量
        row_count = 0
        if current_task and current_task.memory_table:
            row_count = current_task.memory_table.rowCount()

        print(f"双精度搜索耗时: {elapsed:.6f} 秒, 找到 {row_count} 个结果")
        print("✓ 双精度搜索性能测试完成")

    def test_06_parallel_search_performance(self):
        """测试并行搜索性能"""
        print("测试并行搜索性能...")

        # 创建第二个任务
        self.window._on_new_task_clicked()

        # 在第一个任务中搜索整数
        self.window.task_manager.setCurrentIndex(0)
        TestUtils.wait(500)

        # 测量第一个任务搜索时间
        start_time1 = time.time()
        TestUtils.simulate_search(
            self.window,
            "100",
            "整数",
            "等于"
        )
        TestUtils.wait(100)  # 等待搜索开始

        # 切换到第二个任务搜索浮点数
        self.window.task_manager.setCurrentIndex(1)
        TestUtils.wait(500)

        # 测量第二个任务搜索时间
        start_time2 = time.time()
        TestUtils.simulate_search(
            self.window,
            "3.14159",
            "浮点数",
            "等于"
        )
        TestUtils.wait(100)  # 等待搜索开始

        # 等待两个搜索都完成
        all_done = False
        while not all_done:
            TestUtils.wait(100)

            task1 = self.window.task_manager.tasks[0]
            task2 = self.window.task_manager.tasks[1]

            if not task1.is_searching and not task2.is_searching:
                all_done = True

        end_time = time.time()

        # 计算各自的搜索时间
        elapsed1 = end_time - start_time1
        elapsed2 = end_time - start_time2
        total_elapsed = end_time - start_time1

        # 获取搜索结果数量
        self.window.task_manager.setCurrentIndex(0)
        TestUtils.wait(500)
        task1 = self.window.task_manager.get_current_task()
        row_count1 = 0
        if task1 and task1.memory_table:
            row_count1 = task1.memory_table.rowCount()

        self.window.task_manager.setCurrentIndex(1)
        TestUtils.wait(500)
        task2 = self.window.task_manager.get_current_task()
        row_count2 = 0
        if task2 and task2.memory_table:
            row_count2 = task2.memory_table.rowCount()

        print(f"整数搜索耗时: {elapsed1:.6f} 秒, 找到 {row_count1} 个结果")
        print(f"浮点数搜索耗时: {elapsed2:.6f} 秒, 找到 {row_count2} 个结果")
        print(f"总耗时: {total_elapsed:.6f} 秒")
        print("✓ 并行搜索性能测试完成")

    def test_07_memory_scan_efficiency(self):
        """测试内存扫描效率"""
        print("测试内存扫描效率...")

        # 记录内存使用情况
        import psutil
        process = psutil.Process()

        # 测量内存使用前
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # 执行搜索
        TestUtils.simulate_search(
            self.window,
            "100",
            "整数",
            "等于"
        )
        TestUtils.wait(100)  # 等待搜索开始

        # 等待搜索完成
        current_task = self.window.task_manager.get_current_task()
        while current_task and current_task.is_searching:
            TestUtils.wait(100)

        # 测量内存使用后
        memory_after = process.memory_info().rss / 1024 / 1024  # MB

        # 计算内存增长
        memory_increase = memory_after - memory_before

        # 获取搜索结果数量
        row_count = 0
        if current_task and current_task.memory_table:
            row_count = current_task.memory_table.rowCount()

        print(f"搜索前内存使用: {memory_before:.2f} MB")
        print(f"搜索后内存使用: {memory_after:.2f} MB")
        print(f"内存增长: {memory_increase:.2f} MB")
        print(f"找到 {row_count} 个结果")
        print("✓ 内存扫描效率测试完成")

if __name__ == '__main__':
    unittest.main()