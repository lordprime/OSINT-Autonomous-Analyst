"""
Instagram Public Profile Agent - Scrapes public Instagram profiles.
Uses Instaloader for anonymous access to public data.
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


class InstagramAgent(BaseCollectionAgent):
    """
    Instagram public profile agent.
    
    Collects:
    - Public profile info
    - Recent public posts
    - Hashtag searches (limited)
    
    Note: No login required for public profiles, but rate limited.
    """
    
    def __init__(self):
        super().__init__(agent_type="instagram")
        self._loader = None
    
    def _get_loader(self):
        """Lazy initialization of Instaloader"""
        if self._loader is None:
            try:
                import instaloader
                self._loader = instaloader.Instaloader(
                    download_pictures=False,
                    download_videos=False,
                    download_video_thumbnails=False,
                    download_geotags=False,
                    download_comments=False,
                    save_metadata=False,
                    compress_json=False
                )
            except ImportError:
                raise ImportError(
                    "instaloader package not installed. "
                    "Run: pip install instaloader"
                )
        return self._loader
    
    async def collect(
        self,
        investigation_id: str,
        query: str,
        user_id: str,
        justification: str,
        **kwargs
    ) -> CollectionResult:
        """Execute Instagram collection"""
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
        Execute Instagram profile collection.
        
        Args:
            query: Instagram username (without @)
            max_posts: Maximum posts to collect (default: 12)
            collection_type: 'profile' or 'hashtag' (default: profile)
        """
        max_posts = kwargs.get('max_posts', 12)
        collection_type = kwargs.get('collection_type', 'profile')
        
        loader = self._get_loader()
        items = []
        
        # Run sync code in executor
        loop = asyncio.get_event_loop()
        
        if collection_type == 'profile':
            items = await loop.run_in_executor(
                None,
                lambda: self._collect_profile(query, max_posts)
            )
        elif collection_type == 'hashtag':
            items = await loop.run_in_executor(
                None,
                lambda: self._collect_hashtag(query, max_posts)
            )
        else:
            raise ValueError(f"Unsupported collection type: {collection_type}")
        
        self.logger.info(f"Instagram collected {len(items)} items for: {query}")
        return items
    
    def _collect_profile(self, username: str, max_posts: int) -> List[CollectedItem]:
        """Collect posts from a public profile"""
        import instaloader
        
        loader = self._get_loader()
        items = []
        
        try:
            profile = instaloader.Profile.from_username(loader.context, username)
            
            # Add profile info as first item
            items.append(CollectedItem(
                source="instagram_profile",
                source_id=str(profile.userid),
                timestamp=int(time.time()),
                content=profile.biography or "",
                author_id=username,
                entities={
                    "urls": [profile.external_url] if profile.external_url else []
                },
                metadata={
                    "username": username,
                    "full_name": profile.full_name,
                    "followers": profile.followers,
                    "following": profile.followees,
                    "posts_count": profile.mediacount,
                    "is_verified": profile.is_verified,
                    "is_private": profile.is_private,
                    "external_url": profile.external_url,
                    "profile_pic_url": profile.profile_pic_url
                },
                confidence=0.9,
                jurisdiction="unknown"
            ))
            
            # Collect recent posts if public
            if not profile.is_private:
                post_count = 0
                for post in profile.get_posts():
                    if post_count >= max_posts:
                        break
                    
                    items.append(self._normalize_post(post, username))
                    post_count += 1
                    
        except Exception as e:
            self.logger.error(f"Instagram profile collection error: {e}")
            raise
        
        return items
    
    def _collect_hashtag(self, hashtag: str, max_posts: int) -> List[CollectedItem]:
        """Collect posts from a hashtag"""
        import instaloader
        
        loader = self._get_loader()
        items = []
        
        try:
            hashtag_obj = instaloader.Hashtag.from_name(loader.context, hashtag.lstrip('#'))
            
            post_count = 0
            for post in hashtag_obj.get_posts():
                if post_count >= max_posts:
                    break
                
                items.append(self._normalize_post(post, f"#{hashtag}"))
                post_count += 1
                
        except Exception as e:
            self.logger.error(f"Instagram hashtag collection error: {e}")
            raise
        
        return items
    
    def _normalize_post(self, post: Any, source_context: str) -> CollectedItem:
        """Normalize Instagram post to standard format"""
        # Extract hashtags from caption
        hashtags = []
        mentions = []
        
        if post.caption_hashtags:
            hashtags = [f"#{h}" for h in post.caption_hashtags]
        if post.caption_mentions:
            mentions = [f"@{m}" for m in post.caption_mentions]
        
        return CollectedItem(
            source="instagram_post",
            source_id=post.shortcode,
            timestamp=int(post.date_utc.timestamp()) if post.date_utc else int(time.time()),
            content=post.caption or "",
            author_id=post.owner_username,
            entities={
                "urls": [f"https://instagram.com/p/{post.shortcode}"],
                "hashtags": hashtags,
                "mentions": mentions
            },
            metadata={
                "shortcode": post.shortcode,
                "likes": post.likes,
                "comments": post.comments,
                "is_video": post.is_video,
                "video_view_count": post.video_view_count if post.is_video else None,
                "location": post.location.name if post.location else None,
                "source_context": source_context
            },
            confidence=0.8,
            jurisdiction="unknown"
        )


# Singleton instance
instagram_agent = InstagramAgent()
