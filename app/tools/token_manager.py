import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class MiCloudTokenManager:
    """小米云服务Token管理器"""
    
    def __init__(self):
        self.token_file = Path("./data/tokens/micloud_token.json")
        self.last_valid_token_file = Path("./data/tokens/last_valid_token.json")
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Token状态
        self.cookies: Dict[str, str] = {}
        self.last_check_time: Optional[datetime] = None
        
        # 加载初始token
        self._load_initial_token()
        
    def _load_initial_token(self):
        """加载初始token配置"""
        try:
            # 先尝试从本地文件加载
            if self.token_file.exists():
                with open(self.token_file, 'r') as f:
                    self.cookies = json.load(f)
                    if self._validate_token(self.cookies):
                        return
                        
            # 如果token文件无效，尝试从last_valid_token加载
            if self.last_valid_token_file.exists():
                with open(self.last_valid_token_file, 'r') as f:
                    self.cookies = json.load(f)
                    if self._validate_token(self.cookies):
                        self._save_token()
                        return
                        
            # 如果本地文件都无效，尝试从配置加载
            config_cookies = settings.get_micloud_cookies()
            if self._validate_token(config_cookies):
                self.cookies = config_cookies
                self._save_token()
                return
                        
            raise ValueError("无法加载有效的token，请先获取有效的token")
            
        except Exception as e:
            logger.error(f"加载token失败: {str(e)}")
            raise
            
    def _validate_token(self, token_data: Dict[str, str]) -> bool:
        """验证token是否有效"""
        required_fields = {
            "serviceToken",
            "userId",
            "i.mi.com_slh"
        }
        return all(field in token_data for field in required_fields)
        
    def _save_token(self):
        """保存token到本地文件"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(self.cookies, f, indent=2)
                
            # 如果token有效，同时保存到last_valid_token
            if self._validate_token(self.cookies):
                with open(self.last_valid_token_file, 'w') as f:
                    json.dump(self.cookies, f, indent=2)
                    
        except Exception as e:
            logger.error(f"保存token失败: {str(e)}")
            raise
            
    @property
    def is_healthy(self) -> bool:
        """检查token管理器是否健康"""
        try:
            if not self.token_file.exists():
                return False
                
            with open(self.token_file, 'r') as f:
                current_token = json.load(f)
                return self._validate_token(current_token)
                
        except Exception:
            return False
            
    def get_current_token(self) -> Dict[str, str]:
        """获取当前有效的token"""
        if not self.is_healthy:
            raise ValueError("token管理器状态异常")
            
        with open(self.token_file, 'r') as f:
            current_token = json.load(f)
            
        if not self._validate_token(current_token):
            raise ValueError("当前token无效")
            
        return current_token.copy()

# 创建全局token管理器实例
token_manager = MiCloudTokenManager()

async def get_token() -> Dict[str, str]:
    """获取当前有效的token"""
    return token_manager.get_current_token() 