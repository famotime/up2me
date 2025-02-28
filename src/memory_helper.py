import struct
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt

def guess_value_type(value):
    """推测内存值类型"""
    try:
        int_val = int.from_bytes(value, 'little')
        float_val = struct.unpack('<f', value)[0]

        # 检查是否可能是浮点数
        if abs(float_val) > 0.01 and abs(float_val) < 1000000:
            return "浮点数"
        # 检查是否在合理的整数范围内
        elif 0 <= int_val <= 1000000:
            return "整数"
        else:
            return "未知"
    except:
        return "未知"

def update_memory_table(table, addresses, memory_reader, status_callback=None,
                    first_values=None, prev_values=None, current_values=None):
    """更新内存表格"""
    table.setRowCount(len(addresses))
    value_type = memory_reader.current_value_type

    def format_value(value, value_type):
        """格式化值的显示"""
        if value is None:
            return "-"
        try:
            if value_type == 'int32':
                return str(int(value))  # 整数显示
            elif value_type == 'float':
                return f"{float(value)}"  # 浮点数显示
            else:  # double
                return f"{float(value)}"  # 双精度显示
        except (ValueError, TypeError):
            return "-"

    for row, addr in enumerate(addresses):
        try:
            # 设置地址
            addr_item = QTableWidgetItem(hex(addr))
            table.setItem(row, 0, addr_item)

            # 设置当前值
            current_value = current_values.get(addr)
            current_item = QTableWidgetItem(format_value(current_value, value_type))
            table.setItem(row, 1, current_item)

            # 设置先前值
            prev_value = prev_values.get(addr) if prev_values else None
            prev_item = QTableWidgetItem(format_value(prev_value, value_type))
            table.setItem(row, 2, prev_item)

            # 设置首次值
            first_value = first_values.get(addr) if first_values else None
            first_item = QTableWidgetItem(format_value(first_value, value_type))
            table.setItem(row, 3, first_item)

            # 设置类型
            type_text = {
                'int32': '整数',
                'float': '浮点',
                'double': '双精度'
            }.get(value_type, '未知')
            type_item = QTableWidgetItem(type_text)
            table.setItem(row, 4, type_item)

            # 设置颜色标记值的变化
            if prev_value is not None and current_value is not None:
                if value_type == 'int32':
                    has_changed = current_value != prev_value
                else:
                    has_changed = abs(current_value - prev_value) > 1e-6
                if has_changed:
                    current_item.setBackground(Qt.yellow)

        except Exception as e:
            if status_callback:
                status_callback(f"处理地址 {hex(addr)} 时出错: {str(e)}")

    if status_callback:
        status_callback(f"找到 {len(addresses)} 个匹配地址")

def add_to_result_table(table, addr, desc, value_type, initial_value, memory_reader, logger, auto_lock=False):
    """添加地址到结果表格"""
    try:
        row = table.rowCount()
        table.setRowCount(row + 1)

        # 设置描述
        desc_item = QTableWidgetItem(desc)
        table.setItem(row, 0, desc_item)

        # 设置地址
        addr_item = QTableWidgetItem(hex(addr))
        table.setItem(row, 1, addr_item)

        # 处理初始值并写入内存
        try:
            if value_type == 'int':
                value = int(initial_value)
                buffer = value.to_bytes(4, 'little', signed=True)
                value_str = str(value)
                value_type_str = '整数'
                size = 4
            elif value_type == 'float':
                value = float(initial_value)
                buffer = struct.pack('<f', value)
                value_str = f"{value:.6f}"
                value_type_str = '浮点'
                size = 4
            elif value_type == 'double':
                value = float(initial_value)
                buffer = struct.pack('<d', value)
                value_str = f"{value:.6f}"
                value_type_str = '双精度'
                size = 8
            else:
                logger.error(f"不支持的值类型: {value_type}")
                return False, False, None

            # 写入内存
            if memory_reader.write_memory(addr, buffer):
                # 验证写入
                verify_data = memory_reader.read_memory(addr, size)
                if verify_data != buffer:
                    logger.error("写入内存验证失败")
                    return False, False, None
            else:
                logger.error("写入内存失败")
                return False, False, None

            # 如果要锁定，返回实际的值而不是字符串
            lock_value = value if auto_lock else None

        except (ValueError, struct.error) as e:
            logger.error(f"处理初始值失败: {str(e)}")
            return False, False, None

        # 设置值
        value_item = QTableWidgetItem(value_str)
        value_item.setData(Qt.UserRole, value)  # 存储实际值用于锁定
        table.setItem(row, 2, value_item)

        # 设置类型
        type_item = QTableWidgetItem(value_type_str)
        type_item.setData(Qt.UserRole, value_type)  # 存储原始类型
        table.setItem(row, 3, type_item)

        # 设置锁定状态
        lock_item = QTableWidgetItem("是" if auto_lock else "否")
        table.setItem(row, 4, lock_item)

        return True, auto_lock, lock_value

    except Exception as e:
        logger.error(f"添加地址到结果表格失败: {str(e)}")
        return False, False, None