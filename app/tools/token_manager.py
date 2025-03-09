import logging
import aiohttp
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from ..core.config import settings

logger = logging.getLogger(__name__)

class MiCloudTokenManager:
    """小米云服务Token管理器"""
    
    def __init__(self):
        self.base_url = "https://i.mi.com"
        self.token_file = Path("./data/tokens/micloud_token.json")
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Token状态
        self.cookies: Dict[str, str] = {}
        self.last_renewal_time: Optional[datetime] = None
        self.renewal_success_count: int = 0
        self.renewal_fail_count: int = 0
        self.is_running: bool = False
        self.last_check_time: Optional[datetime] = None
        
        # 加载初始token
        self._load_initial_token()
        
    def _load_initial_token(self):
        """加载初始token配置"""
        try:
            logger.info("开始加载token配置...")
            
            # 先尝试从本地文件加载
            if self.token_file.exists():
                logger.info(f"发现本地token文件: {self.token_file}")
                try:
                    with open(self.token_file, 'r') as f:
                        saved_token = json.load(f)
                        logger.info("本地token文件内容:")
                        for key, value in saved_token.items():
                            # 对敏感信息部分打码
                            masked_value = value
                            if len(value) > 8:
                                masked_value = value[:4] + '*' * (len(value)-8) + value[-4:]
                            logger.info(f"  {key}: {masked_value}")
                        
                        if self._validate_token(saved_token):
                            self.cookies = saved_token
                            logger.info("从本地文件加载token成功")
                            return
                        else:
                            logger.warning("本地token文件格式无效")
                except json.JSONDecodeError as e:
                    logger.error(f"本地token文件解析失败: {str(e)}")
                except Exception as e:
                    logger.error(f"读取本地token文件时出错: {str(e)}")
                
            # 如果本地文件不存在或无效，从环境变量加载
            logger.info("尝试从环境变量加载token...")
            cookies_str = settings.MICLOUD_COOKIES
            if not cookies_str:
                raise ValueError("未配置小米云服务的cookies，请在环境变量中设置 MICLOUD_COOKIES")
                
            # 解析cookie字符串
            if isinstance(cookies_str, str):
                logger.info("解析cookie字符串...")
                self.cookies = {}
                for cookie in cookies_str.split(';'):
                    cookie = cookie.strip()
                    if not cookie or '=' not in cookie:
                        continue
                    name, value = cookie.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                    self.cookies[name] = value
                    
                # 记录找到的cookie字段
                logger.info("从环境变量解析到的cookie字段:")
                for key, value in self.cookies.items():
                    # 对敏感信息部分打码
                    masked_value = value
                    if len(value) > 8:
                        masked_value = value[:4] + '*' * (len(value)-8) + value[-4:]
                    logger.info(f"  {key}: {masked_value}")
            else:
                logger.info("环境变量中的cookies已经是字典格式")
                self.cookies = cookies_str
                
            # 验证并保存
            if self._validate_token(self.cookies):
                self._save_token()
                logger.info("从环境变量加载token成功")
            else:
                missing_fields = self._get_missing_fields(self.cookies)
                raise ValueError(f"无效的token配置，缺少必要字段: {', '.join(missing_fields)}")
                
        except Exception as e:
            logger.error(f"加载token失败: {str(e)}")
            raise
            
    def _validate_token(self, token_data: Dict[str, str]) -> bool:
        """验证token是否包含所需字段"""
        required_fields = {
            "serviceToken", 
            "userId",
            "i.mi.com_isvalid_servicetoken",
            "i.mi.com_slh"
        }
        return all(field in token_data for field in required_fields)
        
    def _get_missing_fields(self, token_data: Dict[str, str]) -> List[str]:
        """获取缺失的必要字段"""
        required_fields = {
            "serviceToken", 
            "userId",
            "i.mi.com_isvalid_servicetoken",
            "i.mi.com_slh"
        }
        return [field for field in required_fields if field not in token_data]
        
    def _save_token(self):
        """保存token到本地文件"""
        try:
            # 确保目录存在
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存token
            with open(self.token_file, 'w') as f:
                json.dump(self.cookies, f, indent=2)
            logger.info(f"token已保存到本地文件: {self.token_file}")
        except Exception as e:
            logger.error(f"保存token失败: {str(e)}")
            raise
            
    async def _renew_token(self):
        """更新token"""
        ts = int(datetime.now().timestamp() * 1000)
        params = {
            "ts": ts,
            "type": "AutoRenewal",
            "inactiveTime": "420"  # 7分钟
        }
        
        # 记录当前使用的cookies
        logger.info("当前使用的cookies:")
        for key, value in self.cookies.items():
            # 对敏感信息部分打码
            masked_value = value
            if len(value) > 8:
                masked_value = value[:4] + '*' * (len(value)-8) + value[-4:]
            logger.info(f"  {key}: {masked_value}")
        
        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "referer": "https://i.mi.com/sms/h5",
            "sec-ch-ua": '"Not(A:Brand";v="99", "Microsoft Edge";v="133", "Chromium";v="133"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
            "cookie": "; ".join([f"{k}={v}" for k, v in self.cookies.items()]),
        }
        
        url = f"{self.base_url}/status/lite/setting"
        try:
            async with aiohttp.ClientSession() as session:
                logger.info(f"发送续期请求到: {url}")
                logger.info(f"请求参数: {params}")
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.error(f"续期请求失败: HTTP {response.status}")
                        logger.error(f"响应内容: {response_text[:200]}")
                        raise Exception(f"续期请求失败: {response.status}")
                    
                    # 记录响应头中的Set-Cookie
                    logger.info("服务器返回的Set-Cookie头:")
                    for cookie in response.headers.getall("Set-Cookie", []):
                        logger.info(f"  {cookie}")
                        
                    # 提取新token
                    new_cookies = {}
                    for cookie in response.headers.getall("Set-Cookie", []):
                        if "=" not in cookie:
                            continue
                        name, value = cookie.split("=", 1)
                        name = name.strip()
                        value = value.split(";")[0].strip()
                        
                        if name in ["serviceToken", "i.mi.com_slh"]:
                            new_cookies[name] = value
                            self.cookies[name] = value
                            
                    if new_cookies:
                        logger.info("成功更新以下cookie字段:")
                        for key, value in new_cookies.items():
                            masked_value = value
                            if len(value) > 8:
                                masked_value = value[:4] + '*' * (len(value)-8) + value[-4:]
                            logger.info(f"  {key}: {masked_value}")
                        
                        self.cookies["i.mi.com_isvalid_servicetoken"] = "true"
                        self._save_token()
                        self.last_renewal_time = datetime.now()
                        self.renewal_success_count += 1
                        logger.info(f"token续期成功 - 总次数: {self.renewal_success_count}")
                    else:
                        logger.error("服务器未返回新token")
                        raise Exception("服务器未返回新token")
                        
        except Exception as e:
            self.renewal_fail_count += 1
            logger.error(f"token续期失败: {str(e)}")
            raise
            
    async def start(self):
        """启动token管理器"""
        if self.is_running:
            logger.warning("token管理器已经在运行")
            return
            
        self.is_running = True
        logger.info("token管理器已启动")
        
        retry_count = 0
        max_retries = 3
        
        while self.is_running:
            try:
                # 每7分钟续期一次
                await self._renew_token()
                retry_count = 0  # 重置重试计数
                await asyncio.sleep(420)  # 7分钟
                
            except Exception as e:
                retry_count += 1
                logger.error(f"token续期出错 (尝试 {retry_count}/{max_retries}): {str(e)}")
                
                if retry_count >= max_retries:
                    logger.error("连续多次续期失败，token管理器将停止")
                    await self.stop()
                    raise
                    
                # 出错后等待30秒再试
                await asyncio.sleep(30)
                
    async def stop(self):
        """停止token管理器"""
        self.is_running = False
        logger.info("token管理器已停止")
        
    def _check_token_file_status(self) -> bool:
        """检查token文件状态"""
        try:
            if not self.token_file.exists():
                logger.warning("token文件不存在")
                return False
                
            # 检查文件修改时间
            mtime = datetime.fromtimestamp(self.token_file.stat().st_mtime)
            now = datetime.now()
            if (now - mtime).total_seconds() > 600:  # 10分钟
                logger.warning("token文件已超过10分钟未更新")
                return False
                
            # 检查文件内容
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                if not self._validate_token(token_data):
                    logger.warning("token文件内容无效")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"检查token文件状态时出错: {str(e)}")
            return False
            
    @property
    def is_healthy(self) -> bool:
        """检查token管理器是否健康"""
        try:
            now = datetime.now()
            
            # 限制检查频率，避免频繁IO
            if self.last_check_time and (now - self.last_check_time).total_seconds() < 5:
                return True
                
            self.last_check_time = now
            
            # 检查token文件状态
            if not self._check_token_file_status():
                return False
                
            # 检查token是否有效
            with open(self.token_file, 'r') as f:
                current_token = json.load(f)
                
            # 验证token完整性
            if not self._validate_token(current_token):
                logger.warning("当前token无效")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"检查token管理器状态时出错: {str(e)}")
            return False
            
    def get_current_token(self) -> Dict[str, str]:
        """获取当前有效的token"""
        try:
            if not self.is_healthy:
                raise ValueError("token管理器状态异常，请确保token管理器服务正在运行")
                
            # 从文件读取最新token
            with open(self.token_file, 'r') as f:
                current_token = json.load(f)
                
            if not self._validate_token(current_token):
                raise ValueError("当前token无效")
                
            return current_token.copy()
            
        except Exception as e:
            logger.error(f"获取当前token失败: {str(e)}")
            raise

# 创建全局token管理器实例
token_manager = MiCloudTokenManager()

async def get_token() -> Dict[str, str]:
    """获取当前有效的token"""
    return token_manager.get_current_token()

async def start_token_manager():
    """启动token管理器"""
    await token_manager.start()

async def stop_token_manager():
    """停止token管理器"""
    await token_manager.stop() 