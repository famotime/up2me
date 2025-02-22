from PyQt5.QtGui import QIcon, QImage, QPixmap
import win32gui
import win32ui
import win32con
import win32api
from win32com.shell import shell, shellcon

def get_file_icon(exe_path, logger):
    """获取文件图标

    Args:
        exe_path (str): 可执行文件路径
        logger: 日志记录器

    Returns:
        QIcon: 文件图标，如果获取失败则返回空图标
    """
    try:
        # 使用SHGetFileInfo获取图标
        flags = (shellcon.SHGFI_ICON |
                shellcon.SHGFI_SMALLICON |
                shellcon.SHGFI_USEFILEATTRIBUTES)

        file_info = shell.SHGetFileInfo(
            str(exe_path),
            win32con.FILE_ATTRIBUTE_NORMAL,
            flags
        )

        if file_info and file_info[0]:
            try:
                # 获取图标句柄
                hicon = file_info[0]

                # 创建DC
                screen_dc = win32gui.GetDC(0)
                dc = win32ui.CreateDCFromHandle(screen_dc)
                memdc = dc.CreateCompatibleDC()

                # 创建位图
                bitmap = win32ui.CreateBitmap()
                bitmap.CreateCompatibleBitmap(dc, 16, 16)
                old_bitmap = memdc.SelectObject(bitmap)

                # 填充白色背景
                memdc.FillSolidRect((0, 0, 16, 16), win32api.RGB(255, 255, 255))

                # 绘制图标
                win32gui.DrawIcon(memdc.GetHandleOutput(), 0, 0, hicon)

                # 获取位图数据
                bmpstr = bitmap.GetBitmapBits(True)

                # 创建QImage
                image = QImage(bmpstr, 16, 16, QImage.Format_RGB32)
                pixmap = QPixmap.fromImage(image)

                # 清理资源
                memdc.SelectObject(old_bitmap)
                bitmap.DeleteObject()
                memdc.DeleteDC()
                dc.DeleteDC()
                win32gui.ReleaseDC(0, screen_dc)
                win32gui.DestroyIcon(hicon)

                if not pixmap.isNull():
                    return QIcon(pixmap)

            except Exception as e:
                logger.debug(f"处理图标失败: {str(e)}")
                try:
                    if hicon:
                        win32gui.DestroyIcon(hicon)
                except:
                    pass

        # 如果上述方法失败，尝试使用默认图标
        try:
            # 获取默认的.exe图标
            flags = (shellcon.SHGFI_ICON |
                    shellcon.SHGFI_SMALLICON |
                    shellcon.SHGFI_USEFILEATTRIBUTES)

            file_info = shell.SHGetFileInfo(
                ".exe",
                win32con.FILE_ATTRIBUTE_NORMAL,
                flags
            )

            if file_info and file_info[0]:
                try:
                    hicon = file_info[0]

                    # 创建DC
                    screen_dc = win32gui.GetDC(0)
                    dc = win32ui.CreateDCFromHandle(screen_dc)
                    memdc = dc.CreateCompatibleDC()

                    # 创建位图
                    bitmap = win32ui.CreateBitmap()
                    bitmap.CreateCompatibleBitmap(dc, 16, 16)
                    old_bitmap = memdc.SelectObject(bitmap)

                    # 填充白色背景
                    memdc.FillSolidRect((0, 0, 16, 16), win32api.RGB(255, 255, 255))

                    # 绘制图标
                    win32gui.DrawIcon(memdc.GetHandleOutput(), 0, 0, hicon)

                    # 获取位图数据
                    bmpstr = bitmap.GetBitmapBits(True)

                    # 创建QImage
                    image = QImage(bmpstr, 16, 16, QImage.Format_RGB32)
                    pixmap = QPixmap.fromImage(image)

                    # 清理资源
                    memdc.SelectObject(old_bitmap)
                    bitmap.DeleteObject()
                    memdc.DeleteDC()
                    dc.DeleteDC()
                    win32gui.ReleaseDC(0, screen_dc)
                    win32gui.DestroyIcon(hicon)

                    if not pixmap.isNull():
                        return QIcon(pixmap)

                except Exception as e:
                    logger.debug(f"处理默认图标失败: {str(e)}")
                    try:
                        if hicon:
                            win32gui.DestroyIcon(hicon)
                    except:
                        pass

        except Exception as e:
            logger.debug(f"获取默认图标失败: {str(e)}")

    except Exception as e:
        logger.debug(f"获取图标完全失败: {str(e)}")

    # 如果所有方法都失败，返回一个空图标
    return QIcon()
