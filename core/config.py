import os
import sys
from pathlib import Path


class Config:
    """应用配置"""

    # 应用信息
    APP_NAME = "ADB Tool"
    APP_VERSION = "1.0.0"

    # 服务配置
    HOST = "127.0.0.1"
    PORT = 8088
    DEBUG = False

    # 是否为打包环境
    IS_FROZEN = getattr(sys, 'frozen', False)

    # 静态文件目录
    if IS_FROZEN:
        STATIC_DIR = Path(sys._MEIPASS) / "frontend"
    else:
        STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend"

    # 用户数据目录
    if sys.platform == "win32":
        USER_DATA_DIR = Path(
            os.environ.get("APPDATA", os.path.expanduser("~"))) / APP_NAME
    elif sys.platform == "darwin":
        USER_DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        USER_DATA_DIR = Path.home() / ".local" / "share" / APP_NAME

    # 子目录
    SCREENSHOTS_DIR = USER_DATA_DIR / "screenshots"
    EXPORTS_DIR = USER_DATA_DIR / "exports"
    LOGS_DIR = USER_DATA_DIR / "logs"

    PWD = Path(__file__).resolve().parent.parent
    TEMPLATES_DIR = PWD / "templates"
    # ADB 配置
    ADB_PATH = os.environ.get("ADB_PATH", "adb")
    ADB_TIMEOUT = 10

    @classmethod
    def ensure_dirs(cls):
        """确保所有必要目录存在"""
        for dir_path in [cls.USER_DATA_DIR, cls.SCREENSHOTS_DIR,
                         cls.EXPORTS_DIR, cls.LOGS_DIR, cls.TEMPLATES_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
