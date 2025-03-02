import sys
import os
import unittest
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def run_tests(test_type=None, verbose=2, use_mock=True):
    """运行测试

    参数:
        test_type: 要运行的测试类型，可选值：'all', 'basic', 'performance', 'ui', 'task'
        verbose: 测试输出的详细程度
        use_mock: 是否使用模拟内存进行测试
    """
    try:
        print("=" * 50)
        print("开始运行游戏修改器自动化测试")
        print("=" * 50)
        print()

        # 设置是否使用模拟内存的环境变量
        os.environ['USE_MOCK_MEMORY'] = 'true' if use_mock else 'false'
        if use_mock:
            print("使用模拟内存进行测试")
        else:
            print("使用真实内存进行测试")

            # 检查是否以管理员权限运行
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("警告：未以管理员权限运行，某些测试可能会失败！")
                print("建议：以管理员权限重新运行测试")
                # 不强制退出，让用户决定是否继续
                # sys.exit(1)

        # 使用TestLoader发现并运行所有测试
        loader = unittest.TestLoader()
        test_dir = project_root / 'tests'

        if test_type == 'all' or test_type is None:
            # 运行所有测试
            print("运行所有测试...")
            suite = loader.discover(str(test_dir), pattern='test_*.py')
        elif test_type == 'basic':
            # 只运行基本功能测试
            print("运行基本功能测试...")
            suite = loader.loadTestsFromName('tests.test_game_cheater')
        elif test_type == 'performance':
            # 只运行性能测试
            print("运行性能测试...")
            suite = loader.loadTestsFromName('tests.test_performance')
        elif test_type == 'ui':
            # 只运行UI响应性测试
            print("运行UI响应性测试...")
            suite = loader.loadTestsFromName('tests.test_ui_responsiveness')
        elif test_type == 'task':
            # 只运行任务切换测试
            print("运行任务切换测试...")
            suite = loader.loadTestsFromName('tests.test_task_switching')
        else:
            # 尝试加载指定的测试模块
            try:
                suite = loader.loadTestsFromName(f'tests.{test_type}')
                print(f"运行指定测试: {test_type}")
            except (ImportError, AttributeError):
                print(f"未找到指定的测试模块: {test_type}")
                print("可用的测试类型: all, basic, performance, ui, task")
                return

        # 运行测试
        runner = unittest.TextTestRunner(verbosity=verbose)
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

if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行游戏修改器自动化测试')
    parser.add_argument('--type', '-t',
                        choices=['all', 'basic', 'performance', 'ui', 'task'],
                        default='all',
                        help='要运行的测试类型')
    parser.add_argument('--verbose', '-v',
                        type=int,
                        choices=[0, 1, 2, 3],
                        default=2,
                        help='测试输出的详细程度')
    parser.add_argument('--mock', '-m',
                        action='store_true',
                        default=True,
                        help='使用模拟内存进行测试（默认启用）')
    parser.add_argument('--real', '-r',
                        action='store_true',
                        help='使用真实内存进行测试（需要管理员权限）')

    args = parser.parse_args()

    # 如果指定了--real，则不使用模拟内存
    use_mock = not args.real if args.real else args.mock

    # 运行测试
    run_tests(args.type, args.verbose, use_mock)