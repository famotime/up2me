from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                            QComboBox, QLineEdit, QPushButton, QTableWidget,
                            QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QSize

def create_process_section(process_combo, refresh_callback, attach_callback):
    """创建进程选择区域"""
    process_layout = QHBoxLayout()

    # 设置下拉框样式和大小
    process_combo.setIconSize(QSize(16, 16))
    process_combo.view().setIconSize(QSize(16, 16))  # 设置下拉列表的图标大小
    process_combo.setStyleSheet("""
        QComboBox {
            padding: 5px 5px 5px 25px;  /* 调整左边距 */
            min-height: 25px;
        }
        QComboBox::item {
            padding-left: 25px;  /* 调整下拉项左边距 */
            height: 25px;
            icon-size: 16px;  /* 设置图标大小 */
        }
        QComboBox::item:selected {
            background-color: #0078d7;
            color: white;
        }
    """)
    process_combo.setMinimumWidth(300)  # 设置最小宽度

    refresh_btn = QPushButton('刷新')
    attach_btn = QPushButton('附加')

    process_layout.addWidget(QLabel('选择进程:'))
    process_layout.addWidget(process_combo)
    process_layout.addWidget(refresh_btn)
    process_layout.addWidget(attach_btn)

    refresh_btn.clicked.connect(refresh_callback)
    attach_btn.clicked.connect(attach_callback)

    return process_layout

def create_search_section(search_input, type_combo, compare_combo, search_callback,
                      new_task_callback):
    """创建搜索区域"""
    search_layout = QHBoxLayout()  # 使用水平布局

    # 搜索条
    search_input.setPlaceholderText('输入搜索值')

    # 添加数值类型选择
    type_combo.addItems(['整数', '浮点数', '双精度'])

    # 添加比较方式
    compare_combo.addItems(['精确匹配', '大于', '小于', '已改变', '未改变'])

    # 添加控件到布局
    search_layout.addWidget(QLabel('数值:'))
    search_layout.addWidget(search_input)
    search_layout.addWidget(QLabel('类型:'))
    search_layout.addWidget(type_combo)
    search_layout.addWidget(QLabel('比较:'))
    search_layout.addWidget(compare_combo)

    # 添加搜索按钮
    search_btn = QPushButton('搜索')
    search_btn.clicked.connect(search_callback)
    search_layout.addWidget(search_btn)

    # 添加新建任务按钮
    new_task_btn = QPushButton('新建')
    new_task_btn.clicked.connect(new_task_callback)
    search_layout.addWidget(new_task_btn)

    # 返回布局和搜索按钮，以便在主类中保存引用
    return search_layout, search_btn

def create_button(text, callback):
    """创建按钮的辅助方法"""
    btn = QPushButton(text)
    btn.clicked.connect(callback)
    return btn

def create_memory_table():
    """创建内存表格"""
    memory_table = QTableWidget()
    memory_table.setColumnCount(5)
    memory_table.setHorizontalHeaderLabels(['地址', '当前值', '先前值', '首次值', '类型'])

    # 设置表格样式
    memory_table.setStyleSheet("""
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
    memory_table.horizontalHeader().setStretchLastSection(True)
    memory_table.verticalHeader().setVisible(False)
    memory_table.setAlternatingRowColors(True)
    memory_table.setSelectionBehavior(QTableWidget.SelectRows)
    memory_table.setEditTriggers(QTableWidget.NoEditTriggers)

    return memory_table

def create_result_table(lock_delegate):
    """创建结果表格"""
    result_table = QTableWidget()
    result_table.setColumnCount(5)
    result_table.setHorizontalHeaderLabels(['名称', '地址', '数值', '类型', '锁定'])

    # 设置表格样式
    result_table.setStyleSheet("""
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
    result_table.horizontalHeader().setStretchLastSection(True)
    result_table.verticalHeader().setVisible(False)
    result_table.setAlternatingRowColors(True)
    result_table.setSelectionBehavior(QTableWidget.SelectRows)

    # 设置锁定列的代理
    result_table.setItemDelegateForColumn(4, lock_delegate)

    return result_table

def create_table_control_section(new_address_callback, delete_address_callback, clear_results_callback):
    """创建表格控制区域"""
    control_layout = QHBoxLayout()

    # 添加按钮
    control_layout.addWidget(create_button('添加', new_address_callback))
    control_layout.addWidget(create_button('删除', delete_address_callback))
    control_layout.addWidget(create_button('清空', clear_results_callback))

    # 添加弹性空间
    control_layout.addStretch()

    return control_layout