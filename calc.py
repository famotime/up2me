"""
从2个16进制数据，获得差值，然后从最大的数持续减去差值10次，打印所有数字
"""

def hex_subtraction(hex_num1, hex_num2):
    # 将16进制字符串转换为整数
    num1 = int(hex_num1, 16)
    num2 = int(hex_num2, 16)

    # 计算差值
    diff = abs(num1 - num2)
    # 获取较大的数
    start_num = max(num1, num2)

    # 执行10次减法运算
    for i in range(10):
        # 打印当前值（以16进制和10进制形式）
        print(f"第{i+1}次: {hex(start_num).upper()[2:]}")
        # 执行减法
        start_num -= diff

    return start_num

# 测试代码
if __name__ == "__main__":
    hex1 = "121D81009E8"    # 第一个16进制数
    hex2 = "121D81004A8"    # 第二个16进制数

    print(f"第一个16进制数: {hex1}")
    print(f"第二个16进制数: {hex2}")
    print(f"差值: {abs(int(hex1, 16) - int(hex2, 16))}")
    print("-" * 40)

    final_value = hex_subtraction(hex1, hex2)
    print("-" * 40)
    print(f"最终结果: {hex(final_value).upper()[2:]}")