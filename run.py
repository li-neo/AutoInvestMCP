"""
启动AutoInvestAI服务的脚本
"""
import os
import sys
import argparse
import subprocess

# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def install_dependencies():
    """安装项目依赖"""
    print("正在安装项目依赖...")
    requirements_path = os.path.join(ROOT_DIR, "requirements.txt")
    
    try:
        # 使用pip安装依赖
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
        print("依赖安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装依赖失败: {e}")
        return False


def start_server(host="0.0.0.0", port=8000):
    """启动MCP服务器
    
    Args:
        host: 服务主机地址
        port: 服务端口
    """
    print(f"正在启动AutoInvestAI服务，地址: {host}:{port}...")
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT_DIR
    
    # 服务器脚本路径
    server_path = os.path.join(ROOT_DIR, "src", "mcp_server.py")
    
    try:
        # 启动服务器
        subprocess.run([sys.executable, server_path, "--host", host, "--port", str(port)], env=env)
    except KeyboardInterrupt:
        print("\n服务已停止。")
    except Exception as e:
        print(f"启动服务失败: {e}")


def run_tests():
    """运行单元测试"""
    print("正在运行单元测试...")
    
    # 测试目录
    tests_dir = os.path.join(ROOT_DIR, "tests")
    
    try:
        # 运行所有测试
        subprocess.check_call([sys.executable, "-m", "unittest", "discover", tests_dir])
        print("所有测试通过！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"测试失败: {e}")
        return False


def start_client():
    """启动命令行客户端"""
    print("正在启动命令行客户端...")
    
    # 客户端脚本路径
    client_path = os.path.join(ROOT_DIR, "client.py")
    
    try:
        # 启动客户端
        subprocess.run([sys.executable, client_path])
    except KeyboardInterrupt:
        print("\n客户端已退出。")
    except Exception as e:
        print(f"启动客户端失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AutoInvestAI服务启动脚本")
    parser.add_argument("--install", action="store_true", help="安装依赖")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--client", action="store_true", help="启动命令行客户端")
    parser.add_argument("--host", default="0.0.0.0", help="服务主机地址")
    parser.add_argument("--port", type=int, default=8000, help="服务端口")
    
    args = parser.parse_args()
    
    # 安装依赖
    if args.install:
        if not install_dependencies():
            return
    
    # 运行测试
    if args.test:
        if not run_tests():
            return
    
    # 启动客户端
    if args.client:
        start_client()
        return
    
    # 启动服务器(默认操作)
    start_server(args.host, args.port)


if __name__ == "__main__":
    main()