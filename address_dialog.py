from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QLineEdit, QComboBox, QRadioButton, QGroupBox,
                           QPushButton, QCheckBox, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class AddressDialog(QDialog):
    def __init__(self, parent=None, address=None, value=None):
        super().__init__(parent)
        self.setWindowTitle("添加修改")
        self.setFixedSize(500, 280)  # 增加窗口大小

        # 创建主布局
        layout = QVBoxLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        # 创建上部分左右布局
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)  # 增加左右区域间距
        layout.addLayout(top_layout)

        # 左侧 - 数据属性组
        data_group = QGroupBox("数据属性")
        data_group.setMinimumWidth(230)  # 增加左侧宽度
        data_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #a0a0a0;
                margin-top: 6px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        data_layout = QGridLayout()
        data_layout.setSpacing(8)  # 增加网格间距
        data_group.setLayout(data_layout)

        # 创建标签和输入框
        labels = ['名称:', '数值:', '长度:', '地址:']
        self.inputs = {}

        for i, label_text in enumerate(labels):
            label = QLabel(label_text)
            label.setFixedWidth(50)  # 增加标签宽度

            if i == 0:  # 名称 - 下拉框
                input_widget = QComboBox()
                input_widget.setEditable(True)
                input_widget.addItems(['金钱', '生命值', '魔法值', '经验值', '等级'])
                self.name_combo = input_widget
            elif i == 2:  # 长度 - 下拉框
                input_widget = QComboBox()
                input_widget.addItems(['单字节', '双字节', '四字节', '八字节'])  # 添加八字节选项
                self.length_combo = input_widget
            else:  # 其他 - 文本框
                input_widget = QLineEdit()
                if i == 1 and value is not None:  # 数值
                    input_widget.setText(str(value))
                elif i == 3 and address is not None:  # 地址
                    input_widget.setText(address)

            label.setBuddy(input_widget)
            data_layout.addWidget(label, i, 0)
            data_layout.addWidget(input_widget, i, 1)
            # 存储时使用不带格式符的键名
            key = label_text.replace('(&N)', '').replace('(&V)', '').replace('(&R)', '')\
                          .replace('(&L)', '').replace('(&A)', '').replace(':', '')
            self.inputs[key] = input_widget

        top_layout.addWidget(data_group)

        # 右侧布局
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)  # 增加垂直间距
        top_layout.addLayout(right_layout)

        # 右侧 - 修改方式组
        modify_group = QGroupBox("修改方式")
        modify_group.setStyleSheet(data_group.styleSheet())
        modify_layout = QVBoxLayout()
        modify_layout.setSpacing(8)
        modify_group.setLayout(modify_layout)

        self.auto_radio = QRadioButton("自动锁定")
        self.manual_radio = QRadioButton("手动修改")
        self.manual_radio.setChecked(True)

        modify_layout.addWidget(self.auto_radio)
        modify_layout.addWidget(self.manual_radio)

        right_layout.addWidget(modify_group)

        # 右侧 - 数据类型组
        type_group = QGroupBox("数据类型")
        type_group.setStyleSheet(data_group.styleSheet())
        type_layout = QVBoxLayout()  # 改为垂直布局以容纳更多选项
        type_layout.setSpacing(8)  # 增加垂直间距
        type_group.setLayout(type_layout)

        self.type_int = QRadioButton("整型")
        self.type_float = QRadioButton("浮点")
        self.type_double = QRadioButton("双精度")  # 添加双精度选项
        self.type_string = QRadioButton("字符串")
        self.type_int.setChecked(True)

        # 添加数据类型改变事件处理
        self.type_int.toggled.connect(self._on_type_changed)
        self.type_float.toggled.connect(self._on_type_changed)
        self.type_double.toggled.connect(self._on_type_changed)
        self.type_string.toggled.connect(self._on_type_changed)

        type_layout.addWidget(self.type_int)
        type_layout.addWidget(self.type_float)
        type_layout.addWidget(self.type_double)  # 添加双精度选项
        type_layout.addWidget(self.type_string)

        right_layout.addWidget(type_group)
        right_layout.addStretch()

        # 底部布局
        bottom_layout = QVBoxLayout()
        layout.addLayout(bottom_layout)

        # 超出范围警告选项
        self.range_warning = QCheckBox("修改超出范围时警告")
        self.range_warning.setChecked(True)
        bottom_layout.addWidget(self.range_warning)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.ok_button = QPushButton("确定(&O)")
        self.cancel_button = QPushButton("取消(&C)")

        button_style = """
            QPushButton {
                min-width: 75px;
                padding: 4px 8px;
            }
        """
        self.ok_button.setStyleSheet(button_style)
        self.cancel_button.setStyleSheet(button_style)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        bottom_layout.addLayout(button_layout)

        # 初始化长度选择
        self._on_type_changed()

    def _on_type_changed(self):
        """处理数据类型改变事件"""
        # 根据数据类型设置对应的长度
        if self.type_int.isChecked():
            self.length_combo.setCurrentText('四字节')
        elif self.type_float.isChecked():
            self.length_combo.setCurrentText('四字节')
        elif self.type_double.isChecked():
            self.length_combo.setCurrentText('八字节')
        else:  # string
            self.length_combo.setCurrentText('单字节')

    def get_values(self):
        """获取对话框中的所有值"""
        data_type = ('int' if self.type_int.isChecked() else
                    'float' if self.type_float.isChecked() else
                    'double' if self.type_double.isChecked() else 'string')
        return {
            'name': self.name_combo.currentText(),
            'value': self.inputs['数值'].text(),
            'length': self.length_combo.currentText(),
            'address': self.inputs['地址'].text(),
            'auto_lock': self.auto_radio.isChecked(),
            'data_type': data_type,
            'range_warning': self.range_warning.isChecked()
        }