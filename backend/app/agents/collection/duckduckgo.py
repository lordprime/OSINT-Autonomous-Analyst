"""
DuckDuckGo Search Agent - Free web search with no API key required.
Uses the duckduckgo-search package for anonymous searching.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time
import logging
import asyncio

from app.agents.collection.base import (
    BaseCollectionAgent,
    CollectionResult,
    CollectionStatus,
    CollectedItem
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class DuckDuckGoAgent(BaseCollectionAgent):
    """
    DuckDuckGo search agent - completely free, no API key required.
    
    Features:
    - Text search with region/time filters
    - News search
    - Entity extraction from results
    """
    
    def __init__(self):
        super().__init__(agent_type="duckduckgo")
        self._ddgs = None
    
    def _get_client(self):
        """Lazy initialization of DuckDuckGo client"""
        if self._ddgs is None:
            try:
                from duckduckgo_search import DDGS
                self._ddgs = DDGS()
            except ImportError:
                raise ImportError(
                    "duckduckgo-search package not installed. "
                    "Run: pip install duckduckgo-search"
                )
        return self._ddgs
    
    async def collect(
        self,
        investigation_id: str,
        query: str,
        user_id: str,
        justification: str,
        **kwargs
    ) -> CollectionResult:
        """Execute DuckDuckGo search collection"""
        return await self.collect_with_audit(
            investigation_id=investigation_id,
            query=query,
            user_id=user_id,
            justification=justification,
            **kwargs
        )
    
    async def _execute_collection(
        self,
        query: str,
        **kwargs
    ) -> List[CollectedItem]:
        """
        Execute DuckDuckGo search.
        
        Args:
            query: Search query
            max_results: Maximum results to return (default: 25)
            region: Region code (default: wt-wt for worldwide)
            search_type: 'text', 'news', or 'images' (default: text)
            time_range: 'd' (day), 'w' (week), 'm' (month), 'y' (year)
        """
        max_results = kwargs.get('max_results', 25)
        region = kwargs.get('region', 'wt-wt')
        search_type = kwargs.get('search_type', 'text')
        time_range = kwargs.get('time_range', None)
        
        ddgs = self._get_client()
        items = []
        
        # Run sync code in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        if search_type == 'text':
            results = await loop.run_in_executor(
                None,
                lambda: list(ddgs.text(
                    query,
                    region=region,
                    timelimit=time_range,
                    max_results=max_results
                ))
            )
            items = [self._normalize_text_result(r) for r in results]
            
        elif search_type == 'news':
            results = await loop.run_in_executor(
                None,
                lambda: list(ddgs.news(
                    query,
                    region=region,
                    timelimit=time_range,
                    max_results=max_results
                ))
            )
            items = [self._normalize_news_result(r) for r in results]
            
        else:
            raise ValueError(f"Unsupported search type: {search_type}")
        
        self.logger.info(f"DuckDuckGo search returned {len(items)} results for: {query}")
        return items
    
    def _normalize_text_result(self, result: Dict[str, Any]) -> CollectedItem:
        """Normalize text search result"""
        return CollectedItem(
            source="duckduckgo",
            source_id=result.get('href', ''),
            timestamp=int(time.time()),
            content=result.get('body', ''),
            author_id=None,
            entities={
                "urls": [result.get('href', '')] if result.get('href') else [],
                "titles": [result.get('title', '')] if result.get('title') else []
            },
            metadata={
                "title": result.get('title', ''),
                "url": result.get('href', ''),
                "search_type": "text"
            },
            confidence=0.7,
            jurisdiction="unknown"
        )
    
    def _normalize_news_result(self, result: Dict[str, Any]) -> CollectedItem:
        """Normalize news search result"""
        return CollectedItem(
            source="duckduckgo_news",
            source_id=result.get('url', ''),
            timestamp=int(time.time()),
            content=result.get('body', ''),
            author_id=result.get('source', None),
            entities={
                "urls": [result.get('url', '')] if result.get('url') else [],
                "sources": [result.get('source', '')] if result.get('source') else []
            },
            metadata={
                "title": result.get('title', ''),
                "url": result.get('url', ''),
                "source": result.get('source', ''),
                "date": result.get('date', ''),
                "search_type": "news"
            },
            confidence=0.75,
            jurisdiction="unknown"
        )
    
    async def search_text(
        self,
        query: str,
        investigation_id: str,
        user_id: str,
        justification: str,
        max_results: int = 25,
        region: str = "wt-wt"
    ) -> CollectionResult:
        """Convenience method for text search"""
        return await self.collect(
            investigation_id=investigation_id,
            query=query,
            user_id=user_id,
            justification=justification,
            max_results=max_results,
            region=region,
            search_type="text"
        )
    
    async def search_news(
        self,
        query: str,
        investigation_id: str,
        user_id: str,
        justification: str,
        max_results: int = 25,
        time_range: str = "w"
    ) -> CollectionResult:
        """Convenience method for news search"""
        return await self.collect(
            investigation_id=investigation_id,
            query=query,
            user_id=user_id,
            justification=justification,
            max_results=max_results,
            search_type="news",
            time_range=time_range
        )


# Singleton instance
duckduckgo_agent = DuckDuckGoAgent()
