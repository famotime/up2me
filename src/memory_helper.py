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

def update_memory_table(memory_table, results, memory_reader, status_callback):
    """更新内存表格显示"""
    memory_table.setRowCount(len(results))
    total = len(results)

    try:
        for i, addr in enumerate(results):
            # 更新状态栏显示进度，但不记录到日志
            progress = (i + 1) * 100 // total
            status_callback(f"正在读取内存值... {progress}% ({i + 1}/{total})", log=False)

            # 设置地址
            memory_table.setItem(i, 0, QTableWidgetItem(hex(addr)))

            # 读取不同大小的内存值
            value = memory_reader.read_memory(addr, 4)
            if value:
                # 单字节值
                memory_table.setItem(i, 1, QTableWidgetItem(str(value[0])))

                # 双字节值
                word_val = int.from_bytes(value[:2], 'little')
                memory_table.setItem(i, 2, QTableWidgetItem(str(word_val)))

                # 四字节值（整数和浮点数）
                dword_val = int.from_bytes(value, 'little')
                float_val = struct.unpack('<f', value)[0]
                memory_table.setItem(i, 3, QTableWidgetItem(f"{dword_val} ({float_val:.2f})"))

                # 推测类型
                value_type = guess_value_type(value)
                memory_table.setItem(i, 4, QTableWidgetItem(value_type))

        # 搜索完成后显示结果数量
        status_callback(f"找到 {total} 个结果", log=True)
        return True

    except Exception as e:
        status_callback("更新内存表格时发生错误", log=True)
        return False

def add_to_result_table(result_table, addr, desc, value_type, initial_value, memory_reader, logger, auto_lock=False):
    """添加一行到结果表格"""
    try:
        # 先尝试写入内存
        try:
            # 根据类型转换值并写入内存
            if value_type == 'int':
                value = int(initial_value)
                if value < 0:
                    value = value & 0xFFFFFFFF
                buffer = value.to_bytes(4, 'little')
            elif value_type == 'float':
                value = float(initial_value)
                buffer = struct.pack('<f', value)
            else:  # 字符串
                value = str(initial_value)
                buffer = value.encode('utf-8')

            # 写入内存并验证
            if not memory_reader.write_memory(addr, buffer):
                raise Exception("写入内存失败")

            # 读取回写入的值进行验证
            verify_value = memory_reader.read_memory(addr, len(buffer))
            if verify_value != buffer:
                raise Exception("写入验证失败")

            logger.info(f"成功写入并验证地址 {hex(addr)}: {value}")

        except Exception as e:
            logger.error(f"初始写入失败: {str(e)}")
            # 写入失败时仍然添加到表格，但不设置锁定
            auto_lock = False

        # 添加到结果表格
        row = result_table.rowCount()
        result_table.insertRow(row)

        # 转换数据类型显示
        display_type = {
            'int': '整数',
            'float': '浮点',
            'string': '字符串'
        }.get(value_type, '整数')  # 默认为整数

        items = [
            (0, desc),                # 名称
            (1, hex(addr)),          # 地址
            (2, str(initial_value)), # 当前值
            (3, display_type),       # 类型
            (4, "是" if auto_lock else "否"),  # 锁定状态
            (5, desc)                # 说明
        ]

        # 先创建所有项目，再设置到表格中
        for col, value in items:
            item = QTableWidgetItem(str(value))
            # 让数值列和锁定列可编辑
            if col not in [2, 4]:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            elif col == 4:  # 锁定列特殊处理
                item.setFlags(item.flags() | Qt.ItemIsEditable)
            result_table.setItem(row, col, item)

        return True, auto_lock

    except Exception as e:
        logger.error(f"添加到结果表格失败: {str(e)}")
        return False, False