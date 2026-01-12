"""
LinkedIn Public Profile Agent - Scrapes public LinkedIn profiles.
Uses Playwright for headless browser access to public data.
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


class LinkedInAgent(BaseCollectionAgent):
    """
    LinkedIn public profile agent.
    
    Collects:
    - Public company pages
    - Public profile summaries (limited without login)
    - Job postings
    
    Warning: LinkedIn is aggressive about blocking scrapers.
    Use with caution and implement delays.
    """
    
    def __init__(self):
        super().__init__(agent_type="linkedin")
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
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
        """Execute LinkedIn collection"""
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
        Execute LinkedIn collection.
        
        Args:
            query: LinkedIn URL or company/person name
            collection_type: 'company', 'profile', or 'jobs' (default: company)
        """
        collection_type = kwargs.get('collection_type', 'company')
        
        context = await self._get_browser()
        page = await context.new_page()
        items = []
        
        try:
            if collection_type == 'company':
                items = await self._collect_company(page, query)
            elif collection_type == 'profile':
                items = await self._collect_profile(page, query)
            elif collection_type == 'jobs':
                items = await self._collect_jobs(page, query)
            else:
                raise ValueError(f"Unsupported collection type: {collection_type}")
                
        except Exception as e:
            self.logger.error(f"LinkedIn collection error: {e}")
            raise
        finally:
            await page.close()
        
        return items
    
    async def _collect_company(self, page, company_query: str) -> List[CollectedItem]:
        """Collect public company page info"""
        # Construct URL if not already a URL
        if not company_query.startswith('http'):
            # Search on Google for LinkedIn company page
            search_url = f"https://www.linkedin.com/company/{company_query.lower().replace(' ', '-')}"
        else:
            search_url = company_query
        
        await page.goto(search_url, wait_until='networkidle')
        await asyncio.sleep(2)  # Rate limiting
        
        items = []
        
        try:
            # Get public company info (limited without login)
            title = await page.title()
            
            # Try to get description
            description = ""
            try:
                desc_elem = await page.query_selector('[data-test-id="about-us__description"]')
                if desc_elem:
                    description = await desc_elem.inner_text()
            except:
                pass
            
            # Get any visible text content
            body_text = await page.inner_text('body')
            
            items.append(CollectedItem(
                source="linkedin_company",
                source_id=search_url,
                timestamp=int(time.time()),
                content=description or body_text[:1000],
                author_id=None,
                entities={
                    "urls": [search_url]
                },
                metadata={
                    "title": title,
                    "url": search_url,
                    "collection_type": "company",
                    "note": "Limited data - LinkedIn requires login for full access"
                },
                confidence=0.6,
                jurisdiction="unknown"
            ))
            
        except Exception as e:
            self.logger.warning(f"Could not extract company data: {e}")
        
        return items
    
    async def _collect_profile(self, page, profile_query: str) -> List[CollectedItem]:
        """Collect public profile info (very limited without login)"""
        if not profile_query.startswith('http'):
            search_url = f"https://www.linkedin.com/in/{profile_query}"
        else:
            search_url = profile_query
        
        await page.goto(search_url, wait_until='networkidle')
        await asyncio.sleep(2)
        
        items = []
        title = await page.title()
        
        items.append(CollectedItem(
            source="linkedin_profile",
            source_id=search_url,
            timestamp=int(time.time()),
            content=f"LinkedIn Profile: {title}",
            author_id=profile_query,
            entities={
                "urls": [search_url]
            },
            metadata={
                "title": title,
                "url": search_url,
                "collection_type": "profile",
                "note": "Very limited - LinkedIn requires login for profile data"
            },
            confidence=0.5,
            jurisdiction="unknown"
        ))
        
        return items
    
    async def _collect_jobs(self, page, company_query: str) -> List[CollectedItem]:
        """Collect job postings (public)"""
        # LinkedIn jobs are relatively accessible
        if not company_query.startswith('http'):
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={company_query.replace(' ', '%20')}"
        else:
            search_url = company_query
        
        await page.goto(search_url, wait_until='networkidle')
        await asyncio.sleep(2)
        
        items = []
        
        # Try to get job cards
        job_cards = await page.query_selector_all('.job-card-container')
        
        for i, card in enumerate(job_cards[:10]):  # Limit to 10 jobs
            try:
                title_elem = await card.query_selector('.job-card-list__title')
                company_elem = await card.query_selector('.job-card-container__company-name')
                location_elem = await card.query_selector('.job-card-container__metadata-item')
                
                title = await title_elem.inner_text() if title_elem else "Unknown"
                company = await company_elem.inner_text() if company_elem else "Unknown"
                location = await location_elem.inner_text() if location_elem else "Unknown"
                
                items.append(CollectedItem(
                    source="linkedin_job",
                    source_id=f"job_{i}_{int(time.time())}",
                    timestamp=int(time.time()),
                    content=f"{title} at {company}",
                    author_id=company,
                    entities={
                        "companies": [company],
                        "locations": [location]
                    },
                    metadata={
                        "job_title": title,
                        "company": company,
                        "location": location,
                        "collection_type": "jobs"
                    },
                    confidence=0.75,
                    jurisdiction="unknown"
                ))
            except Exception as e:
                self.logger.debug(f"Could not parse job card: {e}")
        
        return items
    
    async def close(self):
        """Close browser"""
        if self._browser:
            await self._browser.close()
            await self._playwright.stop()


# Singleton instance
linkedin_agent = LinkedInAgent()
