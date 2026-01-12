"""
Twitter/X Collection Agent - API-based tweet collection with rate limiting.
"""

import tweepy
from typing import List, Dict, Any, Optional
import logging
import time

from app.agents.collection.base import BaseCollectionAgent, CollectedItem, CollectionResult
from app.core.rate_limit import rate_limit_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Twitter Collection Agent
# ============================================

class TwitterCollectionAgent(BaseCollectionAgent):
    """
    Twitter/X data collection agent.
    
    Features:
    - API v2 integration with bearer token
    - Rate limit compliance (15 requests/15min)
    - Entity extraction (mentions, hashtags, URLs)
    - Engagement metrics collection
    """
    
    def __init__(self):
        super().__init__(agent_type="twitter")
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Twitter API client"""
        if not settings.TWITTER_BEARER_TOKEN:
            logger.warning("Twitter bearer token not configured")
            return
        
        try:
            self.client = tweepy.Client(
                bearer_token=settings.TWITTER_BEARER_TOKEN,
                wait_on_rate_limit=False  # We handle rate limiting ourselves
            )
            logger.info("Twitter client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
    
    async def _execute_collection(
        self,
        query: str,
        max_results: int = 100,
        **kwargs
    ) -> List[CollectedItem]:
        """
        Execute Twitter search.
        
        Args:
            query: Search query (Twitter search syntax)
            max_results: Maximum tweets to collect (10-100)
        
        Returns:
            List of collected tweets
        """
        if not self.client:
            raise RuntimeError("Twitter client not initialized. Check API credentials.")
        
        # Acquire rate limit token
        await rate_limit_manager.acquire("twitter")
        
        try:
            # Search recent tweets
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),  # API limit
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'lang', 'entities'],
                expansions=['author_id'],
                user_fields=['username', 'name', 'verified', 'public_metrics']
            )
            
            if not response.data:
                logger.info(f"No tweets found for query: {query}")
                return []
            
            # Normalize tweets
            collected_items = []
            users_dict = {user.id: user for user in response.includes.get('users', [])}
            
            for tweet in response.data:
                item = self._normalize_tweet(tweet, users_dict)
                collected_items.append(item)
            
            logger.info(f"Collected {len(collected_items)} tweets for query: {query}")
            return collected_items
        
        except tweepy.TweepyException as e:
            logger.error(f"Twitter API error: {e}")
            raise
    
    def _normalize_tweet(
        self,
        tweet: tweepy.Tweet,
        users_dict: Dict[str, tweepy.User]
    ) -> CollectedItem:
        """Normalize tweet to standard format"""
        
        # Extract entities
        entities = {
            "urls": [],
            "mentions": [],
            "hashtags": []
        }
        
        if hasattr(tweet, 'entities') and tweet.entities:
            if 'urls' in tweet.entities:
                entities['urls'] = [u['expanded_url'] for u in tweet.entities['urls']]
            if 'mentions' in tweet.entities:
                entities['mentions'] = [f"@{m['username']}" for m in tweet.entities['mentions']]
            if 'hashtags' in tweet.entities:
                entities['hashtags'] = [f"#{h['tag']}" for h in tweet.entities['hashtags']]
        
        # Get author info
        author = users_dict.get(tweet.author_id)
        author_username = author.username if author else "unknown"
        
        # Build metadata
        metadata = {
            "platform": "twitter",
            "tweet_id": tweet.id,
            "author_username": author_username,
            "author_verified": author.verified if author else False,
            "language": tweet.lang if hasattr(tweet, 'lang') else "unknown",
            "engagement": {
                "retweets": tweet.public_metrics.get('retweet_count', 0),
                "likes": tweet.public_metrics.get('like_count', 0),
                "replies": tweet.public_metrics.get('reply_count', 0),
                "quotes": tweet.public_metrics.get('quote_count', 0)
            } if hasattr(tweet, 'public_metrics') else {}
        }
        
        return CollectedItem(
            source="twitter",
            source_id=str(tweet.id),
            timestamp=int(tweet.created_at.timestamp()) if hasattr(tweet, 'created_at') else int(time.time()),
            content=tweet.text,
            author_id=f"twitter:{author_username}",
            entities=entities,
            metadata=metadata,
            confidence=0.95,  # High confidence for official API
            jurisdiction="US"  # Twitter is US-based
        )
    
    async def get_user_timeline(
        self,
        investigation_id: str,
        username: str,
        user_id: str,
        justification: str,
        max_results: int = 100
    ) -> CollectionResult:
        """
        Get recent tweets from a specific user.
        
        Args:
            username: Twitter username (without @)
            max_results: Maximum tweets to collect
        """
        # Acquire rate limit
        await rate_limit_manager.acquire("twitter")
        
        try:
            # Get user ID first
            user = self.client.get_user(username=username)
            if not user.data:
                raise ValueError(f"User not found: {username}")
            
            user_id_twitter = user.data.id
            
            # Get user's tweets
            response = self.client.get_users_tweets(
                id=user_id_twitter,
                max_results=min(max_results, 100),
                tweet_fields=['created_at', 'public_metrics', 'lang', 'entities']
            )
            
            if not response.data:
                return CollectionResult(
                    job_id=f"twitter_user_{int(time.time())}",
                    status="completed",
                    items_collected=0,
                    entities_discovered=0,
                    errors=[],
                    metadata={"username": username},
                    audit_log_id="",
                    started_at=int(time.time())
                )
            
            # Normalize tweets
            items = []
            users_dict = {user_id_twitter: user.data}
            for tweet in response.data:
                item = self._normalize_tweet(tweet, users_dict)
                items.append(item)
            
            return await self.collect_with_audit(
                investigation_id=investigation_id,
                query=f"user:{username}",
                user_id=user_id,
                justification=justification
            )
        
        except Exception as e:
            logger.error(f"Failed to get user timeline: {e}")
            raise

# ============================================
# Global Instance
# ============================================

twitter_agent = TwitterCollectionAgent()
