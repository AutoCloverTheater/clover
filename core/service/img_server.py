import cv2
import numpy as np
from PIL import Image
import io

class ImageManager:
    @staticmethod
    def from_file(path):
        """从磁盘加载图片"""
        img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError(f"无法从该路径加载图片: {path}")
        return img

    @staticmethod
    def from_adb(u2_device):
        """直接从 uiautomator2 截图加载到内存"""
        # format='opencv' 直接返回 numpy 数组 (BGR)
        return u2_device.screenshot(format='opencv')

    @staticmethod
    def from_bytes(content: bytes):
        """从内存字节流（比如前端传来的 base64 解码后）加载"""
        nparr = np.frombuffer(content, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
