
from pathlib import Path

# 获取当前工作目录
current_dir = Path.cwd()

def template_path():
    return current_dir/"templates"

def static_path():
    return current_dir/"frontend"
