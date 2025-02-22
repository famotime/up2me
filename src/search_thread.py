from PyQt5.QtCore import QThread, pyqtSignal

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