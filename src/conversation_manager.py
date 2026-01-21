"""
Conversation Manager for YamiBot

This module manages conversation context and history for the Discord bot.
It tracks message history per thread/channel and maintains context for multi-turn conversations.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import time

from .utils.logger import setup_logging
from .utils.logger import log_memory_status

logger = setup_logging(__name__)

class ConversationManager:
    """
    Manages conversation context and history across threads and channels
    """
    
    def __init__(self, max_history: int = 10, context_timeout: int = 3600):
        """
        Initialize the conversation manager
        
        Args:
            max_history: Maximum number of messages to keep per conversation
            context_timeout: Time in seconds before conversation context expires
        """
        self.max_history = max_history
        self.context_timeout = context_timeout
        
        # Store conversations by thread_id or channel_id
        # Format: {conversation_id: {"messages": [...], "last_updated": datetime, "created_at": datetime}}
        self.conversations: Dict[int, Dict] = defaultdict(lambda: {
            "messages": [],
            "last_updated": datetime.utcnow(),
            "created_at": datetime.utcnow()
        })
        
        # Track active conversations
        self.active_conversations: set = set()
        
        # Memory tracking
        self.start_memory = log_memory_status()
        self.last_memory_check = time.time()
        
        logger.info(f"Conversation manager initialized (max_history={max_history}, timeout={context_timeout}s)")
    
    def _get_conversation_id(self, channel_id: int, thread_id: Optional[int] = None) -> int:
        """
        Get the conversation ID for a given channel/thread
        
        Args:
            channel_id: Discord channel ID
            thread_id: Discord thread ID (optional)
            
        Returns:
            Conversation ID to use for tracking
        """
        # Use thread_id if available, otherwise use channel_id
        return thread_id if thread_id else channel_id
    
    def add_message(self, channel_id: int, role: str, content: str, thread_id: Optional[int] = None) -> None:
        """
        Add a message to the conversation history
        
        Args:
            channel_id: Discord channel ID
            role: Message role ("user" or "assistant")
            content: Message content
            thread_id: Discord thread ID (optional)
        """
        conversation_id = self._get_conversation_id(channel_id, thread_id)
        
        # Check if conversation has expired
        if self._is_conversation_expired(conversation_id):
            logger.info(f"Conversation {conversation_id} expired, clearing history")
            self.clear_conversation(channel_id, thread_id)
        
        # Add message to history
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }
        
        self.conversations[conversation_id]["messages"].append(message)
        self.conversations[conversation_id]["last_updated"] = datetime.utcnow()
        
        # Trim history if it exceeds max_history
        if len(self.conversations[conversation_id]["messages"]) > self.max_history:
            self.conversations[conversation_id]["messages"] = \
                self.conversations[conversation_id]["messages"][-self.max_history:]
        
        # Mark as active
        self.active_conversations.add(conversation_id)
        
        logger.debug(f"Added {role} message to conversation {conversation_id} (total: {len(self.conversations[conversation_id]['messages'])})")
    
    def get_conversation_history(self, channel_id: int, thread_id: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get the conversation history for a given channel/thread
        
        Args:
            channel_id: Discord channel ID
            thread_id: Discord thread ID (optional)
            
        Returns:
            List of message dictionaries (role, content)
        """
        conversation_id = self._get_conversation_id(channel_id, thread_id)
        
        # Check if conversation has expired
        if self._is_conversation_expired(conversation_id):
            logger.info(f"Conversation {conversation_id} expired, returning empty history")
            self.clear_conversation(channel_id, thread_id)
            return []
        
        # Return messages without timestamps (API format)
        messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.conversations[conversation_id]["messages"]
        ]
        
        return messages
    
    def get_conversation_messages(self, channel_id: int, thread_id: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get conversation messages with optional limit
        
        Args:
            channel_id: Discord channel ID
            thread_id: Discord thread ID (optional)
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        messages = self.get_conversation_history(channel_id, thread_id)
        
        if limit and len(messages) > limit:
            return messages[-limit:]
        
        return messages
    
    def clear_conversation(self, channel_id: int, thread_id: Optional[int] = None) -> None:
        """
        Clear the conversation history for a given channel/thread
        
        Args:
            channel_id: Discord channel ID
            thread_id: Discord thread ID (optional)
        """
        conversation_id = self._get_conversation_id(channel_id, thread_id)
        
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            self.active_conversations.discard(conversation_id)
            logger.info(f"Cleared conversation {conversation_id}")
    
    def _is_conversation_expired(self, conversation_id: int) -> bool:
        """
        Check if a conversation has expired based on timeout
        
        Args:
            conversation_id: Conversation ID to check
            
        Returns:
            True if expired, False otherwise
        """
        if conversation_id not in self.conversations:
            return False
        
        last_updated = self.conversations[conversation_id]["last_updated"]
        time_elapsed = (datetime.utcnow() - last_updated).total_seconds()
        
        return time_elapsed > self.context_timeout
    
    def get_active_conversation_count(self) -> int:
        """
        Get the number of active conversations
        
        Returns:
            Number of active conversations
        """
        # Clean up expired conversations
        self._cleanup_expired_conversations()
        return len(self.active_conversations)
    
    def _cleanup_expired_conversations(self) -> None:
        """
        Clean up expired conversations from memory
        """
        expired = []
        
        for conversation_id in list(self.conversations.keys()):
            if self._is_conversation_expired(conversation_id):
                expired.append(conversation_id)
        
        for conversation_id in expired:
            del self.conversations[conversation_id]
            self.active_conversations.discard(conversation_id)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired conversations")
    
    def get_conversation_stats(self) -> Dict[str, any]:
        """
        Get statistics about conversations
        
        Returns:
            Dictionary with conversation statistics
        """
        self._cleanup_expired_conversations()
        
        total_messages = sum(
            len(conv["messages"])
            for conv in self.conversations.values()
        )
        
        return {
            "active_conversations": len(self.active_conversations),
            "total_messages": total_messages,
            "max_history": self.max_history,
            "context_timeout": self.context_timeout
        }
    
    async def start_cleanup_task(self, cleanup_interval: int = 300) -> None:
        """
        Start a background task to periodically clean up expired conversations
        
        Args:
            cleanup_interval: Time in seconds between cleanup runs (default: 5 minutes)
        """
        while True:
            try:
                await asyncio.sleep(cleanup_interval)
                await self.cleanup_old_conversations()
                await self._log_memory_status()
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}", exc_info=True)
    
    async def cleanup_old_conversations(self):
        """Remove conversations older than timeout"""
        now = time.time()
        expired = []
        
        for conversation_id, conv_data in list(self.conversations.items()):
            last_activity = conv_data["last_updated"]
            if isinstance(last_activity, datetime):
                last_activity_timestamp = last_activity.timestamp()
            else:
                last_activity_timestamp = last_activity
            
            if now - last_activity_timestamp > self.context_timeout:
                expired.append(conversation_id)
        
        for conversation_id in expired:
            del self.conversations[conversation_id]
            self.active_conversations.discard(conversation_id)
            logger.debug(f"Cleaned up conversation {conversation_id}")
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired conversations")
    
    async def _log_memory_status(self):
        """Log memory status and check for memory leaks"""
        current_time = time.time()
        
        # Log memory status every 10 minutes (600 seconds)
        if current_time - self.last_memory_check >= 600:
            memory_info = log_memory_status()
            
            # Check for significant memory growth
            if self.start_memory and "rss_mb" in memory_info:
                memory_growth = memory_info["rss_mb"] - self.start_memory["rss_mb"]
                if memory_growth > 50:  # 50MB growth threshold
                    logger.warning(f"Memory growth detected: {memory_growth:.2f}MB since startup")
                    
                    # Force aggressive cleanup if memory growth is extreme
                    if memory_growth > 100:  # 100MB growth
                        logger.warning("Performing aggressive cleanup due to high memory usage")
                        await self.cleanup_old_conversations()
            
            self.last_memory_check = current_time
