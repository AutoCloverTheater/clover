# 初始化配置
import logging

from flask import Blueprint, jsonify, request,Response
from flask_restx import Namespace, fields

adb_bp = Blueprint('adb', __name__)
logger = logging.getLogger(__name__)

devices_ns = Namespace('devices', description='设备管理')

device_model = devices_ns.model('Device', {
    'serial': fields.String(description='设备序列号'),
    'port': fields.Integer(description='ADB 端口'),
    'emulator': fields.String(description='模拟器类型')
})

@adb_bp.route('/info', methods=['GET'])
def get_adb_info():
    """
    获取当前连接设备信息
    ---
    tags:
      - adb
    summary: 获取已连接 ADB 设备的详细信息
    description: 返回当前全局 DeviceX 所连接设备的详细信息，包括序列号、SDK 版本、品牌、型号、架构和系统版本
    responses:
      200:
        description: 设备信息获取成功
        schema:
          type: object
          properties:
            serial:
              type: string
              description: 设备序列号
              example: "127.0.0.1:7555"
            sdk:
              type: integer
              description: Android SDK 版本号
              example: 33
              nullable: true
            brand:
              type: string
              description: 设备品牌
              example: "MuMu"
            model:
              type: string
              description: 设备型号
              example: "MuMu Player"
            arch:
              type: string
              description: CPU 架构
              example: "x86_64"
            version:
              type: integer
              description: Android 系统版本号
              example: 13
              nullable: true
        examples:
          application/json:
            serial: "127.0.0.1:7555"
            sdk: 33
            brand: "MuMu"
            model: "MuMu Player"
            arch: "x86_64"
            version: 13
      500:
        description: 设备未连接或内部错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: "设备未连接"
    """
    global DeviceX
    if DeviceX is None:
        return jsonify({'error': '设备未连接，请先调用 POST /adb 连接设备'}), 400

    info = DeviceX.device_info
    return jsonify(info)
