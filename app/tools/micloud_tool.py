import logging
import aiohttp
import json
import csv
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from ..core.config import settings
from .base import BaseTool
import asyncio
from .token_manager import get_token, token_manager

logger = logging.getLogger(__name__)

class MiCloudTool(BaseTool):
    """小米云服务管理工具"""
    
    name: str = "micloud"
    description: str = """小米云服务管理工具，支持以下操作：
    1. 获取短信列表 (list_sms)
    2. 获取通话记录 (list_calls)
    3. 搜索短信内容 (search_sms)
    4. 导出数据 (export_data)
    5. 获取相册列表 (list_photos)
    """
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        """获取工具参数定义"""
        return {
            "action": {
                "type": "string",
                "description": "要执行的操作：list_sms（获取短信列表）, list_calls（获取通话记录）, search_sms（搜索短信）, export_data（导出数据）, list_photos（获取相册列表）",
                "required": True,
                "enum": ["list_sms", "list_calls", "search_sms", "export_data", "list_photos"]
            },
            "limit": {
                "type": "integer",
                "description": "返回结果的数量限制",
                "required": False,
                "default": 20
            },
            "keyword": {
                "type": "string",
                "description": "搜索关键词（search_sms操作需要）",
                "required": False
            },
            "start_time": {
                "type": "string",
                "description": "开始时间，格式：YYYY-MM-DD",
                "required": False
            },
            "end_time": {
                "type": "string",
                "description": "结束时间，格式：YYYY-MM-DD",
                "required": False
            },
            "export_type": {
                "type": "string",
                "description": "要导出的数据类型：sms（短信）或 calls（通话记录）",
                "required": False,
                "default": "sms",
                "enum": ["sms", "calls"]
            },
            "page_num": {
                "type": "integer",
                "description": "页码（从0开始）",
                "required": False,
                "default": 0
            },
            "page_size": {
                "type": "integer",
                "description": "每页数量",
                "required": False,
                "default": 30
            }
        }
    
    def __init__(self):
        """初始化小米云工具"""
        super().__init__()
        self.base_url = "https://i.mi.com"
        self.export_dir = Path("./data/exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # 创建数据目录
        self.data_dir = Path("./data")
        
    async def _make_request(self, url, params=None):
        """发送请求到小米云服务"""
        try:
            # 从文件加载token
            token_file = Path("./data/micloud_token.json")
            if not token_file.exists():
                raise ValueError("Token文件不存在，请先运行test_request.py获取token")
                
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                self.logger.info("从文件加载token成功")
            
            # 构建完整的cookies
            cookies = {
                "serviceToken": token_data.get("serviceToken"),
                "userId": token_data.get("userId", "627885182"),
                "i.mi.com_slh": token_data.get("slh", "MY+I/qqT78I0523bJgPAkcG+OBQ="),
                "Hm_lvt_c3e3e8b3ea48955284516b186acf0f4e": str(int(datetime.now().timestamp())),
                "uLocale": token_data.get("uLocale", "zh_CN"),
                "iplocale": token_data.get("iplocale", "zh_CN"),
                "i.mi.com_isvalid_servicetoken": "true",
                "i.mi.com_ph": token_data.get("ph", "nWAmPwpg3taPGEwEXYYm5Q=="),
                "i.mi.com_istrudev": "true"
            }
            
            # 根据URL选择合适的referer
            if "gallery" in url:
                referer = "https://i.mi.com/gallery/h5"
            else:
                referer = "https://i.mi.com/sms/h5"
            
            headers = {
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
                "referer": referer,
                "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Microsoft Edge";v="134"',
                "sec-ch-ua-mobile": "?0", 
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
                "x-requested-with": "XMLHttpRequest",
                "cookie": "; ".join([f"{k}={v}" for k, v in cookies.items()]),
                "origin": "https://i.mi.com",
                "priority": "u=1, i"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    self.logger.info(f"响应状态码: {response.status}")
                    
                    # 处理响应cookies
                    new_cookies = {}
                    for cookie in response.cookies.values():
                        # 保存所有cookie值
                        if cookie.value:  # 只保存有值的cookie
                            if cookie.key == "serviceToken":
                                new_cookies["serviceToken"] = cookie.value
                            elif cookie.key == "userId":
                                new_cookies["userId"] = cookie.value
                            elif cookie.key == "i.mi.com_slh":
                                new_cookies["slh"] = cookie.value
                            elif cookie.key == "i.mi.com_ph":
                                new_cookies["ph"] = cookie.value
                            elif cookie.key == "uLocale":
                                new_cookies["uLocale"] = cookie.value
                            elif cookie.key == "iplocale":
                                new_cookies["iplocale"] = cookie.value
                            elif cookie.key == "i.mi.com_isvalid_servicetoken":
                                new_cookies["isvalid_servicetoken"] = cookie.value
                            elif cookie.key == "i.mi.com_istrudev":
                                new_cookies["istrudev"] = cookie.value
                            elif cookie.key == "Hm_lvt_c3e3e8b3ea48955284516b186acf0f4e":
                                new_cookies["hm_lvt"] = cookie.value
                    
                    # 如果有新的cookie值，更新token文件
                    if new_cookies:
                        # 保留原有的cookie值
                        for key in new_cookies:
                            token_data[key] = new_cookies[key]
                        
                        # 保存完整的cookie字符串
                        token_data["full_cookie"] = headers["cookie"]
                        
                        with open(token_file, 'w') as f:
                            json.dump(token_data, f, indent=2)
                            self.logger.info("Token文件已更新")
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        # 尝试使用现有cookie重新请求
                        self.logger.info("Token可能已过期，尝试使用现有cookie重新请求")
                        cookies["i.mi.com_isvalid_servicetoken"] = "true"
                        headers["cookie"] = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                        
                        async with session.get(url, params=params, headers=headers) as retry_response:
                            if retry_response.status == 200:
                                return await retry_response.json()
                            else:
                                text = await retry_response.text()
                                self.logger.error(f"重试请求失败: {text[:200]}")
                                raise Exception(f"重试请求失败: {text[:200]}")
                    else:
                        text = await response.text()
                        self.logger.error(f"请求失败: {text[:200]}")
                        raise Exception(f"请求失败: {text[:200]}")
                        
        except Exception as e:
            self.logger.error(f"请求失败: {str(e)}")
            raise
            
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """执行工具操作"""
        action = kwargs.get("action")
        try:
            if action == "list_sms":
                result = await self.list_sms(kwargs.get("limit", 20))
                return result
            elif action == "list_calls":
                return await self.list_calls(kwargs.get("limit", 20))
            elif action == "search_sms":
                return await self.search_sms(
                    kwargs["keyword"],
                    kwargs.get("start_time"),
                    kwargs.get("end_time")
                )
            elif action == "export_data":
                return await self.export_data(kwargs.get("export_type", "sms"))
            elif action == "list_photos":
                return await self.list_photos(
                    kwargs.get("page_num", 0),
                    kwargs.get("page_size", 30),
                    kwargs.get("start_time"),
                    kwargs.get("end_time")
                )
            else:
                raise ValueError(f"未知的操作: {action}")
        except Exception as e:
            logger.error(f"执行操作失败: {str(e)}")
            return f"### 执行失败\n\n执行操作失败: {str(e)}"
    
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """运行工具的方法（必需）"""
        raise NotImplementedError("请使用 execute 方法代替")
    
    async def list_sms(self, limit: int = 20) -> Dict[str, Any]:
        """获取短信列表"""
        self.logger.info("开始获取短信列表...")
        
        ts = int(datetime.now().timestamp() * 1000)
        params = {
            "syncTag": "0",
            "syncThreadTag": "0",
            "limit": str(limit),
            "readMode": "older",
            "withPhoneCall": "true",
            "ts": ts,
            "_dc": ts
        }
        
        self.logger.info(f"请求参数: {params}")
        
        try:
            url = f"{self.base_url}/sms/full/thread"
            data = await self._make_request(url, params)
            
            if data.get("result") == "ok":
                formatted_text = await self._format_sms_data(data)
                if formatted_text.get("status") == "success":
                    return {
                        "success": True,
                        "result": formatted_text["text"]
                    }
                else:
                    raise Exception(formatted_text.get("message", "格式化数据失败"))
            else:
                raise Exception(f"获取短信列表失败: {data}")
                
        except Exception as e:
            self.logger.error(f"获取短信列表失败: {str(e)}")
            return {
                "success": False,
                "result": "### 获取短信失败\n\n抱歉，获取短信列表时出现错误。请确保：\n1. 手机已开启短信同步功能\n2. 网络连接正常\n3. 账号登录状态有效"
            }
    
    async def list_calls(self, limit: int = 20) -> Dict[str, Any]:
        """获取通话记录"""
        try:
            # 从短信接口获取数据
            result = await self.list_sms(limit)
            if not result.get("success"):
                return result
            
            return {
                "success": True,
                "result": {
                    "data": result["data"]["calls"]
                }
            }
        except Exception as e:
            return {
                "success": False,
                "result": f"获取通话记录失败: {str(e)}"
            }
    
    async def search_sms(self, keyword: str, start_time: str = None, end_time: str = None) -> Dict[str, Any]:
        """搜索短信内容"""
        try:
            # 处理时间范围
            if start_time:
                start_ts = int(datetime.strptime(start_time, "%Y-%m-%d").timestamp() * 1000)
            else:
                start_ts = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                
            if end_time:
                end_ts = int(datetime.strptime(end_time, "%Y-%m-%d").timestamp() * 1000)
            else:
                end_ts = int(datetime.now().timestamp() * 1000)
            
            # 获取所有短信
            result = await self.list_sms(1000)
            if not result.get("success"):
                return result
            
            # 在本地进行搜索过滤
            messages = []
            for msg in result["data"]["messages"]:
                msg_time = msg.get("time", 0)
                if msg_time < start_ts or msg_time > end_ts:
                    continue
                    
                content = msg.get("content", "")
                if keyword.lower() not in content.lower():
                    continue
                    
                messages.append(msg)
            
            return {
                "success": True,
                "result": {
                    "data": messages
                }
            }
        except Exception as e:
            return {
                "success": False,
                "result": f"搜索短信失败: {str(e)}"
            }
    
    async def export_data(self, export_type: str = "sms") -> Dict[str, Any]:
        """导出数据"""
        try:
            # 获取数据
            result = await self.list_sms(limit=1000)  # 获取更多记录
            if not result.get("success"):
                return result
            
            # 准备导出文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{export_type}_{timestamp}.csv"
            filepath = self.export_dir / filename
            
            # 写入CSV文件
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                
                if export_type == "sms":
                    # 写入短信数据
                    writer.writerow(["ID", "会话ID", "电话号码", "内容", "时间", "是否未读"])
                    for msg in result["data"]["messages"]:
                        writer.writerow([
                            msg.get("id", ""),
                            msg.get("thread_id", ""),
                            msg.get("phone", ""),
                            msg.get("content", ""),
                            datetime.fromtimestamp(msg.get("time", 0)/1000).strftime("%Y-%m-%d %H:%M:%S"),
                            "是" if msg.get("unread") else "否"
                        ])
                else:
                    # 写入通话记录
                    writer.writerow(["ID", "电话号码", "类型", "时长(秒)", "时间", "状态"])
                    for call in result["data"]["calls"]:
                        writer.writerow([
                            call.get("id", ""),
                            call.get("phone", ""),
                            "来电" if call.get("type") == "incoming" else "去电",
                            call.get("duration", ""),
                            datetime.fromtimestamp(call.get("time", 0)/1000).strftime("%Y-%m-%d %H:%M:%S"),
                            call.get("status", "")
                        ])
            
            return {
                "success": True,
                "result": f"数据已导出到文件: {filepath}"
            }
        except Exception as e:
            return {
                "success": False,
                "result": f"导出数据失败: {str(e)}"
            }
    
    async def _format_sms_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化短信数据"""
        try:
            if not data or "data" not in data or "entries" not in data["data"]:
                return {
                    "status": "error",
                    "message": "数据格式错误"
                }
            
            messages = []
            unread_count = 0
            
            # 处理每个短信会话
            entries = sorted(
                data["data"]["entries"],
                key=lambda x: x["entry"]["localTime"] if "entry" in x and "localTime" in x["entry"] else 0,
                reverse=True
            )
            
            for entry in entries:
                if "entry" not in entry:
                    continue
                    
                msg = entry["entry"]
                # 跳过空内容的系统消息
                if msg.get("filteredBySpNumber", False) and not msg.get("snippet"):
                    continue
                
                # 转换时间戳为可读格式
                local_time = datetime.fromtimestamp(msg["localTime"]/1000).strftime("%Y-%m-%d %H:%M:%S")
                
                # 统计未读消息
                if msg.get("unread"):
                    unread_count += msg.get("unread", 0)
                
                messages.append({
                    "id": msg.get("id", ""),
                    "thread_id": msg.get("threadId", ""),
                    "phone": msg.get("recipients", ""),
                    "content": msg.get("snippet", "(无内容)"),
                    "time": local_time,
                    "unread": bool(msg.get("unread", False)),
                    "total_in_thread": msg.get("total", 1)
                })
            
            # 分类消息
            categorized_messages = {
                "验证码": [],
                "通知提醒": [],
                "其他": []
            }
            
            # 分类规则
            verification_keywords = ["验证码", "校验码", "code", "Code"]
            notification_keywords = ["通知", "提醒", "成功", "【订单", "【快递", "【支付"]
            
            for msg in messages:
                content = msg["content"]
                if any(keyword in content for keyword in verification_keywords):
                    categorized_messages["验证码"].append(msg)
                elif any(keyword in content for keyword in notification_keywords):
                    categorized_messages["通知提醒"].append(msg)
                else:
                    categorized_messages["其他"].append(msg)
            
            # 生成统计信息
            total_messages = len(messages)

            # 生成markdown格式的文本
            md_text = f"\n### 短信列表 (共 {total_messages} 条，未读 {unread_count} 条)\n\n"
            
            for category, msgs in categorized_messages.items():
                if msgs:  # 只显示有消息的分类
                    md_text += f"#### {category} ({len(msgs)} 条)\n\n"
                    for msg in msgs:
                        phone = msg["phone"]
                        time = msg["time"]
                        content = msg["content"]
                        unread = "**[未读]** " if msg["unread"] else ""
                        
                        md_text += f"- {unread}`{phone}` *{time}*\n\n  {content}\n\n"

            return {
                "status": "success",
                "text": md_text
            }
                
        except Exception as e:
            self.logger.error(f"格式化短信数据失败: {str(e)}")
            return {
                "status": "error",
                "message": f"格式化短信数据失败: {str(e)}"
            }

    async def _format_gallery_data(self, galleries: List[Dict[str, Any]]) -> str:
        """格式化相册数据为markdown格式"""
        if not galleries:
            return "### 相册列表\n\n暂无照片或视频。"
        
        # 按日期分组
        date_groups = {}
        for item in galleries:
            # 处理整数类型的时间戳
            timestamp = item.get("dateTaken", 0)
            if isinstance(timestamp, int):
                date_time = datetime.fromtimestamp(timestamp / 1000)  # 转换毫秒时间戳
                date_taken = date_time.strftime("%Y-%m-%d")
                time_taken = date_time.strftime("%H:%M:%S")
            else:
                # 如果不是整数，尝试按原来的方式处理
                try:
                    date_taken = str(timestamp).split()[0]
                    time_taken = str(timestamp).split()[1]
                except:
                    date_taken = "未知日期"
                    time_taken = "未知时间"
            
            if date_taken not in date_groups:
                date_groups[date_taken] = []
            item["formatted_time"] = time_taken  # 保存格式化后的时间
            date_groups[date_taken].append(item)
        
        # 生成markdown文本
        md_text = f"### 相册列表 (共 {len(galleries)} 个项目)\n\n"
        
        # 按日期倒序排序
        for date in sorted(date_groups.keys(), reverse=True):
            items = date_groups[date]
            md_text += f"#### {date} ({len(items)} 个项目)\n\n"
            
            for item in items:
                file_name = item.get("fileName", "未知文件名")
                time = item.get("formatted_time", "未知时间")
                item_type = "📷" if item.get("type") == "image" else "🎥"
                
                # 从 thumbnailInfo.data 获取URL
                thumbnail_info = item.get("thumbnailInfo", {})
                url = ""
                if thumbnail_info and "data" in thumbnail_info:
                    url = thumbnail_info["data"]
                
                size_mb = item.get("size", 0) / 1024 / 1024  # 转换为MB
                
                # 新的格式：[!文件名](URL) 时间|大小
                if url:
                    md_text += f"- ![{file_name}]({url}) *{time}* | {size_mb:.2f}MB\n\n"
                else:
                    md_text += f"- {item_type} {file_name} *{time}* | {size_mb:.2f}MB\n\n"
        
        return md_text

    async def list_photos(self, page_num: int = 0, page_size: int = 30, start_time: str = None, end_time: str = None) -> Dict[str, Any]:
        """获取相册列表"""
        self.logger.info("开始获取相册列表...")
        
        # 处理时间参数
        if not start_time:
            start_time = "20241120"  # 使用固定的日期，避免使用未来日期
        else:
            start_time = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%d")
            
        if not end_time:
            end_time = start_time
        else:
            end_time = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%d")
        
        # 构建请求参数
        params = {
            "ts": str(int(datetime.now().timestamp() * 1000)),  # 使用当前时间戳
            "startDate": start_time,
            "endDate": end_time,
            "pageNum": str(page_num),
            "pageSize": str(page_size)
        }
        
        self.logger.info(f"请求参数: {params}")
        
        try:
            url = f"{self.base_url}/gallery/user/galleries"
            self.logger.info(f"请求URL: {url}")
            
            # 使用 _make_request 方法发送请求
            data = await self._make_request(url, params)
            
            if data.get("result") == "ok" or (isinstance(data, dict) and data.get("R") == 200):
                galleries = data.get("data", {}).get("galleries", [])
                self.logger.info(f"获取到 {len(galleries)} 个相册项目")
                
                # 格式化相册数据为markdown格式
                formatted_text = await self._format_gallery_data(galleries)
                
                result = {
                    "success": True,
                    "result": formatted_text
                }
                return result
            else:
                error_msg = f"获取相册列表失败: {data}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            self.logger.error(f"获取相册列表失败: {str(e)}")
            return {
                "success": False,
                "result": "### 获取相册失败\n\n获取相册列表时出现错误。请确保：\n1. 账号登录状态有效\n2. 网络连接正常\n3. 相册访问权限正常"
            }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        pass 