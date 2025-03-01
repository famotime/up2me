import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 运行测试
if __name__ == '__main__':
    try:
        # 检查是否以管理员权限运行
        import ctypes
        # if not ctypes.windll.shell32.IsUserAnAdmin():
        #     print("请以管理员权限运行测试！")
        #     sys.exit(1)

        # 导入并运行测试
        from tests.test_game_cheater import run_tests
        run_tests()

    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装所需的依赖包：")
        print("pip install PyQt5 psutil pywin32")
    except Exception as e:
        print(f"运行测试时出错: {e}")
        import traceback
        print(traceback.format_exc())