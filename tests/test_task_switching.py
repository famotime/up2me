import sys
import unittest
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import GameCheater

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

    def setUp(self):
        """每个测试方法之前运行"""
        # 创建主窗口实例
        self.window = GameCheater()
        self.logger = self.__class__.logger

    def tearDown(self):
        """每个测试方法之后运行"""
        # 关闭窗口
        self.window.close()

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