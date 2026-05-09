"""
ADB 设备管理器 - 专门用于设备发现和管理
提供设备列表获取，方便 uiautomator2 直接连接
"""
import os
import shutil
import subprocess
import sys
import time
import re
import logging
import socket
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from core.tool.adb_installer import get_or_install_adb

logger = logging.getLogger(__name__)


class DeviceStatus(Enum):
    """设备状态枚举"""
    DEVICE = "device"  # 已连接，已授权
    OFFLINE = "offline"  # 已连接，但未响应
    UNAUTHORIZED = "unauthorized"  # 已连接，未授权
    DISCONNECTED = "disconnected"  # 未连接
    CONNECTING = "connecting"  # 正在连接
    UNKNOWN = "unknown"  # 未知状态


@dataclass
class ADBDevice:
    """
    ADB 设备信息

    属性:
        serial: 设备序列号
        status: 设备状态
        model: 设备型号
        brand: 品牌
        transport: 连接方式 (usb/wifi/emulator)
        host: 主机地址（网络设备）
        port: 端口号（网络设备）
        is_emulator: 是否为模拟器
        raw_info: 原始信息
    """
    serial: str
    status: DeviceStatus = DeviceStatus.UNKNOWN
    model: str = ""
    brand: str = ""
    transport: str = "unknown"  # usb, wifi, emulator
    host: str = ""
    port: int = 0
    is_emulator: bool = False
    raw_info: str = ""

    # uiautomator2 连接参数
    @property
    def connection_serial(self) -> str:
        """
        返回 uiautomator2 可用的连接序列号

        - USB设备: 直接返回 serial
        - 网络设备: 返回 host:port 或 serial
        """
        if self.transport == 'wifi' and self.host:
            return f"{self.host}:{self.port}" if self.port else self.host
        return self.serial

    @property
    def is_connected(self) -> bool:
        """是否已连接且授权"""
        return self.status == DeviceStatus.DEVICE

    @property
    def is_available(self) -> bool:
        """是否可用于连接"""
        return self.status in [DeviceStatus.DEVICE, DeviceStatus.UNAUTHORIZED]

    @property
    def display_name(self) -> str:
        """用户友好的显示名称"""
        parts = []
        if self.model:
            parts.append(self.model)
        elif self.brand:
            parts.append(self.brand)

        parts.append(f"({self.serial})")

        if self.transport == 'wifi':
            parts.append('[WiFi]')
        elif self.transport == 'emulator':
            parts.append('[模拟器]')

        status_map = {
            DeviceStatus.DEVICE: '✅',
            DeviceStatus.OFFLINE: '⚠️',
            DeviceStatus.UNAUTHORIZED: '🔒',
            DeviceStatus.DISCONNECTED: '❌',
        }
        status_icon = status_map.get(self.status, '❓')

        return f"{status_icon} {' '.join(parts)}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'serial': self.serial,
            'connectionSerial': self.connection_serial,
            'status': self.status.value,
            'isConnected': self.is_connected,
            'isAvailable': self.is_available,
            'model': self.model,
            'brand': self.brand,
            'transport': self.transport,
            'host': self.host,
            'port': self.port,
            'isEmulator': self.is_emulator,
            'displayName': self.display_name,
        }


class ADBManager:
    """
    ADB 设备管理器

    专门负责:
    1. 发现和列出所有 ADB 设备
    2. ADB 服务管理（启动/停止/重启）
    3. 网络设备连接/断开
    4. 设备信息解析

    使用示例:
        manager = ADBManager()

        # 获取所有设备
        devices = manager.get_devices()
        for d in devices:
            print(d.display_name)
            # 可用于 uiautomator2:
            # u2.connect(d.connection_serial)

        # 获取可用设备
        available = manager.get_available_devices()

        # 连接网络设备
        manager.connect_network('192.168.1.100:5555')

        # 配对无线调试（Android 11+）
        manager.pair('192.168.1.100', 12345, '配对码')
    """

    # ADB 可能的安装路径
    POSSIBLE_ADB_PATHS = [
        # 系统 PATH 中的 adb
        'adb',
        # Android SDK 默认路径
        '/usr/local/bin/adb',
        '/usr/bin/adb',
        # macOS Homebrew
        '/opt/homebrew/bin/adb',
        '/usr/local/share/android-sdk/platform-tools/adb',
        # Linux Android SDK
        '/home/*/Android/Sdk/platform-tools/adb',
        '/usr/lib/android-sdk/platform-tools/adb',
        # Windows
        'C:/adb/adb.exe',
        'C:/platform-tools/adb.exe',
        '%LOCALAPPDATA%/Android/Sdk/platform-tools/adb.exe',
        '%ANDROID_HOME%/platform-tools/adb.exe',
        # 项目本地
        './adb',
        './adb.exe',
    ]

    def __init__(self, adb_path: str = '', timeout: int = 10, auto_install: bool = True):
        """
        初始化 ADB 管理器

        Args:
            adb_path: ADB 可执行文件路径
            timeout: 命令超时时间（秒）
        """
        self.adb_path = adb_path
        self.timeout = timeout
        # 查找 ADB
        if adb_path:
            self.adb_path = adb_path
        elif auto_install:
            # 自动安装 ADB
            self.adb_path = str(get_or_install_adb())
        else:
            self.adb_path = self._find_adb()

        if not self.adb_path:
            raise RuntimeError(
                "ADB 未找到！请:\n"
                "1. 安装 Android SDK Platform Tools\n"
                "2. 将 ADB 添加到系统 PATH\n"
                "3. 或指定 ADB 路径: ADBManager(adb_path='/path/to/adb')"
            )


        # 检查 ADB 是否可用
        self._verify_adb()

    def _verify_adb(self):
        """验证 ADB 是否可用"""
        try:
            result = self._run(['version'], timeout=5)
            if result[0] != 0:
                raise RuntimeError(f"ADB 返回异常: {result[2]}")

            version_info = result[1].split('\n')[0] if result[1] else '未知版本'
            logger.info(f"ADB 就绪: {version_info}")

        except FileNotFoundError:
            raise RuntimeError(f"ADB 未找到: {self.adb_path}")
        except Exception as e:
            raise RuntimeError(f"ADB 验证失败: {e}")

    def _run(self, args: List[str], timeout: Optional[int] = None) -> Tuple[
        int, str, str]:
        """
        执行 ADB 命令

        Args:
            args: 命令参数
            timeout: 超时时间

        Returns:
            (returncode, stdout, stderr)
        """
        cmd = [self.adb_path] + args

        logger.debug(f"执行: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                encoding='utf-8',
                errors='replace',
            )
            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            logger.error(f"ADB 命令超时: {' '.join(cmd)}")
            return -1, '', '命令超时'
        except Exception as e:
            logger.error(f"ADB 命令异常: {e}")
            return -1, '', str(e)

    # ==================== 设备发现 ====================

    def get_devices(self) -> List[ADBDevice]:
        """
        获取所有设备列表

        Returns:
            ADBDevice 列表
        """
        returncode, stdout, stderr = self._run(['devices', '-l'], timeout=10)

        if returncode != 0:
            logger.error(f"获取设备列表失败: {stderr}")
            return []

        devices = []
        lines = stdout.strip().split('\n')

        for line in lines[1:]:  # 跳过第一行 "List of devices attached"
            line = line.strip()
            if not line:
                continue

            device = self._parse_device_line(line)
            if device:
                devices.append(device)

        logger.info(f"发现 {len(devices)} 个设备")
        return devices

    def get_available_devices(self) -> List[ADBDevice]:
        """
        获取可用于连接的设备（已授权）

        Returns:
            已连接的设备列表
        """
        return [d for d in self.get_devices() if d.is_connected]

    def get_device_by_serial(self, serial: str) -> Optional[ADBDevice]:
        """根据序列号查找设备"""
        devices = self.get_devices()
        for d in devices:
            if d.serial == serial:
                return d
        return None

    def get_first_available(self) -> Optional[ADBDevice]:
        """获取第一个可用设备"""
        available = self.get_available_devices()
        return available[0] if available else None

    def _parse_device_line(self, line: str) -> Optional[ADBDevice]:
        """
        解析 ADB devices -l 的输出行

        示例行:
        - "emulator-5554          device product:sdk_gphone64_arm64 model:sdk_gphone64_arm64 device:emu64a"
        - "192.168.1.100:5555     device product:star2qlte model:SM_G9650 device:star2qlte"
        - "R5CT1234567             unauthorized"
        - "192.168.1.200:5555      offline"
        """
        parts = line.split()
        if len(parts) < 2:
            return None

        serial = parts[0]
        status_str = parts[1]

        # 解析状态
        try:
            status = DeviceStatus(status_str)
        except ValueError:
            status = DeviceStatus.UNKNOWN

        device = ADBDevice(
            serial=serial,
            status=status,
            raw_info=line,
        )

        # 判断传输方式和是否为模拟器
        if serial.startswith('emulator-'):
            device.transport = 'emulator'
            device.is_emulator = True
        elif ':' in serial:
            device.transport = 'wifi'
            host_port = serial.split(':')
            device.host = host_port[0]
            device.port = int(host_port[1]) if len(host_port) > 1 else 5555
        elif serial.startswith('127.0.0.1') or serial.startswith('192.168'):
            device.transport = 'wifi'
        else:
            # USB 设备，格式通常是字母数字组合
            device.transport = 'usb'

        # 解析额外信息 (product:, model:, device:)
        for part in parts[2:]:
            if ':' in part:
                key, value = part.split(':', 1)
                if key == 'model':
                    device.model = value
                elif key == 'product':
                    device.brand = value
                elif key == 'device':
                    # device 字段可能表示设备代号
                    if not device.model:
                        device.model = value

        # 模拟器检测
        if 'emulator' in serial.lower() or 'generic' in device.model.lower():
            device.is_emulator = True
            device.transport = 'emulator'

        return device

    # ==================== ADB 服务管理 ====================

    def start_server(self) -> bool:
        """启动 ADB 服务"""
        returncode, stdout, stderr = self._run(['start-server'], timeout=10)
        success = returncode == 0
        if success:
            logger.info("ADB 服务已启动")
        else:
            logger.error(f"ADB 服务启动失败: {stderr}")
        return success

    def stop_server(self) -> bool:
        """停止 ADB 服务"""
        returncode, stdout, stderr = self._run(['kill-server'], timeout=5)
        success = returncode == 0
        if success:
            logger.info("ADB 服务已停止")
        return success

    def restart_server(self) -> bool:
        """重启 ADB 服务"""
        self.stop_server()
        time.sleep(1)
        return self.start_server()

    def is_server_running(self) -> bool:
        """检查 ADB 服务是否运行"""
        returncode, stdout, stderr = self._run(['devices'], timeout=5)
        # 如果服务运行，即使没有设备也会成功返回
        return returncode == 0 and 'List of devices attached' in stdout

    # ==================== 设备连接 ====================

    def connect_network(self, address: str, timeout: int = 10) -> Tuple[
        bool, str]:
        """
        连接网络设备

        Args:
            address: 设备地址，如 '192.168.1.100:5555' 或 '192.168.1.100'
            timeout: 超时时间

        Returns:
            (成功, 消息)
        """
        # 确保有端口号
        if ':' not in address:
            address = f"{address}:5555"

        logger.info(f"连接网络设备: {address}")
        returncode, stdout, stderr = self._run(
            ['connect', address],
            timeout=timeout
        )

        output = stdout.strip() or stderr.strip()

        if returncode == 0 or 'connected' in output.lower():
            logger.info(f"设备已连接: {address}")
            return True, output
        elif 'already connected' in output.lower():
            logger.info(f"设备已连接: {address}")
            return True, output
        else:
            logger.error(f"连接失败: {output}")
            return False, output

    def disconnect_network(self, address: Optional[str] = None) -> bool:
        """
        断开网络设备连接

        Args:
            address: 设备地址，None 则断开所有
        """
        args = ['disconnect']
        if address:
            args.append(address)

        returncode, stdout, stderr = self._run(args, timeout=5)
        logger.info(f"断开连接: {address or '全部'}")
        return returncode == 0

    def pair(self, host: str, port: int, pairing_code: str) -> Tuple[
        bool, str]:
        """
        配对无线调试（Android 11+）

        Args:
            host: 设备IP
            port: 配对端口（在无线调试页面显示）
            pairing_code: 6位配对码

        Returns:
            (成功, 消息)
        """
        address = f"{host}:{port}"
        logger.info(f"配对设备: {address}")

        returncode, stdout, stderr = self._run(
            ['pair', address, pairing_code],
            timeout=15
        )

        output = stdout.strip() or stderr.strip()
        success = returncode == 0 or 'success' in output.lower()

        if success:
            logger.info(f"配对成功: {host}")
        else:
            logger.error(f"配对失败: {output}")

        return success, output

    # ==================== 设备信息 ====================

    def get_detailed_info(self, serial: str) -> Dict[str, str]:
        """
        获取设备详细信息

        Args:
            serial: 设备序列号

        Returns:
            设备属性字典
        """
        properties = {
            'ro.product.model': 'model',
            'ro.product.brand': 'brand',
            'ro.product.name': 'productName',
            'ro.build.version.release': 'androidVersion',
            'ro.build.version.sdk': 'sdkVersion',
            'ro.product.cpu.abi': 'cpuAbi',
        }

        info = {}
        for prop, key in properties.items():
            returncode, stdout, stderr = self._run(
                ['-s', serial, 'shell', 'getprop', prop],
                timeout=5
            )
            if returncode == 0:
                info[key] = stdout.strip()

        # 获取屏幕尺寸
        returncode, stdout, stderr = self._run(
            ['-s', serial, 'shell', 'wm', 'size'],
            timeout=5
        )
        if returncode == 0:
            # 解析 "Physical size: 1080x2400"
            match = re.search(r'(\d+)x(\d+)', stdout)
            if match:
                info['screenWidth'] = match.group(1)
                info['screenHeight'] = match.group(2)
                info['resolution'] = f"{match.group(1)}x{match.group(2)}"

        # 获取DPI
        returncode, stdout, stderr = self._run(
            ['-s', serial, 'shell', 'wm', 'density'],
            timeout=5
        )
        if returncode == 0:
            dpi_match = re.search(r'(\d+)', stdout)
            if dpi_match:
                info['dpi'] = dpi_match.group(1)

        return info

    def is_device_online(self, serial: str) -> bool:
        """检查设备是否在线"""
        devices = self.get_devices()
        for d in devices:
            if d.serial == serial:
                return d.is_connected
        return False

    def wait_for_device(self, serial: str, timeout: int = 30) -> bool:
        """
        等待设备就绪

        Args:
            serial: 设备序列号
            timeout: 最大等待时间

        Returns:
            是否就绪
        """
        returncode, stdout, stderr = self._run(
            ['-s', serial, 'wait-for-device'],
            timeout=timeout
        )
        return returncode == 0

    # ==================== 便捷方法 ====================

    def auto_discover_usb(self) -> Optional[ADBDevice]:
        """
        自动发现USB设备

        Returns:
            第一个USB设备，没有则返回 None
        """
        devices = self.get_available_devices()
        for d in devices:
            if d.transport == 'usb' and not d.is_emulator:
                return d
        # 没有USB设备，返回第一个可用设备（可能是模拟器）
        return devices[0] if devices else None

    def auto_discover_network(self) -> List[ADBDevice]:
        """
        自动发现可用网络设备

        Returns:
            网络设备列表
        """
        devices = self.get_available_devices()
        return [d for d in devices if d.transport == 'wifi']

    def auto_discover_emulators(self) -> List[ADBDevice]:
        """自动发现模拟器"""
        devices = self.get_available_devices()
        return [d for d in devices if d.is_emulator]

    def to_u2_serial(self, device: ADBDevice) -> str:
        """
        转换为 uiautomator2 可用的连接序列号

        Args:
            device: ADBDevice 对象

        Returns:
            uiautomator2 连接字符串
        """
        return device.connection_serial

    def get_u2_connection_list(self) -> List[str]:
        """
        获取所有可用于 uiautomator2 连接的序列号列表

        Returns:
            序列号列表
        """
        devices = self.get_available_devices()
        return [d.connection_serial for d in devices]

    def print_devices(self):
        """打印所有设备信息（调试用）"""
        devices = self.get_devices()
        print(f"\n{'=' * 60}")
        print(f"发现 {len(devices)} 个设备")
        print(f"{'=' * 60}")

        for i, d in enumerate(devices, 1):
            print(f"\n设备 {i}:")
            print(f"  序列号:     {d.serial}")
            print(f"  连接方式:   {d.connection_serial}")
            print(f"  状态:       {d.status.value}")
            print(f"  型号:       {d.model or '未知'}")
            print(f"  品牌:       {d.brand or '未知'}")
            print(f"  传输方式:   {d.transport}")
            print(f"  是否模拟器: {d.is_emulator}")
            if d.host:
                print(f"  地址:       {d.host}:{d.port}")
            print(f"  可用:       {'✅' if d.is_connected else '❌'}")

        print(f"\n{'=' * 60}")
        print(f"uiautomator2 可连接设备: {self.get_u2_connection_list()}")
        print(f"{'=' * 60}\n")

    @classmethod
    def _find_adb(cls) -> Optional[str]:
        """
        自动查找 ADB 可执行文件

        Returns:
            ADB 路径，找不到返回 None
        """
        # 1. 首先检查系统 PATH
        adb_in_path = shutil.which('adb')
        if adb_in_path:
            return adb_in_path

        # 2. 检查环境变量
        env_paths = [
            os.environ.get('ANDROID_HOME', ''),
            os.environ.get('ANDROID_SDK_ROOT', ''),
            os.environ.get('ANDROID_SDK_HOME', ''),
        ]

        for env_path in env_paths:
            if env_path:
                adb_path = Path(
                    env_path) / 'platform-tools' / cls._adb_filename()
                if adb_path.exists():
                    return str(adb_path)

        # 3. 检查常见安装路径
        for pattern in cls.POSSIBLE_ADB_PATHS:
            expanded = os.path.expandvars(pattern)
            expanded = os.path.expanduser(expanded)

            # 处理通配符
            if '*' in expanded:
                import glob
                matches = glob.glob(expanded)
                for match in matches:
                    if os.path.isfile(match):
                        return match
            elif os.path.isfile(expanded):
                return expanded

        # 4. 在 macOS/Linux 上使用 which 查找
        if sys.platform != 'win32':
            try:
                import subprocess
                result = subprocess.run(
                    ['which', 'adb'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception:
                pass

        return None

    @staticmethod
    def _adb_filename() -> str:
        """根据平台返回 ADB 文件名"""
        return 'adb.exe' if sys.platform == 'win32' else 'adb'

    @staticmethod
    def get_adb_install_instructions() -> str:
        """获取 ADB 安装指南"""
        if sys.platform == 'win32':
            return (
                "Windows ADB 安装:\n"
                "1. 下载: https://dl.google.com/android/repository/platform-tools-latest-windows.zip\n"
                "2. 解压到 C:\\platform-tools\\\n"
                "3. 添加到 PATH: setx PATH \"%PATH%;C:\\platform-tools\"\n"
                "4. 或使用包管理器: scoop install adb"
            )
        elif sys.platform == 'darwin':
            return (
                "macOS ADB 安装:\n"
                "1. Homebrew: brew install android-platform-tools\n"
                "2. 或下载: https://dl.google.com/android/repository/platform-tools-latest-darwin.zip\n"
            )
        else:
            return (
                "Linux ADB 安装:\n"
                "1. Debian/Ubuntu: sudo apt install adb\n"
                "2. Arch: sudo pacman -S android-tools\n"
                "3. 或下载: https://dl.google.com/android/repository/platform-tools-latest-linux.zip\n"
            )


# ==================== 全局单例 ====================
_adb_manager_instance: Optional[ADBManager] = None


def get_adb_manager(adb_path: str = 'adb') -> ADBManager:
    """获取 ADB 管理器单例"""
    global _adb_manager_instance
    if _adb_manager_instance is None:
        _adb_manager_instance = ADBManager(adb_path=adb_path)
    return _adb_manager_instance


# ==================== 与 DeviceService 配合使用 ====================
def discover_and_connect() -> Tuple[Optional[str], Optional[Dict]]:
    """
    自动发现设备并返回 uiautomator2 连接参数

    使用方式:
        import uiautomator2 as u2
        from services.adb_manager import discover_and_connect

        serial, info = discover_and_connect()
        if serial:
            device = u2.connect(serial)

    Returns:
        (连接序列号, 设备信息字典)
    """
    manager = get_adb_manager()
    device = manager.auto_discover_usb()

    if device:
        return device.connection_serial, device.to_dict()
    return None, None


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    manager = ADBManager()
    manager.print_devices()

    # 获取可用设备列表
    available = manager.get_available_devices()
    print(f"可用设备: {len(available)}")
    for d in available:
        print(f"  u2.connect('{d.connection_serial}')  # {d.display_name}")
