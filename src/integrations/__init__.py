"""
Integrations module for YamiBot

This module contains API integrations for music and other external services.
"""

from .genius_api import GeniusAPI
from .soundcloud_api import SoundCloudAPI
from .juice_wrld_api import JuiceWrldAPI  # For backward compatibility, keep original name

__all__ = ["GeniusAPI", "SoundCloudAPI", "JuiceWrldAPI"]
