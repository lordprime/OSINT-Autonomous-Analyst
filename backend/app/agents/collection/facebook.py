"""
Facebook Public Page Agent - Scrapes public Facebook pages and posts.
Uses Playwright for headless browser access.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time
import logging
import asyncio
import re

from app.agents.collection.base import (
    BaseCollectionAgent,
    CollectionResult,
    CollectionStatus,
    CollectedItem
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class FacebookAgent(BaseCollectionAgent):
    """
    Facebook public page agent.
    
    Collects:
    - Public page info
    - Public posts (limited)
    - Public events
    
    Note: Very limited without login. Facebook aggressively blocks scrapers.
    """
    
    def __init__(self):
        super().__init__(agent_type="facebook")
        self._browser = None
        self._context = None
    
    async def _get_browser(self):
        """Lazy initialization of Playwright browser"""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                self._context = await self._browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US'
                )
            except ImportError:
                raise ImportError(
                    "playwright package not installed or browsers not set up. "
                    "Run: pip install playwright && playwright install chromium"
                )
        return self._context
    
    async def collect(
        self,
        investigation_id: str,
        query: str,
        user_id: str,
        justification: str,
        **kwargs
    ) -> CollectionResult:
        """Execute Facebook collection"""
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
        Execute Facebook page collection.
        
        Args:
            query: Facebook page URL or page name
            collection_type: 'page', 'posts', or 'events' (default: page)
        """
        collection_type = kwargs.get('collection_type', 'page')
        
        context = await self._get_browser()
        page = await context.new_page()
        items = []
        
        try:
            if collection_type == 'page':
                items = await self._collect_page(page, query)
            elif collection_type == 'posts':
                items = await self._collect_posts(page, query)
            elif collection_type == 'events':
                items = await self._collect_events(page, query)
            else:
                raise ValueError(f"Unsupported collection type: {collection_type}")
                
        except Exception as e:
            self.logger.error(f"Facebook collection error: {e}")
            raise
        finally:
            await page.close()
        
        return items
    
    async def _collect_page(self, page, page_query: str) -> List[CollectedItem]:
        """Collect public page info"""
        # Construct URL
        if not page_query.startswith('http'):
            url = f"https://www.facebook.com/{page_query}"
        else:
            url = page_query
        
        # Use mobile site for better scraping (simpler HTML)
        mobile_url = url.replace('www.facebook.com', 'm.facebook.com')
        
        await page.goto(mobile_url, wait_until='networkidle')
        await asyncio.sleep(2)
        
        items = []
        title = await page.title()
        
        # Try to get page description
        description = ""
        try:
            # Look for about section
            about_elem = await page.query_selector('[data-sigil="m-page-about-section"]')
            if about_elem:
                description = await about_elem.inner_text()
        except:
            pass
        
        items.append(CollectedItem(
            source="facebook_page",
            source_id=url,
            timestamp=int(time.time()),
            content=description or f"Facebook Page: {title}",
            author_id=page_query if not page_query.startswith('http') else None,
            entities={
                "urls": [url]
            },
            metadata={
                "title": title,
                "url": url,
                "collection_type": "page",
                "note": "Limited data - Facebook requires login for full access"
            },
            confidence=0.5,
            jurisdiction="unknown"
        ))
        
        return items
    
    async def _collect_posts(self, page, page_query: str) -> List[CollectedItem]:
        """Collect public posts (very limited)"""
        if not page_query.startswith('http'):
            url = f"https://m.facebook.com/{page_query}/posts"
        else:
            url = page_query.replace('www.facebook.com', 'm.facebook.com')
            if '/posts' not in url:
                url += '/posts'
        
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(2)
        
        items = []
        
        # Try to find post elements (Facebook's structure changes frequently)
        post_elements = await page.query_selector_all('article')
        
        for i, post_elem in enumerate(post_elements[:5]):  # Limit to 5
            try:
                post_text = await post_elem.inner_text()
                
                items.append(CollectedItem(
                    source="facebook_post",
                    source_id=f"fb_post_{i}_{int(time.time())}",
                    timestamp=int(time.time()),
                    content=post_text[:500] if post_text else "[No text content]",
                    author_id=page_query,
                    entities={
                        "urls": [url]
                    },
                    metadata={
                        "source_page": page_query,
                        "collection_type": "posts",
                        "note": "Content may be incomplete"
                    },
                    confidence=0.4,
                    jurisdiction="unknown"
                ))
            except Exception as e:
                self.logger.debug(f"Could not parse post: {e}")
        
        if not items:
            items.append(CollectedItem(
                source="facebook_posts",
                source_id=url,
                timestamp=int(time.time()),
                content="Could not extract posts - login may be required",
                author_id=page_query,
                entities={"urls": [url]},
                metadata={
                    "url": url,
                    "error": "Facebook blocks most public post access"
                },
                confidence=0.2,
                jurisdiction="unknown"
            ))
        
        return items
    
    async def _collect_events(self, page, page_query: str) -> List[CollectedItem]:
        """Collect public events"""
        if not page_query.startswith('http'):
            url = f"https://m.facebook.com/{page_query}/events"
        else:
            url = page_query.replace('www.facebook.com', 'm.facebook.com')
            if '/events' not in url:
                url += '/events'
        
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(2)
        
        items = []
        title = await page.title()
        body_text = await page.inner_text('body')
        
        items.append(CollectedItem(
            source="facebook_events",
            source_id=url,
            timestamp=int(time.time()),
            content=body_text[:1000] if body_text else f"Events page: {title}",
            author_id=page_query,
            entities={"urls": [url]},
            metadata={
                "url": url,
                "collection_type": "events",
                "note": "Limited event data available without login"
            },
            confidence=0.4,
            jurisdiction="unknown"
        ))
        
        return items
    
    async def close(self):
        """Close browser"""
        if self._browser:
            await self._browser.close()
            await self._playwright.stop()


# Singleton instance
facebook_agent = FacebookAgent()
