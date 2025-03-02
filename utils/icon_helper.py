from PyQt5.QtGui import QIcon, QImage, QPixmap
from win32com.shell import shell, shellcon
import win32api
import win32gui
import win32con
import win32ui
from pathlib import Path

def get_file_icon(exe_path, logger):
    """获取文件图标

    Args:
        exe_path (str): 可执行文件路径
        logger: 日志记录器

    Returns:
        QIcon: 文件图标，如果获取失败则返回空图标
    """
    # 检查文件路径是否存在
    try:
        if not Path(exe_path).exists():
            logger.debug(f"文件路径无效: {exe_path}")
            return QIcon()  # 使用空图标
    except Exception as e:
        logger.debug(f"检查文件路径时出错: {str(e)}")
        return QIcon()  # 使用空图标

    try:
        # 使用ExtractIconEx直接获取图标
        try:
            large, small = win32gui.ExtractIconEx(str(exe_path), 0)
        except Exception as e:
            logger.debug(f"ExtractIconEx失败: {str(e)}")
            large, small = [], []

        if small:
            try:
                # 使用QPixmap直接从图标句柄创建图标
                hicon = small[0]
                if not hicon:
                    raise Exception("无效的图标句柄")

                try:
                    icon_info = win32gui.GetIconInfo(hicon)
                    bmp = win32ui.CreateBitmapFromHandle(icon_info[4])
                    bmp_info = bmp.GetInfo()
                    bmp_str = bmp.GetBitmapBits(True)

                    # 创建QImage
                    image = QImage(bmp_str, bmp_info['bmWidth'], bmp_info['bmHeight'], QImage.Format_ARGB32)
                    pixmap = QPixmap.fromImage(image)

                    # 清理资源
                    win32gui.DestroyIcon(hicon)

                    if not pixmap.isNull():
                        return QIcon(pixmap)
                except Exception as e:
                    logger.debug(f"处理图标失败: {str(e)}")
            except Exception as e:
                logger.debug(f"处理图标失败: {str(e)}")
                # 清理图标句柄
                try:
                    for icon in small:
                        if icon:
                            win32gui.DestroyIcon(icon)
                    for icon in large:
                        if icon:
                            win32gui.DestroyIcon(icon)
                except Exception as e:
                    logger.debug(f"清理图标句柄失败: {str(e)}")
    except Exception as e:
        logger.debug(f"获取图标失败: {str(e)}")

    # 如果上述方法失败，尝试使用SHGetFileInfo
    try:
        flags = (shellcon.SHGFI_ICON | shellcon.SHGFI_SMALLICON)
        file_info = shell.SHGetFileInfo(str(exe_path), 0, flags)

        if file_info and file_info[0]:
            try:
                # 使用QPixmap直接从图标句柄创建图标
                hicon = file_info[0]
                if not hicon:
                    raise Exception("无效的图标句柄")

                try:
                    icon_info = win32gui.GetIconInfo(hicon)
                    bmp = win32ui.CreateBitmapFromHandle(icon_info[4])
                    bmp_info = bmp.GetInfo()
                    bmp_str = bmp.GetBitmapBits(True)

                    # 创建QImage
                    image = QImage(bmp_str, bmp_info['bmWidth'], bmp_info['bmHeight'], QImage.Format_ARGB32)
                    pixmap = QPixmap.fromImage(image)

                    # 清理资源
                    win32gui.DestroyIcon(hicon)

                    if not pixmap.isNull():
                        return QIcon(pixmap)
                except Exception as e:
                    logger.debug(f"处理SHGetFileInfo图标失败: {str(e)}")
            except Exception as e:
                logger.debug(f"处理SHGetFileInfo图标失败: {str(e)}")
                try:
                    if file_info[0]:
                        win32gui.DestroyIcon(file_info[0])
                except Exception as e:
                    logger.debug(f"清理SHGetFileInfo图标句柄失败: {str(e)}")
    except Exception as e:
        logger.debug(f"获取SHGetFileInfo图标失败: {str(e)}")

    # 如果所有方法都失败，返回一个空图标
    return QIcon()
