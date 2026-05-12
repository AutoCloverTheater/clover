import adbutils
from typing import List, Dict


class DeviceScanner:
    """
    基于 adbutils 的跨平台设备管理类
    支持获取 Serial、分辨率、DPI 及模拟器识别
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5037):
        self.adb = adbutils.AdbClient(host=host, port=port)

    def get_detailed_devices(self) -> List[Dict]:
        """
        获取所有在线设备的详细信息：Serial, 分辨率, DPI, 状态等
        """
        detailed_list = []

        for device in self.adb.device_list():
            # 仅对在线(device)状态的设备尝试获取详细参数，避免 offline 阻塞
            info = {
                "serial": device.serial,
                "state": device.info.get('state'),
                "resolution": "N/A",
                "dpi": "N/A",
                "is_emulator": self._check_if_emulator(device.serial)
            }

            if info["state"] == "device":
                try:
                    # 1. 获取分辨率 (返回为 Size 对象，如 Size(width=1080, height=1920))
                    size = device.window_size()
                    info["resolution"] = f"{size.width}x{size.height}"

                    # 2. 获取 DPI (从系统属性中读取)
                    # 常见的属性有 ro.sf.lcd_density 或 qemu.sf.lcd_density
                    dpi = device.prop.get(
                        "ro.sf.lcd_density") or device.prop.get(
                        "qemu.sf.lcd_density")
                    info["dpi"] = dpi if dpi else "unknown"
                except Exception as e:
                    info["resolution"] = f"Error: {str(e)}"

            detailed_list.append(info)

        return detailed_list

    def _check_if_emulator(self, serial: str) -> bool:
        """识别是否为模拟器"""
        features = ["127.0.0.1", "emulator-", "localhost", "192.168.56"]
        return any(f in serial.lower() for f in features)


# --- 调用示例 ---
if __name__ == "__main__":
    scanner = DeviceScanner()
    devices = scanner.get_detailed_devices()

    print(f"{'Serial号':<20} {'状态':<10} {'分辨率':<15} {'DPI':<10} {'类型'}")
    print("-" * 70)

    for d in devices:
        device_type = "模拟器" if d['is_emulator'] else "真机"
        print(
            f"{d['serial']:<20} {d['state']:<10} {d['resolution']:<15} {d['dpi']:<10} {device_type}")
