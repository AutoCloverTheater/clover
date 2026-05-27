import json
import logging
import os

from flask import Blueprint, jsonify, request, send_file
from core.config import Config
from core.tool.filesystem import write_json_file, ensure_file_dir
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename

roi_bp = Blueprint('roi', __name__)
logger = logging.getLogger(__name__)


def get_roi_file_path():
    """获取 ROI 数据文件路径"""
    return Config.TEMPLATES_DIR / f"templates.json"

def roi_json():
    file_path = get_roi_file_path()

    if ensure_file_dir(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    else:
        write_json_file(file_path, {"templates": {}, "rois" :{}})
    return {"templates": {}, "rois" :{}}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@roi_bp.route('/save_screenshot', methods=['POST'])
def save_screenshot():
    """接收并保存图片"""
    try:
        # 方式1: 从 form-data 接收文件
        if 'image' not in request.files:
            return jsonify({'error': '没有找到图片文件'}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400

        if file and allowed_file(file.filename):
            # 生成唯一文件名
            original_filename = secure_filename(file.filename)
            ext = original_filename.rsplit('.', 1)[1].lower()
            new_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"

            # 保存文件
            save_path = os.path.join(Config.TEMPLATES_DIR, "images", new_filename)
            file.save(save_path)

            return jsonify({
                'success': True,
                'message': '图片上传成功',
                'filename': new_filename,
                'path': save_path,
                'url': f"/uploads/{new_filename}"
            }), 200
        else:
            return jsonify({'error': '不支持的文件类型'}), 400

    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@roi_bp.route('/roiById', methods=['GET'])
def get_roi():
    """获取指定截图的 ROI 坐标"""
    data = request.get_json()
    screenshot_id = data.get('screenshot_id', [])

    if roi_json() is not None:
        return jsonify({'rois': roi_json().get("rois", {}).get(screenshot_id), 'message': 'ok'})
    return jsonify({'rois': [], 'message': '暂无ROI数据'})



@roi_bp.route('/roi/edist', methods=['POST'])
def save_roi(screenshot_id):
    """保存 ROI 坐标"""
    data = request.get_json()
    rectangles = data.get('roi', [])

    roi_data = {
        'screenshotId': screenshot_id,
        'rectangles': rectangles,
        'updatedAt': __import__('datetime').datetime.now().isoformat(),
    }

    file_path = get_roi_file_path(screenshot_id)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(roi_data, f, ensure_ascii=False, indent=2)

    logger.info(f"ROI已保存: {screenshot_id}, {len(rectangles)}个矩形")
    return jsonify(
        {'success': True, 'message': f'已保存{len(rectangles)}个ROI'})


@roi_bp.route('/export', methods=['GET'])
def export_all():
    """导出所有 ROI 模板"""
    import io

    screenshot_ids = request.args.get('ids', '')

    all_data = {}

    if screenshot_ids:
        ids = screenshot_ids.split(',')
        for sid in ids:
            file_path = get_roi_file_path(sid)
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_data[sid] = json.load(f)
    else:
        for f in Config.TEMPLATES_DIR.glob('*.json'):
            with open(f, 'r', encoding='utf-8') as fp:
                all_data[f.stem] = json.load(fp)

    export_data = {
        'version': '1.0',
        'exportTime': __import__('datetime').datetime.now().isoformat(),
        'templates': all_data,
    }

    buffer = io.BytesIO()
    buffer.write(
        json.dumps(export_data, ensure_ascii=False, indent=2).encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/json',
        as_attachment=True,
        download_name=f'roi_templates_{__import__("time").strftime("%Y%m%d_%H%M%S")}.json'
    )


@roi_bp.route('/import', methods=['POST'])
def import_roi():
    """导入 ROI 模板"""
    if 'file' not in request.files:
        return jsonify({'error': '请上传文件'}), 400

    file = request.files['file']

    try:
        data = json.loads(file.read())
        imported_count = 0

        templates = data.get('templates', {})
        for screenshot_id, template_data in templates.items():
            file_path = get_roi_file_path(screenshot_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            imported_count += 1

        return jsonify({
            'success': True,
            'importedCount': imported_count,
            'message': f'成功导入{imported_count}个模板',
        })

    except json.JSONDecodeError:
        return jsonify({'error': 'JSON格式错误'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
