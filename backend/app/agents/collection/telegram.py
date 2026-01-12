"""
Telegram Public Channel Agent - Scrapes public Telegram channels.
Uses Telethon for Telegram API access.
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


class TelegramAgent(BaseCollectionAgent):
    """
    Telegram public channel agent.
    
    Collects:
    - Public channel messages
    - Channel info and member counts
    - Media metadata
    
    Requires:
    - TELEGRAM_API_ID and TELEGRAM_API_HASH from https://my.telegram.org
    """
    
    def __init__(self):
        super().__init__(agent_type="telegram")
        self._client = None
        self._connected = False
    
    async def _get_client(self):
        """Lazy initialization of Telegram client"""
        if self._client is None:
            try:
                from telethon import TelegramClient
                from telethon.sessions import StringSession
            except ImportError:
                raise ImportError(
                    "telethon package not installed. "
                    "Run: pip install telethon"
                )
            
            api_id = getattr(settings, 'TELEGRAM_API_ID', None)
            api_hash = getattr(settings, 'TELEGRAM_API_HASH', None)
            
            if not api_id or not api_hash:
                raise ValueError(
                    "TELEGRAM_API_ID and TELEGRAM_API_HASH required. "
                    "Get them from https://my.telegram.org"
                )
            
            self._client = TelegramClient(
                StringSession(),
                int(api_id),
                api_hash
            )
        
        if not self._connected:
            await self._client.start()
            self._connected = True
            
        return self._client
    
    async def collect(
        self,
        investigation_id: str,
        query: str,
        user_id: str,
        justification: str,
        **kwargs
    ) -> CollectionResult:
        """Execute Telegram channel collection"""
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
        Execute Telegram channel collection.
        
        Args:
            query: Channel username (e.g., 'duaborern' or '@channel_name')
            max_messages: Maximum messages to collect (default: 100)
            include_media: Whether to include media metadata (default: True)
        """
        max_messages = kwargs.get('max_messages', 100)
        include_media = kwargs.get('include_media', True)
        
        client = await self._get_client()
        items = []
        
        # Remove @ prefix if present
        channel_username = query.lstrip('@')
        
        try:
            from telethon.tl.functions.channels import GetFullChannelRequest
            
            # Get channel entity
            channel = await client.get_entity(channel_username)
            
            # Get channel info
            full_channel = await client(GetFullChannelRequest(channel))
            
            # Collect messages
            async for message in client.iter_messages(channel, limit=max_messages):
                if message.text or (include_media and message.media):
                    item = self._normalize_message(message, channel_username)
                    items.append(item)
            
            self.logger.info(
                f"Telegram collected {len(items)} messages from @{channel_username}"
            )
            
        except Exception as e:
            self.logger.error(f"Telegram collection error: {e}")
            raise
        
        return items
    
    def _normalize_message(self, message: Any, channel: str) -> CollectedItem:
        """Normalize Telegram message to standard format"""
        # Extract entities (URLs, mentions)
        entities = {
            "urls": [],
            "mentions": [],
            "hashtags": []
        }
        
        if message.entities:
            for entity in message.entities:
                entity_type = type(entity).__name__
                if 'Url' in entity_type and message.text:
                    start = entity.offset
                    end = start + entity.length
                    entities["urls"].append(message.text[start:end])
                elif 'Mention' in entity_type and message.text:
                    start = entity.offset
                    end = start + entity.length
                    entities["mentions"].append(message.text[start:end])
                elif 'Hashtag' in entity_type and message.text:
                    start = entity.offset
                    end = start + entity.length
                    entities["hashtags"].append(message.text[start:end])
        
        return CollectedItem(
            source="telegram",
            source_id=str(message.id),
            timestamp=int(message.date.timestamp()) if message.date else int(time.time()),
            content=message.text or "[Media content]",
            author_id=f"@{channel}",
            entities=entities,
            metadata={
                "channel": channel,
                "message_id": message.id,
                "views": message.views or 0,
                "forwards": message.forwards or 0,
                "has_media": message.media is not None,
                "reply_to": message.reply_to_msg_id if message.reply_to else None
            },
            confidence=0.85,
            jurisdiction="unknown"
        )
    
    async def get_channel_info(self, channel_username: str) -> Dict[str, Any]:
        """Get detailed channel information"""
        client = await self._get_client()
        
        from telethon.tl.functions.channels import GetFullChannelRequest
        
        channel = await client.get_entity(channel_username.lstrip('@'))
        full = await client(GetFullChannelRequest(channel))
        
        return {
            "title": channel.title,
            "username": channel.username,
            "participants_count": full.full_chat.participants_count,
            "about": full.full_chat.about,
            "created": channel.date.isoformat() if channel.date else None
        }
    
    async def close(self):
        """Close Telegram client connection"""
        if self._client and self._connected:
            await self._client.disconnect()
            self._connected = False


# Singleton instance (async initialization required)
telegram_agent = TelegramAgent()
