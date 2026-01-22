"""
Permission System for YamiBot

This module provides user permission management with support for
whitelists, blacklists, and role-based access control.
"""

from enum import Enum
from typing import List, Set

from .logger import setup_logging

logger = setup_logging(__name__)


class Permission(Enum):
    """Permission levels for bot users"""
    NONE = 0      # Blocked/no access
    USER = 1      # Regular user
    TRUSTED = 2   # Trusted user with higher limits
    ADMIN = 3     # Administrator with full access


class PermissionManager:
    """
    Manages user permissions and access control
    """
    
    def __init__(self, config):
        """
        Initialize permission manager with configuration
        
        Args:
            config: Configuration object with permission settings
        """
        self.config = config
        
        # Load permission lists from config
        self.admin_ids: Set[int] = self._parse_user_ids(
            getattr(config, 'admin_user_ids', ''),
            'admins'
        )
        
        self.trusted_ids: Set[int] = self._parse_user_ids(
            getattr(config, 'trusted_user_ids', ''),
            'trusted users'
        )
        
        self.whitelist_ids: Set[int] = self._parse_user_ids(
            getattr(config, 'whitelist_user_ids', ''),
            'whitelist'
        )
        
        self.blacklist_ids: Set[int] = self._parse_user_ids(
            getattr(config, 'blacklist_user_ids', ''),
            'blacklist'
        )
        
        # Log permission configuration
        self._log_permission_status()
    
    def _parse_user_ids(self, id_string: str, list_name: str) -> Set[int]:
        """
        Parse comma-separated user IDs from string
        
        Args:
            id_string: Comma-separated string of user IDs
            list_name: Name of the list for logging
            
        Returns:
            Set of parsed user IDs
        """
        if not id_string or not id_string.strip():
            return set()
        
        user_ids = set()
        for id_str in id_string.split(','):
            id_str = id_str.strip()
            if id_str:
                try:
                    user_ids.add(int(id_str))
                except ValueError:
                    logger.warning(f"Invalid user ID in {list_name}: {id_str}")
        
        return user_ids
    
    def _log_permission_status(self):
        """Log current permission configuration"""
        logger.info("Permission system initialized:")
        logger.info(f"  - Admins: {len(self.admin_ids)}")
        logger.info(f"  - Trusted users: {len(self.trusted_ids)}")
        logger.info(f"  - Whitelist: {len(self.whitelist_ids)} {'(ACTIVE - restricted mode)' if self.whitelist_ids else '(inactive)'}")
        logger.info(f"  - Blacklist: {len(self.blacklist_ids)}")
        
        if self.whitelist_ids:
            logger.warning("Whitelist mode active - only whitelisted users can use the bot")
    
    def get_permission(self, user_id: int) -> Permission:
        """
        Determine user's permission level
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Permission level for the user
        """
        # Blacklist takes precedence over everything
        if user_id in self.blacklist_ids:
            logger.debug(f"User {user_id} is blacklisted")
            return Permission.NONE
        
        # Admin permission
        if user_id in self.admin_ids:
            return Permission.ADMIN
        
        # Trusted user permission
        if user_id in self.trusted_ids:
            return Permission.TRUSTED
        
        # If whitelist is active and user not on it, deny access
        if self.whitelist_ids and user_id not in self.whitelist_ids:
            logger.debug(f"User {user_id} not in whitelist (restricted mode)")
            return Permission.NONE
        
        # Default: regular user permission
        return Permission.USER
    
    def can_use_bot(self, user_id: int) -> bool:
        """
        Check if user can use the bot
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if user can use bot, False otherwise
        """
        return self.get_permission(user_id) != Permission.NONE
    
    def can_admin(self, user_id: int) -> bool:
        """
        Check if user has admin privileges
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if user is an admin, False otherwise
        """
        return self.get_permission(user_id) == Permission.ADMIN
    
    def is_trusted(self, user_id: int) -> bool:
        """
        Check if user is trusted (admin or trusted role)
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if user is trusted or admin, False otherwise
        """
        perm = self.get_permission(user_id)
        return perm in (Permission.TRUSTED, Permission.ADMIN)
    
    def get_user_info(self, user_id: int) -> dict:
        """
        Get detailed permission information for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with user's permission information
        """
        permission = self.get_permission(user_id)
        
        return {
            'user_id': user_id,
            'permission_level': permission.name,
            'can_use_bot': permission != Permission.NONE,
            'is_admin': permission == Permission.ADMIN,
            'is_trusted': permission in (Permission.TRUSTED, Permission.ADMIN),
            'is_blacklisted': user_id in self.blacklist_ids,
            'is_whitelisted': user_id in self.whitelist_ids if self.whitelist_ids else None
        }
    
    def add_to_blacklist(self, user_id: int) -> bool:
        """
        Add user to blacklist (admin function)
        
        Args:
            user_id: Discord user ID to blacklist
            
        Returns:
            True if added, False if already blacklisted
        """
        if user_id in self.blacklist_ids:
            return False
        
        self.blacklist_ids.add(user_id)
        logger.info(f"User {user_id} added to blacklist")
        return True
    
    def remove_from_blacklist(self, user_id: int) -> bool:
        """
        Remove user from blacklist (admin function)
        
        Args:
            user_id: Discord user ID to unblock
            
        Returns:
            True if removed, False if not in blacklist
        """
        if user_id not in self.blacklist_ids:
            return False
        
        self.blacklist_ids.remove(user_id)
        logger.info(f"User {user_id} removed from blacklist")
        return True
