# 初始化配置
import logging

from flask import Blueprint, jsonify, request,Response
from app import DeviceX
from core.service.adb_manager import AdbManager
from core.service.device_service import DeviceService
from flask_restx import Namespace, Resource, fields

adb_bp = Blueprint('adb', __name__)
logger = logging.getLogger(__name__)

devices_ns = Namespace('devices', description='设备管理')

device_model = devices_ns.model('Device', {
    'serial': fields.String(description='设备序列号'),
    'port': fields.Integer(description='ADB 端口'),
    'emulator': fields.String(description='模拟器类型')
})

@adb_bp.route('/', methods=['GET'])
def get_adb_list():
    """
    获取 ADB 设备列表
    ---
    tags:
      - adb
    summary: 获取所有已连接的 ADB 设备
    description: 扫描并返回当前所有可用的 ADB 设备列表，包含序列号、模拟器类型和连接状态
    responses:
      200:
        description: 设备列表获取成功
        schema:
          type: object
          properties:
            adb_list:
              type: array
              description: ADB 设备列表
              items:
                type: object
                properties:
                  serial:
                    type: string
                    description: 设备序列号
                    example: "127.0.0.1:7555"
                  emulator:
                    type: string
                    description: 模拟器类型
                    example: "MuMu"
                  status:
                    type: string
                    description: 设备连接状态
                    example: "device"
        examples:
          application/json:
            adb_list:
              - serial: "127.0.0.1:7555"
                emulator: "MuMu"
                status: "device"
              - serial: "127.0.0.1:7557"
                emulator: "MuMu"
                status: "device"
    """
    adbManagerX = AdbManager()
    devices = adbManagerX.get_all_devices()

    return jsonify({
        'adb_list': devices
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

@adb_bp.route('/', methods=['POST'])
def connect_adb():
    """
    连接 ADB 设备
    ---
    tags:
      - adb
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            serial:
              type: string
              description: 设备序列号
              example: "127.0.0.1:7555"
          required:
            - serial
    responses:
      200:
        description: 连接成功
      400:
        description: serial 参数缺失或为空
    """
    global DeviceX
    data = request.get_json()
    serial = data.get('serial', "")

    if serial == "":
        return jsonify({'error': 'serial 不能为空'}), 400

    if DeviceX is None:
        DeviceX = DeviceService()

    DeviceX.connect(serial)

    return jsonify({})

@adb_bp.route('/disconnect', methods=['POST'])
def disconnect_adb():
    """
    断开 ADB 设备连接
    ---
    tags:
      - adb
    summary: 断开 ADB 设备
    description: 断开已连接的 ADB 设备，无论是否已经连接
    parameters:
      - name: body
        in: body
    responses:
      200:
        description: 断开成功
        schema:
          type: object
          example: {}
    """
    global DeviceX
    DeviceX = DeviceService()
    logger.info("设备已断开")
    return jsonify({})

@adb_bp.route('/screenshot', methods=['GET'])
def screenshot():
    """
    获取设备屏幕截图
    ---
    tags:
      - adb
    summary: 获取当前设备屏幕截图
    description: 截取当前连接设备的屏幕，直接返回 PNG 二进制图片
    responses:
      200:
        description: 截图成功
        content:
          image/png:
            schema:
              type: string
              format: binary
      400:
        description: 设备未连接
        schema:
          type: object
          properties:
            error:
              type: string
              example: "设备未连接"
    """
    global DeviceX
    if DeviceX is None:
        return jsonify({'error': '设备未连接'}), 400
    if DeviceX.device_info is None:
        return jsonify({'error': '设备未连接'}), 400
    DeviceX = DeviceService()
    buffer = DeviceX.screenshot_to_raw()

    return Response(
        buffer.tobytes(),
        mimetype='image/png',
        headers={'Content-Type': 'image/png'}
    )
