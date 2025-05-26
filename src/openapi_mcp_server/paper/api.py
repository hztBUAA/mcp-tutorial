from typing import Optional, Dict, List
from openapi_mcp_server.server import BorAPI

class PaperAPI:
    def __init__(self, bor_api: BorAPI):
        """初始化PaperAPI
        
        Args:
            bor_api: BorAPI实例，用于复用其请求方法和配置
        """
        self.bor_api = bor_api
    
    def search_papers_normal(
        self,
        authors: List[Dict[str, str]],
        start_time: str,
        end_time: str,
        page_size: int = 50
    ) -> Dict:
        """普通版搜索论文
        
        Args:
            authors: 作者列表，每个作者是包含author字段的字典
            start_time: 开始时间，格式：YYYY-MM-DD
            end_time: 结束时间，格式：YYYY-MM-DD
            page_size: 返回结果数量，默认50
        """
        return self.bor_api._make_request(
            "POST",
            "/openapi/v1/paper/rag/pass/keyword",
            data={
                "type": 0,
                "authors": authors,
                "startTime": start_time,
                "endTime": end_time,
                "pageSize": page_size
            }
        )
    
    def search_papers_enhanced(
        self,
        words: List[str],
        question: str,
        start_time: str,
        end_time: str,
        page_size: int = 50,
        rerank: int = 0
    ) -> Dict:
        """加强版搜索论文
        
        Args:
            words: 关键词列表
            question: 问题描述
            start_time: 开始时间，格式：YYYY-MM-DD
            end_time: 结束时间，格式：YYYY-MM-DD
            page_size: 返回结果数量，默认50
            rerank: 是否重排序，默认0
        """
        return self.bor_api._make_request(
            "POST",
            "/openapi/v1/paper/rag/pass/keyword",
            data={
                "type": 1,
                "rerank": rerank,
                "words": words,
                "question": question,
                "startTime": start_time,
                "endTime": end_time,
                "pageSize": page_size
            }
        )
    
    def search_papers_pro_v1(
        self,
        words: List[str],
        area_ids: List[str],
        question: str,
        start_time: str,
        end_time: str,
        page_size: int = 50,
        rerank: int = 0
    ) -> Dict:
        """语料pro1.0版本搜索论文
        
        Args:
            words: 关键词列表
            area_ids: 领域ID列表
            question: 问题描述
            start_time: 开始时间，格式：YYYY-MM-DD
            end_time: 结束时间，格式：YYYY-MM-DD
            page_size: 返回结果数量，默认50
            rerank: 是否重排序，默认0
        """
        return self.bor_api._make_request(
            "POST",
            "/openapi/v1/paper/rag/pass/keyword",
            data={
                "type": 2,
                "rerank": rerank,
                "words": words,
                "areaIds": area_ids,
                "question": question,
                "startTime": start_time,
                "endTime": end_time,
                "pageSize": page_size
            }
        )
    
    def search_papers_pro_v2(
        self,
        words: List[str],
        area_ids: List[str],
        question: str,
        start_time: str,
        end_time: str,
        page_size: int = 50
    ) -> Dict:
        """语料pro2.0版本搜索论文
        
        Args:
            words: 关键词列表
            area_ids: 领域ID列表
            question: 问题描述
            start_time: 开始时间，格式：YYYY-MM-DD
            end_time: 结束时间，格式：YYYY-MM-DD
            page_size: 返回结果数量，默认50
        """
        return self.bor_api._make_request(
            "POST",
            "/openapi/v1/paper/rag/pass/keyword",
            data={
                "type": 3,
                "words": words,
                "areaIds": area_ids,
                "question": question,
                "startTime": start_time,
                "endTime": end_time,
                "pageSize": page_size
            }
        )