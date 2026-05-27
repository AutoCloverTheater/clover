import cv2


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

    def find_match_all(self, target_img, template_img, roi=None, threshold=0.8):
        """
        在目标图片中寻找模板的多个位置
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

        results = []

        if max_val >= threshold:
            # 获取模板尺寸
            h, w = template_img.shape[:2]

            # 计算中心点坐标 (需要加上 ROI 的偏移量还原到原始全屏坐标)
            center_x = max_loc[0] + w // 2 + offset_x
            center_y = max_loc[1] + h // 2 + offset_y

            results.append({
                "pos": (int(center_x), int(center_y)),
                "confidence": round(max_val, 4),
                "rect": (int(max_loc[0] + offset_x),)
            })

        return {"found": bool(len(results)),"num":len(results), "results": results}
