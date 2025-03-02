"""
从剪贴板读取图片，识别游戏数值，输出json字符串
"""
import base64
import os
from pathlib import Path
# 通过 pip install volcengine-python-sdk[ark] 安装方舟SDK
from volcenginesdkarkruntime import Ark
from PIL import ImageGrab


def get_completion_from_messages(endpoint_id, prompt):
    """
    调用大模型API处理剪贴板中的图片

    Args:
        endpoint_id (str): 模型端点ID
        prompt (str): 提示词
    """
    # 初始化Client对象
    client = Ark(
        api_key=os.environ.get("ARK_API_KEY"),
    )

    # 从剪贴板获取图片
    image = ImageGrab.grabclipboard()
    if image is None:
        raise ValueError("剪贴板中没有图片")

    # 将PIL Image转换为bytes
    import io
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    base64_image = base64.b64encode(img_byte_arr).decode('utf-8')

    response = client.chat.completions.create(
        model=endpoint_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            # 需要注意：传入Base64编码前需要增加前缀 data:image/{图片格式};base64,{Base64编码}：
                            # PNG图片："url":  f"data:image/png;base64,{base64_image}"
                            # JEPG图片："url":  f"data:image/jpeg;base64,{base64_image}"
                            # WEBP图片："url":  f"data:image/webp;base64,{base64_image}"
                            "url": f"data:image/png;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    # endpoint_id = "ep-20250118173521-zkx6c"         # Doubao-vision-lite-32k 视觉大模型
    endpoint_id = "ep-20250118221957-kx6pg"         # Doubao-vision-pro-32k 视觉大模型

    prompt = '请识别这张截图中跟游戏资源和人物属性相关的数值，并输出json字符串，不需要任何解释说明。例：{"金币": 906, "生命": 87, "资源1": 100, "资源2": 200}'

    response = get_completion_from_messages(endpoint_id, prompt)
    print("\n提取的文本内容：")
    print(response)

