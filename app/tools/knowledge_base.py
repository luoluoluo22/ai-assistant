from typing import Dict, List, Optional, Any
import logging
import time
import asyncio
from supabase import create_client, Client
from app.core.config import settings
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

class KnowledgeBaseTool(BaseTool):
    """知识库工具，支持增删改查操作"""
    
    name: str = "knowledge_base"
    description: str = """知识库工具，支持以下操作：
    1. 搜索文档 (search)
    2. 获取单个文档 (get)
    3. 创建新文档 (create)
    4. 更新文档 (update)
    5. 删除文档 (delete)
    """
    
    # 添加字段定义
    max_retries: int = 3
    retry_delay: int = 1
    supabase: Optional[Any] = None
    
    def __init__(self):
        """Initialize the tool."""
        super().__init__()
        try:
            # 创建 Supabase 客户端
            self.supabase = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            logger.info("知识库工具初始化成功")
        except Exception as e:
            logger.error(f"知识库工具初始化失败: {str(e)}")
            raise

    async def _retry_operation(self, operation_func, *args, **kwargs):
        """使用重试机制执行操作"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return operation_func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:  # 如果不是最后一次尝试
                    wait_time = self.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"操作失败，{wait_time}秒后重试: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"操作在 {self.max_retries} 次尝试后仍然失败: {str(e)}")
        raise last_error

    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get the parameters schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "description": "操作类型",
                "enum": ["search", "get", "create", "update", "delete"],
                "required": True
            },
            "query": {
                "type": "string",
                "description": "搜索关键词（search操作需要）",
                "required": False
            },
            "doc_id": {
                "type": "string",
                "description": "文档ID（get/update/delete操作需要）",
                "required": False
            },
            "title": {
                "type": "string",
                "description": "文档标题（create/update操作需要）",
                "required": False
            },
            "content": {
                "type": "string",
                "description": "文档内容（create/update操作需要）",
                "required": False
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量限制（search操作可选）",
                "required": False,
                "default": 5
            }
        }
    
    @property
    def examples(self) -> List[str]:
        """Get example usages of the tool."""
        return [
            "搜索API密钥",
            "查找配置信息",
            "添加新文档",
            "更新文档内容",
            "删除文档"
        ]

    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """执行知识库操作
        
        Args:
            operation: 操作类型 (search/get/get_all/create/update/delete)
            **kwargs: 操作相关的参数
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        operations = {
            'search': self.search,
            'get': self.get_document,
            'get_all': self.get_all_documents,
            'create': self.create_document,
            'update': self.update_document,
            'delete': self.delete_document
        }
        
        if operation not in operations:
            return {
                'success': False,
                'message': f'不支持的操作类型: {operation}'
            }
            
        try:
            result = await operations[operation](**kwargs)
            return {
                'success': True,
                'data': result
            }
        except Exception as e:
            error_msg = f"执行 {operation} 操作失败: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }

    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索知识库"""
        try:
            # 由于还没有实现向量搜索，先使用简单的文本搜索
            response = await self._retry_operation(
                lambda: self.supabase.table('notes')
                    .select('*')
                    .ilike('content', f'%{query}%')
                    .limit(limit)
                    .execute()
            )
            
            if response.data:
                return response.data
            return []
            
        except Exception as e:
            logger.error(f"知识库搜索失败: {str(e)}")
            return []

    async def get_document(self, doc_id: str) -> Optional[Dict]:
        """
        获取指定文档的详细内容
        
        Args:
            doc_id: 文档ID
            
        Returns:
            Optional[Dict]: 文档内容
        """
        try:
            response = await self._retry_operation(
                lambda: self.supabase.table('notes')
                    .select('*')
                    .eq('id', doc_id)
                    .single()
                    .execute()
            )
                
            if response.data:
                logger.info(f"成功获取文档 {doc_id}")
                return response.data
                
            logger.warning(f"未找到文档 {doc_id}")
            return None
            
        except Exception as e:
            logger.error(f"获取文档失败: {str(e)}")
            return None

    async def get_all_documents(self) -> List[Dict]:
        """
        获取所有文档
        
        Returns:
            List[Dict]: 所有文档列表
        """
        try:
            response = await self._retry_operation(
                lambda: self.supabase.table('notes')
                    .select('*')
                    .execute()
            )
                
            if response.data:
                logger.info(f"成功获取所有文档，共 {len(response.data)} 条")
                return response.data
                
            logger.warning("数据库中没有文档")
            return []
            
        except Exception as e:
            logger.error(f"获取所有文档失败: {str(e)}")
            return []

    async def create_document(self, title: str, content: str) -> Optional[Dict]:
        """
        创建新的知识条目
        
        Args:
            title: 文档标题
            content: 文档内容
            
        Returns:
            Optional[Dict]: 创建的文档，失败返回 None
        """
        try:
            response = await self._retry_operation(
                lambda: self.supabase.table('notes')
                    .insert({
                        'title': title,
                        'content': content
                    })
                    .execute()
            )
            
            if response.data:
                logger.info(f"成功创建文档: {title}")
                return response.data[0]
                
            logger.warning("创建文档失败")
            return None
            
        except Exception as e:
            logger.error(f"创建文档失败: {str(e)}")
            return None
            
    async def update_document(self, doc_id: str, title: Optional[str] = None, content: Optional[str] = None) -> Optional[Dict]:
        """
        更新知识条目
        
        Args:
            doc_id: 文档ID
            title: 新标题（可选）
            content: 新内容（可选）
            
        Returns:
            Optional[Dict]: 更新后的文档，失败返回 None
        """
        try:
            # 构建更新数据
            update_data = {}
            if title is not None:
                update_data['title'] = title
            if content is not None:
                update_data['content'] = content
                
            if not update_data:
                logger.warning("没有提供要更新的内容")
                return None
                
            response = await self._retry_operation(
                lambda: self.supabase.table('notes')
                    .update(update_data)
                    .eq('id', doc_id)
                    .execute()
            )
            
            if response.data:
                logger.info(f"成功更新文档 {doc_id}")
                return response.data[0]
                
            logger.warning(f"更新文档失败: {doc_id}")
            return None
            
        except Exception as e:
            logger.error(f"更新文档失败: {str(e)}")
            return None
            
    async def delete_document(self, doc_id: str) -> bool:
        """
        删除知识条目
        
        Args:
            doc_id: 文档ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            response = await self._retry_operation(
                lambda: self.supabase.table('notes')
                    .delete()
                    .eq('id', doc_id)
                    .execute()
            )
                
            if response.data:
                logger.info(f"成功删除文档 {doc_id}")
                return True
                
            logger.warning(f"删除文档失败: {doc_id}")
            return False
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return False

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """运行工具的方法（必需）"""
        # 这个方法是为了满足 BaseTool 的要求
        # 实际的执行逻辑在 execute 方法中
        raise NotImplementedError("请使用 execute 方法代替")

    def get_tool_definition(self) -> Dict[str, Any]:
        """获取工具定义"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "examples": self.examples
        } 