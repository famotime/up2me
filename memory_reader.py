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
import math
import time
import os
import concurrent.futures
import threading
from PyQt5.QtCore import QThread

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
        self.current_value_type = 'int32'  # 当前搜索的值类型
        self._thread_local = threading.local()  # 线程局部存储
        self._thread_local.is_running = True  # 默认为运行状态
        self.active_tasks = []  # 存储当前活动的任务
        self._tasks_lock = threading.Lock()  # 用于保护active_tasks的锁

    @property
    def is_running(self):
        """获取当前线程的运行状态"""
        if not hasattr(self._thread_local, 'is_running'):
            self._thread_local.is_running = True
        return self._thread_local.is_running

    @is_running.setter
    def is_running(self, value):
        """设置当前线程的运行状态"""
        self._thread_local.is_running = value

    def stop_all_searches(self):
        """停止所有搜索"""
        # 这个方法会被主线程调用，用于停止所有搜索线程
        # 由于每个线程有自己的is_running状态，我们需要通知所有任务停止搜索
        for task in self.active_tasks:
            if hasattr(task, 'stop_search'):
                task.stop_search()

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

    def search_value(self, value, value_type='float', compare_type='exact', last_results=None, progress_callback=None):
        """搜索内存中的值"""
        self.logger.info(f"开始搜索值: {value}, 类型: {value_type}, 比较方式: {compare_type}")

        # 保存原始值类型，避免影响其他任务
        original_value_type = self.current_value_type

        # 设置当前值类型
        self.current_value_type = value_type

        # 记录开始时间
        start_time = time.time()

        # 初始化结果列表
        results = []

        # 设置搜索参数
        self.is_running = True

        try:
            # 转换值类型
            if value_type == 'int32':
                value_num = int(value)
                value_size = 4
                alignment = 4  # 整数通常是4字节对齐
                pattern = struct.pack('<i', value_num)
            elif value_type == 'float':
                value_num = float(value)
                value_size = 4
                alignment = 4  # 浮点数通常是4字节对齐
                pattern = struct.pack('<f', value_num)
            elif value_type == 'double':
                value_num = float(value)
                value_size = 8
                alignment = 8  # 双精度浮点数通常是8字节对齐
                pattern = struct.pack('<d', value_num)
            else:
                raise ValueError(f"不支持的值类型: {value_type}")

            # 记录搜索模式的十六进制表示，便于调试
            hex_pattern = ' '.join([f'{b:02x}' for b in pattern])
            self.logger.debug(f"搜索模式: {hex_pattern} (类型: {value_type})")

            # 辅助函数：比较浮点数
            def compare_float(a, b, epsilon=None):
                # 根据值的大小动态调整精度
                if epsilon is None:
                    if value_type == 'float':
                        # 单精度浮点数使用更宽松的比较
                        epsilon = max(1e-4, abs(b) * 1e-4)
                    else:  # double
                        # 双精度浮点数使用更精确的比较
                        epsilon = max(1e-8, abs(b) * 1e-8)

                # 检查是否为有效浮点数
                if math.isnan(a) or math.isinf(a) or math.isnan(b) or math.isinf(b):
                    return False

                # 对于接近0的值使用绝对比较
                if abs(b) < 1e-6:
                    return abs(a) < 1e-6

                # 对于其他值使用相对比较
                return abs(a - b) < epsilon

            # 添加性能日志
            total_checked = 0
            total_regions = 0
            total_bytes = 0
            last_progress_update = time.time()  # 上次进度更新时间
            progress_update_interval = 0.1  # 进度更新间隔(秒)，避免频繁更新UI导致卡顿

            # 优化的进度回调函数，减少UI更新频率
            def throttled_progress_callback(current, total):
                nonlocal last_progress_update, total_checked
                current_time = time.time()

                # 检查是否被取消
                if not self.is_running:
                    return

                # 确保current不超过total，避免显示超过100%的进度
                if current > total:
                    current = total

                # 计算百分比，避免除零错误
                percentage = (current / total * 100) if total > 0 else 0

                # 控制进度更新频率，避免UI卡顿
                if current_time - last_progress_update >= progress_update_interval or current == total:
                    if progress_callback:
                        # 添加已检查的地址数量信息
                        # 设置log参数为False，确保进度信息只显示在状态栏，不记录到日志
                        progress_callback(f"正在搜索... {current}/{total} ({percentage:.1f}%) - 已检查 {total_checked} 个地址", False)
                    last_progress_update = current_time

                    # 让出CPU时间，减少UI卡顿
                    QThread.yieldCurrentThread()

            # 如果是在指定结果中搜索
            if last_results is not None:
                total_count = len(last_results)
                self.logger.info(f"在 {total_count} 个先前结果中搜索")
                # 批量读取内存以提高效率
                batch_size = 1000  # 每批处理的地址数量
                for i in range(0, total_count, batch_size):
                    batch_addresses = last_results[i:i+batch_size]
                    batch_results = []

                    # 处理每个地址
                    for addr in batch_addresses:
                        try:
                            data = self.read_memory(addr, value_size)
                            total_checked += 1
                            if data and len(data) == value_size:
                                # 根据类型解析内存值
                                try:
                                    if value_type == 'int32':
                                        current_value = int.from_bytes(data, 'little', signed=True)
                                        match = current_value == value_num if compare_type == 'exact' else \
                                               current_value > value_num if compare_type == 'bigger' else \
                                               current_value < value_num if compare_type == 'smaller' else False
                                    else:  # float or double
                                        try:
                                            if value_type == 'float':
                                                current_value = struct.unpack('<f', data)[0]
                                            else:  # double
                                                current_value = struct.unpack('<d', data)[0]

                                            # 检查是否是有效的浮点数
                                            if math.isnan(current_value) or math.isinf(current_value):
                                                continue

                                            # 对于浮点数，使用更宽松的比较
                                            if compare_type == 'exact':
                                                match = compare_float(current_value, value_num)
                                                # 记录一些匹配的值，帮助调试
                                                if match and i < 10:  # 只记录前10个匹配的值
                                                    self.logger.debug(f"浮点数匹配: 内存值={current_value:.10f}, 搜索值={value_num:.10f}, 地址={hex(addr)}")
                                            elif compare_type == 'bigger':
                                                match = current_value > value_num
                                            elif compare_type == 'smaller':
                                                match = current_value < value_num
                                            else:
                                                match = False
                                        except (struct.error, ValueError, OverflowError):
                                            continue

                                    if match:
                                        batch_results.append(addr)
                                except (struct.error, ValueError, OverflowError):
                                    continue
                        except Exception as e:
                            self.logger.debug(f"读取内存失败: {str(e)}")

                    # 添加批次结果
                    results.extend(batch_results)

                    # 更新进度
                    throttled_progress_callback(i + batch_size if i + batch_size < total_count else total_count, total_count)

                    # 检查是否被取消
                    if not self.is_running:
                        self.logger.info("搜索被用户取消")
                        break

                    # 让出CPU时间，避免UI卡顿
                    QThread.yieldCurrentThread()

            # 如果是搜索整个内存
            else:
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
                        # 放宽内存区域筛选条件，包括更多可能包含浮点数的区域
                        if (mbi.State == win32con.MEM_COMMIT and
                            (mbi.Protect & PAGE_READABLE) and  # 使用可读常量
                            not mbi.Protect & win32con.PAGE_GUARD):
                            memory_regions.append((mbi.BaseAddress, mbi.RegionSize))
                        current_address = mbi.BaseAddress + mbi.RegionSize
                    else:
                        break

                total_count = len(memory_regions)
                total_regions = total_count
                self.logger.info(f"找到 {total_count} 个可搜索内存区域")

                region_start_time = time.time()

                # 优化：使用并行处理提高搜索效率
                # 定义区域搜索函数
                def search_region(region_info):
                    base_address, region_size = region_info
                    region_results = []
                    region_checked = 0

                    try:
                        # 读取内存区域
                        data = self.read_memory(base_address, region_size)
                        if not data:
                            return [], 0, 0

                        region_bytes = len(data)

                        # 限制单次处理的数据量，避免处理过大的区域导致性能问题
                        max_process_size = min(region_bytes, 10 * 1024 * 1024)  # 最多处理10MB

                        # 根据数据类型的对齐方式搜索
                        for i in range(0, max_process_size - value_size + 1, alignment):
                            chunk = data[i:i + value_size]
                            region_checked += 1

                            if len(chunk) == value_size:
                                try:
                                    if value_type == 'int32':
                                        current_value = int.from_bytes(chunk, 'little', signed=True)
                                        match = current_value == value_num if compare_type == 'exact' else \
                                               current_value > value_num if compare_type == 'bigger' else \
                                               current_value < value_num if compare_type == 'smaller' else False
                                    else:  # float or double
                                        try:
                                            if value_type == 'float':
                                                current_value = struct.unpack('<f', chunk)[0]
                                            else:  # double
                                                current_value = struct.unpack('<d', chunk)[0]

                                            # 检查是否是有效的浮点数
                                            if math.isnan(current_value) or math.isinf(current_value):
                                                continue

                                            # 对于浮点数，使用更宽松的比较
                                            if compare_type == 'exact':
                                                match = compare_float(current_value, value_num)
                                                # 记录一些匹配的值，帮助调试
                                                if match and i < 10:  # 只记录前10个匹配的值
                                                    self.logger.debug(f"浮点数匹配: 内存值={current_value:.10f}, 搜索值={value_num:.10f}, 地址={hex(base_address + i)}")
                                            elif compare_type == 'bigger':
                                                match = current_value > value_num
                                            elif compare_type == 'smaller':
                                                match = current_value < value_num
                                            else:
                                                match = False
                                        except (struct.error, ValueError, OverflowError):
                                            continue

                                    if match:
                                        region_results.append(base_address + i)
                                except (struct.error, ValueError, OverflowError):
                                    continue

                            # 检查是否被用户取消
                            if not self.is_running:
                                break

                    except Exception as e:
                        self.logger.debug(f"读取内存区域失败: {str(e)}")

                    return region_results, region_checked, region_bytes

                # 使用线程池并行处理内存区域
                max_workers = min(8, os.cpu_count() or 4)  # 最多使用8个线程
                self.logger.info(f"使用 {max_workers} 个线程并行搜索")

                # 优化：分批提交任务，避免一次性创建过多线程导致内存占用过高
                batch_size = 50  # 每批处理的区域数量
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    for batch_start in range(0, len(memory_regions), batch_size):
                        batch_end = min(batch_start + batch_size, len(memory_regions))
                        batch_regions = memory_regions[batch_start:batch_end]

                        # 提交批次任务
                        future_to_region = {executor.submit(search_region, region): region for region in batch_regions}

                        # 处理完成的任务
                        for future in concurrent.futures.as_completed(future_to_region):
                            if not self.is_running:
                                # 如果搜索被取消，取消所有未完成的任务
                                for f in future_to_region:
                                    f.cancel()
                                break

                            region_results, region_checked, region_bytes = future.result()
                            results.extend(region_results)
                            total_checked += region_checked
                            total_bytes += region_bytes

                            # 更新进度
                            processed_regions = batch_start + len(future_to_region)
                            throttled_progress_callback(processed_regions if processed_regions <= total_regions else total_regions, total_regions)

                            # 如果结果太多，提前返回
                            if len(results) >= 100000:
                                self.logger.info(f"搜索结果过多，提前返回前 {len(results)} 个结果")
                                break

                        # 检查是否被取消或结果过多
                        if not self.is_running or len(results) >= 100000:
                            break

                        # 让出CPU时间，避免UI卡顿
                        QThread.yieldCurrentThread()

                region_total_time = time.time() - region_start_time
                if region_total_time > 0:
                    self.logger.info(f"区域处理总计: 区域数={total_regions}, 总字节数={total_bytes/1024/1024:.1f}MB, 总耗时={region_total_time:.3f}秒")

            total_time = time.time() - start_time
            if total_time > 0 and total_checked > 0:
                self.logger.info(f"搜索性能: 类型={value_type}, 检查地址数={total_checked}, 找到结果={len(results)}, 总耗时={total_time:.3f}秒, 速度={total_checked/total_time:.0f}次/秒")

            # 记录搜索性能
            search_time = time.time() - start_time
            self.logger.info(f"搜索完成: 找到 {len(results)} 个结果, 耗时 {search_time:.2f} 秒")
            self.logger.info(f"搜索性能: 检查了 {total_checked} 个地址, 处理了 {total_bytes/1024/1024:.2f} MB 数据")

            # 添加详细日志，记录搜索结果的前几个地址和值，帮助调试
            if len(results) > 0:
                try:
                    sample_size = min(5, len(results))
                    sample_values = []
                    for i in range(sample_size):
                        addr = results[i]
                        if value_type == 'int32':
                            data = self.read_memory(addr, 4)
                            if data:
                                val = int.from_bytes(data, 'little', signed=True)
                                sample_values.append(f"{hex(addr)}={val}")
                        elif value_type == 'float':
                            data = self.read_memory(addr, 4)
                            if data:
                                val = struct.unpack('<f', data)[0]
                                sample_values.append(f"{hex(addr)}={val:.6f}")
                        elif value_type == 'double':
                            data = self.read_memory(addr, 8)
                            if data:
                                val = struct.unpack('<d', data)[0]
                                sample_values.append(f"{hex(addr)}={val:.6f}")

                    self.logger.info(f"搜索结果样本: {', '.join(sample_values)}")
                except Exception as e:
                    self.logger.error(f"记录搜索结果样本时出错: {str(e)}")

            return results
        except Exception as e:
            self.logger.error(f"搜索值时出错: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return []
        finally:
            # 恢复原始值类型，避免影响其他任务
            self.current_value_type = original_value_type
            self.is_running = False

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

        # 对于过大的内存区域，分块读取以提高稳定性
        max_chunk_size = 4 * 1024 * 1024  # 增加到4MB，提高读取效率

        if size <= max_chunk_size:
            # 对于小块内存，直接读取
            return self._read_memory_chunk(address, size)
        else:
            # 对于大块内存，分块读取
            result = bytearray()
            for offset in range(0, size, max_chunk_size):
                chunk_size = min(max_chunk_size, size - offset)
                chunk = self._read_memory_chunk(address + offset, chunk_size)
                if chunk:
                    result.extend(chunk)
                else:
                    # 如果读取失败，返回已读取的部分
                    return bytes(result) if result else None
            return bytes(result)

    def _read_memory_chunk(self, address, size):
        """读取一块内存"""
        try:
            # 优化：使用缓存减少重复读取
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
            # 减少日志输出频率，避免日志过多影响性能
            if size > 1024:  # 只记录大于1KB的读取失败
                self.logger.debug(f"读取内存失败: 地址={hex(address)}, 大小={size}, 错误={str(e)}")
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

    def read_value(self, address):
        """读取指定地址的值，根据当前设置的值类型返回对应类型的值"""
        if not self.process_handle:
            self.logger.error("读取值失败：未附加到进程")
            return None

        try:
            # 验证地址是否有效
            if not isinstance(address, int) or address <= 0:
                self.logger.error(f"读取值失败：无效的地址 {address}")
                return None

            # 验证值类型是否有效
            valid_types = ['int32', 'float', 'double']
            if self.current_value_type not in valid_types:
                self.logger.error(f"读取值失败：不支持的值类型 {self.current_value_type}，支持的类型: {', '.join(valid_types)}")
                return None

            # 根据值类型确定读取大小
            if self.current_value_type == 'int32':
                size = 4
            elif self.current_value_type == 'float':
                size = 4
            elif self.current_value_type == 'double':
                size = 8
            else:
                # 这里是冗余检查，前面已经验证过类型了
                self.logger.error(f"不支持的值类型: {self.current_value_type}")
                return None

            # self.logger.debug(f"尝试读取地址 {hex(address)} 的值，类型: {self.current_value_type}, 大小: {size}")

            # 读取内存
            try:
                data = self.read_memory(address, size)
                if not data:
                    self.logger.debug(f"读取地址 {hex(address)} 的值失败: 无法读取内存")
                    return None
                if len(data) < size:
                    self.logger.debug(f"读取地址 {hex(address)} 的值失败: 数据不完整，预期{size}字节，实际{len(data)}字节")
                    return None
            except Exception as e:
                self.logger.error(f"读取内存时出错: {str(e)}")
                import traceback
                self.logger.debug(traceback.format_exc())
                return None

            # 根据值类型解析数据
            try:
                if self.current_value_type == 'int32':
                    try:
                        value = int.from_bytes(data, 'little', signed=True)
                        # self.logger.debug(f"成功读取整数值: {value}")
                        return value
                    except Exception as e:
                        self.logger.error(f"解析整数值失败: {str(e)}, 数据: {data.hex()}")
                        return None
                elif self.current_value_type == 'float':
                    try:
                        value = struct.unpack('<f', data)[0]
                        # 检查是否为有效的浮点数
                        if math.isnan(value) or math.isinf(value):
                            self.logger.debug(f"读取地址 {hex(address)} 的浮点数值无效: {value}")
                            return None
                        # self.logger.debug(f"成功读取浮点数值: {value}")
                        return value
                    except struct.error as e:
                        self.logger.error(f"解析浮点数值失败: {str(e)}, 数据: {data.hex()}")
                        return None
                elif self.current_value_type == 'double':
                    try:
                        value = struct.unpack('<d', data)[0]
                        # 检查是否为有效的浮点数
                        if math.isnan(value) or math.isinf(value):
                            self.logger.debug(f"读取地址 {hex(address)} 的双精度浮点数值无效: {value}")
                            return None
                        # self.logger.debug(f"成功读取双精度浮点数值: {value}")
                        return value
                    except struct.error as e:
                        self.logger.error(f"解析双精度浮点数值失败: {str(e)}, 数据: {data.hex()}")
                        return None
            except Exception as e:
                self.logger.error(f"解析地址 {hex(address)} 的值失败: {str(e)}, 值类型: {self.current_value_type}")
                import traceback
                self.logger.debug(traceback.format_exc())
                return None
        except Exception as e:
            self.logger.error(f"读取地址 {hex(address)} 的值时发生异常: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None

    def __del__(self):
        """清理资源"""
        if self.process_handle:
            self.process_handle.Close()

    def register_task(self, task):
        """注册一个搜索任务"""
        with self._tasks_lock:
            if task not in self.active_tasks:
                self.active_tasks.append(task)
                self.logger.debug(f"注册搜索任务: {task.name}")

    def unregister_task(self, task):
        """注销一个搜索任务"""
        with self._tasks_lock:
            if task in self.active_tasks:
                self.active_tasks.remove(task)
                self.logger.debug(f"注销搜索任务: {task.name}")