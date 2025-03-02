from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout,
                            QInputDialog, QMenu, QMessageBox)
from PyQt5.QtCore import Qt
from utils.search_task import SearchTask

class SearchTaskManager(QTabWidget):
    """搜索任务管理器，管理多个搜索任务"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self._on_tab_close)
        self.tabBarDoubleClicked.connect(self._on_tab_double_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.currentChanged.connect(self._on_tab_changed)

        # 初始化日志记录器
        import logging
        self.logger = logging.getLogger('game_cheater')

        # 创建第一个任务
        self.add_task()

    def add_task(self, name=None):
        """添加新的搜索任务"""
        if name is None:
            name = f"任务{len(self.tasks) + 1}"

        # 创建新任务
        task = SearchTask(name)
        self.tasks.append(task)

        # 创建任务页面
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建并添加内存表格
        memory_table = task.create_memory_table()
        layout.addWidget(memory_table)

        # 添加新标签页
        self.addTab(page, name)
        self.setCurrentIndex(len(self.tasks) - 1)

        return task

    def get_current_task(self):
        """获取当前活动的任务"""
        current_index = self.currentIndex()
        if 0 <= current_index < len(self.tasks):
            return self.tasks[current_index]
        return None

    def stop_all_searches(self):
        """停止所有任务的搜索"""
        for task in self.tasks:
            if task.is_searching:
                task.stop_search()

    def get_searching_tasks_count(self):
        """获取正在搜索的任务数量"""
        count = 0
        for task in self.tasks:
            if task.is_searching:
                count += 1
        return count

    def clear_all_tasks_results(self):
        """清空所有任务的搜索结果"""
        try:
            self.logger.debug("开始清空所有任务的搜索结果")
            for task in self.tasks:
                try:
                    task.clear()
                    self.logger.debug(f"已清空任务 '{task.name}' 的搜索结果")
                except Exception as e:
                    self.logger.error(f"清空任务 '{task.name}' 的搜索结果时出错: {str(e)}")
                    import traceback
                    self.logger.error(f"错误详情:\n{traceback.format_exc()}")
            self.logger.info(f"已清空所有 {len(self.tasks)} 个任务的搜索结果")
        except Exception as e:
            self.logger.error(f"清空所有任务搜索结果时出错: {str(e)}")
            import traceback
            self.logger.error(f"错误详情:\n{traceback.format_exc()}")

    def update_task_tab_text(self, index, text):
        """更新任务标签文本，并保存到任务对象中"""
        if 0 <= index < len(self.tasks):
            task = self.tasks[index]
            task.display_name = text  # 保存显示名称
            self.setTabText(index, text)

    def get_task_tab_text(self, index):
        """获取任务标签文本"""
        if 0 <= index < len(self.tasks):
            task = self.tasks[index]
            return getattr(task, 'display_name', task.name)
        return ""

    def _on_tab_close(self, index):
        """处理标签页关闭事件"""
        if len(self.tasks) <= 1:
            QMessageBox.warning(self, "警告", "至少保留一个搜索任务！")
            return

        # 确认是否关闭
        task = self.tasks[index]

        # 如果任务正在搜索，提示用户
        if task.is_searching:
            reply = QMessageBox.question(self, "确认",
                                        f'任务"{task.name}"正在搜索中，确定要关闭吗？',
                                        QMessageBox.Yes | QMessageBox.No)
        else:
            reply = QMessageBox.question(self, "确认",
                                        f'确定要关闭任务"{task.name}"吗？',
                                        QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            # 如果任务正在搜索，先停止搜索
            if task.is_searching:
                task.stop_search()

            self.removeTab(index)
            self.tasks.pop(index)

    def _on_tab_double_clicked(self, index):
        """处理标签页双击事件"""
        if index >= 0:
            self._rename_task(index)

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        index = self.tabBar().tabAt(pos)
        if index >= 0:
            menu = QMenu(self)
            rename_action = menu.addAction("重命名")
            delete_action = menu.addAction("删除")

            action = menu.exec_(self.mapToGlobal(pos))
            if action == rename_action:
                self._rename_task(index)
            elif action == delete_action:
                self.tabCloseRequested.emit(index)

    def _rename_task(self, index):
        """重命名任务"""
        task = self.tasks[index]
        new_name, ok = QInputDialog.getText(self, "重命名任务",
                                          "请输入新的任务名称:",
                                          text=task.name)
        if ok and new_name:
            task.name = new_name
            # 更新显示名称
            if hasattr(task, 'display_name'):
                # 如果有结果数量，保留它
                if '(' in task.display_name and ')' in task.display_name:
                    count_part = task.display_name.split('(')[1].split(')')[0]
                    task.display_name = f"{new_name} ({count_part})"
                else:
                    task.display_name = new_name
            else:
                task.display_name = new_name
            self.setTabText(index, task.display_name)

    def _on_tab_changed(self, index):
        """处理标签页切换事件"""
        if 0 <= index < len(self.tasks):
            current_task = self.tasks[index]

            # 确保显示正确的标签文本
            if hasattr(current_task, 'display_name'):
                self.setTabText(index, current_task.display_name)

            # 确保当前任务的内存表格显示正确的数据
            if current_task.memory_table and current_task.search_results:
                try:
                    from utils.memory_helper import update_memory_table

                    # 保存原始值类型，避免影响其他任务
                    if hasattr(current_task, 'memory_reader') and current_task.memory_reader:
                        original_value_type = current_task.memory_reader.current_value_type

                        try:
                            # 临时设置memory_reader的值类型为当前任务的值类型
                            if current_task.value_type:
                                current_task.memory_reader.current_value_type = current_task.value_type

                            # 更新内存表格
                            update_memory_table(
                                current_task.memory_table,
                                current_task.search_results,
                                current_task.memory_reader,
                                task_value_type=current_task.value_type,
                                first_values=current_task.first_values,
                                prev_values=current_task.prev_values,
                                current_values=current_task.current_values
                            )
                        finally:
                            # 恢复原始值类型，避免影响其他任务
                            current_task.memory_reader.current_value_type = original_value_type
                except Exception as e:
                    import logging
                    logger = logging.getLogger('game_cheater')
                    logger.error(f"切换标签页更新内存表格失败: {str(e)}")
                    import traceback
                    logger.debug(traceback.format_exc())