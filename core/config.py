import os
import sys
import json
import cv2
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

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

    PWD = Path(__file__).resolve().parent.parent

    cwd = os.getcwd()

    LOGS_DIR = Path(cwd).resolve() / "logs"
    cwd = Path(cwd).resolve().parent
    RESOURCE_DIR = cwd / "resource"
    RESOURCE_TEMPLATES_JSON = RESOURCE_DIR / "templates.json"
    TEMPLATES_DIR = RESOURCE_DIR / "templates"
    # ADB 配置
    ADB_PATH = os.environ.get("ADB_PATH", "adb")
    ADB_TIMEOUT = 10

    @classmethod
    def ensure_dirs(cls):
        """确保所有必要目录存在"""
        for dir_path in [ cls.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)


TEMPLATES_DATA = []

def load_resource_templates():
    """加载 resource/templates.json 中的模板数据"""
    global TEMPLATES_DATA
    try:
        json_file = Config.RESOURCE_TEMPLATES_JSON
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                templates_list = json.load(f)

            # 为每个模板加载对应的图片
            for template in templates_list:
                images_id = template.get('images_id')
                if images_id is not None:
                    img_path = Config.TEMPLATES_DIR / f"{images_id}.png"
                    if img_path.exists():
                        img = cv2.imread(str(img_path))
                        if img is not None:
                            template['img'] = img
                        else:
                            logger.warning(f"无法加载图片: {img_path}")
                            template['img'] = None
                    else:
                        logger.warning(f"图片文件不存在: {img_path}")
                        template['img'] = None
                else:
                    template['img'] = None

            TEMPLATES_DATA = templates_list
            logger.info(f"成功加载 {len(TEMPLATES_DATA)} 个模板")
        else:
            logger.warning(f"模板文件不存在: {json_file}")
            TEMPLATES_DATA = []
    except Exception as e:
        logger.error(f"加载模板数据失败: {e}")
        TEMPLATES_DATA = []

if __name__ == '__main__':
    load_resource_templates()
