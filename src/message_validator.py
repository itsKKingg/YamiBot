"""
Message Validator for YamiBot

This module validates Discord messages to determine if they should be
processed by the bot, including mention detection and content extraction.
"""

import discord
from typing import Tuple, Optional

from .utils.logger import setup_logging
from .utils.permissions import PermissionManager

logger = setup_logging(__name__)


class MessageValidator:
    """
    Validates Discord messages before processing
    """
    
    @staticmethod
    def should_process_message(message: discord.Message, bot: discord.Client) -> Tuple[bool, Optional[str]]:
        """
        Determine if bot should process this message
        
        Args:
            message: Discord message object
            bot: Discord bot client
            
        Returns:
            Tuple of (should_process, reason_if_not)
            - should_process: True if message should be processed
            - reason_if_not: Description of why not, or None if should process
        """
        # Ignore bot's own messages
        if message.author == bot.user:
            return False, "Own message"
        
        # Ignore other bots
        if message.author.bot:
            return False, "Message from bot"
        
        # Check if bot is mentioned
        if bot.user not in message.mentions:
            return False, "Bot not mentioned"
        
        # Check message content exists
        if not message.content or len(message.content.strip()) == 0:
            return False, "Empty message"
        
        # Optionally ignore DMs (can be configured)
        # For now, allow DMs but log them
        if isinstance(message.channel, discord.DMChannel):
            logger.info(f"Received DM from {message.author.id}")
            # return False, "DM not supported"
        
        return True, None
    
    @staticmethod
    async def check_permissions(
        message: discord.Message,
        perm_manager: PermissionManager
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user has permission to use bot
        
        Args:
            message: Discord message object
            perm_manager: Permission manager instance
            
        Returns:
            Tuple of (has_permission, denial_reason)
            - has_permission: True if user can use bot
            - denial_reason: Description if denied, None if allowed
        """
        user_id = message.author.id
        
        if not perm_manager.can_use_bot(user_id):
            permission_level = perm_manager.get_permission(user_id)
            
            # Check if user is blacklisted
            if user_id in perm_manager.blacklist_ids:
                logger.warning(f"Blocked blacklisted user {message.author} ({user_id})")
                return False, "You are not authorized to use this bot."
            
            # Check if whitelist mode is active
            if perm_manager.whitelist_ids and user_id not in perm_manager.whitelist_ids:
                logger.info(f"Denied non-whitelisted user {message.author} ({user_id})")
                return False, "This bot is currently in restricted mode. Contact an administrator for access."
            
            # Default denial
            return False, "You are not authorized to use this bot."
        
        return True, None
    
    @staticmethod
    def extract_message_content(message: discord.Message, bot: discord.Client) -> str:
        """
        Extract clean message content
        - Remove bot mentions
        - Remove @everyone/@here
        - Clean up whitespace
        
        Args:
            message: Discord message object
            bot: Discord bot client
            
        Returns:
            Cleaned message content
        """
        content = message.content
        
        # Remove bot mention (both formats)
        if bot.user:
            content = content.replace(f'<@!{bot.user.id}>', '')
            content = content.replace(f'<@{bot.user.id}>', '')
        
        # Remove other user mentions (convert to username)
        for mention in message.mentions:
            if mention != bot.user:
                # Replace mention with username for context
                content = content.replace(f'<@!{mention.id}>', f'@{mention.name}')
                content = content.replace(f'<@{mention.id}>', f'@{mention.name}')
        
        # Remove role mentions
        for role in message.role_mentions:
            content = content.replace(f'<@&{role.id}>', f'@{role.name}')
        
        # Remove @everyone and @here
        content = content.replace('@everyone', '')
        content = content.replace('@here', '')
        
        # Clean up excessive whitespace
        content = ' '.join(content.split())
        
        return content.strip()
    
    @staticmethod
    def is_command_message(message: discord.Message, bot: discord.Client) -> bool:
        """
        Check if message is a bot command (for admin functions)
        
        Args:
            message: Discord message object
            bot: Discord bot client
            
        Returns:
            True if message is a command, False otherwise
        """
        content = message.content.strip()
        
        # Check for mention-based command pattern
        if bot.user in message.mentions:
            # Extract content after mention
            extracted = MessageValidator.extract_message_content(message, bot)
            
            # Check if it starts with common command prefixes
            if extracted.startswith(('!', '/', '.', '$')):
                return True
        
        return False
    
    @staticmethod
    def format_validation_error(error_message: str) -> str:
        """
        Format validation error message for user display
        
        Args:
            error_message: Raw error message
            
        Returns:
            Formatted error message with emoji
        """
        return f"❌ {error_message}"
    
    @staticmethod
    def format_rate_limit_error(error_message: str) -> str:
        """
        Format rate limit error message for user display
        
        Args:
            error_message: Raw rate limit message
            
        Returns:
            Formatted rate limit message with emoji
        """
        return f"⏱️ {error_message}"
