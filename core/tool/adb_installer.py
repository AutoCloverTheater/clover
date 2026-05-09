"""
ADB 自动下载安装模块
下载并解压 ADB 到项目工作目录的 bin/adb 下
"""
import os
import sys
import stat
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Optional
from core.config import Config

logger = logging.getLogger(__name__)


def get_adb_bin_dir() -> Path:
    """
    获取 ADB 存放目录

    Returns:
        bin 目录路径
    """
    # 获取当前文件所在目录，向上找到项目根目录
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent  # backend/services -> project root

    # 或者如果是在打包环境中
    # project_root = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else current_file.parent.parent


    bin_dir = Config.PWD / 'bin'
    return bin_dir


def get_adb_executable_path() -> Path:
    """
    获取 ADB 可执行文件路径

    Returns:
        ADB 可执行文件完整路径
    """
    bin_dir = get_adb_bin_dir()
    adb_name = 'adb.exe' if sys.platform == 'win32' else 'adb'
    return bin_dir / 'adb' / adb_name


def get_adb_download_url() -> tuple[str, str]:
    """
    根据平台获取 ADB 下载地址

    Returns:
        (下载URL, 文件名)
    """
    base_url = 'https://dl.google.com/android/repository/'

    if sys.platform == 'win32':
        return (
            f'{base_url}platform-tools-latest-windows.zip',
            'platform-tools-windows.zip'
        )
    elif sys.platform == 'darwin':
        # macOS 有两种架构
        import platform
        machine = platform.machine()
        if machine == 'arm64':
            return (
                f'{base_url}platform-tools-latest-darwin.zip',
                'platform-tools-darwin.zip'
            )
        else:
            return (
                f'{base_url}platform-tools-latest-darwin.zip',
                'platform-tools-darwin.zip'
            )
    else:
        return (
            f'{base_url}platform-tools-latest-linux.zip',
            'platform-tools-linux.zip'
        )


def is_adb_installed() -> bool:
    """
    检查 ADB 是否已安装在工作目录

    Returns:
        是否已安装
    """
    adb_path = get_adb_executable_path()
    return adb_path.exists()


def get_python_version() -> str:
    """获取 Python 版本"""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def check_ssl_support() -> bool:
    """检查 SSL 支持"""
    try:
        import ssl
        ssl.create_default_context()
        return True
    except Exception:
        return False


def download_file(url: str, save_path: Path,
                  show_progress: bool = True) -> bool:
    """
    下载文件（带进度显示）

    Args:
        url: 下载地址
        save_path: 保存路径
        show_progress: 是否显示进度

    Returns:
        是否下载成功
    """
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # 尝试使用 urllib（标准库）
    try:
        import urllib.request

        logger.info(f"下载: {url}")
        logger.info(f"保存到: {save_path}")

        def progress_hook(block_num, block_size, total_size):
            if show_progress and total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 / total_size)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)

                # 只在有明显进度变化时打印
                if block_num % 10 == 0 or percent >= 100:
                    print(
                        f"\r  下载进度: {percent:.0f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)",
                        end='', flush=True)

        urllib.request.urlretrieve(url, str(save_path),
                                   reporthook=progress_hook)

        if show_progress:
            print()  # 换行

        logger.info("下载完成")
        return True

    except Exception as e:
        logger.warning(f"urllib 下载失败: {e}")

        # 尝试使用 wget
        try:
            import subprocess
            result = subprocess.run(
                ['wget', '-O', str(save_path), url],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                logger.info("wget 下载完成")
                return True
        except Exception:
            pass

        # 尝试使用 curl
        try:
            import subprocess
            result = subprocess.run(
                ['curl', '-L', '-o', str(save_path), url],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                logger.info("curl 下载完成")
                return True
        except Exception:
            pass

        logger.error(f"所有下载方式均失败")
        return False


def verify_zip_file(zip_path: Path) -> bool:
    """
    验证 ZIP 文件完整性

    Args:
        zip_path: ZIP 文件路径

    Returns:
        是否完整
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 检查是否包含 adb
            file_list = zf.namelist()
            has_adb = any('adb' in name.lower() for name in file_list)

            if not has_adb:
                logger.error("ZIP 文件中未找到 ADB")
                return False

            # 测试 ZIP 完整性
            bad_file = zf.testzip()
            if bad_file:
                logger.error(f"ZIP 文件损坏: {bad_file}")
                return False

            logger.info(f"ZIP 验证通过，包含 {len(file_list)} 个文件")
            return True

    except zipfile.BadZipFile:
        logger.error("无效的 ZIP 文件")
        return False
    except Exception as e:
        logger.error(f"ZIP 验证失败: {e}")
        return False


def extract_zip_safe(zip_path: Path, extract_dir: Path) -> bool:
    """
    安全解压 ZIP 文件（防止路径遍历攻击）

    Args:
        zip_path: ZIP 文件路径
        extract_dir: 解压目录

    Returns:
        是否解压成功
    """
    try:
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 安全检查：防止路径遍历
            for member in zf.namelist():
                member_path = extract_dir / member
                # 确保解压路径在目标目录内
                if not str(member_path.resolve()).startswith(
                    str(extract_dir.resolve())):
                    logger.warning(f"跳过不安全路径: {member}")
                    continue

            # 解压
            zf.extractall(extract_dir)

        logger.info(f"解压完成: {extract_dir}")
        return True

    except Exception as e:
        logger.error(f"解压失败: {e}")
        return False


def set_executable_permissions(file_path: Path):
    """设置文件可执行权限（非 Windows）"""
    if sys.platform != 'win32':
        try:
            st = file_path.stat()
            file_path.chmod(
                st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            logger.debug(f"设置可执行权限: {file_path}")
        except Exception as e:
            logger.warning(f"设置权限失败: {e}")


def copy_adb_from_platform_tools(extract_dir: Path, target_dir: Path) -> bool:
    """
    从 platform-tools 目录复制 ADB 到目标目录

    Args:
        extract_dir: 解压后的 platform-tools 目录
        target_dir: 目标 bin/adb 目录

    Returns:
        是否复制成功
    """
    adb_name = 'adb.exe' if sys.platform == 'win32' else 'adb'

    # 查找 ADB
    adb_src = extract_dir / adb_name

    # 如果不在根目录，可能在里面
    if not adb_src.exists():
        # 查找所有可能的路径
        for root, dirs, files in os.walk(extract_dir):
            if adb_name in files:
                adb_src = Path(root) / adb_name
                break

    if not adb_src.exists():
        logger.error(f"未找到 ADB 文件: {adb_name}")
        return False

    # 复制到目标目录
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / adb_name

    shutil.copy2(adb_src, target_path)
    set_executable_permissions(target_path)

    logger.info(f"ADB 已复制到: {target_path}")
    return True


def install_adb(force: bool = False) -> Optional[Path]:
    """
    自动下载并安装 ADB 到 bin/adb 目录

    流程:
    1. 检查是否已安装
    2. 下载 platform-tools ZIP
    3. 验证 ZIP 完整性
    4. 解压到临时目录
    5. 复制 ADB 到 bin/adb
    6. 清理临时文件

    Args:
        force: 是否强制重新安装

    Returns:
        ADB 可执行文件路径，失败返回 None
    """
    adb_path = get_adb_executable_path()

    # 如果已安装且不强制重新安装
    if not force and is_adb_installed():
        logger.info(f"ADB 已安装: {adb_path}")

        # 检查是否可执行
        try:
            import subprocess
            result = subprocess.run(
                [str(adb_path), 'version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version_info = result.stdout.split('\n')[
                    0] if result.stdout else ''
                logger.info(f"ADB 可用: {version_info}")
                return adb_path
        except Exception:
            logger.warning("已安装的 ADB 不可用，将重新下载")

    print("\n" + "=" * 60)
    print("📦 安装 ADB Platform Tools")
    print("=" * 60)

    # 获取下载地址
    download_url, filename = get_adb_download_url()

    bin_dir = get_adb_bin_dir()
    temp_dir = bin_dir / 'temp'
    zip_path = temp_dir / filename
    extract_dir = temp_dir / 'platform-tools'

    # 清理旧的临时文件
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 下载
        print(f"\n🌍 平台: {sys.platform}")
        print(f"📥 下载地址: {download_url}")
        print(f"📁 临时目录: {temp_dir}")
        print()

        if not download_file(download_url, zip_path):
            print("\n❌ 下载失败")
            print("\n请手动下载 ADB:")
            print(f"  {download_url}")
            print(f"  解压后将 adb 放到: {get_adb_executable_path()}")
            return None

        # 验证
        print("\n🔍 验证文件完整性...")
        if not verify_zip_file(zip_path):
            print("❌ ZIP 文件验证失败")
            return None

        # 解压
        print("\n📦 解压中...")
        if not extract_zip_safe(zip_path, extract_dir):
            print("❌ 解压失败")
            return None

        # 复制 ADB
        target_dir = bin_dir / 'adb'
        print(f"\n📋 复制 ADB 到: {target_dir}")

        if not copy_adb_from_platform_tools(extract_dir, target_dir):
            print("❌ 复制失败")
            return None

        # 验证安装
        print("\n🔧 验证安装...")
        try:
            import subprocess
            result = subprocess.run(
                [str(get_adb_executable_path()), 'version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.split('\n')[
                    0] if result.stdout else 'ok'
                print(f"✅ ADB 安装成功: {version}")
                print(f"📁 路径: {get_adb_executable_path()}")

                # 添加环境变量提示
                if sys.platform == 'win32':
                    print(f"\n💡 添加到 PATH:")
                    print(f"   setx PATH \"%PATH%;{target_dir.absolute()}\"")
                else:
                    print(f"\n💡 添加到 PATH:")
                    print(f"   export PATH=\"$PATH:{target_dir.absolute()}\"")

                return get_adb_executable_path()
        except Exception as e:
            print(f"❌ 验证失败: {e}")
            return None

    except Exception as e:
        logger.error(f"安装 ADB 异常: {e}")
        print(f"\n❌ 安装失败: {e}")
        return None

    finally:
        # 清理临时文件
        print("\n🧹 清理临时文件...")
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        print("=" * 60 + "\n")


def get_or_install_adb() -> Path:
    """
    获取 ADB 路径，如果不存在则自动安装

    使用优先级:
    1. 系统 PATH 中的 adb
    2. 项目 bin/adb 中的 adb
    3. 自动下载安装到 bin/adb

    Returns:
        ADB 可执行文件路径

    Raises:
        RuntimeError: 无法获取 ADB
    """
    # 1. 检查系统 PATH
    system_adb = shutil.which('adb')
    if system_adb:
        logger.info(f"使用系统 ADB: {system_adb}")
        # 检查版本
        try:
            import subprocess
            result = subprocess.run(
                [system_adb, 'version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return Path(system_adb)
        except Exception:
            pass

    # 2. 检查项目本地
    local_adb = get_adb_executable_path()
    if local_adb.exists():
        try:
            import subprocess
            result = subprocess.run(
                [str(local_adb), 'version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info(f"使用本地 ADB: {local_adb}")
                return local_adb
        except Exception:
            pass

    # 3. 自动安装
    logger.info("ADB 未找到，开始自动安装...")
    installed_path = install_adb()

    if installed_path and installed_path.exists():
        return installed_path

    raise RuntimeError(
        "无法获取 ADB！\n"
        f"请手动下载并放置到: {get_adb_executable_path()}\n"
        "或安装 Android SDK Platform Tools 并添加到系统 PATH"
    )


def check_adb_update() -> bool:
    """
    检查 ADB 是否有更新

    Returns:
        是否有更新（需要手动处理）
    """
    try:
        # 这只是一个简单检查，实际更新需要对比版本号
        import urllib.request
        response = urllib.request.urlopen(
            'https://dl.google.com/android/repository/platform-tools-latest-windows.zip',
            timeout=5
        )
        return response.status == 200
    except Exception:
        return False


# ==================== 命令行入口 ====================
if __name__ == '__main__':
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    parser = argparse.ArgumentParser(description='ADB 自动安装工具')
    parser.add_argument('--force', '-f', action='store_true',
                        help='强制重新安装')
    parser.add_argument('--check', '-c', action='store_true',
                        help='仅检查是否已安装')
    parser.add_argument('--version', '-v', action='store_true',
                        help='显示 ADB 版本')

    args = parser.parse_args()

    if args.version:
        try:
            adb_path = get_or_install_adb()
            import subprocess

            result = subprocess.run(
                [str(adb_path), 'version'],
                capture_output=True, text=True, timeout=5
            )
            print(f"ADB 路径: {adb_path}")
            print(result.stdout)
        except Exception as e:
            print(f"获取 ADB 版本失败: {e}")

    elif args.check:
        if is_adb_installed():
            print(f"✅ ADB 已安装: {get_adb_executable_path()}")
        else:
            print("❌ ADB 未安装")

    else:
        result = install_adb(force=args.force)
        if result:
            print(f"\n✅ ADB 安装成功: {result}")
        else:
            print("\n❌ ADB 安装失败")
            sys.exit(1)
