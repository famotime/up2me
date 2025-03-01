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

    def _on_tab_close(self, index):
        """处理标签页关闭事件"""
        if len(self.tasks) <= 1:
            QMessageBox.warning(self, "警告", "至少保留一个搜索任务！")
            return

        # 确认是否关闭
        task = self.tasks[index]
        reply = QMessageBox.question(self, "确认", f'确定要关闭任务"{task.name}"吗？', QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
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
            self.setTabText(index, new_name)