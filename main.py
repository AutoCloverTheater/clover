from core.api.app import main
import argparse

from core.config import Config

if __name__ == '__main__':
    # 1. 创建参数解析器
    parser = argparse.ArgumentParser(description="Clover 桌面端后台服务")

    # 2. 添加 -p / --port 参数
    # type=int 会自动把输入的字符串转为整数，如果输入的不是数字会直接报错提示
    # default=8088 设置了缺省值
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8088,
        help="指定服务启动的端口号 (默认: 8088)",
    )

    # 3. 解析命令行参数
    args = parser.parse_args()

    # 4. 获取解析后的端口值
    port = args.port

    Config.PORT = port
    main()
