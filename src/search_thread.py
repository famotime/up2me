from PyQt5.QtCore import QThread, pyqtSignal

class SearchThread(QThread):
    """搜索线程"""
    finished = pyqtSignal(list)  # 搜索完成信号
    progress = pyqtSignal(str, bool)  # 进度信号，包含消息和是否记录到日志

    def __init__(self, memory_reader, value, value_type):
        super().__init__()
        self.memory_reader = memory_reader
        self.value = value
        self.value_type = value_type

    def run(self):
        try:
            def progress_callback(current, total):
                progress = current * 100 // total if total > 0 else 0
                self.progress.emit(f"正在搜索... {progress}% ({current}/{total})", False)

            results = self.memory_reader.search_value(
                self.value,
                self.value_type,
                'exact',
                progress_callback=progress_callback
            )

            # 发送完成信号
            self.progress.emit(f"搜索完成: 找到 {len(results)} 个匹配地址", True)
            self.finished.emit(results)
        except Exception as e:
            self.progress.emit(f"搜索失败: {str(e)}", True)
            self.finished.emit([])