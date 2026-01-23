"""
Integrations module for external API wrappers.

Provides clean interfaces to external music and data APIs:
- Juice WRLD API for Juice WRLD catalog
- Genius API for lyrics and annotations
- SoundCloud API for track search and embedding
"""

from .juicewrld_api import JuiceWRLDAPI
from .genius_api import GeniusAPI
from .soundcloud_api import SoundCloudAPI

__all__ = [
    "JuiceWRLDAPI",
    "GeniusAPI",
    "SoundCloudAPI",
]
