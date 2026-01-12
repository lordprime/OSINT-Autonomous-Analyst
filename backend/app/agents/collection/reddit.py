"""
Reddit Collection Agent - PRAW-based subreddit and user monitoring.
"""

import praw
from typing import List, Dict, Any, Optional
import logging
import time

from app.agents.collection.base import BaseCollectionAgent, CollectedItem, CollectionResult
from app.core.rate_limit import rate_limit_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Reddit Collection Agent
# ============================================

class RedditCollectionAgent(BaseCollectionAgent):
    """
    Reddit data collection agent using PRAW.
    
    Features:
    - Subreddit post collection
    - Comment thread extraction
    - User profile scraping
    - Rate limit compliance (60 requests/min)
    """
    
    def __init__(self):
        super().__init__(agent_type="reddit")
        self.reddit = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Reddit API client"""
        if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
            logger.warning("Reddit API credentials not configured")
            return
        
        try:
            self.reddit = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT
            )
            logger.info("Reddit client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
    
    async def _execute_collection(
        self,
        query: str,
        max_results: int = 100,
        **kwargs
    ) -> List[CollectedItem]:
        """
        Execute Reddit search.
        
        Args:
            query: Search query or subreddit name
            max_results: Maximum posts to collect
        
        Returns:
            List of collected posts
        """
        if not self.reddit:
            raise RuntimeError("Reddit client not initialized. Check API credentials.")
        
        # Determine if query is subreddit or search
        if query.startswith("r/"):
            return await self._collect_subreddit(query[2:], max_results)
        else:
            return await self._search_reddit(query, max_results)
    
    async def _collect_subreddit(
        self,
        subreddit_name: str,
        max_results: int
    ) -> List[CollectedItem]:
        """Collect posts from a subreddit"""
        
        # Acquire rate limit
        await rate_limit_manager.acquire("reddit")
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Get hot posts
            posts = subreddit.hot(limit=max_results)
            
            collected_items = []
            for post in posts:
                item = self._normalize_post(post)
                collected_items.append(item)
            
            logger.info(f"Collected {len(collected_items)} posts from r/{subreddit_name}")
            return collected_items
        
        except Exception as e:
            logger.error(f"Failed to collect from r/{subreddit_name}: {e}")
            raise
    
    async def _search_reddit(
        self,
        query: str,
        max_results: int
    ) -> List[CollectedItem]:
        """Search Reddit globally"""
        
        # Acquire rate limit
        await rate_limit_manager.acquire("reddit")
        
        try:
            # Search all of Reddit
            search_results = self.reddit.subreddit("all").search(
                query,
                limit=max_results,
                sort="relevance"
            )
            
            collected_items = []
            for post in search_results:
                item = self._normalize_post(post)
                collected_items.append(item)
            
            logger.info(f"Collected {len(collected_items)} posts for query: {query}")
            return collected_items
        
        except Exception as e:
            logger.error(f"Reddit search failed: {e}")
            raise
    
    def _normalize_post(self, post: praw.models.Submission) -> CollectedItem:
        """Normalize Reddit post to standard format"""
        
        # Extract entities
        entities = {
            "urls": [],
            "mentions": [],
            "subreddit": [f"r/{post.subreddit.display_name}"]
        }
        
        # Extract URLs from post
        if hasattr(post, 'url') and post.url:
            entities['urls'].append(post.url)
        
        # Extract user mentions from text (u/username pattern)
        import re
        if post.selftext:
            mentions = re.findall(r'u/(\w+)', post.selftext)
            entities['mentions'] = [f"u/{m}" for m in mentions]
        
        # Build metadata
        metadata = {
            "platform": "reddit",
            "post_id": post.id,
            "subreddit": post.subreddit.display_name,
            "author": post.author.name if post.author else "[deleted]",
            "title": post.title,
            "post_type": "link" if post.is_self == False else "text",
            "is_nsfw": post.over_18,
            "is_locked": post.locked,
            "engagement": {
                "score": post.score,
                "upvote_ratio": post.upvote_ratio,
                "num_comments": post.num_comments
            },
            "awards": post.total_awards_received if hasattr(post, 'total_awards_received') else 0
        }
        
        # Combine title and selftext for content
        content = f"{post.title}\n\n{post.selftext}" if post.selftext else post.title
        
        return CollectedItem(
            source="reddit",
            source_id=post.id,
            timestamp=int(post.created_utc),
            content=content,
            author_id=f"reddit:{post.author.name}" if post.author else "reddit:[deleted]",
            entities=entities,
            metadata=metadata,
            confidence=0.90,  # High confidence for official API
            jurisdiction="US"  # Reddit is US-based
        )
    
    async def collect_comments(
        self,
        investigation_id: str,
        post_id: str,
        user_id: str,
        justification: str,
        max_comments: int = 100
    ) -> List[CollectedItem]:
        """
        Collect comments from a specific post.
        
        Args:
            post_id: Reddit post ID
            max_comments: Maximum comments to collect
        """
        # Acquire rate limit
        await rate_limit_manager.acquire("reddit")
        
        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)  # Don't fetch "load more" comments
            
            collected_items = []
            for comment in submission.comments.list()[:max_comments]:
                item = self._normalize_comment(comment, submission)
                collected_items.append(item)
            
            logger.info(f"Collected {len(collected_items)} comments from post {post_id}")
            return collected_items
        
        except Exception as e:
            logger.error(f"Failed to collect comments: {e}")
            raise
    
    def _normalize_comment(
        self,
        comment: praw.models.Comment,
        submission: praw.models.Submission
    ) -> CollectedItem:
        """Normalize Reddit comment to standard format"""
        
        # Extract user mentions
        import re
        mentions = re.findall(r'u/(\w+)', comment.body) if comment.body else []
        
        entities = {
            "mentions": [f"u/{m}" for m in mentions],
            "subreddit": [f"r/{submission.subreddit.display_name}"],
            "parent_post": [submission.id]
        }
        
        metadata = {
            "platform": "reddit",
            "comment_id": comment.id,
            "post_id": submission.id,
            "subreddit": submission.subreddit.display_name,
            "author": comment.author.name if comment.author else "[deleted]",
            "is_submitter": comment.is_submitter,
            "engagement": {
                "score": comment.score,
                "is_controversial": comment.controversiality > 0 if hasattr(comment, 'controversiality') else False
            }
        }
        
        return CollectedItem(
            source="reddit",
            source_id=comment.id,
            timestamp=int(comment.created_utc),
            content=comment.body if comment.body else "[deleted]",
            author_id=f"reddit:{comment.author.name}" if comment.author else "reddit:[deleted]",
            entities=entities,
            metadata=metadata,
            confidence=0.90,
            jurisdiction="US"
        )

# ============================================
# Global Instance
# ============================================

reddit_agent = RedditCollectionAgent()
