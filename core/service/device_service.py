"""
设备服务模块 - 基于 uiautomator2 封装
"""
import os
import time
import base64
import logging
import threading
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from pathlib import Path
from io import BytesIO

import uiautomator2 as u2
from PIL import Image

from core.service.adb_manager import ADBManager

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """设备信息"""
    serial: str
    status: str = "disconnected"  # connected, disconnected, unauthorized
    model: str = ""
    brand: str = ""
    android_version: str = ""
    sdk_version: int = 0
    resolution: str = ""  # "1080x2400"
    screen_width: int = 0
    screen_height: int = 0
    is_emulator: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'serial': self.serial,
            'status': self.status,
            'model': self.model,
            'brand': self.brand,
            'androidVersion': self.android_version,
            'sdkVersion': self.sdk_version,
            'resolution': self.resolution,
            'screenWidth': self.screen_width,
            'screenHeight': self.screen_height,
            'isEmulator': self.is_emulator,
        }

    @property
    def display_name(self) -> str:
        if self.model:
            return f"{self.model} ({self.serial})"
        return self.serial


class DeviceConnectionError(Exception):
    """设备连接异常"""
    pass


class DeviceService:
    """
    设备管理服务（基于 uiautomator2）

    使用示例:
        service = DeviceService()

        # 连接设备
        device = service.connect('192.168.1.100:5555')
        # 或自动连接第一个USB设备
        device = service.auto_connect()

        # 截图
        screenshot_data = service.screenshot()
        service.screenshot_to_file('screenshot.png')

        # 点击、滑动
        service.click(500, 1000)
        service.swipe(100, 500, 100, 200)

        # 获取UI层级
        xml = service.dump_hierarchy()
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, adb_path: Optional[str] = None):
        """
        初始化设备服务

        Args:
            adb_path: ADB 可执行文件路径，None 则自动查找
        """
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self._adb_path = adb_path
        self._current_serial: Optional[str] = None
        self._device: Optional[u2.Device] = None
        self._device_info: Optional[DeviceInfo] = None
        self._screenshot_cache: Optional[bytes] = None
        self._screenshot_lock = threading.Lock()

        # 截图流相关
        self._streaming = False
        self._stream_interval = 2.0
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_callbacks: List[Callable] = []

        # 设置 ADB 路径
        if adb_path:
            os.environ['ANDROID_ADB_PATH'] = adb_path

        logger.info("DeviceService 初始化完成")

    # ==================== 设备发现 ====================

    def list_devices(self) -> List[DeviceInfo]:
        """
        列出所有设备

        Returns:
            设备信息列表
        """
        devices = []

        try:
            # 获取 ADB 设备列表
            adb = ADBManager()

            adb_devices = adb.get_devices()

            for serial, status in adb_devices.items():
                info = DeviceInfo(
                    serial=serial,
                    status='connected' if status == 'device' else status,
                )

                # 尝试获取设备详细信息
                if status == 'device':
                    try:
                        d = u2.connect(serial)
                        info.model = d.info.get('productModel', '')
                        info.brand = d.info.get('productBrand', '')
                        info.android_version = d.info.get('version', '')
                        info.sdk_version = d.info.get('sdk', 0)
                        info.screen_width = d.info.get('displayWidth', 0)
                        info.screen_height = d.info.get('displayHeight', 0)
                        info.resolution = f"{info.screen_width}x{info.screen_height}"
                        info.is_emulator = serial.startswith('emulator-') or \
                                           'generic' in info.model.lower()
                    except Exception as e:
                        logger.debug(f"获取设备 {serial} 详情失败: {e}")

                devices.append(info)

        except Exception as e:
            logger.error(f"列出设备失败: {e}")

        return devices

    def get_connected_devices(self) -> List[DeviceInfo]:
        """获取已连接的设备"""
        return [d for d in self.list_devices() if d.status == 'connected']

    def get_first_device(self) -> Optional[DeviceInfo]:
        """获取第一个已连接的设备"""
        devices = self.get_connected_devices()
        return devices[0] if devices else None

    # ==================== 设备连接 ====================

    def connect(self, serial: Optional[str] = None,
                timeout: int = 30) -> u2.Device:
        """
        连接设备

        Args:
            serial: 设备序列号，None 则自动选择第一个USB设备
            timeout: 连接超时时间

        Returns:
            uiautomator2 Device 对象
        """
        if not serial:
            # 自动选择设备
            device_info = self.get_first_device()
            if device_info:
                serial = device_info.serial

        logger.info(f"正在连接设备: {serial}")

        try:
            device = u2.connect(serial)

            # 获取设备信息
            self._device = device
            self._current_serial = serial
            self._device_info = DeviceInfo(
                serial=serial,
                status='connected',
                model=device.info.get('productModel', ''),
                brand=device.info.get('productBrand', ''),
                android_version=device.info.get('version', ''),
                sdk_version=device.info.get('sdk', 0),
                screen_width=device.info.get('displayWidth', 0),
                screen_height=device.info.get('displayHeight', 0),
                resolution=f"{device.info.get('displayWidth', 0)}x{device.info.get('displayHeight', 0)}",
            )

            logger.info(f"设备已连接: {self._device_info.display_name}")
            return device

        except Exception as e:
            self._device = None
            self._current_serial = None
            raise DeviceConnectionError(f"连接设备失败 [{serial}]: {e}")

    def auto_connect(self) -> u2.Device:
        """自动连接第一个可用设备"""
        return self.connect()

    def disconnect(self):
        """断开当前设备"""
        if self._device:
            try:
                self._device.disconnect()
            except Exception as e:
                logger.warning(f"断开设备时出错: {e}")

        self._device = None
        self._current_serial = None
        self._device_info = None
        self.stop_stream()
        logger.info("设备已断开")

    def reconnect(self, serial: Optional[str] = None) -> u2.Device:
        """重新连接设备"""
        self.disconnect()
        return self.connect(serial)

    @property
    def is_connected(self) -> bool:
        """检查设备是否已连接"""
        if not self._device:
            return False
        try:
            return self._device.info is not None
        except Exception:
            return False

    @property
    def device(self) -> Optional[u2.Device]:
        """获取当前设备对象"""
        if not self.is_connected:
            return None
        return self._device

    @property
    def device_info(self) -> Optional[DeviceInfo]:
        """获取当前设备信息"""
        return self._device_info

    @property
    def current_serial(self) -> Optional[str]:
        """获取当前设备序列号"""
        return self._current_serial

    # ==================== 截图功能 ====================

    def screenshot(self, format: str = 'png') -> bytes:
        """
        截图（返回图片字节数据）

        Args:
            format: 图片格式 ('png' 或 'jpeg')

        Returns:
            图片字节数据
        """
        device = self._get_device()

        with self._screenshot_lock:
            img = device.screenshot(format=format)
            self._screenshot_cache = img

        logger.debug(f"截图完成: {len(img)} bytes")
        return img

    def screenshot_to_base64(self, format: str = 'png') -> str:
        """
        截图并返回 Base64 编码

        Args:
            format: 图片格式

        Returns:
            Base64 编码的图片字符串
        """
        img_bytes = self.screenshot(format)
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        return f"data:image/{format};base64,{b64}"

    def screenshot_to_file(self, filepath: str, format: str = 'png') -> str:
        """
        截图并保存到文件

        Args:
            filepath: 保存路径
            format: 图片格式

        Returns:
            文件绝对路径
        """
        img_bytes = self.screenshot(format)

        file_path = Path(filepath)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'wb') as f:
            f.write(img_bytes)

        logger.info(f"截图已保存: {file_path}")
        return str(file_path.absolute())

    def screenshot_to_pil(self) -> Image.Image:
        """截图并返回 PIL Image 对象"""
        img_bytes = self.screenshot('png')
        return Image.open(BytesIO(img_bytes))

    def get_cached_screenshot(self) -> Optional[bytes]:
        """获取缓存的截图"""
        return self._screenshot_cache

    # ==================== 截图流（实时截图） ====================

    def start_stream(self, interval: float = 2.0,
                     callback: Optional[Callable] = None):
        """
        开始截图流

        Args:
            interval: 截图间隔（秒）
            callback: 回调函数，参数为 base64 图片字符串
        """
        if self._streaming:
            logger.warning("截图流已在运行")
            return

        self._stream_interval = interval

        if callback:
            self._stream_callbacks.append(callback)

        self._streaming = True
        self._stream_thread = threading.Thread(target=self._stream_loop,
                                               daemon=True)
        self._stream_thread.start()
        logger.info(f"截图流已启动，间隔: {interval}s")

    def _stream_loop(self):
        """截图流循环"""
        while self._streaming:
            try:
                if self.is_connected:
                    b64 = self.screenshot_to_base64()
                    for cb in self._stream_callbacks:
                        try:
                            cb(b64)
                        except Exception as e:
                            logger.error(f"截图流回调异常: {e}")
                else:
                    for cb in self._stream_callbacks:
                        try:
                            cb(None)
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"截图流异常: {e}")

            time.sleep(self._stream_interval)

    def stop_stream(self):
        """停止截图流"""
        self._streaming = False
        if self._stream_thread:
            self._stream_thread.join(timeout=3)
            self._stream_thread = None
        self._stream_callbacks.clear()
        logger.info("截图流已停止")

    def is_streaming(self) -> bool:
        """是否正在截图流"""
        return self._streaming

    # ==================== 操作动作 ====================

    def click(self, x: int, y: int):
        """
        点击屏幕

        Args:
            x: X 坐标
            y: Y 坐标
        """
        device = self._get_device()
        device.click(x, y)
        logger.debug(f"点击: ({x}, {y})")

    def long_click(self, x: int, y: int, duration: float = 1.0):
        """
        长按

        Args:
            x: X 坐标
            y: Y 坐标
            duration: 按住时长（秒）
        """
        device = self._get_device()
        device.long_click(x, y, duration)
        logger.debug(f"长按: ({x}, {y}) {duration}s")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        """
        滑动

        Args:
            x1, y1: 起始坐标
            x2, y2: 结束坐标
            duration: 滑动时长（秒）
        """
        device = self._get_device()
        device.swipe(x1, y1, x2, y2, duration)
        logger.debug(f"滑动: ({x1},{y1}) -> ({x2},{y2})")

    def swipe_points(self, points: List[Tuple[int, int]],
                     duration: float = 0.5):
        """
        多点滑动（复杂路径）

        Args:
            points: 坐标点列表 [(x1,y1), (x2,y2), ...]
            duration: 总时长
        """
        device = self._get_device()
        device.swipe_points(points, duration)

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        """拖拽（同滑动）"""
        self.swipe(x1, y1, x2, y2, duration)

    def input_text(self, text: str):
        """输入文本"""
        device = self._get_device()
        device.send_keys(text)
        logger.debug(f"输入文本: {text}")

    def press_key(self, key: str):
        """
        按键

        Args:
            key: 按键名称，如 'home', 'back', 'enter', 'delete'
        """
        device = self._get_device()
        device.press(key)
        logger.debug(f"按键: {key}")

    def press_home(self):
        """按 Home 键"""
        self.press_key('home')

    def press_back(self):
        """按返回键"""
        self.press_key('back')

    def press_enter(self):
        """按回车键"""
        self.press_key('enter')

    # ==================== 应用管理 ====================

    def start_app(self, package_name: str):
        """启动应用"""
        device = self._get_device()
        device.app_start(package_name)
        logger.info(f"启动应用: {package_name}")

    def stop_app(self, package_name: str):
        """停止应用"""
        device = self._get_device()
        device.app_stop(package_name)
        logger.info(f"停止应用: {package_name}")

    def clear_app(self, package_name: str):
        """清除应用数据"""
        device = self._get_device()
        device.app_clear(package_name)
        logger.info(f"清除应用数据: {package_name}")

    def get_current_app(self) -> Dict[str, str]:
        """获取当前前台应用"""
        device = self._get_device()
        info = device.app_current()
        return {
            'package': info.get('package', ''),
            'activity': info.get('activity', ''),
            'pid': info.get('pid', 0),
        }

    def list_installed_apps(self) -> List[str]:
        """列出已安装应用"""
        device = self._get_device()
        return device.app_list()

    # ==================== UI 交互 ====================

    def find_element(self,
                     selector: Dict[str, Any],
                     timeout: float = 10) -> Optional[u2.xpath.XMLElement]:
        """
        查找UI元素

        Args:
            selector: 选择器，如 {'text': '设置', 'className': 'android.widget.TextView'}
            timeout: 超时时间

        Returns:
            XMLElement 或 None
        """
        device = self._get_device()

        try:
            if 'text' in selector:
                element = device(text=selector['text'])
            elif 'resourceId' in selector:
                element = device(resourceId=selector['resourceId'])
            elif 'className' in selector:
                element = device(className=selector['className'])
            elif 'xpath' in selector:
                element = device.xpath(selector['xpath'])
            else:
                raise ValueError("不支持的选择器类型")

            if element.exists(timeout=timeout):
                return element
            return None

        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return None

    def wait_for_element(self,
                         selector: Dict[str, Any],
                         timeout: float = 30) -> Optional[u2.xpath.XMLElement]:
        """等待元素出现"""
        return self.find_element(selector, timeout)

    def element_exists(self, selector: Dict[str, Any]) -> bool:
        """检查元素是否存在"""
        return self.find_element(selector, timeout=2) is not None

    def dump_hierarchy(self) -> str:
        """获取UI层级XML"""
        device = self._get_device()
        return device.dump_hierarchy()

    # ==================== 辅助方法 ====================

    def _get_device(self) -> u2.Device:
        """获取设备对象，未连接则抛出异常"""
        if not self.is_connected:
            raise DeviceConnectionError("设备未连接，请先调用 connect()")
        return self._device

    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        device = self._get_device()
        return device.info['displayWidth'], device.info['displayHeight']

    def get_device_settings(self) -> Dict[str, Any]:
        """获取设备配置"""
        device = self._get_device()
        return {
            'screenOn': device.info.get('screenOn', False),
            'currentPackageName': device.info.get('currentPackageName', ''),
            'displayRotation': device.info.get('displayRotation', 0),
        }

    def wake_up(self):
        """唤醒设备"""
        device = self._get_device()
        device.screen_on()

    def sleep(self):
        """设备休眠"""
        device = self._get_device()
        device.screen_off()

    def is_screen_on(self) -> bool:
        """检查屏幕是否亮着"""
        device = self._get_device()
        return device.info.get('screenOn', False)


# ==================== 全局单例 ====================
_device_service_instance: Optional[DeviceService] = None


def get_device_service() -> DeviceService:
    """获取设备服务单例"""
    global _device_service_instance
    if _device_service_instance is None:
        _device_service_instance = DeviceService()
        return _device_service_instance
    else:
        return _device_service_instance


if __name__ == '__main__':
    d = DeviceService()
    d.connect()
    d.start_app("com.moefantasy.clover")
    # manager = ADBManager()
    # available = manager.get_available_devices()
    # d.connect(available[0].connection_serial)
    # print("\n")
    # print(d.is_screen_on())
