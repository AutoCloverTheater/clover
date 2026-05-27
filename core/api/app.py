import os
import sys
import json
import logging
import webbrowser
import threading
import time
from pathlib import Path

from core.service.device_service import DeviceService

# 将 backend 目录添加到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask, send_from_directory, jsonify, request, abort
from flask_cors import CORS
from core.config import Config
from flasgger import Swagger

# 初始化配置
Config.ensure_dirs()

# 配置日志
log_file = Config.LOGS_DIR / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def create_app():
    """创建 Flask 应用"""
    app = Flask(
        __name__,
        # static_folder=str(Config.STATIC_DIR),
        static_url_path='',
        template_folder=str(Config.TEMPLATES_DIR)
    )
    CORS(app)

    app.config['SWAGGER'] = {
        'title': '四叶草小助手',
        'uiversion': 3,
        'specs_route': '/docs/'  # 文档页面路径，默认 /apidocs/
    }
    Swagger(app)
    # 存储配置到 app.config
    app.config.from_object(Config)

    # ==================== 注册 API 蓝图 ====================
    from core.api.adb_api import adb_bp
    from core.api.roi_api import roi_bp
    # from api.roi_api import roi_bp
    # from api.task_api import task_bp
    # from api.settings_api import settings_bp
    #
    app.register_blueprint(adb_bp, url_prefix='/api/adb')
    # app.register_blueprint(screenshot_bp, url_prefix='/api/screenshot')
    app.register_blueprint(roi_bp, url_prefix='/api/roi')
    # app.register_blueprint(task_bp, url_prefix='/api/tasks')
    # app.register_blueprint(settings_bp, url_prefix='/api/settings')

    # ==================== 静态文件路由 ====================
    # @app.route('/')
    # def index():
    #     """主页"""
    #     index_file = Config.STATIC_DIR / 'index.html'
    #     if index_file.exists():
    #         return send_from_directory(str(Config.STATIC_DIR), 'index.html')
    #     return '<h1>前端文件未找到</h1><p>请将 index.html 放在 frontend 目录下</p>', 404

    @app.route('/<path:filename>')
    def serve_static(filename):
        """托管静态资源"""
        file_path = Config.STATIC_DIR / filename
        if file_path.exists() and file_path.is_file():
            return send_from_directory(str(Config.STATIC_DIR), filename)
        return abort(404)

    # ==================== 健康检查 ====================
    @app.route('/api/health')
    def health():
        return jsonify({
            'status': 'ok',
            'version': Config.APP_VERSION,
            'timestamp': time.time(),
        })

    # ==================== 错误处理 ====================
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not Found', 'message': str(e)}), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

    logger.info(f"Flask app created, static dir: {Config.STATIC_DIR}")
    return app


def open_browser(port):
    """延迟打开浏览器"""
    time.sleep(1.5)
    url = f'http://127.0.0.1:{port}'
    logger.info(f"Opening browser: {url}")
    # webbrowser.open(url)

DeviceX = DeviceService()

def main():
    """主入口"""
    app = create_app()

    # 自动打开浏览器
    if not Config.DEBUG:
        threading.Thread(target=open_browser, args=(Config.PORT,),
                         daemon=True).start()
    # 单例adb

    logger.info(f"Starting {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info(f"Server: http://{Config.HOST}:{Config.PORT}")
    logger.info(f"Data directory: {Config.USER_DATA_DIR}")

    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        use_reloader=False,
    )


if __name__ == '__main__':
    main()
