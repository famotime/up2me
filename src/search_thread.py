from PyQt5.QtCore import QThread, pyqtSignal

class SearchThread(QThread):
    """搜索线程"""
    finished = pyqtSignal(list)  # 搜索完成信号
    progress = pyqtSignal(str, bool)  # 进度信号，包含消息和是否记录到日志

    def __init__(self, memory_reader, search_params):
        super().__init__()
        self.memory_reader = memory_reader
        self.search_params = search_params

    def run(self):
        try:
            def progress_callback(current, total):
                progress = current * 100 // total if total > 0 else 0
                self.progress.emit(f"正在搜索... {progress}% ({current}/{total})", False)

            # 获取搜索参数
            value = self.search_params['value']
            value_type = self.search_params['value_type']
            compare_type = self.search_params['compare_type']
            last_results = self.search_params['last_results']
            is_first_search = self.search_params['is_first_search']

            # 转换比较类型
            compare_map = {
                '精确匹配': 'exact',
                '大于': 'bigger',
                '小于': 'smaller',
                '已改变': 'changed',
                '未改变': 'unchanged'
            }

            # 如果是首次搜索或是"已改变"/"未改变"，则搜索整个内存
            search_in_results = None if is_first_search or compare_type in ['已改变', '未改变'] else last_results

            results = self.memory_reader.search_value(
                value,
                value_type,
                compare_map.get(compare_type, 'exact'),
                progress_callback=progress_callback,
                search_in_results=search_in_results
            )

            # 发送完成信号
            self.progress.emit(f"搜索完成: 找到 {len(results)} 个匹配地址", True)
            self.finished.emit(results)

        except Exception as e:
            self.progress.emit(f"搜索失败: {str(e)}", True)
            self.finished.emit([])