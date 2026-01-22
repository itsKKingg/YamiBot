"""
Input Validator for YamiBot

This module provides comprehensive input validation and sanitization
to prevent abuse, injection attacks, and ensure message safety.
"""

import re
from typing import Optional, Tuple

from .logger import setup_logging

logger = setup_logging(__name__)


class InputValidator:
    """
    Validates and sanitizes user input before processing
    """
    
    # Configuration
    MAX_MESSAGE_LENGTH = 2000  # Discord limit
    MIN_MESSAGE_LENGTH = 1
    MAX_RESPONSE_LENGTH = 2000  # Discord limit
    
    # Suspicious patterns that could indicate injection attempts
    SUSPICIOUS_PATTERNS = [
        r'@everyone',
        r'@here',
    ]
    
    @staticmethod
    def validate_message(message: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user message before processing
        
        Args:
            message: User's message content
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if message is valid, False otherwise
            - error_message: Error description if invalid, None if valid
        """
        # Check if empty or whitespace only
        if not message or len(message.strip()) == 0:
            return False, "Message cannot be empty"
        
        # Check length constraints
        if len(message) > InputValidator.MAX_MESSAGE_LENGTH:
            return False, f"Message too long (max {InputValidator.MAX_MESSAGE_LENGTH} characters)"
        
        if len(message) < InputValidator.MIN_MESSAGE_LENGTH:
            return False, "Message too short"
        
        # Check for suspicious patterns (potential injection)
        for pattern in InputValidator.SUSPICIOUS_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                logger.warning(f"Suspicious pattern detected in message: {pattern}")
                return False, "Message contains suspicious content (@everyone/@here not allowed)"
        
        # Check for excessive special characters (spam detection)
        if len(message) > 0:
            special_char_count = sum(1 for c in message if not c.isalnum() and not c.isspace())
            special_char_ratio = special_char_count / len(message)
            
            if special_char_ratio > 0.7:  # More than 70% special chars = likely spam
                logger.warning(f"Excessive special characters detected: {special_char_ratio:.2%}")
                return False, "Message contains too many special characters"
        
        return True, None
    
    @staticmethod
    def sanitize_message(message: str) -> str:
        """
        Sanitize message for safety
        - Remove control characters (except newlines/tabs)
        - Normalize excessive whitespace
        - Remove null bytes
        
        Args:
            message: Raw message content
            
        Returns:
            Sanitized message
        """
        # Remove null bytes
        message = message.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        message = ''.join(char for char in message if ord(char) >= 32 or char in '\n\t')
        
        # Normalize excessive whitespace while preserving single newlines
        # Replace multiple spaces with single space
        message = re.sub(r' +', ' ', message)
        
        # Replace multiple newlines with double newline (paragraph break)
        message = re.sub(r'\n\n+', '\n\n', message)
        
        # Strip leading/trailing whitespace
        message = message.strip()
        
        return message
    
    @staticmethod
    def validate_response(response: str) -> str:
        """
        Ensure response is safe to send to Discord
        - Truncate if too long (preserving word boundaries)
        - Remove control characters
        - Ensure it's not empty
        
        Args:
            response: AI-generated response
            
        Returns:
            Validated and truncated response safe for Discord
        """
        if not response or len(response.strip()) == 0:
            logger.warning("Empty response generated, using fallback message")
            return "I'm sorry, I couldn't generate a proper response. Could you try rephrasing your question?"
        
        # Remove control characters except newlines and tabs
        response = ''.join(char for char in response if ord(char) >= 32 or char in '\n\t')
        
        # Truncate to Discord limit if needed, preserving word boundaries
        if len(response) > InputValidator.MAX_RESPONSE_LENGTH:
            logger.info(f"Truncating response from {len(response)} to {InputValidator.MAX_RESPONSE_LENGTH} chars")
            
            # Try to truncate at last space before limit
            truncate_point = InputValidator.MAX_RESPONSE_LENGTH - 3  # Leave room for "..."
            
            # Find last space before truncate point
            last_space = response.rfind(' ', 0, truncate_point)
            
            if last_space > InputValidator.MAX_RESPONSE_LENGTH * 0.8:  # If space is reasonably close to limit
                response = response[:last_space] + "..."
            else:
                # No good space found, hard truncate
                response = response[:truncate_point] + "..."
        
        return response
    
    @staticmethod
    def check_repeated_characters(message: str, threshold: int = 10) -> Tuple[bool, Optional[str]]:
        """
        Check for excessive repeated characters (spam detection)
        
        Args:
            message: Message to check
            threshold: Maximum allowed repeated characters
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Find longest sequence of repeated characters
        max_repeat = 0
        current_repeat = 1
        
        for i in range(1, len(message)):
            if message[i] == message[i-1]:
                current_repeat += 1
                max_repeat = max(max_repeat, current_repeat)
            else:
                current_repeat = 1
        
        if max_repeat > threshold:
            logger.warning(f"Excessive repeated characters detected: {max_repeat} in a row")
            return False, f"Message contains too many repeated characters ({max_repeat} in a row)"
        
        return True, None
