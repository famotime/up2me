import sys
import ctypes
import win32com.shell.shell as shell
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTableWidget, QLineEdit, QComboBox)
from PyQt5.QtCore import Qt, QTimer
import psutil
from memory_reader import MemoryReader
from utils.logger import setup_logger
import traceback
from pathlib import Path
import json
import struct
from address_dialog import AddressDialog
from PyQt5.QtGui import QIcon

from src.delegates import LockStateDelegate
from src.search_thread import SearchThread
from src.icon_helper import get_file_icon
from src.process_helper import get_game_processes
from src.ui_helper import (create_process_section, create_search_section,
                         create_memory_table, create_result_table)
from src.memory_helper import (update_memory_table, add_to_result_table)

class GameCheater(QMainWindow):
    def __init__(self):
        super().__init__()
        self.search_thread = None
        self.logger = setup_logger()
        self.logger.info("游戏修改器启动")

        self.memory_reader = MemoryReader()
        self.search_results = []
        self.locked_addresses = {}

        # 加载配置文件
        self.config_file = Path('config.json')
        self.config = self._load_config()

        self.setWindowTitle('"由我"游戏修改器')
        self.setGeometry(100, 100, 800, 600)

        # 将窗口移动到屏幕中央
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

        # 添加状态栏初始化
        self.statusBar().showMessage('搜索 0 次找到 0 个地址')

        # 初始化UI组件
        self.process_combo = QComboBox()
        self.search_input = QLineEdit()
        self.type_combo = QComboBox()
        self.compare_combo = QComboBox()

        # 初始化表格
        self.memory_table = create_memory_table()
        self.result_table = create_result_table(LockStateDelegate(self))

        # 设置UI布局
        self._setup_ui()

        # 初始化定时器
        self._setup_timer()

        # 初始化进程列表
        self.refresh_process_list()

        # 添加事件处理
        self.memory_table.cellDoubleClicked.connect(self._on_memory_table_double_clicked)
        self.result_table.itemChanged.connect(self._on_result_item_changed)

    def _setup_ui(self):
        """设置UI布局"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # 添加进程选择区域
        layout.addLayout(create_process_section(
            self.process_combo,
            self.refresh_process_list,
            self.attach_process
        ))

        # 添加搜索区域
        layout.addLayout(create_search_section(
            self.search_input,
            self.type_combo,
            self.compare_combo,
            self.first_scan,
            self.next_scan,
            self.new_address,
            self.delete_address,
            self.clear_results
        ))

        # 添加表格
        layout.addWidget(self.memory_table)
        layout.addWidget(self.result_table)

    def _setup_timer(self):
        """设置定时器用于更新锁定的值和刷新显示"""
        self.lock_timer = QTimer()
        self.lock_timer.timeout.connect(self._update_timer_event)
        self.lock_timer.start(100)  # 每100ms更新一次

    def _update_timer_event(self):
        """定时器事件：更新锁定值和刷新显示"""
        try:
            self._update_locked_values()
            self._refresh_memory_table()
            self._refresh_result_table()
        except Exception as e:
            self.logger.error(f"定时更新失败: {str(e)}")

    def _load_config(self):
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
        return {'last_process': None}

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {str(e)}")

    def refresh_process_list(self):
        """刷新进程列表"""
        self.process_combo.clear()
        last_process = self.config.get('last_process')
        selected_index = -1

        try:
            game_processes = get_game_processes()

            # 将进程添加到下拉列表
            for i, (name, pid, exe_path) in enumerate(game_processes):
                process_text = f"{name} ({pid})"
                icon = get_file_icon(exe_path, self.logger)
                self.process_combo.addItem(icon, process_text)

                # 如果找到上次使用的进程，记录其索引
                if last_process and last_process['name'] == name:
                    selected_index = i

            # 如果找到上次使用的进程，设置为当前选中项
            if selected_index >= 0:
                self.process_combo.setCurrentIndex(selected_index)
                self.logger.info(f"找到上次使用的进程: {last_process['name']}")

            # 更新状态栏
            msg = f'找到 {len(game_processes)} 个可能的游戏进程'
            self.logger.info(msg)
            self.statusBar().showMessage(msg)

        except Exception as e:
            self.logger.error(f"刷新进程列表失败: {str(e)}")
            self.statusBar().showMessage('刷新进程列表失败')

    def attach_process(self):
        """附加到选中的进程"""
        if not self.process_combo.currentText():
            msg = '请选择要附加的进程'
            self.logger.warning(msg)
            self.statusBar().showMessage(msg)
            return

        try:
            process_text = self.process_combo.currentText()
            self.logger.info(f"正在尝试附加进程: {process_text}")

            # 解析进程名和PID
            process_name = process_text.split(' (')[0]
            pid = int(process_text.split('(')[-1].strip(')'))

            # 检查进程是否存在
            if not psutil.pid_exists(pid):
                msg = '所选进程不存在'
                self.logger.error(msg)
                self.statusBar().showMessage(msg)
                return

            # 尝试附加进程
            self.logger.debug(f"开始附加进程 PID: {pid}")
            result, message = self.memory_reader.attach_process(pid)

            if result:
                # 保存当前进程信息到配置
                self.config['last_process'] = {
                    'name': process_name,
                    'pid': pid
                }
                self._save_config()

                msg = f'成功附加到进程 {process_name} (PID: {pid})'
                self.logger.info(msg)
                self.statusBar().showMessage(msg)
                self.clear_results()
            else:
                msg = f'附加进程失败: {message}'
                self.logger.error(msg)
                self.statusBar().showMessage(msg)

        except Exception as e:
            error_msg = f'附加进程时发生错误: {str(e)}'
            self.logger.error(error_msg)
            self.logger.error(f"错误详情:\n{traceback.format_exc()}")
            self.statusBar().showMessage(error_msg)

    def first_scan(self):
        """首次扫描"""
        if not self.memory_reader.process_handle:
            self.logger.warning("未附加进程")
            self.statusBar().showMessage('请先附加进程')
            return

        try:
            value = self.search_input.text()
            value_type = self.type_combo.currentText()

            # 转换值类型
            if '整数' in value_type:
                search_value = int(value)
                type_name = 'int32'
            elif '浮点' in value_type:
                search_value = float(value)
                type_name = 'float'
            else:
                search_value = float(value)
                type_name = 'double'

            self.logger.info(f"开始首次扫描: 值={search_value}, 类型={type_name}")

            # 创建并启动搜索线程
            self.search_thread = SearchThread(self.memory_reader, search_value, type_name)
            self.search_thread.finished.connect(self._on_search_completed)
            self.statusBar().showMessage('正在搜索...')
            self.search_thread.start()

        except ValueError:
            msg = '请输入有效的数值'
            self.logger.warning(msg)
            self.statusBar().showMessage(msg)

    def _on_search_completed(self, results):
        """搜索完成的回调函数"""
        update_memory_table(self.memory_table, results, self.memory_reader, self.statusBar().showMessage)
        self.search_thread = None

    def next_scan(self):
        """下一次扫描"""
        if not self.memory_reader.last_results:
            self.statusBar().showMessage('请先进行首次扫描')
            return

        try:
            value = self.search_input.text()
            value_type = self.type_combo.currentText()
            compare_type = self.compare_combo.currentText()

            # 转换比较类型
            compare_map = {
                '精确匹配': 'exact',
                '大于': 'bigger',
                '小于': 'smaller',
                '已改变': 'changed',
                '未改变': 'unchanged'
            }

            results = self.memory_reader.search_value(
                float(value) if '浮点' in value_type else int(value),
                'float' if '浮点' in value_type else 'int32',
                compare_map[compare_type]
            )

            update_memory_table(self.memory_table, results, self.memory_reader, self.statusBar().showMessage)

        except ValueError:
            self.statusBar().showMessage('请输入有效的数值')

    def new_address(self):
        """添加新地址到结果表格"""
        try:
            # 获取当前选中的内存表格行
            current_row = self.memory_table.currentRow()

            # 如果有选中的行，获取该行的数据
            if current_row >= 0:
                addr = self.memory_table.item(current_row, 0).text()
                value = self.memory_table.item(current_row, 3).text().split(' ')[0]
                value_type = self.memory_table.item(current_row, 4).text()

                # 创建并显示添加地址对话框
                dialog = AddressDialog(self, address=addr, value=value)

                # 设置数据类型
                if "浮点" in value_type:
                    dialog.type_float.setChecked(True)
                elif "字符" in value_type:
                    dialog.type_string.setChecked(True)
                else:
                    dialog.type_int.setChecked(True)

            else:
                # 如果没有选中行，则打开空白对话框
                dialog = AddressDialog(self)

            # 显示对话框
            if dialog.exec_():
                values = dialog.get_values()
                try:
                    addr = int(values['address'], 16)
                    success, is_locked = add_to_result_table(
                        self.result_table,
                        addr=addr,
                        desc=values['name'],
                        value_type=values['data_type'],
                        initial_value=values['value'],
                        memory_reader=self.memory_reader,
                        logger=self.logger,
                        auto_lock=values['auto_lock']
                    )

                    if success:
                        if is_locked:
                            self.locked_addresses[addr] = values['value']
                        self.statusBar().showMessage(f"已添加地址 {hex(addr)} 到修改列表")
                    else:
                        self.statusBar().showMessage("添加地址失败")
                except ValueError:
                    self.statusBar().showMessage('请输入有效的地址')
        except Exception as e:
            self.logger.error(f"添加地址失败: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.statusBar().showMessage("添加地址失败")

    def delete_address(self):
        """从结果表格中删除选中的地址"""
        current_row = self.result_table.currentRow()
        if current_row >= 0:
            try:
                addr = int(self.result_table.item(current_row, 1).text(), 16)
                if addr in self.locked_addresses:
                    del self.locked_addresses[addr]
                self.result_table.removeRow(current_row)
                self.statusBar().showMessage(f"已删除地址 {hex(addr)}")
            except Exception as e:
                self.logger.error(f"删除地址失败: {str(e)}")
                self.statusBar().showMessage("删除地址失败")
        else:
            self.statusBar().showMessage("请先选择要删除的地址")

    def clear_results(self):
        """清空结果表格"""
        self.result_table.setRowCount(0)
        self.locked_addresses.clear()
        self.statusBar().showMessage('已清空修改列表')

    def _on_memory_table_double_clicked(self, row, column):
        """处理内存表格的双击事件"""
        try:
            # 获取当前行的数据
            addr = self.memory_table.item(row, 0).text()
            value = self.memory_table.item(row, 3).text().split(' ')[0]
            value_type = self.memory_table.item(row, 4).text()

            # 创建并显示添加地址对话框
            dialog = AddressDialog(self, address=addr, value=value)

            # 设置数据类型
            if "浮点" in value_type:
                dialog.type_float.setChecked(True)
            elif "字符" in value_type:
                dialog.type_string.setChecked(True)
            else:
                dialog.type_int.setChecked(True)

            # 显示对话框
            if dialog.exec_():
                values = dialog.get_values()
                success, is_locked = add_to_result_table(
                    self.result_table,
                    addr=int(addr, 16),
                    desc=values['name'],
                    value_type=values['data_type'],
                    initial_value=values['value'],
                    memory_reader=self.memory_reader,
                    logger=self.logger,
                    auto_lock=values['auto_lock']
                )

                if success:
                    if is_locked:
                        self.locked_addresses[int(addr, 16)] = values['value']
                    self.statusBar().showMessage(f"已添加地址 {addr} 到修改列表")
                else:
                    self.statusBar().showMessage("添加地址失败")

        except Exception as e:
            self.logger.error(f"处理双击事件失败: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.statusBar().showMessage("添加地址失败")

    def _on_result_item_changed(self, item):
        """处理结果表格的值改变事件"""
        try:
            row = item.row()
            col = item.column()

            # 只处理数值列(2)和锁定列(4)的改变
            if col not in [2, 4]:
                return

            # 获取必要的值，并进行空值检查
            addr_item = self.result_table.item(row, 1)
            type_item = self.result_table.item(row, 3)
            value_item = self.result_table.item(row, 2)

            if not all([addr_item, type_item, value_item]):
                self.logger.warning("表格数据不完整")
                return

            addr = int(addr_item.text(), 16)  # 获取地址
            value_type = type_item.text()     # 获取类型
            value_text = value_item.text()    # 获取值

            if col == 2:  # 数值列
                try:
                    # 根据类型转换值并写入内存
                    if value_type == '整数':
                        value = int(value_text)
                        if value < 0:
                            value = value & 0xFFFFFFFF
                        buffer = value.to_bytes(4, 'little')
                    elif value_type == '浮点':
                        value = float(value_text)
                        buffer = struct.pack('<f', value)
                    else:  # 字符串
                        value = value_text
                        buffer = value.encode('utf-8')

                    # 写入内存前检查进程是否还在运行
                    if not self.memory_reader.process_handle:
                        raise Exception("进程未附加或已退出")

                    # 写入内存并验证
                    if self.memory_reader.write_memory(addr, buffer):
                        verify_value = self.memory_reader.read_memory(addr, len(buffer))
                        if verify_value == buffer:
                            self.logger.info(f"成功写入并验证地址 {hex(addr)}: {value}")
                            self.statusBar().showMessage(f"成功修改值: {value}")

                            # 如果该地址被锁定，更新锁定值
                            if addr in self.locked_addresses:
                                self.locked_addresses[addr] = value
                        else:
                            raise Exception("写入验证失败")
                    else:
                        raise Exception("写入内存失败")

                except ValueError as e:
                    self.logger.error(f"输入的值格式无效: {value_text} - {str(e)}")
                    self.statusBar().showMessage("请输入有效的数值")
                    # 恢复原值
                    item.setText(str(self.locked_addresses.get(addr, value_text)))
                except Exception as e:
                    self.logger.error(f"写入内存时出错: {str(e)}")
                    self.statusBar().showMessage("写入内存失败")
                    # 恢复原值
                    item.setText(str(self.locked_addresses.get(addr, value_text)))

            elif col == 4:  # 锁定列
                is_locked = item.text().lower() == "是"
                if is_locked:
                    # 获取当前值并添加到锁定列表
                    try:
                        if value_type == '整数':
                            value = int(value_text)
                        elif value_type == '浮点':
                            value = float(value_text)
                        else:
                            value = value_text
                        self.locked_addresses[addr] = value
                    except ValueError:
                        self.logger.error("无法锁定：无效的值")
                        item.setText("否")
                else:
                    # 从锁定列表中移除
                    if addr in self.locked_addresses:
                        del self.locked_addresses[addr]

                self.logger.info(f"地址 {hex(addr)} 锁定状态: {is_locked}")

        except Exception as e:
            self.logger.error(f"处理值改变事件失败: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def _update_locked_values(self):
        """更新锁定的值"""
        try:
            for addr, value in self.locked_addresses.items():
                try:
                    if isinstance(value, int):
                        buffer = value.to_bytes(4, 'little', signed=True)
                    elif isinstance(value, float):
                        buffer = struct.pack('<f', value)
                    else:
                        buffer = value.encode('utf-8')

                    if not self.memory_reader.write_memory(addr, buffer):
                        self.logger.debug(f"无法写入锁定地址: {hex(addr)}")
                except Exception as e:
                    self.logger.debug(f"更新锁定值失败: {hex(addr)} - {str(e)}")

        except Exception as e:
            self.logger.error(f"更新锁定值时出错: {str(e)}")

    def _refresh_memory_table(self):
        """刷新内存表格显示"""
        try:
            for row in range(self.memory_table.rowCount()):
                addr_item = self.memory_table.item(row, 0)
                if not addr_item:
                    continue

                addr = int(addr_item.text(), 16)
                value = self.memory_reader.read_memory(addr, 4)

                if value:
                    # 更新单字节值
                    self.memory_table.item(row, 1).setText(str(value[0]))

                    # 更新双字节值
                    word_val = int.from_bytes(value[:2], 'little')
                    self.memory_table.item(row, 2).setText(str(word_val))

                    # 更新四字节值（整数和浮点数）
                    dword_val = int.from_bytes(value, 'little')
                    float_val = struct.unpack('<f', value)[0]
                    self.memory_table.item(row, 3).setText(f"{dword_val} ({float_val:.2f})")

        except Exception as e:
            self.logger.error(f"刷新内存表格失败: {str(e)}")

    def _refresh_result_table(self):
        """刷新结果表格显示"""
        try:
            for row in range(self.result_table.rowCount()):
                addr_item = self.result_table.item(row, 1)
                type_item = self.result_table.item(row, 3)
                if not addr_item or not type_item:
                    continue

                addr = int(addr_item.text(), 16)
                value_type = type_item.text()

                # 读取内存值
                value = self.memory_reader.read_memory(addr, 4)
                if not value:
                    continue

                # 根据类型转换值
                try:
                    if value_type == '整数':
                        current_value = str(int.from_bytes(value, 'little', signed=True))
                    elif value_type == '浮点':
                        current_value = f"{struct.unpack('<f', value)[0]:.2f}"
                    else:  # 字符串
                        current_value = value.decode('utf-8', errors='ignore')

                    # 更新显示的值（不触发 itemChanged 信号）
                    value_item = self.result_table.item(row, 2)
                    if value_item and value_item.text() != current_value:
                        self.result_table.blockSignals(True)
                        value_item.setText(current_value)
                        self.result_table.blockSignals(False)

                except Exception as e:
                    self.logger.debug(f"转换值失败: {str(e)}")

        except Exception as e:
            self.logger.error(f"刷新结果表格失败: {str(e)}")

if __name__ == '__main__':
    try:
        # 检查管理员权限
        if not ctypes.windll.shell32.IsUserAnAdmin():
            try:
                script = Path(__file__).absolute()
                params = ' '.join(sys.argv[1:])
                ret = shell.ShellExecuteEx(
                    lpVerb='runas',
                    lpFile=sys.executable,
                    lpParameters=f'"{script}" {params}',
                    nShow=1  # 显示窗口
                )
                if ret['hInstApp'] <= 32:  # 如果返回值小于等于32，表示启动失败
                    raise Exception('启动失败')
                sys.exit(0)  # 原进程退出
            except Exception as e:
                print(f'错误：请以管理员身份运行此程序！\n{str(e)}')
                input("按任意键退出...")
                sys.exit(1)
        else:
            # 已经具有管理员权限，创建应用程序
            app = QApplication(sys.argv)
            app.setStyle('Fusion')
            app.setWindowIcon(QIcon('nezha.png'))  # 设置应用程序图标

            # 创建主窗口
            window = GameCheater()
            window.logger.info("正在显示主窗口...")
            window.show()

            # 进入事件循环
            window.logger.info("进入应用程序事件循环...")
            ret = app.exec_()
            window.logger.info(f"应用程序退出，返回值：{ret}")
            sys.exit(ret)

    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        print(f"错误详情:\n{traceback.format_exc()}")
        input("按任意键退出...")
        sys.exit(1)