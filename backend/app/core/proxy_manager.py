"""
Proxy Rotation Manager - OpSec layer for anonymous collection.
Rotates residential proxies to avoid IP bans and detection.
"""

import random
import time
from typing import Optional, Dict
from dataclasses import dataclass
import logging

from app.core.database import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Data Models
# ============================================

@dataclass
class ProxyConfig:
    """Proxy configuration"""
    http: str
    https: str
    provider: str
    last_used: int = 0
    failure_count: int = 0
    is_healthy: bool = True

# ============================================
# Proxy Manager
# ============================================

class ProxyManager:
    """
    Manages proxy rotation for anonymous collection.
    
    OpSec Features:
    - Residential IP rotation (not datacenter IPs)
    - Health checking and automatic failover
    - Usage tracking to avoid patterns
    - Random selection to prevent fingerprinting
    """
    
    def __init__(self):
        self.enabled = settings.ENABLE_PROXY_ROTATION
        self.proxies = []
        self._initialize_proxies()
    
    def _initialize_proxies(self):
        """Initialize proxy pool"""
        if not self.enabled:
            logger.info("Proxy rotation disabled")
            return
        
        if settings.PROXY_PROVIDER and settings.PROXY_ENDPOINT:
            # Use configured proxy provider
            proxy_url = self._build_proxy_url()
            self.proxies.append(ProxyConfig(
                http=proxy_url,
                https=proxy_url,
                provider=settings.PROXY_PROVIDER
            ))
            logger.info(f"Initialized proxy: {settings.PROXY_PROVIDER}")
        else:
            logger.warning("Proxy rotation enabled but no provider configured")
    
    def _build_proxy_url(self) -> str:
        """Build proxy URL with authentication"""
        if settings.PROXY_USERNAME and settings.PROXY_PASSWORD:
            # Format: http://username:password@endpoint
            return f"http://{settings.PROXY_USERNAME}:{settings.PROXY_PASSWORD}@{settings.PROXY_ENDPOINT}"
        else:
            return f"http://{settings.PROXY_ENDPOINT}"
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get a random healthy proxy.
        
        Returns:
            Proxy dict for requests library or None if proxies disabled
        """
        if not self.enabled or not self.proxies:
            return None
        
        # Filter healthy proxies
        healthy_proxies = [p for p in self.proxies if p.is_healthy]
        
        if not healthy_proxies:
            logger.error("No healthy proxies available!")
            # Reset all proxies to healthy (circuit breaker)
            for proxy in self.proxies:
                proxy.is_healthy = True
                proxy.failure_count = 0
            healthy_proxies = self.proxies
        
        # Select random proxy
        proxy = random.choice(healthy_proxies)
        proxy.last_used = int(time.time())
        
        return {
            "http": proxy.http,
            "https": proxy.https
        }
    
    def report_failure(self, proxy_dict: Dict[str, str]):
        """
        Report proxy failure for health tracking.
        
        Args:
            proxy_dict: The proxy dict that failed
        """
        if not proxy_dict:
            return
        
        # Find matching proxy
        for proxy in self.proxies:
            if proxy.http == proxy_dict.get("http"):
                proxy.failure_count += 1
                
                # Mark unhealthy after 3 failures
                if proxy.failure_count >= 3:
                    proxy.is_healthy = False
                    logger.warning(
                        f"Proxy marked unhealthy: {proxy.provider} "
                        f"(failures: {proxy.failure_count})"
                    )
                break
    
    def report_success(self, proxy_dict: Dict[str, str]):
        """Report proxy success (resets failure count)"""
        if not proxy_dict:
            return
        
        for proxy in self.proxies:
            if proxy.http == proxy_dict.get("http"):
                proxy.failure_count = 0
                proxy.is_healthy = True
                break

# ============================================
# User-Agent Rotation
# ============================================

class UserAgentRotator:
    """
    Rotates user-agents to avoid fingerprinting.
    Uses top 50 real browser user-agents.
    """
    
    # Top user-agents (real browsers, not automated tools)
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    @staticmethod
    def get_random() -> str:
        """Get a random user-agent"""
        return random.choice(UserAgentRotator.USER_AGENTS)

# ============================================
# OpSec Request Helper
# ============================================

class OpSecRequestHelper:
    """
    Helper for making OpSec-hardened HTTP requests.
    
    Features:
    - Proxy rotation
    - User-agent randomization
    - Timing randomization
    - Referer stripping
    """
    
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.ua_rotator = UserAgentRotator()
    
    def get_headers(self) -> Dict[str, str]:
        """Get randomized headers"""
        return {
            "User-Agent": self.ua_rotator.get_random(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Referrer-Policy": "no-referrer"  # CRITICAL: No referer leakage
        }
    
    def get_request_config(self) -> Dict[str, any]:
        """
        Get complete request configuration with OpSec features.
        
        Returns:
            Dict with headers, proxies, timeout
        """
        return {
            "headers": self.get_headers(),
            "proxies": self.proxy_manager.get_proxy(),
            "timeout": 30,
            "allow_redirects": True
        }
    
    async def random_delay(self):
        """
        Random delay to avoid timing patterns.
        Uses configured min/max from settings.
        """
        import asyncio
        delay = random.uniform(
            settings.TIMING_RANDOMIZATION_MIN_SEC,
            settings.TIMING_RANDOMIZATION_MAX_SEC
        )
        logger.debug(f"OpSec delay: {delay:.2f}s")
        await asyncio.sleep(delay)

# ============================================
# Global Instances
# ============================================

proxy_manager = ProxyManager()
opsec_helper = OpSecRequestHelper()
