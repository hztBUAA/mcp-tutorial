# 添加新模块API指南

本指南描述了如何将新的API模块添加到系统中的标准流程。

## 1. 创建模块API类

> 可以将api-fox的api文档进行导出 给出params body 路由这几个部分  注意不用给出response等占特别大位置的信息

首先在 `src/openapi_mcp_server/{module_name}/api.py` 中创建新模块的API类：

```python
from typing import Optional, Dict, List
from openapi_mcp_server.server import BorAPI

class NewModuleAPI:
    def __init__(self, bor_api: BorAPI):
        """初始化新模块API
        
        Args:
            bor_api: BorAPI实例，用于复用其请求方法和配置
        """
        self.bor_api = bor_api
    
    def method_name(self, param1: type1, param2: type2, ...) -> Dict:
        """方法的详细描述
        
        Args:
            param1: 参数1的描述
            param2: 参数2的描述
            ...
            
        Returns:
            Dict: 返回值描述
        """
        return self.bor_api._make_request(
            "HTTP_METHOD",
            "/openapi/v1/endpoint/path",
            data={
                "param1": param1,
                "param2": param2,
                ...
            }
        )
```

## 2. 集成到BorAPI类

在 `src/openapi_mcp_server/server.py` 的 `BorAPI` 类中添加新模块：

```python
class BorAPI:
    def __init__(self, base_url: str, access_key: str):
        self.base_url = base_url
        self.access_key = access_key
        self.headers = {
            "Content-Type": "application/json"
        }
        # 初始化新模块
        self.new_module = NewModuleAPI(self)
```

## 3. 添加工具定义

在 `handle_list_tools()` 函数中添加新模块的工具定义：

```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        # ... 现有工具 ...
        
        types.Tool(
            name="new-module-method",  # 工具名称使用kebab-case
            description="工具功能描述",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",  # 或其他适当的类型
                        "description": "参数1的描述"
                    },
                    "param2": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "参数2的描述"
                    }
                },
                "required": ["param1"]  # 必需参数列表
            }
        ),
    ]
```

## 4. 实现工具调用处理

在 `handle_call_tool()` 函数中添加新工具的处理逻辑：

```python
@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    try:
        # ... 现有工具处理逻辑 ...
        
        elif name == "new-module-method":
            result = bor_api.new_module.method_name(
                param1=arguments["param1"],
                param2=arguments.get("param2", default_value)  # 可选参数使用get
            )
            return [types.TextContent(
                type="text",
                text=f"操作结果: {result}"
            )]
            
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"操作失败: {str(e)}"
            )
        ]
```

## 5. 命名规范

- 模块类名：使用PascalCase，以API结尾，如 `NewModuleAPI`
- 方法名：使用snake_case，如 `get_user_info`
- 工具名：使用kebab-case，如 `get-user-info`
- 参数名：使用snake_case，如 `user_id`

## 6. 文档规范

- 所有类和方法都必须有文档字符串
- 参数和返回值类型必须有类型注解
- 工具描述必须清晰说明功能和用途
- 参数描述必须包含类型、用途和示例（如适用）

## 7. 错误处理

- 使用 try-except 包装所有API调用
- 提供有意义的错误消息
- 保持与现有错误处理格式一致

## 8. 测试检查清单

在提交新模块前，确保：

- [ ] API类的所有方法都有完整的类型注解
- [ ] 所有方法都有详细的文档字符串
- [ ] 工具定义中的inputSchema完整且准确
- [ ] 错误处理逻辑完善
- [ ] 与现有代码风格保持一致
- [ ] 所有必需参数都在required列表中
- [ ] 可选参数有合理的默认值

## 9. 示例

参考现有模块（如ScholarAPI、PaperAPI）的实现方式。这些模块展示了标准的实现模式和最佳实践。

## 10. 注意事项

- 保持向后兼容性
- 遵循RESTful API设计原则
- 确保参数验证
- 使用统一的响应格式
- 保持代码简洁清晰