"""
Surface Web Collection Agent - Google dorking and web scraping.
"""

from typing import List, Dict, Any, Optional
import logging
import time
import asyncio
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup

from app.agents.collection.base import BaseCollectionAgent, CollectedItem
from app.core.rate_limit import rate_limit_manager
from app.core.proxy_manager import opsec_helper

logger = logging.getLogger(__name__)

# ============================================
# Surface Web Collection Agent
# ============================================

class SurfaceWebAgent(BaseCollectionAgent):
    """
    Surface web collection agent.
    
    Features:
    - Google dorking (search operators)
    - Web page scraping with BeautifulSoup
    - Entity extraction (emails, URLs, phone numbers)
    - OpSec-hardened requests (proxy + user-agent rotation)
    """
    
    def __init__(self):
        super().__init__(agent_type="surface_web")
    
    async def _execute_collection(
        self,
        query: str,
        max_results: int = 50,
        **kwargs
    ) -> List[CollectedItem]:
        """
        Execute Google search with dorking support.
        
        Args:
            query: Search query (supports Google operators)
            max_results: Maximum results to collect
        
        Returns:
            List of collected search results
        """
        # Acquire rate limit
        await rate_limit_manager.acquire("google")
        
        # OpSec delay
        await opsec_helper.random_delay()
        
        try:
            # Perform Google search
            search_results = await self._google_search(query, max_results)
            
            collected_items = []
            for result in search_results:
                item = self._normalize_search_result(result)
                collected_items.append(item)
            
            logger.info(f"Collected {len(collected_items)} search results for: {query}")
            return collected_items
        
        except Exception as e:
            logger.error(f"Surface web collection failed: {e}")
            raise
    
    async def _google_search(
        self,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Perform Google search (scraping-based, not official API).
        
        Note: This is a simplified implementation. Production should use:
        - Google Custom Search API (paid)
        - SerpAPI (third-party)
        - Or more sophisticated scraping with Playwright
        """
        
        # Build Google search URL
        encoded_query = quote_plus(query)
        url = f"https://www.google.com/search?q={encoded_query}&num={min(max_results, 100)}"
        
        # Get OpSec request config
        request_config = opsec_helper.get_request_config()
        
        try:
            async with httpx.AsyncClient(**request_config) as client:
                response = await client.get(url)
                response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search results
            results = []
            for result_div in soup.find_all('div', class_='g'):
                # Extract title
                title_elem = result_div.find('h3')
                title = title_elem.get_text() if title_elem else "No title"
                
                # Extract URL
                link_elem = result_div.find('a')
                url = link_elem.get('href') if link_elem else ""
                
                # Extract snippet
                snippet_elem = result_div.find('div', class_='VwiC3b')
                snippet = snippet_elem.get_text() if snippet_elem else ""
                
                if url and title:
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
            
            return results[:max_results]
        
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []
    
    def _normalize_search_result(self, result: Dict[str, Any]) -> CollectedItem:
        """Normalize search result to standard format"""
        
        # Extract entities from snippet
        entities = self._extract_entities(result.get('snippet', ''))
        entities['urls'] = [result['url']]
        
        metadata = {
            "platform": "google",
            "title": result.get('title', ''),
            "url": result.get('url', ''),
            "search_engine": "google"
        }
        
        return CollectedItem(
            source="surface_web",
            source_id=result.get('url', ''),
            timestamp=int(time.time()),
            content=f"{result.get('title', '')}\n\n{result.get('snippet', '')}",
            entities=entities,
            metadata=metadata,
            confidence=0.75,  # Lower confidence for scraped data
            jurisdiction="unknown"  # Varies by result
        )
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text using regex"""
        import re
        
        entities = {
            "emails": [],
            "urls": [],
            "phone_numbers": []
        }
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities['emails'] = re.findall(email_pattern, text)
        
        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        entities['urls'] = re.findall(url_pattern, text)
        
        # Extract phone numbers (US format)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        entities['phone_numbers'] = re.findall(phone_pattern, text)
        
        return entities
    
    async def scrape_url(
        self,
        url: str,
        investigation_id: str,
        user_id: str,
        justification: str
    ) -> CollectedItem:
        """
        Scrape a specific URL.
        
        Args:
            url: Target URL to scrape
        """
        # Acquire rate limit
        await rate_limit_manager.acquire("google")
        
        # OpSec delay
        await opsec_helper.random_delay()
        
        # Get OpSec request config
        request_config = opsec_helper.get_request_config()
        
        try:
            async with httpx.AsyncClient(**request_config) as client:
                response = await client.get(url)
                response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract text content
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Extract entities
            entities = self._extract_entities(text)
            entities['urls'] = [url]
            
            metadata = {
                "platform": "web_scrape",
                "url": url,
                "title": soup.title.string if soup.title else "No title",
                "content_length": len(text)
            }
            
            return CollectedItem(
                source="surface_web",
                source_id=url,
                timestamp=int(time.time()),
                content=text[:5000],  # Limit to 5000 chars
                entities=entities,
                metadata=metadata,
                confidence=0.70,
                jurisdiction="unknown"
            )
        
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            raise

# ============================================
# Google Dork Templates
# ============================================

class GoogleDorkTemplates:
    """Pre-built Google dork queries for common OSINT tasks"""
    
    @staticmethod
    def find_person(name: str, organization: str = None) -> str:
        """Find information about a person"""
        query = f'"{name}"'
        if organization:
            query += f' "{organization}"'
        return query
    
    @staticmethod
    def find_email(domain: str) -> str:
        """Find email addresses for a domain"""
        return f'site:{domain} intext:"@{domain}"'
    
    @staticmethod
    def find_documents(domain: str, filetype: str = "pdf") -> str:
        """Find specific document types"""
        return f'site:{domain} filetype:{filetype}'
    
    @staticmethod
    def find_subdomains(domain: str) -> str:
        """Find subdomains"""
        return f'site:*.{domain}'
    
    @staticmethod
    def find_exposed_data(keyword: str) -> str:
        """Find potentially exposed sensitive data"""
        return f'"{keyword}" (inurl:admin | inurl:login | inurl:password)'

# ============================================
# Global Instance
# ============================================

surface_web_agent = SurfaceWebAgent()
dork_templates = GoogleDorkTemplates()
