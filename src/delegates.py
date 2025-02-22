from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate
from PyQt5.QtCore import Qt

class LockStateDelegate(QStyledItemDelegate):
    """锁定状态下拉菜单代理"""
    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(["是", "否"])
        editor.currentTextChanged.connect(lambda: self.commitData.emit(editor))
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole)
        editor.setCurrentText(value)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)