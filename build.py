"""
PyInstaller 打包脚本
使用方法: python build.py
"""
import os
import sys
import subprocess
from pathlib import Path


def build():
    """执行打包"""
    project_root = Path(__file__).resolve().parent

    # 打包参数
    pyinstaller_args = [
        'pyinstaller',
        '--onefile',  # 单文件模式
        '--name', 'ADB_Tool',  # 输出名称
        '--clean',  # 清理临时文件
        '--noconfirm',  # 不询问确认

        # 添加数据文件
        '--add-data', f'frontend{os.pathsep}frontend',

        # 隐藏导入（确保Flask相关模块被打包）
        '--hidden-import', 'flask',
        '--hidden-import', 'flask_cors',
        '--hidden-import', 'PIL',
        '--hidden-import', 'PIL.Image',

        # 排除不需要的模块（减小体积）
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'numpy',
        '--exclude-module', 'pandas',
        '--exclude-module', 'scipy',
        '--exclude-module', 'tkinter',

        # macOS 特定选项
        # '--windowed',                       # macOS: 不显示控制台
        # '--osx-bundle-identifier', 'com.yourcompany.adbtool',
        # pyinstaller --clean --add-data "templates;templates" --add-data "static;static" app.py
        # Windows 特定选项
        # '--icon', 'icon.ico',              # 图标

        # 入口文件
        str(project_root / 'backend' / 'app.py'),
    ]

    # Windows 上添加 .exe 后缀
    if sys.platform == 'win32':
        pyinstaller_args.insert(3, '--console')  # Windows 显示控制台（调试用）

    print("=" * 60)
    print("开始打包...")
    print("=" * 60)
    print(f"项目目录: {project_root}")
    print(f"命令: {' '.join(pyinstaller_args)}")
    print()

    result = subprocess.run(pyinstaller_args, cwd=str(project_root))

    if result.returncode == 0:
        output_dir = project_root / 'dist'
        print("\n" + "=" * 60)
        print("打包成功!")
        print(f"输出目录: {output_dir}")
        if sys.platform == 'win32':
            print(f"可执行文件: {output_dir / 'ADB_Tool.exe'}")
        else:
            print(f"可执行文件: {output_dir / 'ADB_Tool'}")
        print("=" * 60)
    else:
        print("\n打包失败，请检查错误信息")
        sys.exit(1)


if __name__ == '__main__':
    build()
