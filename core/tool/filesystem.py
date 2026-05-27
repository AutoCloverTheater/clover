import os
import json
from pathlib import Path

# 获取当前工作目录
current_dir = Path.cwd()

def template_path():
    return current_dir/"templates"

def static_path():
    return current_dir/"frontend"


def ensure_dir(path):
    """
    确保目录存在，如果不存在则创建（包括父目录）

    参数:
        path (str): 目录路径

    返回:
        bool: 成功返回True，失败返回False
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except OSError as e:
            print(f"无法创建目录 {path}: {e}")
            return False
    return os.path.isdir(path)


# 处理文件路径的便捷函数
def ensure_file_dir(filepath):
    """
    确保文件所在的目录存在，如果不存在则创建

    参数:
        filepath (str): 文件路径

    返回:
        bool: 成功返回True，失败返回False
    """
    directory = os.path.dirname(filepath)
    if directory:  # 如果文件不在当前目录
        return ensure_dir(directory)
    return True


def write_json_file(filepath, data, indent=4, ensure_ascii=False):
    """
    将数据写入JSON文件

    参数:
        filepath (str): 文件路径
        data: 要写入的数据（dict, list等）
        indent (int): 缩进空格数，默认4
        ensure_ascii (bool): 是否转义非ASCII字符，默认False（保留中文）
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
        print(f"成功写入文件: {filepath}")
        return True
    except Exception as e:
        print(f"写入失败: {e}")
        return False
