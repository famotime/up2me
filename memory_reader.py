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

    def search_value(self, value, value_type='int32', compare_type='exact'):
        """搜索内存值"""
        if not self.process_handle:
            return []

        try:
            results = []
            total_regions = 0
            current_region = 0

            # 先统计需要搜索的内存区域数量
            system_info = SYSTEM_INFO()
            ctypes.windll.kernel32.GetSystemInfo(ctypes.byref(system_info))
            min_address = system_info.lpMinimumApplicationAddress
            max_address = system_info.lpMaximumApplicationAddress

            # 将地址转换为整数
            current_address = ctypes.cast(min_address, ctypes.c_void_p).value
            max_address_int = ctypes.cast(max_address, ctypes.c_void_p).value

            mbi = MEMORY_BASIC_INFORMATION()

            # 添加调试日志
            self.logger.debug(f"开始搜索内存: 地址范围 {hex(current_address)} - {hex(max_address_int)}")

            # 第一次遍历统计可搜索的内存区域数量
            while current_address < max_address_int:
                if not ctypes.windll.kernel32.VirtualQueryEx(
                    self.process_handle.handle,
                    ctypes.c_void_p(current_address),  # 转换为c_void_p
                    ctypes.byref(mbi),
                    ctypes.sizeof(mbi)
                ):
                    break

                if (mbi.Protect & PAGE_READABLE and
                    mbi.State == win32con.MEM_COMMIT and
                    mbi.RegionSize < 100 * 1024 * 1024):  # 跳过超大内存区域
                    total_regions += 1

                current_address += mbi.RegionSize

            # 确定搜索的字节模式
            if value_type == 'int32':
                pattern = value.to_bytes(4, 'little')
            elif value_type == 'float':
                pattern = struct.pack('<f', float(value))
            elif value_type == 'double':
                pattern = struct.pack('<d', float(value))

            # 如果是第二次搜索，只搜索上次结果
            search_addresses = self.last_results if self.last_results else None

            # 重置地址开始搜索
            current_address = ctypes.cast(min_address, ctypes.c_void_p).value

            # 第二次遍历执行实际搜索
            while current_address < max_address_int:
                if not ctypes.windll.kernel32.VirtualQueryEx(
                    self.process_handle.handle,
                    ctypes.c_void_p(current_address),  # 转换为c_void_p
                    ctypes.byref(mbi),
                    ctypes.sizeof(mbi)
                ):
                    break

                try:
                    # 检查内存区域是否可读且已提交，并跳过超大区域
                    if (mbi.Protect & PAGE_READABLE and
                        mbi.State == win32con.MEM_COMMIT and
                        mbi.RegionSize < 100 * 1024 * 1024):

                        current_region += 1
                        progress = (current_region * 100) // total_regions
                        self.logger.info(f"搜索进度: {progress}% ({current_region}/{total_regions})")

                        # 如果有上次结果，只检查这些地址
                        if search_addresses:
                            addrs_in_range = [
                                addr for addr in search_addresses
                                if current_address <= addr < current_address + mbi.RegionSize
                            ]
                            if addrs_in_range:
                                for addr in addrs_in_range:
                                    value = self.read_memory(addr, len(pattern))
                                    if value and self._compare_value(value, pattern, compare_type):
                                        results.append(addr)
                        else:
                            # 首次搜索时使用更大的块大小
                            chunk_size = 4 * 1024 * 1024  # 4MB
                            for offset in range(0, mbi.RegionSize, chunk_size):
                                size = min(chunk_size, mbi.RegionSize - offset)
                                buffer = self.read_memory(current_address + offset, size)
                                if buffer:
                                    # 使用更高效的搜索方法
                                    pos = 0
                                    while True:
                                        pos = buffer.find(pattern, pos)
                                        if pos == -1:
                                            break
                                        results.append(current_address + offset + pos)
                                        pos += 1

                except Exception as e:
                    self.logger.debug(f"搜索内存区域失败: {str(e)}")

                current_address += mbi.RegionSize

            self.last_results = results
            self.logger.info(f"搜索完成: 找到 {len(results)} 个匹配地址")
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