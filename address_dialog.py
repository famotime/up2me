from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                           QLabel, QPushButton, QComboBox)

class AddressDialog(QDialog):
    """添加地址对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('添加新地址')
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 地址输入
        addr_layout = QHBoxLayout()
        addr_label = QLabel('地址:')
        self.addr_input = QLineEdit()
        self.addr_input.setPlaceholderText('输入16进制地址 (例如: 0x12345678)')
        addr_layout.addWidget(addr_label)
        addr_layout.addWidget(self.addr_input)
        layout.addLayout(addr_layout)

        # 描述输入
        desc_layout = QHBoxLayout()
        desc_label = QLabel('描述:')
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText('输入描述信息')
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.desc_input)
        layout.addLayout(desc_layout)

        # 类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel('类型:')
        self.type_combo = QComboBox()
        self.type_combo.addItems(['整数(4字节)', '浮点数', '双精度'])
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # 按钮区域
        button_layout = QHBoxLayout()
        ok_button = QPushButton('确定')
        cancel_button = QPushButton('取消')
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)