"""
Error Handler for YamiBot

This module provides user-friendly error messages and error handling utilities.
"""

from typing import Optional


class UserFriendlyError(Exception):
    """Custom exception for errors that should be shown to users"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        """
        Initialize a user-friendly error
        
        Args:
            message: User-facing error message
            details: Technical details for logging
        """
        super().__init__(message)
        self.message = message
        self.details = details


def format_error_for_user(error: Exception) -> str:
    """
    Format an exception into a user-friendly message
    
    Args:
        error: The exception to format
        
    Returns:
        User-friendly error message
    """
    # If it's already a user-friendly error, use its message
    if isinstance(error, UserFriendlyError):
        return error.message
    
    # Map common exceptions to user-friendly messages
    error_type = type(error).__name__
    
    if "timeout" in error_type.lower() or "TimeoutError" in error_type:
        return "The request took too long. Please try again."
    
    if "connection" in error_type.lower() or "ConnectionError" in error_type:
        return "Connection error. Please try again in a moment."
    
    if "rate" in str(error).lower() and "limit" in str(error).lower():
        return "Rate limit reached. Please wait a moment before trying again."
    
    if "unauthorized" in str(error).lower() or "401" in str(error):
        return "Authentication error. Please contact the bot administrator."
    
    if "forbidden" in str(error).lower() or "403" in str(error):
        return "Permission denied. Please contact the bot administrator."
    
    if "not found" in str(error).lower() or "404" in str(error):
        return "Resource not found. Please try again."
    
    if "500" in str(error) or "internal server" in str(error).lower():
        return "Server error. Please try again in a moment."
    
    # Default generic message
    return "An error occurred while processing your request. Please try again."
