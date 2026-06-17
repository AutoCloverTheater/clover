import logging

import cv2
import numpy as np
from flask import Blueprint, jsonify, request,Response
from core.config import TEMPLATES_DATA

from core.service.template_manager import TemplateManager
from core.service.template_matcher import TemplateMatcher

templates = Blueprint('templates', __name__)
logger = logging.getLogger(__name__)

@templates.route('/', methods=['GET'])
def find_all_in_templates():
    file = request.files['image']
    # 读取文件字节流并转为 numpy 数组
    np_arr = np.frombuffer(file.read(), np.uint8)
    # 解码为 OpenCV 图像格式 (BGR)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    templatesKey = request.form['templates']
    threshold = request.form.get('threshold', 0.8)

    Manager = TemplateManager()
    temps = Manager.find_template_by_id(templatesKey)
    roi = temps.roi
    template_matcher = TemplateMatcher()
    results = template_matcher.find_match_all(img, temps.img, roi, threshold)

    return jsonify(results)


@templates.route('/findAllInTemplatesByName', methods=['POST'])
def find_all_in_templates_by_name():
    """
    根据模板名称在大图中查找所有匹配的模板

    请求参数:
    POST multipart/form-data:
    - image: 上传的图片文件
    - name: 模板名称
    - padding: [上, 右, 下, 左] (可选，默认[0,0,0,0])
    - roi: [x, y, width, height] (可选，指定搜索区域)

    返回:
    {
        "success": true/false,
        "matches": [
            {
                "template_name": "模板名称",
                "template_id": 模板ID,
                "rect": [x, y, w, h],
                "confidence": 匹配度
            }
        ]
    }
    """
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': '缺少图片文件'
            }), 400

        name = request.form.get('name')
        if not name:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: name'
            }), 400

        padding_str = request.form.get('padding', '[0,0,0,0]')
        roi_str = request.form.get('roi', None)

        try:
            import ast
            padding = ast.literal_eval(padding_str)
        except:
            padding = [0, 0, 0, 0]

        if roi_str:
            try:
                import ast
                roi = ast.literal_eval(roi_str)
            except:
                roi = None
        else:
            roi = None

        if len(padding) != 4:
            return jsonify({
                'success': False,
                'error': 'padding 必须是包含4个元素的数组 [上, 右, 下, 左]'
            }), 400

        pad_top, pad_right, pad_bottom, pad_left = padding

        file = request.files['image']
        np_arr = np.frombuffer(file.read(), np.uint8)
        target_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if target_img is None:
            return jsonify({
                'success': False,
                'error': '图片解码失败'
            }), 400

        matches = []

        for template in TEMPLATES_DATA:
            if template.get('name') == name and template.get(
                'img') is not None:
                template_roi = template.get('roi')

                if template_roi and len(template_roi) == 4:
                    tx, ty, tw, th = template_roi

                    expanded_x = max(0, tx - pad_left)
                    expanded_y = max(0, ty - pad_top)
                    expanded_w = tw + pad_left + pad_right
                    expanded_h = th + pad_top + pad_bottom

                    final_roi = [expanded_x, expanded_y, expanded_w,
                                 expanded_h]
                elif roi and len(roi) == 4:
                    final_roi = roi
                else:
                    final_roi = None

                template_matcher = TemplateMatcher()

                results = template_matcher.find_match_all(
                    image=target_img,
                    template=template['img'],
                    threshold=0.8,
                    roi=final_roi
                )

                for rect in results:
                    matches.append({
                        'template_name': name,
                        'template_id': template.get('id'),
                        'rect': list(rect),
                        'confidence': 0.0
                    })

        return jsonify({
            'success': True,
            'matches': matches
        })

    except Exception as e:
        logger.error(f"查找模板失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
