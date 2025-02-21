import sys
import ctypes
import win32com.shell.shell as shell
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
                           QLineEdit, QLabel, QHeaderView, QComboBox, QProgressDialog,
                           QMessageBox)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
import psutil
from memory_reader import MemoryReader
from utils.logger import setup_logger
import traceback
from pathlib import Path
import struct
import json
from address_dialog import AddressDialog

class GameCheater(QMainWindow):
    search_completed = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.search_thread = None  # 添加线程引用
        # 初始化日志记录器
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

        # 添加状态栏初始化
        self.statusBar().showMessage('搜索 0 次找到 0 个地址')

        # 初始化定时器
        self._setup_timer()

        # 优化UI布局
        self._setup_ui()

        # 初始化进程列表
        self.refresh_process_list()

        # 添加双击事件处理
        self.memory_table.cellDoubleClicked.connect(self._on_memory_table_double_clicked)

    def _setup_ui(self):
        """设置UI布局"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # 添加进程选择区域
        layout.addLayout(self._create_process_section())

        # 添加搜索区域
        layout.addLayout(self._create_search_section())

        # 添加表格
        layout.addWidget(self._create_memory_table())
        layout.addWidget(self._create_result_table())

    def _create_process_section(self):
        """创建进程选择区域"""
        process_layout = QHBoxLayout()
        self.process_combo = QComboBox()
        refresh_btn = QPushButton('刷新')
        attach_btn = QPushButton('附加')

        process_layout.addWidget(QLabel('选择进程:'))
        process_layout.addWidget(self.process_combo)
        process_layout.addWidget(refresh_btn)
        process_layout.addWidget(attach_btn)

        refresh_btn.clicked.connect(self.refresh_process_list)
        attach_btn.clicked.connect(self.attach_process)

        return process_layout

    def _create_search_section(self):
        """创建搜索区域"""
        search_layout = QVBoxLayout()  # 改用垂直布局

        # 上方搜索条
        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入搜索值')

        # 添加数值类型选择
        self.type_combo = QComboBox()
        self.type_combo.addItems(['整数(4字节)', '浮点数', '双精度'])

        # 添加比较方式
        self.compare_combo = QComboBox()
        self.compare_combo.addItems(['精确匹配', '大于', '小于', '已改变', '未改变'])

        top_layout.addWidget(QLabel('数值:'))
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(QLabel('类型:'))
        top_layout.addWidget(self.type_combo)
        top_layout.addWidget(QLabel('比较:'))
        top_layout.addWidget(self.compare_combo)

        # 下方按钮区
        button_layout = QHBoxLayout()

        # 搜索按钮组
        search_buttons = QHBoxLayout()
        search_buttons.addWidget(self._create_button('首次扫描', self.first_scan))
        search_buttons.addWidget(self._create_button('下一次扫描', self.next_scan))
        button_layout.addLayout(search_buttons)

        button_layout.addStretch()  # 添加弹性空间

        # 结果操作按钮组
        result_buttons = QHBoxLayout()
        result_buttons.addWidget(self._create_button('添加', self.new_address))
        result_buttons.addWidget(self._create_button('删除', self.delete_address))
        result_buttons.addWidget(self._create_button('清空', self.clear_results))
        button_layout.addLayout(result_buttons)

        search_layout.addLayout(top_layout)
        search_layout.addLayout(button_layout)
        return search_layout

    def _create_button(self, text, callback):
        """创建按钮的辅助方法"""
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        return btn

    def _create_memory_table(self):
        """创建内存表格"""
        self.memory_table = QTableWidget()
        self.memory_table.setColumnCount(5)
        self.memory_table.setHorizontalHeaderLabels(['地址', '单字节', '双字节', '四字节', '类型'])

        # 设置表格样式
        self.memory_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #d8d8d8;
                selection-background-color: #0078d7;
                selection-color: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: none;
                border-right: 1px solid #d8d8d8;
                border-bottom: 1px solid #d8d8d8;
            }
        """)

        # 优化表格外观
        self.memory_table.horizontalHeader().setStretchLastSection(True)
        self.memory_table.verticalHeader().setVisible(False)
        self.memory_table.setAlternatingRowColors(True)
        self.memory_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.memory_table.setEditTriggers(QTableWidget.NoEditTriggers)

        return self.memory_table

    def _create_result_table(self):
        """创建结果表格"""
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(['名称', '地址', '数值', '类型', '锁定', '说明'])

        # 设置表格样式
        self.result_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #d8d8d8;
                selection-background-color: #0078d7;
                selection-color: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: none;
                border-right: 1px solid #d8d8d8;
                border-bottom: 1px solid #d8d8d8;
            }
        """)

        # 优化表格外观
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)

        # 允许编辑数值和锁定列
        self.result_table.itemChanged.connect(self._on_result_item_changed)

        return self.result_table

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
                        # 确保使用4字节，支持负数
                        if value < 0:
                            # 负数需要特殊处理，使用补码
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
                        # 读取回写入的值进行验证
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

    def _setup_timer(self):
        """设置定时器用于更新锁定的值和刷新显示"""
        self.lock_timer = QTimer()
        self.lock_timer.timeout.connect(self._update_timer_event)
        self.lock_timer.start(100)  # 每100ms更新一次

    def _update_timer_event(self):
        """定时器事件：更新锁定值和刷新显示"""
        try:
            # 更新锁定的值
            self._update_locked_values()

            # 刷新内存表格显示
            self._refresh_memory_table()

            # 刷新结果表格显示
            self._refresh_result_table()

        except Exception as e:
            self.logger.error(f"定时更新失败: {str(e)}")

    def _refresh_memory_table(self):
        """刷新内存表格的值"""
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
        """刷新结果表格的值"""
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
        """刷新进程列表，只显示可能是游戏的进程"""
        self.process_combo.clear()
        last_process = self.config.get('last_process')
        selected_index = -1

        # 系统进程黑名单
        system_processes = {
            'svchost.exe', 'csrss.exe', 'services.exe', 'lsass.exe', 'winlogon.exe',
            'explorer.exe', 'smss.exe', 'spoolsv.exe', 'wininit.exe', 'taskmgr.exe',
            'conhost.exe', 'cmd.exe', 'powershell.exe', 'notepad.exe', 'chrome.exe',
            'firefox.exe', 'msedge.exe', 'RuntimeBroker.exe', 'SearchApp.exe',
            'SystemSettings.exe', 'TextInputHost.exe', 'SearchIndexer.exe'
        }

        try:
            # 用列表收集符合条件的进程
            game_processes = []

            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower()

                    # 跳过系统进程
                    if proc_name in system_processes:
                        continue

                    # 检查是否可能是游戏进程
                    is_game = False

                    # 检查进程名称特征
                    game_keywords = ['game', 'unity', 'unreal', 'ue4', 'ue5', 'godot',
                                   'cryengine', 'directx', 'vulkan', 'opengl']

                    if any(keyword in proc_name for keyword in game_keywords):
                        is_game = True

                    # 检查可执行文件路径
                    if proc_info['exe']:
                        exe_path = Path(proc_info['exe']).resolve()

                        # 检查是否在游戏常见目录
                        game_paths = ['games', 'steam', 'program files (x86)', 'program files']
                        if any(game_path in str(exe_path).lower() for game_path in game_paths):
                            is_game = True

                        # 检查是否包含游戏相关DLL
                        try:
                            if proc.memory_maps():
                                dlls = [m.path.lower() for m in proc.memory_maps() if m.path.endswith('.dll')]
                                game_dlls = ['d3d', 'xinput', 'unity', 'unreal', 'mono', 'physics']
                                if any(any(dll_name in dll for dll_name in game_dlls) for dll in dlls):
                                    is_game = True
                        except:
                            pass

                    if is_game:
                        # 将进程信息添加到列表中
                        game_processes.append((proc_info['name'], proc_info['pid']))

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # 按进程名称排序（不区分大小写）
            game_processes.sort(key=lambda x: x[0].lower())

            # 将排序后的进程添加到下拉列表
            for i, (name, pid) in enumerate(game_processes):
                process_text = f"{name} ({pid})"
                self.process_combo.addItem(process_text)

                # 如果找到上次使用的进程，记录其索引
                if last_process and last_process['name'] == name:
                    selected_index = i

            # 如果找到上次使用的进程，设置为当前选中项
            if selected_index >= 0:
                self.process_combo.setCurrentIndex(selected_index)
                self.logger.info(f"找到上次使用的进程: {last_process['name']}")

            # 更新状态栏显示找到的进程数量
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
        self._update_memory_table(results)
        self.search_thread = None  # 清理线程引用

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

            self._update_memory_table(results)

        except ValueError:
            self.statusBar().showMessage('请输入有效的数值')

    def _update_memory_table(self, results):
        """更新内存表格显示"""
        self.memory_table.setRowCount(len(results))
        total = len(results)

        try:
            for i, addr in enumerate(results):
                # 更新状态栏显示进度
                progress = (i + 1) * 100 // total if total > 0 else 100
                self.statusBar().showMessage(f"正在读取内存值... {progress}% ({i + 1}/{total})")

                # 让UI有机会更新
                QApplication.processEvents()

                # 设置地址
                self.memory_table.setItem(i, 0, QTableWidgetItem(hex(addr)))

                # 读取不同大小的内存值
                value = self.memory_reader.read_memory(addr, 4)
                if value:
                    # 单字节值
                    self.memory_table.setItem(i, 1, QTableWidgetItem(str(value[0])))

                    # 双字节值
                    word_val = int.from_bytes(value[:2], 'little')
                    self.memory_table.setItem(i, 2, QTableWidgetItem(str(word_val)))

                    # 四字节值（整数和浮点数）
                    dword_val = int.from_bytes(value, 'little')
                    float_val = struct.unpack('<f', value)[0]
                    self.memory_table.setItem(i, 3, QTableWidgetItem(f"{dword_val} ({float_val:.2f})"))

                    # 推测类型
                    value_type = self._guess_value_type(value)
                    self.memory_table.setItem(i, 4, QTableWidgetItem(value_type))

            # 搜索完成后显示结果提示
            self._show_search_result_tips(total)

        except Exception as e:
            self.logger.error(f"更新内存表格失败: {str(e)}")
            self.statusBar().showMessage("更新内存表格时发生错误")

    def _guess_value_type(self, value):
        """推测内存值类型"""
        try:
            int_val = int.from_bytes(value, 'little')
            float_val = struct.unpack('<f', value)[0]

            # 检查是否可能是浮点数
            if abs(float_val) > 0.01 and abs(float_val) < 1000000:
                return "浮点数"
            # 检查是否在合理的整数范围内
            elif 0 <= int_val <= 1000000:
                return "整数"
            else:
                return "未知"
        except:
            return "未知"

    def _show_search_result_tips(self, result_count):
        """显示搜索结果提示"""
        if result_count == 0:
            msg = "未找到匹配的内存值"
        elif result_count > 1000:
            msg = f"找到 {result_count} 个匹配地址，建议在游戏中改变目标值后继续筛选"
        elif result_count > 100:
            msg = f"找到 {result_count} 个匹配地址，建议改变游戏中的值继续筛选"
        else:
            msg = f"找到 {result_count} 个匹配地址，可以尝试修改这些地址的值"

        # 更新状态栏
        self.statusBar().showMessage(msg)

    def new_address(self):
        """添加新地址到结果表格"""
        try:
            dialog = AddressDialog(self)
            if dialog.exec_():
                values = dialog.get_values()
                try:
                    addr = int(values['address'], 16)
                    self._add_to_result_table(
                        addr=addr,
                        desc=values['name'],
                        value_type=values['data_type'],
                        initial_value=values['value'],
                        auto_lock=values['auto_lock']
                    )
                    self.statusBar().showMessage(f"已添加地址 {hex(addr)} 到修改列表")
                except ValueError:
                    self.statusBar().showMessage('请输入有效的地址')
        except Exception as e:
            self.logger.error(f"添加地址失败: {str(e)}")
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
            value = self.memory_table.item(row, 3).text().split(' ')[0]  # 获取四字节值
            value_type = self.memory_table.item(row, 4).text()

            # 创建并显示添加地址对话框，传入地址和值
            dialog = AddressDialog(self, address=addr, value=value)

            # 设置数据类型
            if "浮点" in value_type:
                dialog.type_float.setChecked(True)
            elif "字符" in value_type:
                dialog.type_string.setChecked(True)
            else:
                dialog.type_int.setChecked(True)

            # 设置长度
            if "单字节" in value_type:
                dialog.length_combo.setCurrentText("单字节")
            elif "双字节" in value_type:
                dialog.length_combo.setCurrentText("双字节")
            else:
                dialog.length_combo.setCurrentText("四字节")

            # 显示对话框
            if dialog.exec_():
                values = dialog.get_values()
                # 添加到结果表格
                self._add_to_result_table(
                    addr=int(addr, 16),
                    desc=values['name'],
                    value_type=values['data_type'],
                    initial_value=values['value'],
                    auto_lock=values['auto_lock']
                )

                self.statusBar().showMessage(f"已添加地址 {addr} 到修改列表")

        except Exception as e:
            self.logger.error(f"处理双击事件失败: {str(e)}")
            self.logger.debug(traceback.format_exc())
            self.statusBar().showMessage("添加地址失败")

    def _add_to_result_table(self, addr, desc, value_type, initial_value, auto_lock=False):
        """添加一行到结果表格"""
        try:
            # 先尝试写入内存
            try:
                # 根据类型转换值并写入内存
                if value_type == 'int':
                    value = int(initial_value)
                    if value < 0:
                        value = value & 0xFFFFFFFF
                    buffer = value.to_bytes(4, 'little')
                elif value_type == 'float':
                    value = float(initial_value)
                    buffer = struct.pack('<f', value)
                else:  # 字符串
                    value = str(initial_value)
                    buffer = value.encode('utf-8')

                # 写入内存并验证
                if not self.memory_reader.write_memory(addr, buffer):
                    raise Exception("写入内存失败")

                # 读取回写入的值进行验证
                verify_value = self.memory_reader.read_memory(addr, len(buffer))
                if verify_value != buffer:
                    raise Exception("写入验证失败")

                self.logger.info(f"成功写入并验证地址 {hex(addr)}: {value}")

            except Exception as e:
                self.logger.error(f"初始写入失败: {str(e)}")
                # 写入失败时仍然添加到表格，但不设置锁定
                auto_lock = False

            # 添加到结果表格
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)

            # 转换数据类型显示
            display_type = {
                'int': '整数',
                'float': '浮点',
                'string': '字符串'
            }.get(value_type, '整数')  # 默认为整数

            items = [
                (0, desc),                # 名称
                (1, hex(addr)),          # 地址
                (2, str(initial_value)), # 当前值
                (3, display_type),       # 类型
                (4, "是" if auto_lock else "否"),  # 锁定状态
                (5, desc)                # 说明
            ]

            # 先创建所有项目，再设置到表格中
            for col, value in items:
                item = QTableWidgetItem(str(value))
                # 让数值列和锁定列可编辑
                if col not in [2, 4]:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.result_table.setItem(row, col, item)

            # 如果设置了自动锁定，添加到锁定列表
            if auto_lock:
                try:
                    if value_type == 'int':
                        self.locked_addresses[addr] = int(initial_value)
                    elif value_type == 'float':
                        self.locked_addresses[addr] = float(initial_value)
                    else:
                        self.locked_addresses[addr] = str(initial_value)
                except ValueError:
                    self.logger.warning(f"无法锁定值: {initial_value}")
                    # 设置锁定状态为否
                    self.result_table.item(row, 4).setText("否")

            return True

        except Exception as e:
            self.logger.error(f"添加到结果表格失败: {str(e)}")
            return False

class SearchThread(QThread):
    """搜索线程"""
    finished = pyqtSignal(list)  # 搜索完成信号

    def __init__(self, memory_reader, value, value_type):
        super().__init__()
        self.memory_reader = memory_reader
        self.value = value
        self.value_type = value_type

    def run(self):
        try:
            results = self.memory_reader.search_value(self.value, self.value_type, 'exact')
            self.finished.emit(results)
        except Exception as e:
            self.logger.error(f"搜索失败: {str(e)}")
            self.finished.emit([])

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