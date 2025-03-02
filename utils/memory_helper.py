import struct
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt
import logging

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
                    first_values=None, prev_values=None, current_values=None, task_value_type=None):
    """更新内存表格"""
    if not table or not memory_reader or not addresses:
        logger = logging.getLogger('game_cheater')
        logger.error("更新内存表格失败: 无效的参数")
        return False

    # 获取logger
    logger = logging.getLogger('game_cheater')
    logger.debug(f"开始更新内存表格: 地址数量={len(addresses)}, 值类型={task_value_type}")

    # 限制显示的最大地址数量，避免UI卡顿
    max_display = 1000
    if len(addresses) > max_display:
        if status_callback:
            status_callback(f"找到 {len(addresses)} 个匹配地址，仅显示前 {max_display} 个")
        addresses = addresses[:max_display]

    # 清空表格并重新设置行数，确保只显示当前搜索结果
    table.setRowCount(0)
    table.setRowCount(len(addresses))

    # 使用任务的value_type，如果没有提供则使用memory_reader的
    value_type = task_value_type if task_value_type else memory_reader.current_value_type

    # 如果value_type仍然为None，使用默认值
    if not value_type:
        value_type = 'int32'
        if status_callback:
            status_callback("警告：未指定值类型，使用默认值 int32", True)
        logger.warning(f"更新内存表格时未指定值类型，使用默认值 int32")

    # 记录当前使用的值类型
    logger.debug(f"更新内存表格使用值类型: {value_type}")

    # 保存原始值类型，避免影响其他任务
    original_value_type = memory_reader.current_value_type

    # 临时设置memory_reader的值类型为当前任务的值类型
    memory_reader.current_value_type = value_type

    def format_value(value, value_type):
        """格式化值的显示"""
        if value is None:
            return "-"
        try:
            if value_type == 'int32':
                return str(int(value))  # 整数显示
            elif value_type == 'float' or value_type == 'double':
                # 统一浮点数和双精度的格式化
                if isinstance(value, bytes):
                    # 如果是字节数据，使用struct.unpack解析
                    if value_type == 'float' and len(value) >= 4:
                        return f"{struct.unpack('<f', value[:4])[0]:.6f}"
                    elif value_type == 'double' and len(value) >= 8:
                        return f"{struct.unpack('<d', value[:8])[0]:.6f}"
                    else:
                        return "-数据长度错误-"
                else:
                    # 如果已经是数值，直接格式化
                    return f"{float(value):.6f}"
        except (ValueError, TypeError, struct.error) as e:
            logger.debug(f"格式化值失败: {str(e)}, 值类型: {value_type}, 值: {value}, 类型: {type(value)}")
            return f"-错误-"

    # 优化：批量处理，减少UI更新次数
    table.setUpdatesEnabled(False)  # 暂时禁用表格更新

    try:
        # 批量设置表格项
        for row, addr in enumerate(addresses):
            try:
                # 设置地址
                addr_item = QTableWidgetItem(hex(addr))
                table.setItem(row, 0, addr_item)

                # 如果没有提供当前值，则从内存中读取
                current_value = None
                if current_values and addr in current_values:
                    current_value = current_values.get(addr)
                else:
                    # 从内存中读取当前值
                    try:
                        current_value = memory_reader.read_value(addr)
                        # 如果读取成功，更新current_values字典
                        if current_value is not None and current_values is not None:
                            current_values[addr] = current_value
                    except Exception as e:
                        logger.debug(f"读取地址 {hex(addr)} 的当前值失败: {str(e)}")

                # 设置当前值
                current_item = QTableWidgetItem(format_value(current_value, value_type))
                table.setItem(row, 1, current_item)

                # 设置先前值
                prev_value = prev_values.get(addr) if prev_values else None
                prev_item = QTableWidgetItem(format_value(prev_value, value_type))
                table.setItem(row, 2, prev_item)

                # 设置首次值
                first_value = first_values.get(addr) if first_values else None
                if first_value is None and current_value is not None and first_values is not None:
                    # 如果是首次搜索且没有首次值但有当前值，使用当前值作为首次值
                    first_value = current_value
                    first_values[addr] = current_value
                first_item = QTableWidgetItem(format_value(first_value, value_type))
                table.setItem(row, 3, first_item)

                # 设置类型
                type_text = ""
                type_mapping = {
                    'int32': '整数',
                    'float': '浮点',
                    'double': '双精度'
                }

                type_text = type_mapping.get(value_type, value_type)

                if logger:
                    logger.debug(f"设置类型文本: {type_text} (原始类型: {value_type})")

                type_item = QTableWidgetItem(type_text)
                table.setItem(row, 4, type_item)

                # 设置颜色标记值的变化
                if prev_value is not None and current_value is not None:
                    try:
                        if value_type == 'int32':
                            has_changed = current_value != prev_value
                        else:
                            # 对于浮点数和双精度，使用更精确的比较
                            has_changed = abs(float(current_value) - float(prev_value)) > 1e-6
                        if has_changed:
                            current_item.setBackground(Qt.yellow)
                    except Exception as e:
                        logger.debug(f"比较值变化失败: {str(e)}")

            except Exception as e:
                logger.error(f"处理地址 {hex(addr)} 时出错: {str(e)}")
                if status_callback:
                    status_callback(f"处理地址 {hex(addr)} 时出错: {str(e)}")
    except Exception as e:
        logger.error(f"更新内存表格失败: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
    finally:
        table.setUpdatesEnabled(True)  # 恢复表格更新
        # 恢复原始值类型，避免影响其他任务
        memory_reader.current_value_type = original_value_type

    if status_callback:
        status_callback(f"找到 {len(addresses)} 个匹配地址")

    logger.debug(f"内存表格更新完成: {len(addresses)} 个地址")
    return True

def add_to_result_table(result_table, address=None, memory_reader=None, value_type=None,
                     desc=None, initial_value=None, auto_lock=False, logger=None):
    """添加地址到结果表格"""
    try:
        if logger:
            logger.debug(f"开始添加地址到结果表格: 地址={hex(address) if address else 'None'}, 类型={value_type}, 描述={desc}, 自动锁定={auto_lock}")

        if not result_table or not memory_reader:
            if logger:
                logger.error("添加地址到结果表格失败: 无效的参数")
            return False, False, None

        if not memory_reader.process_handle:
            if logger:
                logger.error("添加地址到结果表格失败: 未附加到进程")
            return False, False, None

        if address is None:
            if logger:
                logger.error("添加地址到结果表格失败: 未提供地址")
            return False, False, None

        # 验证地址是否有效
        if not isinstance(address, int) or address <= 0:
            if logger:
                logger.error(f"添加地址到结果表格失败: 无效的地址 {address}")
            return False, False, None

        # 保存原始值类型，避免影响其他任务
        original_value_type = memory_reader.current_value_type
        if logger:
            logger.debug(f"保存原始值类型: {original_value_type}")

        try:
            # 如果未指定值类型，使用当前值类型
            if not value_type:
                value_type = memory_reader.current_value_type
                if logger:
                    logger.debug(f"使用当前值类型: {value_type}")

            # 验证值类型是否有效
            if value_type not in ['int32', 'float', 'double']:
                if logger:
                    logger.error(f"添加地址到结果表格失败: 不支持的值类型 {value_type}")
                return False, False, None

            # 读取当前值
            memory_reader.current_value_type = value_type
            if logger:
                logger.debug(f"设置当前值类型为: {value_type}")

            try:
                current_value = memory_reader.read_value(address)
                if logger:
                    logger.debug(f"读取当前值: 地址={hex(address)}, 类型={value_type}, 值={current_value}")
            except Exception as e:
                if logger:
                    logger.error(f"读取当前值失败: 地址={hex(address)}, 类型={value_type}, 错误={str(e)}")
                    import traceback
                    logger.debug(traceback.format_exc())
                current_value = None

            # 设置初始值和上一次值
            if initial_value is not None:
                try:
                    # 尝试转换initial_value为对应类型的值
                    if value_type == 'int32':
                        initial_value = int(initial_value)
                    elif value_type == 'float' or value_type == 'double':
                        initial_value = float(initial_value)
                    if logger:
                        logger.debug(f"转换初始值: {initial_value}, 类型={value_type}")
                except (ValueError, TypeError) as e:
                    if logger:
                        logger.error(f"转换初始值失败: {str(e)}")
                        import traceback
                        logger.debug(traceback.format_exc())
                    initial_value = current_value
            else:
                initial_value = current_value

            previous_value = current_value

            # 获取当前行数
            row_count = result_table.rowCount()
            result_table.setRowCount(row_count + 1)
            if logger:
                logger.debug(f"设置表格行数: {row_count + 1}")

            try:
                # 设置锁定状态
                try:
                    lock_item = QTableWidgetItem("是" if auto_lock else "否")
                    result_table.setItem(row_count, 4, lock_item)
                    if logger:
                        logger.debug(f"设置锁定状态: {auto_lock}")
                except Exception as e:
                    if logger:
                        logger.error(f"设置锁定状态失败: {str(e)}")
                        import traceback
                        logger.debug(traceback.format_exc())
                    # 继续执行，不要因为一个表格项设置失败而中断整个过程

                # 设置地址
                try:
                    addr_item = QTableWidgetItem(hex(address))
                    result_table.setItem(row_count, 1, addr_item)
                    if logger:
                        logger.debug(f"设置地址: {hex(address)}")
                except Exception as e:
                    if logger:
                        logger.error(f"设置地址失败: {str(e)}")
                        import traceback
                        logger.debug(traceback.format_exc())
                    # 继续执行

                # 设置描述
                try:
                    desc_item = QTableWidgetItem(desc if desc else "")
                    result_table.setItem(row_count, 0, desc_item)
                    if logger:
                        logger.debug(f"设置描述: {desc}")
                except Exception as e:
                    if logger:
                        logger.error(f"设置描述失败: {str(e)}")
                        import traceback
                        logger.debug(traceback.format_exc())
                    # 继续执行

                # 设置类型
                try:
                    type_text = ""
                    type_mapping = {
                        'int32': '整数',
                        'float': '浮点',
                        'double': '双精度'
                    }

                    type_text = type_mapping.get(value_type, value_type)

                    if logger:
                        logger.debug(f"设置类型文本: {type_text} (原始类型: {value_type})")

                    type_item = QTableWidgetItem(type_text)
                    result_table.setItem(row_count, 3, type_item)
                except Exception as e:
                    if logger:
                        logger.error(f"设置类型失败: {str(e)}")
                        import traceback
                        logger.debug(traceback.format_exc())
                    # 继续执行

                # 设置当前值
                try:
                    if current_value is not None:
                        if value_type == 'double' or value_type == 'float':
                            # 格式化浮点数，避免科学计数法
                            value_item = QTableWidgetItem(f"{current_value:.10f}")
                        else:
                            value_item = QTableWidgetItem(str(current_value))
                    else:
                        value_item = QTableWidgetItem("读取失败")

                    result_table.setItem(row_count, 2, value_item)
                    if logger:
                        logger.debug(f"设置当前值: {value_item.text()}")
                except (ValueError, struct.error) as e:
                    if logger:
                        logger.error(f"处理当前值失败: {str(e)}")
                        import traceback
                        logger.debug(traceback.format_exc())
                    try:
                        value_item = QTableWidgetItem("格式错误")
                        result_table.setItem(row_count, 2, value_item)
                    except Exception as inner_e:
                        if logger:
                            logger.error(f"设置错误值失败: {str(inner_e)}")

                if logger:
                    logger.debug(f"成功添加地址到结果表格: {hex(address)}, 类型={value_type}, 值={current_value}")

                return True, auto_lock, initial_value
            except Exception as e:
                if logger:
                    logger.error(f"设置表格项时出错: {str(e)}")
                    import traceback
                    logger.debug(traceback.format_exc())
                # 尝试删除可能部分添加的行
                try:
                    if row_count < result_table.rowCount():
                        result_table.removeRow(row_count)
                        if logger:
                            logger.debug(f"已删除部分添加的行: {row_count}")
                except Exception as remove_e:
                    if logger:
                        logger.error(f"删除部分添加的行失败: {str(remove_e)}")
                return False, False, None
        except Exception as e:
            if logger:
                logger.error(f"添加地址到结果表格时出错: {str(e)}")
                import traceback
                logger.debug(traceback.format_exc())
            return False, False, None
        finally:
            # 恢复原始值类型，避免影响其他任务
            memory_reader.current_value_type = original_value_type
            if logger:
                logger.debug(f"恢复原始值类型: {original_value_type}")
    except Exception as e:
        if logger:
            logger.error(f"添加地址到结果表格函数执行失败: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
        return False, False, None