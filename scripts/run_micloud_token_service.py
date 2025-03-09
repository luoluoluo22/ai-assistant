import sys
import os
import threading
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 加载环境变量
env_path = project_root / '.env'
load_dotenv(env_path)

from app.services import MiCloudTokenService

def main():
    # 检查必要的环境变量
    if not os.getenv('MICLOUD_COOKIE'):
        print("错误: 环境变量 MICLOUD_COOKIE 未设置。请在 .env 文件中设置。")
        sys.exit(1)
    
    # 创建服务实例
    token_service = MiCloudTokenService()
    
    try:
        # 启动token刷新服务
        print("启动小米云服务Token刷新服务...")
        token_service.start_token_refresh_service()
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"服务发生错误: {e}")

if __name__ == "__main__":
    main() 