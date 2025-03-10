import logging
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('MiCloudToken')

class MiCloudTokenService:
    """小米云服务Token管理服务"""
    
    def __init__(self):
        self.token_file = Path('data/micloud_token.json')
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 从配置加载初始cookies
        self.cookies = self._load_cookies_from_config()
        if not self.cookies:
            raise ValueError("未找到有效的cookies配置")
            
        logger.info("成功从配置加载cookies")
        
    def _load_cookies_from_config(self) -> Dict[str, str]:
        """从配置加载cookies"""
        try:
            # 从配置获取cookies
            cookie_str = settings.MICLOUD_COOKIE
            if not cookie_str:
                logger.error("配置中未设置 MICLOUD_COOKIE")
                return {}
                
            # 去除可能存在的引号
            cookie_str = cookie_str.strip("'\"")
                
            # 解析cookie字符串为字典
            cookies = {}
            for item in cookie_str.split(';'):
                if '=' in item:
                    key, value = item.strip().split('=', 1)
                    cookies[key.strip()] = value.strip()
                    
            # 验证必要的cookie字段
            required_fields = {'serviceToken', 'userId', 'i.mi.com_slh'}
            missing_fields = required_fields - set(cookies.keys())
            if missing_fields:
                logger.error(f"缺少必要的cookie字段: {missing_fields}")
                return {}
                
            return cookies
            
        except Exception as e:
            logger.error(f"解析配置cookies失败: {str(e)}")
            return {}
            
    def _save_cookies(self, cookies: Dict[str, str]):
        """保存cookies到文件，供其他服务使用"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(cookies, f, indent=2)
        except Exception as e:
            logger.error(f"保存cookies失败: {str(e)}")
            
    async def refresh_token(self):
        """刷新token"""
        try:
            # 显示当前token的前20个字符
            current_token = self.cookies.get('serviceToken', '')[:20] + '...'
            logger.info(f"当前Token: {current_token}")
            
            headers = {
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "referer": "https://i.mi.com/gallery/h5",
                "origin": "https://i.mi.com",
                "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Microsoft Edge";v="134"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "priority": "u=1, i",
                ":authority": "i.mi.com",
                ":method": "GET",
                ":scheme": "https",
                "cookie": "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
            }
            
            async with aiohttp.ClientSession() as session:
                url = "https://i.mi.com/status/lite/setting"
                params = {
                    "ts": str(int(datetime.now().timestamp() * 1000)),
                    "type": "AutoRenewal",
                    "inactiveTime": "10"
                }
                
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        # 获取新的serviceToken
                        for cookie in response.cookies.values():
                            if cookie.key == 'serviceToken' and cookie.value:
                                new_token = cookie.value[:20] + '...'
                                logger.info(f"获取新Token: {new_token}")
                                self.cookies[cookie.key] = cookie.value
                                
                        # 保存完整的cookies
                        self._save_cookies(self.cookies)
                        logger.info("Token刷新成功")
                        return True
                    else:
                        logger.error(f"刷新token失败. 状态码: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"刷新token失败: {str(e)}")
            return False
            
    async def run(self, interval: int = 120):
        """运行token刷新服务
        
        Args:
            interval: 刷新间隔（秒）
        """
        logger.info(f"Token刷新服务已启动，刷新间隔: {interval}秒")
        
        while True:
            try:
                await self.refresh_token()
            except Exception as e:
                logger.error(f"Token刷新出错: {str(e)}")
                
            await asyncio.sleep(interval)

def main():
    """主函数"""
    service = MiCloudTokenService()
    
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"服务异常退出: {str(e)}")

if __name__ == "__main__":
    main() 