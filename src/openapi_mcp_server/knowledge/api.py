from typing import Optional, Dict, List, Union
from openapi_mcp_server.server import BorAPI

class KnowledgeAPI:
    def __init__(self, bor_api: BorAPI):
        """初始化知识库API
        
        Args:
            bor_api: BorAPI实例，用于复用其请求方法和配置
        """
        self.bor_api = bor_api

    def create_folder(self, parent_id: int, folder_name: str) -> Dict:
        """创建文件夹
        
        Args:
            parent_id: 父文件夹ID
            folder_name: 文件夹名称
            
        Returns:
            Dict: 包含创建结果的响应
        """
        return self.bor_api._make_request(
            "POST",
            "/api/v1/folder/create",
            json={
                "parentId": parent_id,
                "folderName": folder_name
            }
        )

    def update_folder(self, folder_id: int, folder_name: str) -> Dict:
        """更新文件夹名称
        
        Args:
            folder_id: 文件夹ID
            folder_name: 新的文件夹名称
            
        Returns:
            Dict: 包含更新结果的响应
        """
        return self.bor_api._make_request(
            "POST",
            "/api/v1/folder/update",
            json={
                "folderId": folder_id,
                "folderName": folder_name
            }
        )

    def move_folder(self, source_folder_id: int, target_folder_id: int) -> Dict:
        """移动文件夹
        
        Args:
            source_folder_id: 源文件夹ID
            target_folder_id: 目标文件夹ID
            
        Returns:
            Dict: 包含移动结果的响应
        """
        return self.bor_api._make_request(
            "POST",
            "/api/v1/folder/move",
            params={
                "sourceFolderId": source_folder_id,
                "targetFolderId": target_folder_id
            }
        )

    def delete_folder(self, nodes_id: int, parent_id: int, force_delete: bool = False) -> Dict:
        """删除文件夹
        
        Args:
            nodes_id: 节点ID
            parent_id: 父文件夹ID
            force_delete: 是否强制删除
            
        Returns:
            Dict: 包含删除结果的响应
        """
        return self.bor_api._make_request(
            "POST",
            "/api/v1/folder/delete",
            params={
                "nodesId": nodes_id,
                "parentId": parent_id,
                "forceDelete": force_delete
            }
        )

    def get_directory(self) -> Dict:
        """获取目录结构
        
        Returns:
            Dict: 包含目录结构的响应
        """
        return self.bor_api._make_request(
            "GET",
            "/api/v1/folder/directory"
        )

    def get_capacity(self, folder_id: Optional[int] = None) -> Dict:
        """获取知识库容量
        
        Args:
            folder_id: 文件夹ID，不传则获取总容量
            
        Returns:
            Dict: 包含容量信息的响应
        """
        params = {}
        if folder_id is not None:
            params["folderId"] = folder_id
        return self.bor_api._make_request(
            "GET",
            "/api/v1/folder/capacity",
            params=params
        )

    def get_file_list(self, 
                      page_num: int = 1,
                      page_size: int = 10,
                      parent_id: Optional[int] = None,
                      order_by: Optional[int] = None,
                      order: Optional[int] = None,
                      query: Optional[int] = None,
                      keyword: Optional[str] = None,
                      tags: Optional[List[str]] = None) -> Dict:
        """获取文献列表
        
        Args:
            page_num: 页码，默认1
            page_size: 每页数量，默认10
            parent_id: 父文件夹ID，不传则获取所有文献
            order_by: 排序字段（1:标题，2:作者，3:添加时间，4:期刊，5:重要性）
            order: 排序方式（1:升序，2:降序）
            query: 检索方式（1:检索作者，2:检索关键词）
            keyword: 检索关键词
            tags: 标签列表
            
        Returns:
            Dict: 包含文献列表的响应
        """
        params = {
            "pageNum": page_num,
            "pageSize": page_size
        }
        if parent_id is not None:
            params["parentId"] = parent_id
        if order_by is not None:
            params["orderBy"] = order_by
        if order is not None:
            params["order"] = order
        if query is not None:
            params["query"] = query
        if keyword is not None:
            params["keyword"] = keyword
        if tags is not None:
            params["tags"] = tags
            
        return self.bor_api._make_request(
            "GET",
            "/api/v1/file",
            params=params
        )

    def get_file_tags(self, resource_id: Union[int, List[int]]) -> Dict:
        """获取文献标签信息
        
        Args:
            resource_id: 资源ID或资源ID列表
            
        Returns:
            Dict: 包含文献标签信息的响应
        """
        return self.bor_api._make_request(
            "GET",
            "/api/v1/file/tagInfo",
            params={"resourceId": resource_id}
        )

    def add_file_tag(self, tag_id: int, resource_id: int) -> Dict:
        """为文献添加标签
        
        Args:
            tag_id: 标签ID
            resource_id: 资源ID
            
        Returns:
            Dict: 包含操作结果的响应
        """
        return self.bor_api._make_request(
            "POST",
            "/api/v1/file/tag",
            json={
                "tagId": tag_id,
                "resourceId": resource_id
            }
        )

    def remove_file_tag(self, tag_id: int, resource_id: int) -> Dict:
        """移除文献标签
        
        Args:
            tag_id: 标签ID
            resource_id: 资源ID
            
        Returns:
            Dict: 包含操作结果的响应
        """
        return self.bor_api._make_request(
            "POST",
            "/api/v1/file/untag",
            json={
                "tagId": tag_id,
                "resourceId": resource_id
            }
        )

    def get_file_tag_stats(self, 
                          parent_id: Optional[int] = None,
                          query: Optional[int] = None,
                          keyword: Optional[str] = None) -> Dict:
        """获取文献标签统计信息
        
        Args:
            parent_id: 父文件夹ID，不传则统计所有文献
            query: 检索方式（1:检索作者，2:检索关键词）
            keyword: 检索关键词
            
        Returns:
            Dict: 包含标签统计信息的响应
        """
        params = {}
        if parent_id is not None:
            params["parentId"] = parent_id
        if query is not None:
            params["query"] = query
        if keyword is not None:
            params["keyword"] = keyword
            
        return self.bor_api._make_request(
            "GET",
            "/api/v1/file/tag",
            params=params
        )

    def get_note(self, resource_id: int) -> Dict:
        """获取文献笔记
        
        Args:
            resource_id: 资源ID
            
        Returns:
            Dict: 包含笔记内容的响应
        """
        return self.bor_api._make_request(
            "GET",
            "/api/v1/note",
            params={"resourceId": resource_id}
        )

    def save_note(self, resource_id: int, note: str) -> Dict:
        """保存文献笔记
        
        Args:
            resource_id: 资源ID
            note: 笔记内容
            
        Returns:
            Dict: 包含保存结果的响应
        """
        return self.bor_api._make_request(
            "POST",
            "/api/v1/note",
            json={
                "resourceId": resource_id,
                "note": note
            }
        )
