"""
User Preferences Manager for YamiBot

This module manages per-user and per-guild preferences for model selection
and other customizable behaviors.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta

from .logger import setup_logging

logger = setup_logging(__name__)


class UserPreferences:
    """
    Manages user and guild preferences for model selection
    """
    
    def __init__(self):
        """Initialize the preferences manager"""
        # User preferences: {user_id: {preference_type: value}}
        self.user_preferences: Dict[int, Dict[str, any]] = {}
        
        # Guild preferences: {guild_id: {preference_type: value}}
        self.guild_preferences: Dict[int, Dict[str, any]] = {}
        
        # Timestamps for cleanup
        self.user_timestamps: Dict[int, datetime] = {}
        self.guild_timestamps: Dict[int, datetime] = {}
        
        logger.info("UserPreferences manager initialized")
    
    def set_user_preference(self, user_id: int, preference_type: str, value: any) -> None:
        """
        Set a preference for a specific user
        
        Args:
            user_id: Discord user ID
            preference_type: Type of preference (e.g., "model", "intent_model")
            value: Preference value
        """
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        self.user_preferences[user_id][preference_type] = value
        self.user_timestamps[user_id] = datetime.utcnow()
        
        logger.debug(f"Set user preference for {user_id}: {preference_type} = {value}")
    
    def get_user_preference(self, user_id: int, preference_type: str) -> Optional[any]:
        """
        Get a preference for a specific user
        
        Args:
            user_id: Discord user ID
            preference_type: Type of preference to retrieve
            
        Returns:
            Preference value or None if not set
        """
        if user_id not in self.user_preferences:
            return None
        
        return self.user_preferences[user_id].get(preference_type)
    
    def get_user_model_preference(self, user_id: int, intent: Optional[str] = None) -> Optional[str]:
        """
        Get model preference for a user, optionally filtered by intent
        
        Args:
            user_id: Discord user ID
            intent: Optional intent type to check for intent-specific preference
            
        Returns:
            Model name or None if not set
        """
        # Check intent-specific preference first
        if intent:
            intent_pref = self.get_user_preference(user_id, f"model_{intent}")
            if intent_pref:
                return intent_pref
        
        # Fall back to general model preference
        return self.get_user_preference(user_id, "model")
    
    def clear_user_preference(self, user_id: int, preference_type: str) -> bool:
        """
        Clear a specific preference for a user
        
        Args:
            user_id: Discord user ID
            preference_type: Type of preference to clear
            
        Returns:
            True if preference was cleared, False if it didn't exist
        """
        if user_id not in self.user_preferences:
            return False
        
        if preference_type in self.user_preferences[user_id]:
            del self.user_preferences[user_id][preference_type]
            self.user_timestamps[user_id] = datetime.utcnow()
            logger.debug(f"Cleared user preference for {user_id}: {preference_type}")
            return True
        
        return False
    
    def set_guild_preference(self, guild_id: int, preference_type: str, value: any) -> None:
        """
        Set a preference for a specific guild
        
        Args:
            guild_id: Discord guild ID
            preference_type: Type of preference
            value: Preference value
        """
        if guild_id not in self.guild_preferences:
            self.guild_preferences[guild_id] = {}
        
        self.guild_preferences[guild_id][preference_type] = value
        self.guild_timestamps[guild_id] = datetime.utcnow()
        
        logger.debug(f"Set guild preference for {guild_id}: {preference_type} = {value}")
    
    def get_guild_preference(self, guild_id: int, preference_type: str) -> Optional[any]:
        """
        Get a preference for a specific guild
        
        Args:
            guild_id: Discord guild ID
            preference_type: Type of preference to retrieve
            
        Returns:
            Preference value or None if not set
        """
        if guild_id not in self.guild_preferences:
            return None
        
        return self.guild_preferences[guild_id].get(preference_type)
    
    def get_effective_preference(
        self,
        user_id: int,
        guild_id: Optional[int] = None,
        preference_type: str = "model",
        intent: Optional[str] = None
    ) -> Optional[any]:
        """
        Get the effective preference, checking user first then guild
        
        Args:
            user_id: Discord user ID
            guild_id: Optional Discord guild ID
            preference_type: Type of preference to retrieve
            intent: Optional intent type for intent-specific preferences
            
        Returns:
            Preference value or None if not set
        """
        # Check user preference first
        user_pref = self.get_user_model_preference(user_id, intent)
        if user_pref:
            return user_pref
        
        # Fall back to guild preference
        if guild_id:
            guild_pref = self.get_guild_preference(guild_id, preference_type)
            if guild_pref:
                return guild_pref
        
        return None
    
    def get_all_user_preferences(self, user_id: int) -> Optional[Dict[str, any]]:
        """
        Get all preferences for a specific user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary of all preferences or None if user has none
        """
        return self.user_preferences.get(user_id, {}).copy() if user_id in self.user_preferences else None
    
    def get_all_guild_preferences(self, guild_id: int) -> Optional[Dict[str, any]]:
        """
        Get all preferences for a specific guild
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary of all preferences or None if guild has none
        """
        return self.guild_preferences.get(guild_id, {}).copy() if guild_id in self.guild_preferences else None
    
    def clear_all_user_preferences(self, user_id: int) -> int:
        """
        Clear all preferences for a specific user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Number of preferences cleared
        """
        if user_id not in self.user_preferences:
            return 0
        
        count = len(self.user_preferences[user_id])
        del self.user_preferences[user_id]
        self.user_timestamps.pop(user_id, None)
        
        logger.debug(f"Cleared {count} preferences for user {user_id}")
        return count
    
    def clear_all_guild_preferences(self, guild_id: int) -> int:
        """
        Clear all preferences for a specific guild
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Number of preferences cleared
        """
        if guild_id not in self.guild_preferences:
            return 0
        
        count = len(self.guild_preferences[guild_id])
        del self.guild_preferences[guild_id]
        self.guild_timestamps.pop(guild_id, None)
        
        logger.debug(f"Cleared {count} preferences for guild {guild_id}")
        return count
    
    async def cleanup_old_preferences(self, max_age_days: int = 30) -> int:
        """
        Clean up old preferences that haven't been accessed
        
        Args:
            max_age_days: Maximum age in days before cleanup
            
        Returns:
            Number of preferences cleaned up
        """
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
        cleaned = 0
        
        # Clean up old user preferences
        for user_id in list(self.user_timestamps.keys()):
            if self.user_timestamps[user_id] < cutoff_time:
                if user_id in self.user_preferences:
                    cleaned += len(self.user_preferences[user_id])
                    del self.user_preferences[user_id]
                del self.user_timestamps[user_id]
        
        # Clean up old guild preferences
        for guild_id in list(self.guild_timestamps.keys()):
            if self.guild_timestamps[guild_id] < cutoff_time:
                if guild_id in self.guild_preferences:
                    cleaned += len(self.guild_preferences[guild_id])
                    del self.guild_preferences[guild_id]
                del self.guild_timestamps[guild_id]
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old preferences (older than {max_age_days} days)")
        
        return cleaned
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get statistics about stored preferences
        
        Returns:
            Dictionary with preference statistics
        """
        user_pref_count = sum(len(prefs) for prefs in self.user_preferences.values())
        guild_pref_count = sum(len(prefs) for prefs in self.guild_preferences.values())
        
        return {
            "total_users": len(self.user_preferences),
            "total_user_preferences": user_pref_count,
            "total_guilds": len(self.guild_preferences),
            "total_guild_preferences": guild_pref_count,
            "total_preferences": user_pref_count + guild_pref_count
        }
