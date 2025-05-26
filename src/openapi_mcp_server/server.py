import asyncio
import uvicorn
import logging
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
import mcp.types as types
from typing import Optional, Dict, List, Any
import requests
import os
from dotenv import load_dotenv
import traceback

# 加载.env文件
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bor_api")

class BorAPI:
    def __init__(self, base_url: str, access_key: str):
        self.base_url = base_url
        self.access_key = access_key
        self.headers = {
            "Content-Type": "application/json"
        }
        # 初始化各个子模块
        from openapi_mcp_server.scholar.api import ScholarAPI
        from openapi_mcp_server.paper.api import PaperAPI
        from openapi_mcp_server.knowledge.api import KnowledgeAPI
        self.scholar = ScholarAPI(self)
        self.paper = PaperAPI(self)
        self.knowledge = KnowledgeAPI(self)
        
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """统一的请求处理方法
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL查询参数
            data: 请求体数据
        """
        url = f"{self.base_url}{endpoint}"
        # 确保每个请求都带上accessKey
        if params is None:
            params = {}
        params["accessKey"] = self.access_key
        
        # 记录请求信息
        logger.info(f"Making request: {method} {url}")
        logger.debug(f"Request params: {params}")
        if data:
            logger.debug(f"Request data: {data}")
            
        try:
            response = requests.request(method, url, headers=self.headers, params=params, json=data)
            response.raise_for_status()
            
            # 记录响应信息
            logger.info(f"Request successful: {response.status_code}")
            logger.debug(f"Response data: {response.json()}")
            
            return response.json()
        except requests.exceptions.RequestException as e:
            # 记录错误信息
            logger.error(f"Request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Error response: {e.response.text}")
            raise

# 初始化服务器和API客户端
server = Server("openapi-mcp-server")
bor_api = None  # 将在main函数中初始化

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出所有可用的工具"""
    return [
        # 知识库文件夹管理工具
        types.Tool(
            name="create-knowledge-folder",
            description="在知识库中创建新文件夹",
            inputSchema={
                "type": "object",
                "properties": {
                    "parent_id": {"type": "integer", "description": "父文件夹ID"},
                    "folder_name": {"type": "string", "description": "文件夹名称"}
                },
                "required": ["parent_id", "folder_name"]
            }
        ),
        types.Tool(
            name="update-knowledge-folder",
            description="更新知识库中的文件夹名称",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_id": {"type": "integer", "description": "文件夹ID"},
                    "folder_name": {"type": "string", "description": "新的文件夹名称"}
                },
                "required": ["folder_id", "folder_name"]
            }
        ),
        types.Tool(
            name="move-knowledge-folder",
            description="移动知识库中的文件夹",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_folder_id": {"type": "integer", "description": "源文件夹ID"},
                    "target_folder_id": {"type": "integer", "description": "目标文件夹ID"}
                },
                "required": ["source_folder_id", "target_folder_id"]
            }
        ),
        types.Tool(
            name="delete-knowledge-folder",
            description="删除知识库中的文件夹",
            inputSchema={
                "type": "object",
                "properties": {
                    "nodes_id": {"type": "integer", "description": "节点ID"},
                    "parent_id": {"type": "integer", "description": "父文件夹ID"},
                    "force_delete": {"type": "boolean", "description": "是否强制删除"}
                },
                "required": ["nodes_id", "parent_id"]
            }
        ),
        types.Tool(
            name="get-knowledge-directory",
            description="获取知识库目录结构",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get-knowledge-capacity",
            description="获取知识库容量信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_id": {"type": "integer", "description": "文件夹ID,不传则获取总容量"}
                }
            }
        ),
        
        # 知识库文献管理工具
        types.Tool(
            name="get-knowledge-file-list",
            description="获取知识库文献列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_num": {"type": "integer", "description": "页码,默认1"},
                    "page_size": {"type": "integer", "description": "每页数量,默认10"},
                    "parent_id": {"type": "integer", "description": "父文件夹ID"},
                    "order_by": {"type": "integer", "description": "排序字段(1:标题,2:作者,3:添加时间,4:期刊,5:重要性)"},
                    "order": {"type": "integer", "description": "排序方式(1:升序,2:降序)"},
                    "query": {"type": "integer", "description": "检索方式(1:检索作者,2:检索关键词)"},
                    "keyword": {"type": "string", "description": "检索关键词"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表"}
                }
            }
        ),
        types.Tool(
            name="get-knowledge-file-tags",
            description="获取知识库文献的标签信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {
                        "oneOf": [
                            {"type": "integer"},
                            {"type": "array", "items": {"type": "integer"}}
                        ],
                        "description": "资源ID或资源ID列表"
                    }
                },
                "required": ["resource_id"]
            }
        ),
        types.Tool(
            name="add-knowledge-file-tag",
            description="为知识库文献添加标签",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag_id": {"type": "integer", "description": "标签ID"},
                    "resource_id": {"type": "integer", "description": "资源ID"}
                },
                "required": ["tag_id", "resource_id"]
            }
        ),
        types.Tool(
            name="remove-knowledge-file-tag",
            description="移除知识库文献的标签",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag_id": {"type": "integer", "description": "标签ID"},
                    "resource_id": {"type": "integer", "description": "资源ID"}
                },
                "required": ["tag_id", "resource_id"]
            }
        ),
        
        # 知识库笔记管理工具
        types.Tool(
            name="get-knowledge-note",
            description="获取知识库文献笔记",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "integer", "description": "资源ID"}
                },
                "required": ["resource_id"]
            }
        ),
        types.Tool(
            name="save-knowledge-note",
            description="保存知识库文献笔记",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "integer", "description": "资源ID"},
                    "note": {"type": "string", "description": "笔记内容"}
                },
                "required": ["resource_id", "note"]
            }
        ),

        # 学者相关工具
        types.Tool(
            name="get-scholar-info",
            description="获取学者个人信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "scholar_id": {"type": "string", "description": "学者ID"},
                },
                "required": ["scholar_id"],
            },
        ),
        types.Tool(
            name="get-scholar-coauthors",
            description="获取学者合作作者",
            inputSchema={
                "type": "object",
                "properties": {
                    "scholar_id": {"type": "string", "description": "学者ID"},
                },
                "required": ["scholar_id"],
            },
        ),
        # 在list_tools()中修改search-scholars的定义
        types.Tool(
            name="search-scholars",
            description="搜索学者",
            inputSchema={
                "type": "object",
                "properties": {
                    "scholar_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "学者ID列表，如果为空列表，则不使用学者ID进行搜索"
                    },
                    "name": {
                        "type": "string",
                        "description": "学者名，如果为空，则不使用学者名进行搜索。不使用学者ID搜索时，学者名必传，用于模糊搜索学者，能够返回多个学者id的信息，可用于后续进一步的学者信息查询"
                    },
                    "page": {
                        "type": "integer",
                        "description": "页码，默认1"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "每页数量，默认20"
                    },
                    "source": {
                        "type": "string",
                        "description": "曝光来源: paper_homepage_recommend/scholar_homepage_recommend/ai_search/mix_search/scholar_homepage_search/subscribe_search/view_page/paper_related_author/scholar_card",
                        "default": "mix_search"
                    },
                    "search_source": {
                        "type": "string",
                        "description": "搜索来源: mix_search/scholar_tab_search/ai_search/scholar_home_page_search/scholar_subscribe_search",
                        "default": "mix_search"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="batch-get-scholars",
            description="批量获取学者信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "scholar_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "学者ID列表"
                    },
                },
                "required": ["scholar_ids"],
            },
        ),
        types.Tool(
            name="get-scholar-papers",
            description="获取学者论文列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "scholar_id": {"type": "string", "description": "学者ID"},
                    "page": {"type": "integer", "description": "页码，默认1"},
                    "size": {"type": "integer", "description": "每页数量，默认20"},
                    "sort": {"type": "integer", "description": "排序方式：1-最新发表时间 2-引用数 3-被引用，默认1"}
                },
                "required": ["scholar_id"],
            },
        ),
        types.Tool(
            name="get-follow-list",
            description="获取关注列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "页码，默认1"},
                    "page_size": {"type": "integer", "description": "每页数量，默认20"},
                },
            },
        ),
        types.Tool(
            name="get-subscription-list",
            description="获取订阅列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "页码，默认1"},
                    "page_size": {"type": "integer", "description": "每页数量，默认20"},
                },
            },
        ),
        
        # 论文搜索工具
        types.Tool(
            name="search-papers-normal",
            description="普通版搜索论文",
            inputSchema={
                "type": "object",
                "properties": {
                    "authors": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "author": {"type": "string"}
                            }
                        },
                        "description": "作者列表"
                    },
                    "start_time": {"type": "string", "description": "开始时间 (YYYY-MM-DD)"},
                    "end_time": {"type": "string", "description": "结束时间 (YYYY-MM-DD)"},
                    "page_size": {"type": "integer", "description": "返回结果数量，默认50"}
                },
                "required": ["authors", "start_time", "end_time"]
            }
        ),
        types.Tool(
            name="search-papers-enhanced",
            description="加强版搜索论文",
            inputSchema={
                "type": "object",
                "properties": {
                    "words": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "关键词列表"
                    },
                    "question": {"type": "string", "description": "问题描述"},
                    "start_time": {"type": "string", "description": "开始时间 (YYYY-MM-DD)"},
                    "end_time": {"type": "string", "description": "结束时间 (YYYY-MM-DD)"},
                    "page_size": {"type": "integer", "description": "返回结果数量，默认50"},
                    "rerank": {"type": "integer", "description": "是否重排序，默认0"}
                },
                "required": ["words", "question", "start_time", "end_time"]
            }
        ),
        types.Tool(
            name="search-papers-pro-v1",
            description="语料pro1.0版本搜索论文",
            inputSchema={
                "type": "object",
                "properties": {
                    "words": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "关键词列表"
                    },
                    "area_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "领域ID列表"
                    },
                    "question": {"type": "string", "description": "问题描述"},
                    "start_time": {"type": "string", "description": "开始时间 (YYYY-MM-DD)"},
                    "end_time": {"type": "string", "description": "结束时间 (YYYY-MM-DD)"},
                    "page_size": {"type": "integer", "description": "返回结果数量，默认50"},
                    "rerank": {"type": "integer", "description": "是否重排序，默认0"}
                },
                "required": ["words", "area_ids", "question", "start_time", "end_time"]
            }
        ),
        types.Tool(
            name="search-papers-pro-v2",
            description="语料pro2.0版本搜索论文",
            inputSchema={
                "type": "object",
                "properties": {
                    "words": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "关键词列表"
                    },
                    "area_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "领域ID列表"
                    },
                    "question": {"type": "string", "description": "问题描述"},
                    "start_time": {"type": "string", "description": "开始时间 (YYYY-MM-DD)"},
                    "end_time": {"type": "string", "description": "结束时间 (YYYY-MM-DD)"},
                    "page_size": {"type": "integer", "description": "返回结果数量，默认50"}
                },
                "required": ["words", "area_ids", "question", "start_time", "end_time"]
            }
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """处理工具调用请求"""
    if not arguments:
        raise ValueError("Missing arguments")

    try:
        
        # 处理学者相关的工具调用
        if name == "get-scholar-info":
            result = bor_api.scholar.get_scholar_info(arguments["scholar_id"])
            return [types.TextContent(type="text", text=f"学者信息: {result}")]
        
        elif name == "get-scholar-coauthors":
            result = bor_api.scholar.get_scholar_coauthors(arguments["scholar_id"])
            return [types.TextContent(type="text", text=f"合作作者信息: {result}")]
        
        # 在handle_call_tool()中修改对应的处理逻辑
        elif name == "search-scholars":
            result = bor_api.scholar.search_scholars(
                scholar_ids=arguments.get("scholar_ids", []),
                name=arguments.get("name", ""),
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 20),
                source=arguments.get("source", "mix_search"),
                search_source=arguments.get("search_source", "mix_search")
            )
            return [types.TextContent(type="text", text=f"搜索结果: {result}")]
            
        elif name == "batch-get-scholars":
            result = bor_api.scholar.batch_get_scholars(arguments["scholar_ids"])
            return [types.TextContent(type="text", text=f"批量查询结果: {result}")]
            
        elif name == "get-scholar-papers":
            result = bor_api.scholar.get_scholar_papers(
                scholar_id=arguments["scholar_id"],
                page=arguments.get("page", 1),
                size=arguments.get("size", 20),
                sort=arguments.get("sort", 1)
            )
            return [types.TextContent(type="text", text=f"学者论文列表: {result}")]
            
        elif name == "get-follow-list":
            result = bor_api.scholar.get_follow_list(
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 20)
            )
            return [types.TextContent(type="text", text=f"关注列表: {result}")]
            
        elif name == "get-subscription-list":
            result = bor_api.scholar.get_subscription_list(
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 20)
            )
            return [types.TextContent(type="text", text=f"订阅列表: {result}")]
            
        # 论文搜索相关的工具处理
        elif name == "search-papers-normal":
            result = bor_api.paper.search_papers_normal(
                authors=arguments["authors"],
                start_time=arguments["start_time"],
                end_time=arguments["end_time"],
                page_size=arguments.get("page_size", 50)
            )
            return [types.TextContent(type="text", text=f"普通版搜索结果: {result}")]

        elif name == "search-papers-enhanced":
            result = bor_api.paper.search_papers_enhanced(
                words=arguments["words"],
                question=arguments["question"],
                start_time=arguments["start_time"],
                end_time=arguments["end_time"],
                page_size=arguments.get("page_size", 50),
                rerank=arguments.get("rerank", 0)
            )
            return [types.TextContent(type="text", text=f"加强版搜索结果: {result}")]

        elif name == "search-papers-pro-v1":
            result = bor_api.paper.search_papers_pro_v1(
                words=arguments["words"],
                area_ids=arguments["area_ids"],
                question=arguments["question"],
                start_time=arguments["start_time"],
                end_time=arguments["end_time"],
                page_size=arguments.get("page_size", 50),
                rerank=arguments.get("rerank", 0)
            )
            return [types.TextContent(type="text", text=f"Pro1.0搜索结果: {result}")]

        elif name == "search-papers-pro-v2":
            result = bor_api.paper.search_papers_pro_v2(
                words=arguments["words"],
                area_ids=arguments["area_ids"],
                question=arguments["question"],
                start_time=arguments["start_time"],
                end_time=arguments["end_time"],
                page_size=arguments.get("page_size", 50)
            )
            return [types.TextContent(type="text", text=f"Pro2.0搜索结果: {result}")]

        # 知识库文件夹管理
        elif name == "create-knowledge-folder":
            result = bor_api.knowledge.create_folder(
                parent_id=arguments["parent_id"],
                folder_name=arguments["folder_name"]
            )
            return [types.TextContent(type="text", text=f"文件夹创建成功: {result}")]
            
        elif name == "update-knowledge-folder":
            result = bor_api.knowledge.update_folder(
                folder_id=arguments["folder_id"],
                folder_name=arguments["folder_name"]
            )
            return [types.TextContent(type="text", text=f"文件夹更新成功: {result}")]
            
        elif name == "move-knowledge-folder":
            result = bor_api.knowledge.move_folder(
                source_folder_id=arguments["source_folder_id"],
                target_folder_id=arguments["target_folder_id"]
            )
            return [types.TextContent(type="text", text=f"文件夹移动成功: {result}")]
            
        elif name == "delete-knowledge-folder":
            result = bor_api.knowledge.delete_folder(
                nodes_id=arguments["nodes_id"],
                parent_id=arguments["parent_id"],
                force_delete=arguments.get("force_delete", False)
            )
            return [types.TextContent(type="text", text=f"文件夹删除成功: {result}")]
            
        elif name == "get-knowledge-directory":
            result = bor_api.knowledge.get_directory()
            return [types.TextContent(type="text", text=f"目录结构: {result}")]
            
        elif name == "get-knowledge-capacity":
            result = bor_api.knowledge.get_capacity(
                folder_id=arguments.get("folder_id")
            )
            return [types.TextContent(type="text", text=f"容量信息: {result}")]
            
        # 知识库文献管理
        elif name == "get-knowledge-file-list":
            result = bor_api.knowledge.get_file_list(
                page_num=arguments.get("page_num", 1),
                page_size=arguments.get("page_size", 10),
                parent_id=arguments.get("parent_id"),
                order_by=arguments.get("order_by"),
                order=arguments.get("order"),
                query=arguments.get("query"),
                keyword=arguments.get("keyword"),
                tags=arguments.get("tags")
            )
            return [types.TextContent(type="text", text=f"文献列表: {result}")]
            
        elif name == "get-knowledge-file-tags":
            result = bor_api.knowledge.get_file_tags(
                resource_id=arguments["resource_id"]
            )
            return [types.TextContent(type="text", text=f"文献标签信息: {result}")]
            
        elif name == "add-knowledge-file-tag":
            result = bor_api.knowledge.add_file_tag(
                tag_id=arguments["tag_id"],
                resource_id=arguments["resource_id"]
            )
            return [types.TextContent(type="text", text=f"标签添加成功: {result}")]
            
        elif name == "remove-knowledge-file-tag":
            result = bor_api.knowledge.remove_file_tag(
                tag_id=arguments["tag_id"],
                resource_id=arguments["resource_id"]
            )
            return [types.TextContent(type="text", text=f"标签移除成功: {result}")]
            
        # 知识库笔记管理
        elif name == "get-knowledge-note":
            result = bor_api.knowledge.get_note(
                resource_id=arguments["resource_id"]
            )
            return [types.TextContent(type="text", text=f"笔记内容: {result}")]
            
        elif name == "save-knowledge-note":
            result = bor_api.knowledge.save_note(
                resource_id=arguments["resource_id"],
                note=arguments["note"]
            )
            return [types.TextContent(type="text", text=f"笔记保存成功: {result}")]

        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }
        logger.error(f"操作失败: {error_details}")  # 记录完整错误信息到日志
        return [
            types.TextContent(
                type="text",
                text=f"操作失败: {type(e).__name__} - {str(e)}"  # 至少显示异常类型和消息
            )
        ]

# 创建SSE transport
sse = SseServerTransport("/messages/")

async def handle_sse(request):
    """处理SSE连接请求"""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], 
            streams[1], 
            server.create_initialization_options(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            )
        )
    # 返回空响应以避免NoneType错误
    return Response()

# 创建Starlette路由
routes = [
    Route("/sse", endpoint=handle_sse, methods=["GET"]),
    Mount("/messages/", app=sse.handle_post_message),
]

# 创建Starlette应用
app = Starlette(routes=routes)

async def main():
    # 从环境变量获取API配置
    global bor_api
    
    logger.info("开始初始化 BorAPI...")
    
    # 获取环境变量，如果没有设置则抛出错误
    access_key = os.getenv("BOR_ACCESS_KEY")
    if not access_key:
        logger.error("环境变量 BOR_ACCESS_KEY 未设置")
        raise ValueError("必须设置环境变量 BOR_ACCESS_KEY")
    else:
        logger.info(f"成功获取 BOR_ACCESS_KEY:{access_key}")
        
    base_url = os.getenv("BOR_BASE_URL", "https://openapi.dp.tech")
    logger.info(f"使用 base_url: {base_url}")
    
    try:
        logger.info("正在创建 BorAPI 实例...")
        bor_api = BorAPI(
            base_url=base_url,
            access_key=access_key
        )
        logger.info("BorAPI 实例创建成功")
        
        # 验证API模块是否正确初始化
        logger.info(f"已初始化的API模块:")
        logger.info(f"- Scholar API: {bor_api.scholar is not None}")
        logger.info(f"- Paper API: {bor_api.paper is not None}")
        logger.info(f"- Knowledge API: {bor_api.knowledge is not None}")
        
    except Exception as e:
        logger.error(f"BorAPI 初始化失败: {str(e)}")
        raise
    
    # 运行Starlette应用
    logger.info("正在启动 Starlette 应用...")
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())