from typing import Optional, Dict, List
import requests
from openapi_mcp_server.server import BorAPI

class ScholarAPI:
    def __init__(self, bor_api: BorAPI):
        """初始化ScholarAPI
        
        Args:
            bor_api: BorAPI实例，用于复用其请求方法和配置
        """
        self.bor_api = bor_api
    
    def get_scholar_info(self, scholar_id: str) -> Dict:
        """获取学者个人信息
        
        Args:
            scholar_id: 学者ID，例如："d7fef46d"
            
        Returns:
            Dict: 包含学者个人信息的字典
        """
        return self.bor_api._make_request(
            "GET", 
            "/openapi/v1/scholar/info", 
            params={"scholarId": scholar_id}
        )
    
    def get_scholar_coauthors(self, scholar_id: str, page: int = 1, page_size: int = 20) -> Dict:
        """获取学者合作作者列表
        
        Args:
            scholar_id: 学者ID
            page: 页码，默认1
            page_size: 每页数量，默认20
            
        Returns:
            Dict: 包含合作作者列表的字典，包括分页信息和作者详细信息
        """
        return self.bor_api._make_request(
            "GET", 
            "/openapi/v1/scholar/coauthors", 
            params={
                "scholarId": scholar_id,
                "page": page,
                "pageSize": page_size
            }
        )
    
    def search_scholars(
        self, 
        scholar_ids: List[str],
        name: str,
        page: int = 1,
        page_size: int = 20,
        source: str = "mix_search",
        search_source: str = "mix_search"
    ) -> Dict:
        """搜索学者
        Args:
            scholar_ids (List[str]): 学者ID列表，如果为空，则不使用学者ID进行搜索。列表的每个item需要是scholar id的字符串形式
            name (str): 学者名，如果为空，则不使用学者名进行搜索。不使用学者ID搜索时，学者名必传，用于模糊搜索学者，能够返回多个学者id的信息，可用于后续进一步的学者信息查询
            page (int, optional): 页码. Defaults to 1.
            page_size (int, optional): 每页数量. Defaults to 20.
            source (str, optional): 曝光来源. Defaults to "mix_search".
                可选值: paper_homepage_recommend/scholar_homepage_recommend/ai_search/mix_search/
                    scholar_homepage_search/subscribe_search/view_page/paper_related_author/scholar_card
            search_source (str, optional): 搜索来源. Defaults to "mix_search".
                可选值: mix_search/scholar_tab_search/ai_search/scholar_home_page_search/scholar_subscribe_search
        """
        return self.bor_api._make_request(
            "POST", 
            "/openapi/v1/scholar/search",
            data={
                "scholarIds": scholar_ids,
                "name": name,
                "page": page,
                "pageSize": page_size,
                "source": source,
                "searchSource": search_source
            }
        )
    
    def batch_get_scholars(self, scholar_ids: List[str]) -> Dict:
        """批量获取学者信息"""
        return self.bor_api._make_request(
            "POST", 
            "/openapi/v1/scholar/batch", 
            data={"scholarIds": scholar_ids}
        )
    
    def get_scholar_papers(self, scholar_id: str, page: int = 1, size: int = 20, sort: int = 1) -> Dict:
        """获取学者论文列表
        
        Args:
            scholar_id: 学者ID
            page: 页码，默认1
            size: 每页大小，默认20
            sort: 排序方式 1-最新发表时间 2-引用数 3-被引用，默认1
        """
        return self.bor_api._make_request(
            "POST",
            "/openapi/v1/scholar/paper",
            data={
                "scholarIds": [scholar_id],
                "page": page,
                "pageSize": size,
                "sort": sort
            }
        )
    
    def get_follow_list(self, page: int = 1, page_size: int = 20) -> Dict:
        """获取关注列表
        
        Args:
            page: 页码，默认1
            page_size: 每页大小，默认20
        """
        return self.bor_api._make_request(
            "GET", 
            "/openapi/v1/scholar/follow_list", 
            params={
                "page": page,
                "pageSize": page_size
            }
        )

    def get_subscription_list(self, page: int = 1, page_size: int = 20) -> Dict:
        """获取订阅列表
        
        Args:
            page: 页码，默认1
            page_size: 每页大小，默认20
        """
        return self.bor_api._make_request(
            "GET", 
            "/openapi/v1/scholar/subscribe", 
            params={
                "page": page,
                "pageSize": page_size
            }
        )