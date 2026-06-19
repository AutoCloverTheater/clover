import json
import logging
import os

from flask import Blueprint, jsonify, request, send_file
from core.config import Config
from core.tool.filesystem import write_json_file, ensure_file_dir
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename

common_bp = Blueprint('common', __name__)
logger = logging.getLogger(__name__)

@common_bp.route('/pwd', methods=['GET'])
def pwd():
    """
    获取当前工作目录信息
    ---
    tags:
      - common
    summary: 获取当前工作目录及目录内容
    description: 返回当前工作目录路径及该目录下所有文件和文件夹名称
    responses:
      200:
        description: 成功获取目录信息
        schema:
          type: object
          properties:
            pwd:
              type: string
              description: 当前工作目录路径
              example: "/home/user/project"
            items:
              type: array
              description: 目录下所有文件和文件夹名称
              items:
                type: string
              example: ["src", "README.md", "package.json"]
            message:
              type: string
              description: 响应消息
              example: "ok"
            success:
              type: boolean
              description: 请求是否成功
              example: true
    """
    current_dir = os.getcwd()
    items = os.listdir(current_dir)
    data = {
        'pwd': current_dir,
        'items': items,
        'message': 'ok',
        'success': True
    }
    return jsonify(data)
