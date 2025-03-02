import sys
import os
import unittest
import time
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QPushButton, QLineEdit
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt, QTimer
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from main import GameCheater
from tests.test_utils import TestUtils

class TestUIResponsiveness(unittest.TestCase):
    """测试UI响应性和多线程功能"""

    @classmethod
    def setUpClass(cls):
        """在所有测试开始前运行一次"""
        cls.app = QApplication(sys.argv)
        cls.config = TestUtils.load_test_config()
        print("\n开始UI响应性测试...")

        # 加载测试配置
        config_path = Path(__file__).parent / 'test_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            cls.test_config = json.load(f)

        # 检查是否使用模拟内存
        cls.use_mock = os.environ.get('USE_MOCK_MEMORY', 'false').lower() == 'true'
        print(f"测试UI响应性 - {'使用模拟内存' if cls.use_mock else '使用真实内存'}")

    def setUp(self):
        """每个测试用例开始前运行"""
        self.window = GameCheater()
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

    def test_01_ui_responsiveness_during_search(self):
        """测试搜索过程中UI响应性"""
        print("测试搜索过程中UI响应性...")

        # 开始一个搜索操作
        TestUtils.simulate_search(
            self.window,
            "100",
            "整数",
            "等于"
        )
        TestUtils.wait(500)  # 等待搜索开始

        # 测试UI响应性 - 尝试点击按钮和输入文本
        response_times = []

        # 测试10次UI响应
        for i in range(10):
            # 记录开始时间
            start_time = time.time()

            # 尝试在搜索输入框中输入文本
            self.window.search_input.clear()
            QTest.keyClicks(self.window.search_input, f"测试{i}")

            # 记录结束时间
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 毫秒
            response_times.append(response_time)

            print(f"UI响应测试 #{i+1}: {response_time:.2f} ms")
            TestUtils.wait(200)  # 等待一段时间再进行下一次测试

        # 计算平均响应时间
        avg_response_time = sum(response_times) / len(response_times)
        print(f"搜索过程中平均UI响应时间: {avg_response_time:.2f} ms")

        # 等待搜索完成
        current_task = self.window.task_manager.get_current_task()
        while current_task and current_task.is_searching:
            TestUtils.wait(100)

        print("✓ 搜索过程中UI响应性测试完成")

    def test_02_button_state_during_search(self):
        """测试搜索过程中按钮状态"""
        print("测试搜索过程中按钮状态...")

        # 获取搜索按钮
        search_button = None
        for button in self.window.findChildren(QPushButton):
            if button.text() == "搜索":
                search_button = button
                break

        if not search_button:
            self.fail("未找到搜索按钮")

        # 验证初始状态
        self.assertTrue(search_button.isEnabled())

        # 开始搜索
        TestUtils.simulate_search(
            self.window,
            "100",
            "整数",
            "等于"
        )
        TestUtils.wait(500)  # 等待搜索开始

        # 验证搜索过程中按钮状态
        current_task = self.window.task_manager.get_current_task()
        if current_task and current_task.is_searching:
            # 搜索过程中按钮应该被禁用
            self.assertFalse(search_button.isEnabled())

        # 等待搜索完成
        while current_task and current_task.is_searching:
            TestUtils.wait(100)

        # 验证搜索完成后按钮状态
        TestUtils.wait(500)  # 等待UI更新
        self.assertTrue(search_button.isEnabled())

        print("✓ 搜索过程中按钮状态测试完成")

    def test_03_status_bar_updates(self):
        """测试状态栏更新"""
        print("测试状态栏更新...")

        # 记录初始状态栏文本
        initial_status = self.window.statusBar().currentMessage()
        print(f"初始状态栏文本: {initial_status}")

        # 开始搜索
        TestUtils.simulate_search(
            self.window,
            "100",
            "整数",
            "等于"
        )
        TestUtils.wait(500)  # 等待搜索开始

        # 记录搜索过程中的状态栏文本
        searching_status = self.window.statusBar().currentMessage()
        print(f"搜索过程中状态栏文本: {searching_status}")

        # 验证状态栏文本已更新
        self.assertNotEqual(initial_status, searching_status)

        # 等待搜索完成
        current_task = self.window.task_manager.get_current_task()
        while current_task and current_task.is_searching:
            TestUtils.wait(100)

        # 记录搜索完成后的状态栏文本
        TestUtils.wait(500)  # 等待UI更新
        final_status = self.window.statusBar().currentMessage()
        print(f"搜索完成后状态栏文本: {final_status}")

        # 验证状态栏文本已更新
        self.assertNotEqual(searching_status, final_status)

        print("✓ 状态栏更新测试完成")

    def test_04_multiple_ui_operations(self):
        """测试多个UI操作的响应性"""
        print("测试多个UI操作的响应性...")

        # 执行一系列UI操作并测量响应时间
        operations = [
            ("刷新进程列表", lambda: self.window.refresh_process_list()),
            ("切换值类型", lambda: self.window.type_combo.setCurrentIndex(1)),
            ("切换比较模式", lambda: self.window.compare_combo.setCurrentIndex(1)),
            ("输入搜索值", lambda: self.window.search_input.setText("123")),
            ("清空搜索值", lambda: self.window.search_input.clear()),
            ("创建新任务", lambda: self.window._on_new_task_clicked()),
            ("切换任务", lambda: self.window.task_manager.setCurrentIndex(0))
        ]

        for name, operation in operations:
            # 记录开始时间
            start_time = time.time()

            # 执行操作
            operation()

            # 记录结束时间
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 毫秒

            print(f"操作 '{name}' 响应时间: {response_time:.2f} ms")
            TestUtils.wait(200)  # 等待一段时间再进行下一次操作

        print("✓ 多个UI操作响应性测试完成")

    def test_05_concurrent_operations(self):
        """测试并发操作"""
        print("测试并发操作...")

        # 创建第二个任务
        self.window._on_new_task_clicked()

        # 在第一个任务中开始搜索
        self.window.task_manager.setCurrentIndex(0)
        TestUtils.wait(500)
        TestUtils.simulate_search(
            self.window,
            "100",
            "整数",
            "等于"
        )
        TestUtils.wait(500)  # 等待搜索开始

        # 切换到第二个任务并开始另一个搜索
        self.window.task_manager.setCurrentIndex(1)
        TestUtils.wait(500)

        # 测试在第一个搜索进行时启动第二个搜索
        TestUtils.simulate_search(
            self.window,
            "3.14",
            "浮点数",
            "等于"
        )
        TestUtils.wait(500)  # 等待搜索开始

        # 验证两个任务都在搜索
        task1 = self.window.task_manager.tasks[0]
        task2 = self.window.task_manager.tasks[1]

        # 等待两个搜索都完成
        while task1.is_searching or task2.is_searching:
            TestUtils.wait(100)

        # 验证两个任务都完成了搜索
        self.assertFalse(task1.is_searching)
        self.assertFalse(task2.is_searching)

        print("✓ 并发操作测试完成")

    def test_06_ui_freezing_detection(self):
        """测试UI冻结检测"""
        print("测试UI冻结检测...")

        # 设置一个计时器来检测UI冻结
        freeze_detected = [False]
        freeze_duration = [0]
        last_response_time = [time.time()]

        def check_ui_response():
            # 更新上次响应时间
            current_time = time.time()
            elapsed = current_time - last_response_time[0]

            # 如果响应时间超过1秒，认为UI冻结
            if elapsed > 1.0:
                freeze_detected[0] = True
                freeze_duration[0] = max(freeze_duration[0], elapsed)

            last_response_time[0] = current_time

        # 创建一个定时器，每100毫秒检查一次UI响应
        timer = QTimer()
        timer.timeout.connect(check_ui_response)
        timer.start(100)

        # 开始一个搜索操作
        TestUtils.simulate_search(
            self.window,
            "100",
            "整数",
            "等于"
        )

        # 等待搜索完成
        current_task = self.window.task_manager.get_current_task()
        while current_task and current_task.is_searching:
            # 处理事件，确保定时器回调被执行
            QApplication.processEvents()
            TestUtils.wait(100)

        # 停止定时器
        timer.stop()

        # 报告结果
        if freeze_detected[0]:
            print(f"检测到UI冻结，最长冻结时间: {freeze_duration[0]:.2f} 秒")
        else:
            print("未检测到UI冻结")

        print("✓ UI冻结检测测试完成")

if __name__ == '__main__':
    unittest.main()