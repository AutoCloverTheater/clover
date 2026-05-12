import sys
import psutil
from adbutils import adb


class AdbManager:
    def __init__(self):
        # 1. 适配列表：仅包含名称和进程特征
        self.adapters = {
            "win32": [
                {"name": "雷电", "process": "dnplayer"},
                {"name": "MuMu", "process": "MuMu"},
                {"name": "蓝叠", "process": "BlueStacks"}
            ],
            "darwin": [  # macOS
                {"name": "蓝叠", "process": "BlueStacks"},
                {"name": "MuMu", "process": "MuMu"}
            ]
        }
        self.current_platform = sys.platform

    def get_all_devices(self):
        """循环执行适配器逻辑并附加结果"""
        all_devices = []
        seen_ports = set()

        # 获取当前平台的适配清单
        platform_adapters = self.adapters.get(self.current_platform, [])

        for adapter in platform_adapters:
            # 获取该适配器对应的所有端口
            ports = self._scan_ports_by_name(adapter["process"])

            for port in ports:
                if port in seen_ports:
                    continue

                # 提取数据并附加到列表
                device_info = self._get_device_data(port, adapter["name"])
                if device_info:
                    all_devices.append(device_info)
                    seen_ports.add(port)

        return all_devices

    def _scan_ports_by_name(self, process_name):
        """核心扫描逻辑：根据进程名获取 LISTEN 端口"""
        ports = set()
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    for conn in proc.net_connections(kind='inet'):
                        if conn.status == 'LISTEN':
                            ports.add(conn.laddr.port)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return ports

    def _get_device_data(self, port, type_name):
        """使用 adbutils 提取元数据"""
        serial = f"127.0.0.1:{port}"
        try:
            adb.connect(serial, timeout=2)
            device = adb.device(serial=serial)

            w, h = device.window_size()
            density_str = device.shell("wm density")
            dpi = "".join(filter(str.isdigit, density_str.split(':')[-1]))

            return {
                "type": type_name,
                "emulator": type_name,
                "serial": serial,
                "resolution": f"{w}x{h}",
                "dpi": dpi or "Unknown",
                "model": device.prop.get("ro.product.model", "Unknown")
            }
        except Exception:
            return None


# --- 调用演示 ---
if __name__ == "__main__":
    scanner = AdbManager()
    devices = scanner.get_all_devices()

    print(f"检测到 {len(devices)} 个设备：")
    for d in devices:
        print(
            f"[{d['type']}] {d['serial']} - {d['resolution']} - DPI:{d['dpi']} - {d['model']}")
