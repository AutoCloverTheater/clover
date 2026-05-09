import json
import logging
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file
from core.config import Config

roi_bp = Blueprint('roi', __name__)
logger = logging.getLogger(__name__)


def get_roi_file_path(screenshot_id):
    """获取 ROI 数据文件路径"""
    return Config.TEMPLATES_DIR / f"{screenshot_id}.json"


@roi_bp.route('/<screenshot_id>', methods=['GET'])
def get_roi(screenshot_id):
    """获取指定截图的 ROI 坐标"""
    file_path = get_roi_file_path(screenshot_id)

    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)

    return jsonify({'rectangles': [], 'message': '暂无ROI数据'})


@roi_bp.route('/<screenshot_id>', methods=['POST'])
def save_roi(screenshot_id):
    """保存 ROI 坐标"""
    data = request.get_json()
    rectangles = data.get('rectangles', [])

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
