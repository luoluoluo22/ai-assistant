import requests
import json
import time
import logging
import os
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/micloud_token.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('MiCloudToken')

class MiCloudTokenService:
    def __init__(self):
        self.token_file = Path('data/micloud_token.json')
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 从环境变量获取初始cookie
        self.initial_cookie = self._clean_cookie_string(os.getenv('MICLOUD_COOKIE', ''))
        if not self.initial_cookie:
            logger.warning("No initial cookie found in environment variables")
        
        self.headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'referer': 'https://i.mi.com/',
            'origin': 'https://i.mi.com',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        }
        
        self.base_url = 'https://i.mi.com/status/lite/setting'
        self.current_token = self._extract_token_from_cookie(self.initial_cookie) if self.initial_cookie else None
        
        if self.current_token:
            self._save_token(self.current_token)
            # 设置完整的cookie
            self.headers['cookie'] = self.initial_cookie
        else:
            self._load_token()
            if self.current_token:
                self.headers['cookie'] = f'serviceToken={self.current_token}'

    def _clean_cookie_string(self, cookie_str):
        """清理cookie字符串，移除多余的引号和空格"""
        if not cookie_str:
            return ''
        # 移除开头和结尾的引号和空格
        cookie_str = cookie_str.strip()
        if cookie_str.startswith(("'", '"')):
            cookie_str = cookie_str[1:]
        if cookie_str.endswith(("'", '"')):
            cookie_str = cookie_str[:-1]
        return cookie_str

    def _extract_token_from_cookie(self, cookie_str):
        """从cookie字符串中提取serviceToken"""
        if not cookie_str:
            return None
        
        cookies = cookie_str.split(';')
        for cookie in cookies:
            cookie = cookie.strip()
            if 'serviceToken=' in cookie:
                return cookie.split('serviceToken=', 1)[1].strip()
        return None

    def _load_token(self):
        """从文件加载token"""
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    self.current_token = data.get('serviceToken')
                    logger.info("Token loaded from file successfully")
            except Exception as e:
                logger.error(f"Error loading token from file: {e}")

    def _save_token(self, token_data):
        """保存token到文件"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump({
                    'serviceToken': token_data,
                    'updateTime': datetime.now().isoformat()
                }, f, indent=2)
            logger.info("Token saved to file successfully")
        except Exception as e:
            logger.error(f"Error saving token to file: {e}")

    def _extract_service_token(self, cookies):
        """从响应cookies中提取serviceToken"""
        for cookie in cookies:
            if cookie.name == 'serviceToken':
                return cookie.value
        return None

    def refresh_token(self):
        """刷新token"""
        try:
            params = {
                'ts': int(time.time() * 1000),
                'type': 'AutoRenewal',
                'inactiveTime': 10
            }

            # 记录当前cookie
            logger.info("当前cookie:")
            if self.initial_cookie:
                logger.info(f"初始cookie: {self.initial_cookie}")
            if self.current_token:
                logger.info(f"当前token: {self.current_token}")
            logger.info(f"完整headers: {json.dumps(self.headers, ensure_ascii=False, indent=2)}")

            # 使用完整的初始 cookie
            if self.initial_cookie:
                self.headers['cookie'] = self.initial_cookie

            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                allow_redirects=False
            )

            # 记录响应信息
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应cookies: {[f'{c.name}={c.value}' for c in response.cookies]}")
            logger.info(f"响应头: {json.dumps(dict(response.headers), ensure_ascii=False, indent=2)}")
            
            # 记录响应内容
            try:
                response_content = response.json()
                logger.info(f"响应内容: {json.dumps(response_content, ensure_ascii=False, indent=2)}")
            except:
                logger.info(f"响应内容: {response.text[:1000]}")  # 限制长度避免日志过大

            if response.status_code == 200:
                new_token = None
                for cookie in response.cookies:
                    if cookie.name == 'serviceToken':
                        new_token = cookie.value
                        logger.info(f"获取到新token: {new_token}")
                        break

                if new_token:
                    self.current_token = new_token
                    self._save_token(new_token)
                    # 更新 cookie 时保持其他字段不变
                    if self.initial_cookie:
                        cookies = self.initial_cookie.split(';')
                        updated_cookies = []
                        for cookie in cookies:
                            if 'serviceToken=' not in cookie:
                                updated_cookies.append(cookie.strip())
                        updated_cookies.append(f'serviceToken={new_token}')
                        self.headers['cookie'] = '; '.join(updated_cookies)
                        logger.info(f"更新后的完整cookie: {self.headers['cookie']}")
                    else:
                        self.headers['cookie'] = f'serviceToken={new_token}'
                    logger.info("Token刷新成功")
                    return new_token
                else:
                    logger.warning("响应cookies中未找到serviceToken")
            else:
                logger.error(f"刷新token失败. 状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")

        except Exception as e:
            logger.error(f"刷新token时发生错误: {e}")

        return None

    def start_token_refresh_service(self, interval=120):  # 2分钟 = 120秒
        """启动定时刷新服务"""
        logger.info(f"Starting token refresh service with {interval} seconds interval")
        while True:
            try:
                self.refresh_token()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in token refresh service: {e}")
                time.sleep(60)  # 发生错误时等待1分钟后重试

    def get_current_token(self):
        """获取当前token"""
        return self.current_token 