import sys
import ctypes
import win32com.shell.shell as shell
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTableWidget, QLineEdit, QComboBox, QPushButton, QLabel)
from PyQt5.QtCore import Qt, QTimer, QCoreApplication
import psutil
from memory_reader import MemoryReader
from utils.logger import setup_logger
import traceback
from pathlib import Path
import json
import struct
from address_dialog import AddressDialog
from PyQt5.QtGui import QIcon

from utils.delegates import LockStateDelegate
from utils.search_thread import SearchThread
from utils.icon_helper import get_file_icon
from utils.process_helper import get_game_processes
from utils.ui_helper import (create_process_section, create_search_section,
                         create_memory_table, create_result_table, create_table_control_section)
from utils.memory_helper import (update_memory_table, add_to_result_table)
from utils.task_manager import SearchTaskManager

class GameCheater(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = setup_logger()
        self.logger.info("游戏修改器启动")

        self.memory_reader = MemoryReader()
        self.locked_addresses = {}

        # 加载配置文件
        self.config_file = Path('config.json')
        self.config = self._load_config()

        self.setWindowTitle('"由我"修改器')
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

        # 设置搜索输入框的回车键事件
        self.search_input.returnPressed.connect(self._on_search_clicked)

        # 初始化任务管理器
        self.task_manager = SearchTaskManager()

        # 连接任务切换信号到自定义处理函数
        self.task_manager.currentChanged.connect(self._on_task_changed)

        # 将任务列表赋值给memory_reader
        self.memory_reader.active_tasks = self.task_manager.tasks

        # 初始化结果表格
        self.result_table = create_result_table(LockStateDelegate(self))

        # 设置UI布局
        self._setup_ui()

        # 初始化定时器
        self._setup_timer()

        # 初始化进程列表
        self.refresh_process_list()

        # 添加事件处理
        self.result_table.itemChanged.connect(self._on_result_item_changed)

    def _on_task_changed(self, index):
        """处理任务切换事件"""
        self.logger.debug(f"任务切换事件: 索引 {index}")

        # 获取当前任务
        current_task = self.task_manager.get_current_task()
        if current_task and current_task.value_type:
            self.logger.debug(f"当前任务值类型: {current_task.value_type}")

            # 将任务的值类型映射到下拉菜单选项
            value_type_map = {
                "int32": "整数",
                "float": "浮点数",
                "double": "双精度"
            }
            combo_text = value_type_map.get(current_task.value_type, "整数")
            self.logger.debug(f"映射后的下拉菜单文本: {combo_text}")

            # 设置下拉菜单值
            self.type_combo.setCurrentText(combo_text)
            self.logger.debug(f"设置下拉菜单文本为: {combo_text}")

            # 验证设置是否成功
            new_text = self.type_combo.currentText()
            self.logger.debug(f"设置后的下拉菜单文本: {new_text}")

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
        search_layout, self.search_button = create_search_section(
            self.search_input,
            self.type_combo,
            self.compare_combo,
            self._on_search_clicked,
            self._on_new_task_clicked
        )
        layout.addLayout(search_layout)

        # 添加任务管理器
        layout.addWidget(self.task_manager)

        # 添加表格控制区域
        layout.addLayout(create_table_control_section(
            self.new_address,
            self.delete_address,
            self.clear_results
        ))

        # 添加结果表格
        layout.addWidget(self.result_table)

        # 添加停止按钮
        self.stop_button = QPushButton("停止")
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)

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
            self.logger.debug("开始刷新进程列表")
            game_processes = get_game_processes()
            self.logger.debug(f"获取到 {len(game_processes)} 个进程")

            # 将进程添加到下拉列表
            for i, (name, pid, exe_path) in enumerate(game_processes):
                try:
                    process_text = f"{name} ({pid})"

                    # 获取图标，如果失败则使用空图标
                    try:
                        icon = get_file_icon(exe_path, self.logger)
                        if icon.isNull():
                            self.logger.debug(f"进程 {name} 的图标为空，使用默认图标")
                            icon = QIcon()  # 使用空图标
                    except Exception as e:
                        self.logger.debug(f"获取进程 {name} 的图标失败: {str(e)}")
                        icon = QIcon()  # 使用空图标

                    self.process_combo.addItem(icon, process_text)
                    self.logger.debug(f"添加进程到列表: {process_text}")

                    # 如果找到上次使用的进程，记录其索引
                    if last_process and isinstance(last_process, dict) and last_process.get('name') == name:
                        selected_index = i
                        self.logger.debug(f"找到上次使用的进程: {name}, 索引: {i}")
                except Exception as e:
                    self.logger.error(f"添加进程 {name} 到列表失败: {str(e)}")
                    continue

            # 如果找到上次使用的进程，设置为当前选中项
            if selected_index >= 0:
                self.process_combo.setCurrentIndex(selected_index)
                self.logger.info(f"设置上次使用的进程为当前选中项: {last_process.get('name')}")

            # 更新状态栏
            msg = f'找到 {len(game_processes)} 个可能的游戏进程'
            self.logger.info(msg)
            self.statusBar().showMessage(msg)

        except Exception as e:
            self.logger.error(f"刷新进程列表失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情:\n{traceback.format_exc()}")
            self.statusBar().showMessage('刷新进程列表失败')

    def attach_process(self):
        """附加到选中的进程"""
        if not self.process_combo.currentText():
            msg = '请选择要附加的进程'
            self.logger.warning(msg)
            self.statusBar().showMessage(msg)
            return

        try:
            # 停止所有正在进行的搜索
            searching_count = self.task_manager.get_searching_tasks_count()
            if searching_count > 0:
                self.task_manager.stop_all_searches()
                self.logger.info(f"已停止 {searching_count} 个正在进行的搜索任务")

            process_text = self.process_combo.currentText()
            self.logger.info(f"正在尝试附加进程: {process_text}")

            # 解析进程名和PID
            process_name = process_text.split(' (')[0]
            pid = int(process_text.split('(')[-1].strip(')'))
            self.logger.debug(f"解析进程信息: 名称={process_name}, PID={pid}")

            # 检查进程是否存在
            if not psutil.pid_exists(pid):
                msg = '所选进程不存在'
                self.logger.error(msg)
                self.statusBar().showMessage(msg)
                return

            # 尝试附加进程
            self.logger.debug(f"开始附加进程 PID: {pid}")
            success, message = self.memory_reader.attach_process(pid)

            if success:
                self.logger.info(f"成功附加到进程: {process_name} (PID: {pid})")
                self.statusBar().showMessage(f"已附加到进程: {process_name}")

                # 保存当前进程信息到配置
                self.config['last_process'] = process_text
                self._save_config()
                self.logger.debug(f"已保存进程信息到配置: {process_text}")

                # 清空所有任务的搜索结果
                self.task_manager.clear_all_tasks_results()
                self.logger.debug("已清空所有任务的搜索结果")

                # 刷新内存表格
                self._refresh_memory_table()
                self.logger.debug("已刷新内存表格")
            else:
                self.logger.error(f"附加进程失败: {message}")
                self.statusBar().showMessage(f"附加进程失败: {message}")
        except Exception as e:
            self.logger.error(f"附加进程时出错: {str(e)}")
            self.statusBar().showMessage(f"附加进程时出错: {str(e)}")
            import traceback
            self.logger.debug(f"错误详情: {traceback.format_exc()}")

    def _on_search_clicked(self):
        """搜索按钮点击事件"""
        try:
            self.logger.info("开始搜索操作")

            # 检查是否已附加到进程
            if not self.memory_reader.process_handle:
                self.logger.warning("搜索失败：未附加到进程")
                self.statusBar().showMessage("请先附加到进程", 3000)
                return

            # 获取当前活动的任务
            current_task = self.task_manager.get_current_task()
            if not current_task:
                self.logger.warning("搜索失败：未创建任务")
                self.statusBar().showMessage("请先创建任务", 3000)
                return

            # 获取搜索值
            value_text = self.search_input.text().strip()
            if not value_text:
                self.logger.warning("搜索失败：未输入搜索值")
                self.statusBar().showMessage("请输入搜索值", 3000)
                return

            # 获取值类型
            value_type = self.type_combo.currentText()
            value_type_map = {
                "整数": "int32",
                "浮点数": "float",
                "单精度": "float",
                "双精度": "double"
            }
            value_type = value_type_map.get(value_type, "int32")
            self.logger.debug(f"搜索值类型: {value_type} (原始类型: {self.type_combo.currentText()})")

            # 获取比较类型
            compare_type = self.compare_combo.currentText()
            self.logger.debug(f"比较类型: {compare_type}")

            # 转换搜索值
            try:
                if value_type == "int32":
                    value = int(value_text)
                    self.logger.debug(f"转换整数值: {value}")
                else:  # float or double
                    value = float(value_text)
                    self.logger.debug(f"转换浮点值: {value}")
            except ValueError:
                self.logger.error(f"无效的{value_type}值: {value_text}")
                self.statusBar().showMessage(f"无效的{value_type}值: {value_text}", 3000)
                return

            # 保存当前任务的值类型
            current_task.value_type = value_type
            current_task.value = value
            current_task.compare_type = compare_type
            self.logger.debug(f"更新任务 '{current_task.name}' 的参数: 值={value}, 类型={value_type}, 比较方式={compare_type}")

            # 禁用搜索按钮，避免重复点击
            self.search_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.logger.debug("禁用搜索按钮，启用停止按钮")

            # 更新状态栏
            self.statusBar().showMessage("正在准备搜索...", 0)

            # 准备搜索参数
            search_params = {
                "value": value,
                "value_type": value_type,
                "compare_type": compare_type,
                "last_results": current_task.last_results,
                "is_first_search": current_task.is_first_search,
                "task": current_task
            }
            self.logger.info(f"开始搜索: 值={value}, 类型={value_type}, 比较方式={compare_type}, 是否首次搜索={current_task.is_first_search}")

            # 创建并启动搜索线程
            self.search_thread = SearchThread(self.memory_reader, search_params, self.logger)
            self.search_thread.progress.connect(self._on_search_progress)
            self.search_thread.finished.connect(lambda result: self._on_search_finished(result))
            self.search_thread.start()
            self.logger.debug("搜索线程已启动")
        except Exception as e:
            self.logger.error(f"搜索按钮点击事件处理失败: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            self.statusBar().showMessage(f"搜索失败: {str(e)}", 3000)
            self.search_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def _on_new_task_clicked(self):
        """处理新建任务按钮点击事件"""
        new_task = self.task_manager.add_task()

        # 设置新任务的内存读取器和值类型
        new_task.memory_reader = self.memory_reader

        # 使用当前选择的值类型
        value_type = self.type_combo.currentText().lower()
        if value_type == '整数':
            new_task.value_type = 'int32'
        elif value_type == '浮点':
            new_task.value_type = 'float'
        elif value_type == '双精度':
            new_task.value_type = 'double'
        else:
            new_task.value_type = 'int32'  # 默认为整数

    def new_address(self):
        """添加新地址到结果表格"""
        try:
            current_task = self.task_manager.get_current_task()
            if not current_task or not current_task.memory_table:
                self.statusBar().showMessage("请先选择搜索任务")
                return

            # 获取当前选中的内存表格行
            current_row = current_task.memory_table.currentRow()

            # 如果有选中的行，获取该行的数据
            if current_row >= 0:
                addr = current_task.memory_table.item(current_row, 0).text()  # 地址列
                value = current_task.memory_table.item(current_row, 1).text()  # 当前值列
                value_type = current_task.memory_table.item(current_row, 4).text()  # 类型列

                # 创建并显示添加地址对话框
                dialog = AddressDialog(self, address=addr, value=value)

                # 设置数据类型
                type_to_radio = {
                    "整数": dialog.type_int,
                    "浮点": dialog.type_float,
                    "单精度": dialog.type_float,
                    "双精度": dialog.type_double
                }

                if value_type in type_to_radio:
                    type_to_radio[value_type].setChecked(True)
                    self.logger.debug(f"设置对话框数据类型: {value_type}")
                else:
                    # 默认使用整型
                    dialog.type_int.setChecked(True)
                    self.logger.debug(f"未知数据类型 {value_type}，默认使用整型")

            else:
                # 如果没有选中行，则打开空白对话框
                dialog = AddressDialog(self)
                # 根据当前搜索类型设置默认值类型
                if current_task.value_type == 'float':
                    dialog.type_float.setChecked(True)
                elif current_task.value_type == 'double':
                    dialog.type_double.setChecked(True)
                else:
                    dialog.type_int.setChecked(True)

            # 显示对话框
            if dialog.exec_():
                values = dialog.get_values()
                try:
                    addr = int(values['address'], 16)
                    # 确保数据类型格式正确
                    data_type = values['data_type']
                    if data_type not in ['int32', 'float', 'double']:
                        self.logger.error(f"不支持的数据类型: {data_type}")
                        if data_type == 'int':
                            data_type = 'int32'
                        elif data_type == 'string':
                            self.statusBar().showMessage("不支持字符串类型", 3000)
                            return

                    success, is_locked, lock_value = add_to_result_table(
                        self.result_table,
                        address=addr,
                        desc=values['name'],
                        value_type=data_type,
                        initial_value=values['value'],
                        memory_reader=self.memory_reader,
                        logger=self.logger,
                        auto_lock=values['auto_lock']
                    )

                    if success:
                        if is_locked and lock_value is not None:
                            self.locked_addresses[addr] = lock_value
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
        # 停止所有正在进行的搜索
        searching_count = self.task_manager.get_searching_tasks_count()
        if searching_count > 0:
            self.task_manager.stop_all_searches()
            self.logger.info(f"已停止 {searching_count} 个正在进行的搜索任务")

        self.result_table.setRowCount(0)
        self.locked_addresses.clear()
        self.statusBar().showMessage('已清空修改列表')

    def _on_result_item_changed(self, item):
        """处理结果表格的值改变事件"""
        # 在try块外定义original_value_type变量
        original_value_type = None
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

            # 保存原始值类型，避免影响其他任务
            original_value_type = self.memory_reader.current_value_type

            if col == 2:  # 数值列
                try:
                    # 根据类型转换值并写入内存
                    if value_type == '整数':
                        value = int(value_text)
                        if value < 0:
                            value = value & 0xFFFFFFFF
                        buffer = value.to_bytes(4, 'little')
                        self.memory_reader.current_value_type = 'int32'
                    elif value_type == '浮点':
                        value = float(value_text)
                        buffer = struct.pack('<f', value)
                        self.memory_reader.current_value_type = 'float'
                    else:  # 双精度
                        value = float(value_text)
                        buffer = struct.pack('<d', value)
                        self.memory_reader.current_value_type = 'double'

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
                        else:  # 双精度
                            value = float(value_text)
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
        finally:
            # 恢复原始值类型，避免影响其他任务
            if original_value_type is not None:
                self.memory_reader.current_value_type = original_value_type

    def _update_locked_values(self):
        """更新锁定的值"""
        # 在try块外定义original_value_type变量
        original_value_type = None
        try:
            # 保存原始值类型，避免影响其他任务
            original_value_type = self.memory_reader.current_value_type

            for addr, value in self.locked_addresses.items():
                try:
                    if isinstance(value, int):
                        buffer = value.to_bytes(4, 'little', signed=True)
                        self.memory_reader.current_value_type = 'int32'
                    elif isinstance(value, float):
                        # 查找该地址在结果表格中的类型
                        is_double = False
                        try:
                            for row in range(self.result_table.rowCount()):
                                addr_item = self.result_table.item(row, 1)
                                if addr_item and int(addr_item.text(), 16) == addr:
                                    type_item = self.result_table.item(row, 3)
                                    if type_item and type_item.text() == '双精度':
                                        is_double = True
                                        # self.logger.debug(f"检测到双精度浮点数: 地址={hex(addr)}, 值={value}")
                                    break
                        except Exception as e:
                            self.logger.debug(f"检测双精度类型时出错: {str(e)}")
                            # 默认使用单精度浮点数
                            is_double = False

                        try:
                            if is_double:
                                buffer = struct.pack('<d', value)
                                self.memory_reader.current_value_type = 'double'
                            else:
                                buffer = struct.pack('<f', value)
                                self.memory_reader.current_value_type = 'float'
                        except struct.error as e:
                            self.logger.debug(f"打包浮点数时出错: {str(e)}, 值={value}, 类型={'双精度' if is_double else '单精度'}")
                            continue
                    else:
                        self.logger.debug(f"不支持的值类型: {type(value)}, 地址={hex(addr)}")
                        continue

                    # 检查进程是否还在运行
                    if not self.memory_reader.process_handle:
                        self.logger.debug("进程未附加或已退出，无法更新锁定值")
                        break

                    # 写入内存前检查buffer是否有效
                    if not buffer:
                        self.logger.debug(f"无效的缓冲区: 地址={hex(addr)}, 值={value}")
                        continue

                    if not self.memory_reader.write_memory(addr, buffer):
                        self.logger.debug(f"无法写入锁定地址: {hex(addr)}")
                except Exception as e:
                    self.logger.debug(f"更新锁定值失败: {hex(addr)} - {str(e)}")

        except Exception as e:
            self.logger.error(f"更新锁定值时出错: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
        finally:
            # 恢复原始值类型，避免影响其他任务
            if original_value_type is not None:
                self.memory_reader.current_value_type = original_value_type

    def _refresh_memory_table(self):
        """刷新内存表格显示"""
        # 在try块外定义original_value_type变量
        original_value_type = None
        try:
            current_task = self.task_manager.get_current_task()
            if not current_task or not current_task.memory_table:
                return

            # 保存原始值类型，避免影响其他任务
            original_value_type = self.memory_reader.current_value_type

            try:
                for row in range(current_task.memory_table.rowCount()):
                    addr_item = current_task.memory_table.item(row, 0)
                    if not addr_item:
                        continue

                    addr = int(addr_item.text(), 16)
                    # 根据任务的值类型决定读取大小
                    value_type = current_task.value_type
                    if not value_type:
                        value_type = 'int32'  # 默认为整数

                    size = 8 if value_type == 'double' else 4

                    # 临时设置memory_reader的值类型为当前任务的值类型
                    self.memory_reader.current_value_type = value_type

                    value = self.memory_reader.read_memory(addr, size)

                    if value:
                        try:
                            if value_type == 'int32':
                                current_value = str(int.from_bytes(value, 'little', signed=True))
                            elif value_type == 'float':
                                current_value = f"{struct.unpack('<f', value)[0]:.6f}"
                            else:  # double
                                current_value = f"{struct.unpack('<d', value)[0]:.6f}"

                            # 更新当前值
                            current_item = current_task.memory_table.item(row, 1)
                            if current_item:
                                current_item.setText(current_value)

                            # 更新先前值（如果有）
                            prev_value = current_task.prev_values.get(addr)
                            prev_item = current_task.memory_table.item(row, 2)
                            if prev_item:
                                if prev_value is not None:
                                    if value_type == 'int32':
                                        prev_text = str(prev_value)
                                    else:  # float or double
                                        prev_text = f"{prev_value:.6f}"
                                else:
                                    prev_text = "-"
                                prev_item.setText(prev_text)

                            # 更新首次值（如果有）
                            first_value = current_task.first_values.get(addr)
                            first_item = current_task.memory_table.item(row, 3)
                            if first_item:
                                if first_value is not None:
                                    if value_type == 'int32':
                                        first_text = str(first_value)
                                    else:  # float or double
                                        first_text = f"{first_value:.6f}"
                                else:
                                    first_text = "-"
                                first_item.setText(first_text)

                            # 高亮显示变化的值
                            if prev_value is not None and current_item:
                                if value_type == 'int32':
                                    has_changed = int(current_value) != prev_value
                                else:  # float or double
                                    has_changed = abs(float(current_value) - prev_value) > 1e-6
                                if has_changed:
                                    current_item.setBackground(Qt.yellow)
                                else:
                                    current_item.setBackground(Qt.white)

                        except Exception as e:
                            self.logger.debug(f"格式化值失败: {str(e)}")
            except Exception as e:
                self.logger.error(f"刷新内存表格失败: {str(e)}")
                import traceback
                self.logger.debug(traceback.format_exc())
        finally:
            # 恢复原始值类型，避免影响其他任务
            if original_value_type is not None:
                self.memory_reader.current_value_type = original_value_type

    def _refresh_result_table(self):
        """刷新结果表格显示"""
        # 在try块外定义original_value_type变量
        original_value_type = None
        try:
            # 保存原始值类型，避免影响其他任务
            original_value_type = self.memory_reader.current_value_type

            for row in range(self.result_table.rowCount()):
                addr_item = self.result_table.item(row, 1)
                type_item = self.result_table.item(row, 3)
                lock_item = self.result_table.item(row, 4)
                if not addr_item or not type_item or not lock_item:
                    continue

                addr = int(addr_item.text(), 16)
                value_type = type_item.text()
                is_locked = lock_item.text() == "是"

                # 如果是锁定的地址，使用锁定的值
                if is_locked and addr in self.locked_addresses:
                    locked_value = self.locked_addresses[addr]
                    try:
                        # 根据类型格式化锁定值
                        if value_type == '整数':
                            self.memory_reader.current_value_type = 'int32'
                            buffer = int(locked_value).to_bytes(4, 'little', signed=True)
                            if not self.memory_reader.write_memory(addr, buffer):
                                self.logger.debug(f"写入锁定值失败: {addr}")
                                continue
                            current_value = str(locked_value)
                        elif value_type == '浮点':
                            self.memory_reader.current_value_type = 'float'
                            buffer = struct.pack('<f', float(locked_value))
                            if not self.memory_reader.write_memory(addr, buffer):
                                self.logger.debug(f"写入锁定值失败: {addr}")
                                continue
                            current_value = f"{locked_value:.6f}"
                        elif value_type == '双精度':
                            self.memory_reader.current_value_type = 'double'
                            buffer = struct.pack('<d', float(locked_value))
                            if not self.memory_reader.write_memory(addr, buffer):
                                self.logger.debug(f"写入锁定值失败: {addr}")
                                continue
                            current_value = f"{locked_value:.6f}"
                        else:
                            continue
                    except (ValueError, struct.error) as e:
                        self.logger.debug(f"处理锁定值失败: {str(e)}")
                        continue
                else:
                    # 读取内存值
                    size = 8 if value_type == '双精度' else 4

                    # 设置正确的值类型
                    if value_type == '整数':
                        self.memory_reader.current_value_type = 'int32'
                    elif value_type == '浮点':
                        self.memory_reader.current_value_type = 'float'
                    elif value_type == '双精度':
                        self.memory_reader.current_value_type = 'double'

                    value = self.memory_reader.read_memory(addr, size)
                    if not value:
                        continue

                    # 根据类型转换值
                    try:
                        if value_type == '整数':
                            current_value = str(int.from_bytes(value, 'little', signed=True))
                        elif value_type == '浮点':
                            current_value = f"{struct.unpack('<f', value)[0]:.6f}"
                        elif value_type == '双精度':
                            current_value = f"{struct.unpack('<d', value)[0]:.6f}"
                        else:
                            continue
                    except (ValueError, struct.error) as e:
                        self.logger.debug(f"转换值失败: {str(e)}")
                        continue

                # 更新显示的值（不触发 itemChanged 信号）
                value_item = self.result_table.item(row, 2)
                if value_item and value_item.text() != current_value:
                    self.result_table.blockSignals(True)
                    value_item.setText(current_value)
                    self.result_table.blockSignals(False)

        except Exception as e:
            self.logger.error(f"刷新结果表格失败: {str(e)}")
            self.logger.debug(traceback.format_exc())
        finally:
            # 恢复原始值类型，避免影响其他任务
            if original_value_type is not None:
                self.memory_reader.current_value_type = original_value_type

    def show_status(self, message, log=True):
        """显示状态栏消息，可选择是否记录到日志"""
        self.statusBar().showMessage(message)
        if log:
            self.logger.info(message)
        else:
            # 即使不记录为info，也记录为debug，方便调试
            self.logger.debug(f"状态栏: {message}")

    def _on_add_address_clicked(self):
        """添加地址按钮点击事件"""
        # 在try块外定义original_value_type变量
        original_value_type = None
        try:
            self.logger.info("开始添加地址操作")
            dialog = AddressDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                self.logger.debug("用户确认添加地址对话框")
                try:
                    address = dialog.get_address()
                    value_type = dialog.get_value_type()
                    description = dialog.get_description()
                    auto_lock = dialog.get_auto_lock()

                    self.logger.debug(f"对话框返回值: 地址={hex(address) if address else 'None'}, 类型={value_type}, 描述={description}, 自动锁定={auto_lock}")

                    if not address:
                        self.logger.warning("添加地址失败: 地址无效")
                        self.statusBar().showMessage("地址无效", 3000)
                        return

                    # 检查进程是否还在运行
                    if not self.memory_reader.process_handle:
                        self.logger.warning("添加地址失败: 进程未附加或已退出")
                        self.statusBar().showMessage("进程未附加或已退出", 3000)
                        return
                except Exception as e:
                    self.logger.error(f"处理对话框返回值时出错: {str(e)}")
                    import traceback
                    self.logger.error(f"错误详情:\n{traceback.format_exc()}")
                    self.statusBar().showMessage(f"添加地址失败: {str(e)}", 3000)
                    return

                # 保存原始值类型，避免影响其他任务
                original_value_type = self.memory_reader.current_value_type
                self.logger.debug(f"保存原始值类型: {original_value_type}")

                try:
                    # 验证数据类型
                    if value_type not in ['int32', 'float', 'double']:
                        self.logger.error(f"不支持的值类型: {value_type}")
                        self.statusBar().showMessage(f"不支持的数据类型: {value_type}", 3000)
                        return

                    # 记录数据类型信息
                    type_mapping = {
                        'int32': '整数',
                        'float': '浮点',
                        'double': '双精度'
                    }
                    self.logger.debug(f"使用数据类型: {value_type} ({type_mapping.get(value_type, '未知')})")

                    # 设置当前值类型
                    self.memory_reader.current_value_type = value_type
                    self.logger.debug(f"设置当前值类型为: {value_type}")

                    # 读取当前值
                    # self.logger.debug(f"尝试读取地址 {hex(address)} 的值")
                    try:
                        current_value = self.memory_reader.read_value(address)
                        if current_value is None:
                            self.logger.error(f"读取地址 {hex(address)} 的值失败")
                            self.statusBar().showMessage("读取地址失败", 3000)
                            return
                        # self.logger.debug(f"成功读取地址 {hex(address)} 的值: {current_value}")
                    except Exception as e:
                        self.logger.error(f"读取地址 {hex(address)} 的值时出错: {str(e)}")
                        import traceback
                        self.logger.error(f"错误详情:\n{traceback.format_exc()}")
                        self.statusBar().showMessage(f"读取地址失败: {str(e)}", 3000)
                        return

                    # 添加到结果表格
                    # self.logger.debug(f"尝试添加地址 {hex(address)} 到结果表格")
                    try:
                        success, is_locked, lock_value = add_to_result_table(
                            self.result_table,
                            address=address,
                            memory_reader=self.memory_reader,
                            value_type=value_type,
                            desc=description,
                            auto_lock=auto_lock,
                            logger=self.logger
                        )

                        if success:
                            self.logger.info(f"成功添加地址 {hex(address)} 到结果表格")
                            # 如果需要自动锁定
                            if is_locked and lock_value is not None:
                                try:
                                    # 添加到锁定地址
                                    self.locked_addresses[address] = lock_value
                                    self.logger.debug(f"自动锁定地址: {hex(address)}, 值={lock_value}")
                                except Exception as e:
                                    self.logger.error(f"锁定地址时出错: {str(e)}")
                                    # 继续执行，不要因为锁定失败而中断

                            self.statusBar().showMessage(f"已添加地址 {hex(address)} 到修改列表", 3000)
                        else:
                            self.logger.warning(f"添加地址 {hex(address)} 到结果表格失败")
                            self.statusBar().showMessage("添加地址失败", 3000)
                    except Exception as e:
                        self.logger.error(f"调用add_to_result_table函数时出错: {str(e)}")
                        import traceback
                        self.logger.error(f"错误详情:\n{traceback.format_exc()}")
                        self.statusBar().showMessage(f"添加地址失败: {str(e)}", 3000)
                except Exception as e:
                    self.logger.error(f"添加地址时出错: {str(e)}")
                    import traceback
                    self.logger.error(f"错误详情:\n{traceback.format_exc()}")
                    self.statusBar().showMessage(f"添加地址失败: {str(e)}", 3000)
                finally:
                    # 恢复原始值类型，避免影响其他任务
                    try:
                        if original_value_type is not None:
                            self.memory_reader.current_value_type = original_value_type
                            self.logger.debug(f"恢复原始值类型: {original_value_type}")
                    except Exception as e:
                        self.logger.error(f"恢复原始值类型时出错: {str(e)}")
        except Exception as e:
            self.logger.error(f"添加地址按钮点击事件处理失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情:\n{traceback.format_exc()}")
            self.statusBar().showMessage("添加地址失败", 3000)

    def _on_search_progress(self, message, log=False):
        """搜索进度回调"""
        try:
            # 更新状态栏
            self.statusBar().showMessage(message, 0)

            # 只有当log参数为True时才记录日志
            if log:
                self.logger.info(message)

            # 处理事件队列，保持UI响应
            QCoreApplication.processEvents()
        except Exception as e:
            self.logger.error(f"处理搜索进度回调失败: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())

    def _on_search_finished(self, results):
        """搜索完成回调"""
        try:
            # 获取当前活动的任务
            current_task = self.task_manager.get_current_task()
            if current_task:
                # 更新任务标签显示结果数量
                current_index = self.task_manager.currentIndex()
                new_tab_text = f"{current_task.display_name} ({len(results)})"
                self.task_manager.setTabText(current_index, new_tab_text)

                # 记录日志
                self.logger.info(f"搜索完成: 任务={current_task.display_name}, 结果数量={len(results)}")

            # 重新启用搜索按钮
            self.search_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        except Exception as e:
            self.logger.error(f"处理搜索完成回调失败: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            # 确保按钮被重新启用
            self.search_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def _on_stop_clicked(self):
        """停止按钮点击事件"""
        try:
            if hasattr(self, 'search_thread') and self.search_thread:
                self.logger.info("用户请求停止搜索")
                self.search_thread.stop()
                self.status_bar.showMessage("搜索已停止", 3000)

                # 重新启用搜索按钮
                self.search_button.setEnabled(True)
                self.stop_button.setEnabled(False)
        except Exception as e:
            self.logger.error(f"停止搜索失败: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())

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