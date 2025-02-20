from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import datetime

def setup_logger(name='game_cheater'):
    """
    设置日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建logs目录
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # 生成日志文件名，包含日期
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = log_dir / f'{name}_{current_date}.log'

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 创建文件处理器
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger