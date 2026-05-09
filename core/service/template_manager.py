from core.config import Config
from pathlib import Path

class TemplateManager:

    templatesDir = Config.TEMPLATES_DIR
    jsonFile = Config.TEMPLATES_DIR / "templates.json"
    json = {
        "images": [],
        "rois" :[],
    }

    def __init__(self):
        pass

    def load(self):
        def ensure_file_exists(file_path: str):
            """
            跨平台确保文件存在：如果文件或其所在的目录不存在，则自动创建。
            :param file_path: 文件路径字符串
            """
            # 1. 将字符串转换为跨平台 Path 对象
            path = Path(file_path)

            # 2. 确保父级目录存在
            # parents=True: 递归创建缺失的父目录 (类似 mkdir -p)
            # exist_ok=True: 如果目录已存在，不会抛出异常
            path.parent.mkdir(parents=True, exist_ok=True)

            # 3. 确保文件存在
            # exist_ok=True: 如果文件已存在，不会覆盖或报错
            path.touch(exist_ok=True)

        def get_png_files(directory_path: str):
            """
            获取指定目录下所有 .png 和 .PNG 的文件名称列表
            :param directory_path: 目录路径
            :return: 文件名列表, 例如 ['image1.png', 'screenshot.PNG']
            """
            path = Path(directory_path)

            # 如果路径不存在或不是目录，直接返回空列表
            if not path.is_dir():
                return []

            # 使用列表推导式过滤文件
            # .suffix 获取后缀（带点），.lower() 确保同时匹配 .png 和 .PNG
            # .name 获取文件全称（含后缀）
            png_files = [f.name for f in path.iterdir() if
                         f.is_file() and f.suffix.lower() == '.png']

            return png_files
        ensure_file_exists(self.jsonFile)

        pass

    def save(self):
        pass

    def delete(self):
        pass
