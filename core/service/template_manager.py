from core.config import Config
from pathlib import Path
from typing import List, Any,Union

from core.service.template_matcher import TemplateMatcher
from core.tool.filesystem import ensure_dir
import json
import cv2
import numpy as np
import uuid

class TemplateImg(TemplateMatcher):
    """
    模板图片
    可以使用 find_match find_match_all
    """
    def __init__(self, path: Union[str, bytes]):
        super().__init__()

        self.roi = None

        if isinstance(path, bytes):
            self.img = cv2.imdecode(np.frombuffer(path, np.uint8), cv2.IMREAD_COLOR)
            pass

        elif  isinstance(path, str):
            self.img = cv2.imread(path)
            pass
    def set_roi(self, roi):
        self.roi = roi

class TemplateManager:

    rootDir = Config.TEMPLATES_DIR
    jsonFile = rootDir / "templates.json"
    ImgDir = rootDir / "images"
    templatesDir = rootDir / "templates"
    jsonData = {
        "images": {},
        "rois" :{},
    }

    def __init__(self):
        self.jsonData = self._load_json()
        pass

    def save(self, id: str,name: str, roi: List[Any], img_data: np.ndarray):
        # 保存json
        # 保存到目录为png图片
        if id == "" :
            template_id = str(uuid.uuid4())
        else:
            template_id = id

        saveRoi = {
            "id": template_id,
            "name": name,
            "roi": roi
        }

        try:
            # 确保目录存在
            ensure_dir(self.templatesDir)
            ensure_dir(self.ImgDir)

            # 保存 ROI 图片
            # roi 格式应该是 [x, y, width, height] 或 [x1, y1, x2, y2]
            if len(roi) == 4:
                x, y, w, h = roi[0], roi[1], roi[2], roi[3]
                # 这里需要从设备获取截图并裁剪 ROI 区域
                # 暂时保存一个占位图片，实际使用时需要传入截图数据
                img_path = self.templatesDir / f"{template_id}.png"

                cv2.imwrite(str(img_path), img_data)

            # 加载现有的 JSON 数据
            existing_data = self.jsonData
            if self.jsonFile.exists():
                with open(self.jsonFile, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)

            # 添加新的 ROI
            existing_data["rois"][template_id] = saveRoi

            # 保存 JSON 文件
            with open(self.jsonFile, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)

            return True

        except Exception as e:
            print(f"保存模板失败: {e}")
            return False

    def find_template_by_id(self, id: str) -> TemplateImg | None:
        # 根据id找到模板
        img_path = self.templatesDir / f"{id}.png"
        if not img_path.exists():
            return None

        try:
            img = TemplateImg(str(img_path))
            img.set_roi(roi=self.jsonData["rois"][id]["roi"])
            return img
        except Exception as e:
            print(f"加载模板图片失败: {e}")
            return None

    def delete(self, id: str) -> bool:
        """
        删除指定ID的模板
        :param id: 模板ID
        :return: 是否删除成功
        """
        try:
            # 1. 从 JSON 数据中移除
            if id not in self.jsonData.get("rois", {}):
                print(f"模板 ID {id} 不存在于记录中")
                return True

            # 移除 ROI 信息
            del self.jsonData["rois"][id]

            # 2. 从目录中删除对应的图片文件
            img_path = self.templatesDir / f"{id}.png"
            if img_path.exists():
                img_path.unlink()

            # 3. 保存更新后的 JSON 文件
            with open(self.jsonFile, 'w', encoding='utf-8') as f:
                json.dump(self.jsonData, f, ensure_ascii=False, indent=4)

            return True

        except Exception as e:
            print(f"删除模板失败: {e}")
            return False

    def _load_json(self):
        # 加载现有的 JSON 数据
        existing_data = self.jsonData
        if self.jsonFile.exists():
            with open(self.jsonFile, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            # 保存 JSON 文件
            with open(self.jsonFile, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)
        return existing_data

    def _load_png_file_from_dir(self):
        """
        加载目录下的PNG文件，并清理JSON中不存在对应图片文件的无效数据。
        :return: PNG文件名列表
        """
        # 确保目录存在
        ensure_dir(self.templatesDir)

        path = Path(self.templatesDir)

        # 获取目录下所有有效的 .png 文件名（不含后缀，以便与 JSON ID 对比）
        # 假设 JSON 中的 key (id) 对应的是文件名去掉 .png 的部分
        valid_png_ids = set()
        png_files_full_name = []

        if path.exists() and path.is_dir():
            for f in path.iterdir():
                if f.is_file() and f.suffix.lower() == '.png':
                    png_files_full_name.append(f.name)
                    # 提取 ID (即文件名去掉 .png)
                    valid_png_ids.add(f.stem)

        # 检查 JSON 数据中的 rois，如果 ID 对应的图片文件不存在，则从 JSON 数据中删除
        rois = self.jsonData.get("rois", {})
        ids_to_delete = []

        for template_id in rois:
            if template_id not in valid_png_ids:
                ids_to_delete.append(template_id)

        if ids_to_delete:
            for tid in ids_to_delete:
                del self.jsonData["rois"][tid]

            # 保存更新后的 JSON 文件到磁盘
            try:
                ensure_dir(self.rootDir)
                with open(self.jsonFile, 'w', encoding='utf-8') as f:
                    json.dump(self.jsonData, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"清理无效模板数据并保存 JSON 失败: {e}")

        return png_files_full_name

    def _del_file_from_dir(self):
        path = Path(self.templatesDir)

# class ScreenShot:
#     def __init__(self):
#         rootDir = Config.TEMPLATES_DIR
#         self.imgDir =  rootDir+"/images"
#         pass
#
#     def save(self, img : Union[str, bytes]):
#
#         if isinstance(img, bytes):
#             img = cv2_to_base64(img)
#             return save_base64_to_file(img, self.imgDir)
#         if isinstance(img, np):
#             img = cv2_to_base64(img)
