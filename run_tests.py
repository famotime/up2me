import sys
import os
import unittest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 运行测试
if __name__ == '__main__':
    try:
        print("=" * 50)
        print("开始运行游戏修改器自动化测试")
        print("=" * 50)
        print()

        # 检查是否以管理员权限运行
        import ctypes
        # if not ctypes.windll.shell32.IsUserAnAdmin():
        #     print("请以管理员权限运行测试！")
        #     sys.exit(1)

        # 使用TestLoader发现并运行所有测试
        loader = unittest.TestLoader()
        test_dir = project_root / 'tests'
        suite = loader.discover(str(test_dir), pattern='test_*.py')

        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)

        print()
        print("所有测试执行完成")

    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装所需的依赖包：")
        print("pip install PyQt5 psutil pywin32")
    except Exception as e:
        print(f"运行测试时出错: {e}")
        import traceback
        print(traceback.format_exc())