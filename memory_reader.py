import win32api
import win32process
import win32security
import win32con
import psutil
import ctypes
from ctypes import wintypes, Structure, sizeof, byref
import logging
import struct
import traceback

# 定义内存信息结构体
class MEMORY_BASIC_INFORMATION(Structure):
    _fields_ = [
        ("BaseAddress", wintypes.LPVOID),
        ("AllocationBase", wintypes.LPVOID),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]

# 定义内存保护常量
PAGE_READABLE = (
    win32con.PAGE_EXECUTE_READ |
    win32con.PAGE_EXECUTE_READWRITE |
    win32con.PAGE_READONLY |
    win32con.PAGE_READWRITE
)

# 在文件开头添加
class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ("wProcessorArchitecture", wintypes.WORD),
        ("wReserved", wintypes.WORD),
        ("dwPageSize", wintypes.DWORD),
        ("lpMinimumApplicationAddress", wintypes.LPVOID),
        ("lpMaximumApplicationAddress", wintypes.LPVOID),
        ("dwActiveProcessorMask", wintypes.LPVOID),
        ("dwNumberOfProcessors", wintypes.DWORD),
        ("dwProcessorType", wintypes.DWORD),
        ("dwAllocationGranularity", wintypes.DWORD),
        ("wProcessorLevel", wintypes.WORD),
        ("wProcessorRevision", wintypes.WORD),
    ]

class MemoryReader:
    def __init__(self):
        self.process_handle = None
        self.process_id = None
        self.logger = logging.getLogger('game_cheater')
        self.last_results = None  # 存储上次搜索结果

    def attach_process(self, pid):
        """附加到指定进程"""
        try:
            # 获取进程句柄
            process_handle = win32api.OpenProcess(
                win32con.PROCESS_ALL_ACCESS,
                False,
                pid
            )

            self.process_handle = process_handle
            self.process_id = pid
            return True, "成功"
        except Exception as e:
            self.logger.error(f"附加进程失败: {str(e)}")
            return False, str(e)

    def search_value(self, value, value_type='int32', compare_type='exact', progress_callback=None):
        """搜索内存中的值

        Args:
            value: 要搜索的值
            value_type: 值类型 ('int32', 'float', 'double')
            compare_type: 比较类型 ('exact', 'bigger', 'smaller', 'changed', 'unchanged')
            progress_callback: 进度回调函数，接收当前进度和总数两个参数

        Returns:
            list: 匹配的地址列表
        """
        if not self.process_handle:
            self.logger.error("进程未附加")
            return []

        try:
            results = []
            searched_count = 0

            # 准备搜索值的字节表示
            if value_type == 'int32':
                value_bytes = int(value).to_bytes(4, 'little', signed=True)
            elif value_type == 'float':
                value_bytes = struct.pack('<f', float(value))
            else:  # double
                value_bytes = struct.pack('<d', float(value))

            # 如果是首次搜索
            if not self.last_results or compare_type in ['changed', 'unchanged']:
                # 获取系统信息
                system_info = SYSTEM_INFO()
                kernel32 = ctypes.windll.kernel32
                kernel32.GetSystemInfo(ctypes.byref(system_info))

                # 设置搜索范围
                min_address = system_info.lpMinimumApplicationAddress
                max_address = system_info.lpMaximumApplicationAddress

                # 准备搜索
                current_address = min_address
                memory_regions = []  # 存储可搜索的内存区域

                # 首先收集所有可搜索的内存区域
                while current_address < max_address:
                    mbi = MEMORY_BASIC_INFORMATION()
                    if kernel32.VirtualQueryEx(
                        self.process_handle.handle,
                        ctypes.c_void_p(current_address),
                        ctypes.byref(mbi),
                        ctypes.sizeof(mbi)
                    ):
                        if (mbi.State == win32con.MEM_COMMIT and
                            mbi.Protect & win32con.PAGE_READWRITE and
                            not mbi.Protect & win32con.PAGE_GUARD):
                            memory_regions.append((mbi.BaseAddress, mbi.RegionSize))
                        current_address = mbi.BaseAddress + mbi.RegionSize
                    else:
                        break

                total_count = len(memory_regions)
                # 搜索每个内存区域
                for base_address, region_size in memory_regions:
                    try:
                        data = self.read_memory(base_address, region_size)
                        if data:
                            # 在数据中搜索值
                            pos = 0
                            while True:
                                pos = data.find(value_bytes, pos)
                                if pos == -1:
                                    break
                                results.append(base_address + pos)
                                pos += 1

                    except Exception as e:
                        self.logger.debug(f"读取内存区域失败: {str(e)}")

                    searched_count += 1
                    if progress_callback and total_count > 0:
                        progress = min(100, (searched_count * 100) // total_count)
                        progress_callback(searched_count, total_count)

            # 如果是下一次搜索
            else:
                total_count = len(self.last_results)
                # 在上次结果中搜索
                for addr in self.last_results:
                    try:
                        data = self.read_memory(addr, len(value_bytes))
                        if data:
                            if compare_type == 'exact' and data == value_bytes:
                                results.append(addr)
                            elif compare_type == 'bigger' and int.from_bytes(data, 'little') > int.from_bytes(value_bytes, 'little'):
                                results.append(addr)
                            elif compare_type == 'smaller' and int.from_bytes(data, 'little') < int.from_bytes(value_bytes, 'little'):
                                results.append(addr)

                    except Exception as e:
                        self.logger.debug(f"读取内存失败: {str(e)}")

                    searched_count += 1
                    if progress_callback and total_count > 0:
                        progress = min(100, (searched_count * 100) // total_count)
                        progress_callback(searched_count, total_count)

            self.last_results = results
            return results

        except Exception as e:
            self.logger.error(f"搜索内存失败: {str(e)}")
            self.logger.debug(f"错误详情: {traceback.format_exc()}")
            return []

    def _compare_value(self, buffer, pattern, compare_type):
        """比较内存值"""
        if not buffer or len(buffer) != len(pattern):
            return False

        if compare_type == 'exact':
            return buffer == pattern
        elif compare_type == 'bigger':
            return int.from_bytes(buffer, 'little') > int.from_bytes(pattern, 'little')
        elif compare_type == 'smaller':
            return int.from_bytes(buffer, 'little') < int.from_bytes(pattern, 'little')
        elif compare_type == 'changed':
            return buffer != pattern
        elif compare_type == 'unchanged':
            return buffer == pattern

    def read_memory(self, address, size):
        """读取内存"""
        if not self.process_handle:
            return None

        try:
            buffer = ctypes.create_string_buffer(size)
            bytes_read = ctypes.c_size_t()

            result = ctypes.windll.kernel32.ReadProcessMemory(
                self.process_handle.handle,
                ctypes.c_void_p(address),  # 转换地址为c_void_p
                buffer,
                size,
                ctypes.byref(bytes_read)
            )

            if result and bytes_read.value > 0:
                return buffer.raw[:bytes_read.value]
            return None
        except Exception as e:
            self.logger.debug(f"读取内存失败: 地址={hex(address)}, 错误={str(e)}")
            return None

    def write_memory(self, address, buffer):
        """写入内存"""
        if not self.process_handle:
            return False

        try:
            bytes_written = ctypes.c_size_t()
            result = ctypes.windll.kernel32.WriteProcessMemory(
                self.process_handle.handle,
                ctypes.c_void_p(address),  # 转换地址为c_void_p
                buffer,
                len(buffer),
                ctypes.byref(bytes_written)
            )

            success = result != 0 and bytes_written.value == len(buffer)
            if not success:
                self.logger.error(f"写入内存失败: 地址={hex(address)}, 错误码={ctypes.get_last_error()}")
            return success

        except Exception as e:
            self.logger.error(f"写入内存失败: {str(e)}")
            return False

    def __del__(self):
        """清理资源"""
        if self.process_handle:
            self.process_handle.Close()