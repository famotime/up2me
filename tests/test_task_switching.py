import sys
import os
import unittest
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
import time
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from main import GameCheater

# 导入测试工具类
from tests.test_utils import TestUtils

class TestTaskSwitching(unittest.TestCase):
    """测试任务切换功能"""

    @classmethod
    def setUpClass(cls):
        """在所有测试之前运行一次"""
        # 创建QApplication实例
        cls.app = QApplication(sys.argv)

        # 设置日志
        cls.logger = logging.getLogger('test_task_switching')
        cls.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        cls.logger.addHandler(handler)

        # 设置游戏修改器日志级别为DEBUG
        game_logger = logging.getLogger('game_cheater')
        game_logger.setLevel(logging.DEBUG)
        if not game_logger.handlers:
            game_handler = logging.StreamHandler()
            game_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            game_logger.addHandler(game_handler)

        # 加载测试配置
        config_path = Path(__file__).parent / 'test_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            cls.test_config = json.load(f)

        # 检查是否使用模拟内存
        cls.use_mock = os.environ.get('USE_MOCK_MEMORY', 'false').lower() == 'true'
        print(f"测试任务切换 - {'使用模拟内存' if cls.use_mock else '使用真实内存'}")

    def setUp(self):
        """每个测试方法之前运行"""
        # 创建主窗口实例
        self.window = GameCheater()
        self.logger = self.__class__.logger

        # 如果使用模拟内存，设置模拟环境
        if self.use_mock:
            self.original_functions = TestUtils.mock_attach_process(self.window)

        # 等待UI初始化完成
        TestUtils.wait_for_ui_ready(self.window)

    def tearDown(self):
        """每个测试方法之后运行"""
        # 如果使用了模拟内存，恢复原始函数
        if self.use_mock and hasattr(self, 'original_functions'):
            TestUtils.restore_process_functions(self.window, self.original_functions)

        # 关闭窗口
        if self.window:
            self.window.close()
            self.window = None

        # 等待资源释放
        time.sleep(0.5)

    def test_value_type_combo_updates_on_task_switch(self):
        """测试切换任务时数值类型下拉菜单会自动更新"""
        self.logger.info("开始测试数值类型下拉菜单自动切换功能")

        # 设置第一个任务的值类型为整数
        task1 = self.window.task_manager.get_current_task()
        task1.value_type = 'int32'
        self.logger.info(f"设置任务1的值类型为: {task1.value_type}")

        # 确保当前数值类型下拉菜单显示"整数"
        self.window.type_combo.setCurrentText("整数")
        self.logger.info(f"当前数值类型下拉菜单值: {self.window.type_combo.currentText()}")
        self.assertEqual(self.window.type_combo.currentText(), "整数")

        # 创建第二个任务，设置值类型为浮点数
        self.window._on_new_task_clicked()
        task2 = self.window.task_manager.get_current_task()
        task2.value_type = 'float'
        self.logger.info(f"设置任务2的值类型为: {task2.value_type}")

        # 确保第二个任务的数值类型下拉菜单显示"浮点数"
        self.window.type_combo.setCurrentText("浮点数")
        self.logger.info(f"当前数值类型下拉菜单值: {self.window.type_combo.currentText()}")

        # 切换回第一个任务
        self.logger.info("切换回任务1")
        self.window.task_manager.setCurrentIndex(0)

        # 手动触发标签切换事件
        self.logger.info("手动触发标签切换事件")
        self.window.task_manager._on_tab_changed(0)

        # 验证数值类型下拉菜单已更新为"整数"
        current_text = self.window.type_combo.currentText()
        self.logger.info(f"切换后数值类型下拉菜单值: {current_text}")
        self.assertEqual(current_text, "整数")

        # 切换到第二个任务
        self.logger.info("切换到任务2")
        self.window.task_manager.setCurrentIndex(1)

        # 手动触发标签切换事件
        self.logger.info("手动触发标签切换事件")
        self.window.task_manager._on_tab_changed(1)

        # 验证数值类型下拉菜单已更新为"浮点数"
        current_text = self.window.type_combo.currentText()
        self.logger.info(f"切换后数值类型下拉菜单值: {current_text}")
        self.assertEqual(current_text, "浮点数")

if __name__ == '__main__':
    unittest.main()