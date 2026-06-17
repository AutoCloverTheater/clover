import cv2
import numpy as np

class TemplateMatcher:
    def __init__(self):
        pass
    def find_match(self, target_img, template_img, roi=None, threshold=0.8):
        """
        在目标图片中寻找模板
        :param threshold:
        :param target_img: 大图 (OpenCV 格式)
        :param template_img: 小图/模板 (OpenCV 格式)
        :param roi: 限制区域 [x1, y1, x2, y2]，如果不传则全屏匹配
        :return: {'found': bool, 'pos': (x, y), 'conf': float}
        """
        search_img = target_img
        offset_x, offset_y = 0, 0

        # 如果指定了 ROI，先裁剪小部分图片进行匹配以提高效率和准确率
        if roi:
            x1, y1, x2, y2 = roi
            search_img = target_img[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1

        # 执行匹配
        res = cv2.matchTemplate(search_img, template_img, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            # 获取模板尺寸
            h, w = template_img.shape[:2]

            # 计算中心点坐标 (需要加上 ROI 的偏移量还原到原始全屏坐标)
            center_x = max_loc[0] + w // 2 + offset_x
            center_y = max_loc[1] + h // 2 + offset_y

            return {
                "found": True,
                "pos": (int(center_x), int(center_y)),
                "confidence": round(max_val, 4),
                "rect": (int(max_loc[0] + offset_x),
                         int(max_loc[1] + offset_y), w, h)
            }

        return {"found": False, "confidence": round(max_val, 4)}

    def find_match_all(self,image, template, threshold=0.8, method=cv2.TM_CCOEFF_NORMED,
                         nms_threshold=0.3, roi=None):
        """
        在大图中模板匹配所有可能存在的矩形目标，支持 ROI 区域限定

        Args:
            image: 大图 (numpy数组)
            template: 模板图 (numpy数组)
            threshold: 匹配阈值
            method: 匹配方法
            nms_threshold: 非极大值抑制阈值
            roi: 限定搜索区域 (x, y, w, h)，默认 None 表示全图搜索

        Returns:
            list: [(x, y, w, h), ...] 基于原图坐标的匹配矩形
        """
        h, w = template.shape[:2]
        img_h, img_w = image.shape[:2]

        # 处理 ROI
        offset_x, offset_y = 0, 0
        search_image = image

        if roi is not None:
            rx, ry, rw, rh = roi
            # 边界限制，防止越界
            x1 = max(0, rx)
            y1 = max(0, ry)
            x2 = min(img_w, rx + rw)
            y2 = min(img_h, ry + rh)

            # 裁剪搜索区域
            search_image = image[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1

        # ROI 必须能容纳模板
        if search_image.shape[0] < h or search_image.shape[1] < w:
            return []

        # 模板匹配
        result = cv2.matchTemplate(search_image, template, method)

        # 根据方法取阈值方向
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            loc = np.where(result <= threshold)
        else:
            loc = np.where(result >= threshold)

        # 收集候选矩形（坐标转回原图）
        rectangles = []
        scores = []
        for pt in zip(*loc[::-1]):
            x, y = pt[0] + offset_x, pt[1] + offset_y
            rectangles.append([x, y, w, h])
            scores.append(float(result[pt[1], pt[0]]))

        if len(rectangles) == 0:
            return []

        # 非极大值抑制
        indices = cv2.dnn.NMSBoxes(rectangles, scores, threshold,
                                   nms_threshold)

        matched = []
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, rw, rh = rectangles[i]
                matched.append((int(x), int(y), int(rw), int(rh)))

        return matched
