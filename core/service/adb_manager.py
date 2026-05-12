import psutil
from adbutils import adb, AdbTimeout


class EmulatorAdbScanner:
    def __init__(self, keyword="dnplayer"):
        """
        :param keyword: 模拟器关键字 (dnplayer, MEmu, Nox, HD-Player)
        """
        self.keyword = keyword.lower()

    def _find_potential_ports(self):
        """扫描进程监听的 127.0.0.1 端口"""
        ports = set()
        for proc in psutil.process_iter(['name']):
            try:
                if self.keyword in proc.info['name'].lower():
                    for conn in proc.connections(kind='inet'):
                        if conn.status == 'LISTEN' and conn.laddr.ip == '127.0.0.1':
                            # 模拟器 ADB 端口范围通常在此区间
                            if 5000 <= conn.laddr.port <= 65535:
                                ports.add(conn.laddr.port)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return ports

    def get_devices_data(self):
        """连接设备并使用 adbutils 提取元数据"""
        ports = self._find_potential_ports()
        results = []

        for port in ports:
            addr = f"127.0.0.1:{port}"
            try:
                # 1. 尝试连接设备
                adb.connect(addr)
                device = adb.device(serial=addr)

                # 2. 获取元数据
                # window_size 返回一个命名元组，如 (width=1080, height=1920)
                size = device.window_size()

                # 获取 DPI (通过 shell 执行获取 prop)
                density = device.shell("wm density")
                dpi = density.split(':')[
                    -1].strip() if ":" in density else "Unknown"

                # 获取更多系统信息
                prop = device.prop

                results.append({
                    "serial": addr,
                    "resolution": f"{size[0]}x{size[1]}",
                    "dpi": dpi,
                    "model": prop.get("ro.product.model", "Unknown"),
                    "sdk": prop.get("ro.build.version.sdk", "Unknown"),
                    "brand": prop.get("ro.product.brand", "Unknown")
                })
            except Exception as e:
                # 端口可能不是 ADB 服务，直接跳过
                continue

        return results


# --- 使用示例 ---
if __name__ == "__main__":
    # 实例化并扫描
    scanner = EmulatorAdbScanner(keyword="mumu")  # 雷电
    devices = scanner.get_devices_data()

    if not devices:
        print("未发现运行中的模拟器或 ADB 连接失败")
    else:
        print(f"{'Serial':<20} | {'Resolution':<12} | {'DPI':<6} | {'Model'}")
        print("-" * 65)
        for d in devices:
            print(
                f"{d['serial']:<20} | {d['resolution']:<12} | {d['dpi']:<6} | {d['model']}")
