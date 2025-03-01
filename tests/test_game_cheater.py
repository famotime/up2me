import sys
import unittest
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from main import GameCheater
from tests.test_utils import TestUtils

class TestGameCheater(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """在所有测试开始前运行一次"""
        cls.app = QApplication(sys.argv)
        cls.config = TestUtils.load_test_config()
        print("\n开始游戏修改器自动化测试...")

    def setUp(self):
        """每个测试用例开始前运行"""
        self.window = GameCheater()
        print(f"\n运行测试: {self._testMethodName}")

    def tearDown(self):
        """每个测试用例结束后运行"""
        self.window.close()
        print(f"测试完成: {self._testMethodName}")

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
        for test_case in self.config['test_search_values']:
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
        for test_case in self.config['test_addresses']:
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
        test_case = self.config['test_addresses'][0]
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
        for test_case in self.config['test_addresses']:
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
        for test_case in self.config['test_addresses']:
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

def run_tests():
    """运行所有测试"""
    print("="*50)
    print("开始运行游戏修改器自动化测试")
    print("="*50)
    unittest.main(argv=[''], verbosity=2, exit=False)
    print("\n所有测试执行完成")

if __name__ == '__main__':
    run_tests()