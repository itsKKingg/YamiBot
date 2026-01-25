"""
Intent Detector for YamiBot

This module classifies user intent from natural language messages.
Supports keyword-based classification for reliable detection without LLM overhead.
"""

from typing import Dict, Optional, List
import re

from .utils.logger import setup_logging

logger = setup_logging(__name__)


class IntentDetector:
    """
    Detects user intent from natural language messages using keyword patterns
    """

    # Intent definitions with keywords and patterns (ordered by specificity)
    INTENTS = {
        "clear_memory": {
            "keywords": [
                "clear my memory", "clear memory", "erase memory", "forget everything",
                "reset memory", "wipe memory", "clear conversation", "reset conversation",
                "start over", "new conversation", "clear history"
            ],
            "patterns": [
                r"\bclear\s+(my\s+)?memory\b",
                r"\berase\s+(my\s+)?memory\b",
                r"\bforget\s+everything\b",
                r"\breset\s+(my\s+)?(memory|conversation)\b",
                r"\bwipe\s+(my\s+)?memory\b",
                r"\bstart\s+over\b"
            ],
            "confidence": 0.9
        },
        "view_memory": {
            "keywords": [
                "what do you remember", "show my memory", "my memory", "show conversation",
                "what do you know", "conversation history", "our conversation",
                "what have we discussed", "what did we talk about", "show history"
            ],
            "patterns": [
                r"\bwhat\s+do\s+you\s+remember\b",
                r"\bshow\s+(my\s+)?memory\b",
                r"\bmy\s+memory\b",
                r"\bshow\s+conversation\b",
                r"\bwhat\s+do\s+you\s+know\b",
                r"\bconversation\s+history\b",
                r"\bwhat\s+have\s+we\s+discussed\b",
                r"\bwhat\s+did\s+we\s+talk\s+about\b"
            ],
            "confidence": 0.85
        },
        "clear_specific": {
            "keywords": [
                "forget last", "forget about", "remove last", "delete last",
                "clear last"
            ],
            "patterns": [
                r"\bforget\s+last\s+(\d+)\s+messages?\b",
                r"\bremove\s+last\s+(\d+)\s+messages?\b",
                r"\bdelete\s+last\s+(\d+)\s+messages?\b",
                r"\bclear\s+last\s+(\d+)\s+messages?\b"
            ],
            "confidence": 0.9,
            "extract_param": True
        },
        # ============ JUICE WRLD API (PRIMARY MUSIC SOURCE) ============
        "juice_random": {
            "keywords": [
                "random track", "random song", "random juice", "radio", "shuffle",
                "surprise me", "play something random"
            ],
            "patterns": [
                r"\brandom\s+(?:juice\s+)?(?:track|song)\b",
                r"\b(?:juice\s+)?radio\b",
                r"\bshuffle\b"
            ],
            "confidence": 0.9
        },
        "juice_stats": {
            "keywords": [
                "juice stats", "how many juice", "how many songs", "database stats",
                "overall stats", "song stats", "stats"
            ],
            "patterns": [
                r"\bhow\s+many\s+(?:juice\s+)?songs?\b",
                r"\b(?:juice\s+)?stats\b",
                r"\bdatabase\s+stats\b"
            ],
            "confidence": 0.85
        },
        "juice_eras_list": {
            "keywords": [
                "list eras", "show eras", "eras", "era list", "timeline"
            ],
            "patterns": [
                r"\blist\s+all\s+eras\b",
                r"\bshow\s+all\s+eras\b",
                r"\beras\b",
                r"\bera\s+timeline\b"
            ],
            "confidence": 0.8
        },
        "juice_era_filter": {
            "keywords": [
                "songs from", "from era", "era songs"
            ],
            "patterns": [
                r"\bsongs?\s+from\s+([^?]+?)(?:\s+era)?\b",
                r"\bfrom\s+the\s+([^?]+?)\s+era\b",
                r"\b([^?]+?)\s+era\s+songs\b"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_category_filter": {
            "keywords": [
                "unreleased", "unsurfaced", "released", "studio session", "studio sessions"
            ],
            "patterns": [
                r"\b(?:show\s+me\s+)?(released|unreleased|unsurfaced|studio_session|studio\s+sessions?)\s+(?:songs?|tracks?)\b",
                r"\bsongs?\s+in\s+(released|unreleased|unsurfaced|studio_session)\b"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_lyric_search": {
            "keywords": [
                "find lyrics with", "songs with lyric", "songs containing", "lyrics with"
            ],
            "patterns": [
                r"\bfind\s+lyrics\s+with\s+([^?]+)",
                r"\bsongs?\s+containing\s+([^?]+)",
                r"\bsongs?\s+with\s+lyrics?\s+([^?]+)",
                r"\blyrics?\s+search\s+([^?]+)"
            ],
            "confidence": 0.9,
            "extract_param": True
        },
        "juice_producer_filter": {
            "keywords": [
                "produced by", "songs produced by", "what was produced by"
            ],
            "patterns": [
                r"\bsongs?\s+produced\s+by\s+([^?]+)",
                r"\bwhat\s+was\s+produced\s+by\s+([^?]+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_song_info": {
            "keywords": [
                "song details", "details for", "when was", "where was", "who produced", "recorded", "produced"
            ],
            "patterns": [
                r"\bwho\s+produced\s+([^?]+)\b",
                r"\bwhen\s+was\s+([^?]+)\s+recorded\b",
                r"\bwhere\s+was\s+([^?]+)\s+recorded\b",
                r"\bdetails\s+for\s+([^?]+)",
                r"\bsong\s+details\s+for\s+([^?]+)",
                r"\b(?:song\s+)?id\s+(\d+)\b"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_cover_art": {
            "keywords": [
                "cover art", "artwork", "album art"
            ],
            "patterns": [
                r"\b(?:cover\s+art|artwork|album\s+art)\s+(?:for\s+)?([^?]+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_stream": {
            "keywords": [
                "streaming link", "listen link", "listen here", "download link", "stream"
            ],
            "patterns": [
                r"\b(?:streaming\s+link|listen\s+link|download\s+link)\s+(?:for\s+)?([^?]+)",
                r"\blisten\s+to\s+([^?]+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_collection": {
            "keywords": [
                "zip", "archive", "collection", "download era", "download zip"
            ],
            "patterns": [
                r"\b(?:make|generate|create)\s+(?:a\s+)?(?:zip|archive)\s+(?:of\s+)?([^?]+)",
                r"\bdownload\s+(?:a\s+)?(?:zip|archive)\s+(?:of\s+)?([^?]+)",
                r"\bzip\s+of\s+([^?]+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_search": {
            "keywords": [
                "find juice song", "search juice", "juice song", "juice track"
            ],
            "patterns": [
                # Specific Juice WRLD song searches with song titles
                r"\b(?:search|find)\s+(?:for\s+)?(?:juice\s+(?:song|track)\s+)?([^?]+?)(?:\s+(?:by|from)\s+juice)?\b",
                r"\bfind\s+(?:me\s+)?(?:juice\s+(?:song|track)\s+)?([^?]+?)(?:\s+(?:by|from)\s+juice)?\b",
                # Song/track searches specifically mentioning Juice WRLD
                r"\b(?:search|find)\s+(?:a\s+)?(?:song|track)\s+([^?]+?)(?:\s+(?:by|from)\s+juice)?\b",
                r"\b(?:search|find)\s+(?:a\s+)?(?:song|track)\s+(?:by|from)\s+juice\s+([^?]+)\b"
            ],
            "confidence": 0.8,
            "extract_param": True
        },
        "music_lyrics": {
            "keywords": [
                "lyrics", "lyric", "words to", "what are the lyrics",
                "show me lyrics", "get lyrics", "find lyrics"
            ],
            "patterns": [
                r"\b(?:lyrics?|words?)\s+(?:for\s+)?([^?]+)",
                r"\bwhat\s+are\s+the\s+lyrics?\s+for\s+([^?]+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "music_search": {
            "keywords": [
                "find song", "search for song", "what song",
                "soundcloud", "find music", "search music", "find track"
            ],
            "patterns": [
                r"\bfind\s+(?:a\s+)?song\s+(?:by\s+)?([^?]+)",
                r"\bsearch\s+(?:for\s+)?(?:a\s+)?song\s+(?:by\s+)?([^?]+)",
                r"\bwhat(?:'s|s)?\s+the\s+song\s+(?:that\s+goes\s+)?([^?]+)",
                r"\bsoundcloud\s+(?:search\s+)?([^?]+)",
                r"\bfind\s+(?:on\s+)?soundcloud\s+([^?]+)",
                r"\bfind\s+music\s+([^?]+)",
                r"\bsearch\s+music\s+([^?]+)",
                r"\bfind\s+track\s+([^?]+)"
            ],
            "confidence": 0.8,
            "extract_param": True
        },
        "music_artist": {
            "keywords": [
                "tell me about", "who is", "artist", "singer", "rapper",
                "musician", "band", "artist info", "artist bio"
            ],
            "patterns": [
                r"\btell\s+me\s+about\s+([^?]+)",
                r"\bwho\s+is\s+([^?]+)",
                r"\bartist\s+info\s+for\s+([^?]+)",
                r"\bartist\s+bio\s+for\s+([^?]+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "music_annotation": {
            "keywords": [
                "what does", "meaning of", "annotation",
                "what's the meaning", "interpretation", "explain lyrics"
            ],
            "patterns": [
                r"\bwhat\s+does\s+([^?]+)\s+mean\b",
                r"\bmeaning\s+of\s+([^?]+)",
                r"\bexplain\s+(?:lyrics?|song)\s+([^?]+)",
                r"\bwhat(?:'s|s)\s+the\s+meaning\s+of\s+([^?]+)",
                r"\bannotation\s+for\s+([^?]+)"
            ],
            "confidence": 0.8,
            "extract_param": True
        },
        "model_switch": {
            "keywords": [
                "use model", "switch to", "change model", "switch model",
                "use gemini", "use cerebras", "use groq", "use mistral",
                "change to"
            ],
            "patterns": [
                r"\buse\s+(?:model\s+)?([^?]+)",
                r"\bswitch\s+(?:to\s+)?(?:model\s+)?([^?]+)",
                r"\bchange\s+(?:to\s+)?(?:model\s+)?([^?]+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "model_list": {
            "keywords": [
                "available models", "what models", "list models", "which models",
                "show models", "what ai models", "what models can you use"
            ],
            "patterns": [
                r"\bavailable\s+models\b",
                r"\bwhat\s+models\b",
                r"\blist\s+models\b",
                r"\bwhich\s+models\b",
                r"\bshow\s+models\b",
                r"\bwhat\s+ai\s+models\b"
            ],
            "confidence": 0.9
        },
        "status": {
            "keywords": [
                "status", "how are you", "how are you doing", "stats",
                "bot status", "system status", "health check"
            ],
            "patterns": [
                r"\bstatus\b",
                r"\bhow\s+are\s+you\b(?!\s+doing)",
                r"\bhow\s+are\s+you\s+doing\b",
                r"\bstats\b",
                r"\bbot\s+status\b",
                r"\bsystem\s+status\b",
                r"\bhealth\s+check\b"
            ],
            "confidence": 0.85
        },
        "remember_preference": {
            "keywords": [
                "remember that", "note that", "i prefer", "preference",
                "keep in mind", "remember this"
            ],
            "patterns": [
                r"\bremember\s+(?:that\s+)?([^?]+)",
                r"\bnote\s+(?:that\s+)?([^?]+)",
                r"\bi\s+prefer\s+([^?]+)",
                r"\bkeep\s+in\s+mind\s+([^?]+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "search": {
            "keywords": [
                "search for", "look up", "find", "research", "google",
                "search about", "find information about", "look for"
            ],
            "patterns": [
                r"\bsearch\s+(for\s+)?([^?]+)",
                r"\blook\s+up\s+([^?]+)",
                r"\bfind\s+([^?]+)",
                r"\bresearch\s+([^?]+)",
                r"\bgoogle\s+([^?]+)"
            ],
            "confidence": 0.9,
            "extract_param": True
        }
    }

    @staticmethod
    def classify_intent(message: str) -> Dict[str, any]:
        """
        Classify the intent of a user message

        Args:
            message: The user's message

        Returns:
            Dictionary containing:
            - intent: The detected intent (or "chat" if no special intent)
            - confidence: Confidence score (0-1)
            - params: Extracted parameters (if any)
            - api_source: Recommended API source (music intents only)
        """
        message_lower = message.lower().strip()
        
        logger.debug(f"Classifying intent for message: '{message}'")

        # Check each intent
        for intent_name, intent_data in IntentDetector.INTENTS.items():
            # Check keyword matches first (more precise)
            keyword_match = IntentDetector._check_keyword_match(message_lower, intent_data["keywords"])
            
            # Check pattern matches
            pattern_match, matched_pattern = IntentDetector._check_pattern_match(message_lower, intent_data.get("patterns", []))

            # Log matches for debugging
            if keyword_match:
                logger.debug(f"Keyword match for intent '{intent_name}'")
            if pattern_match:
                logger.debug(f"Pattern match for intent '{intent_name}': {matched_pattern}")

            # If either keyword or pattern matches
            if keyword_match or pattern_match:
                # Guardrails: prevent misclassification of artist info requests as song searches
                if intent_name == "juice_search":
                    # Skip if asking for artist information/facts instead of songs
                    info_keywords = ["birthday", "death", "age", "born", "information", "about", "bio", "biography", "when did", "when was"]
                    music_keywords = ["song", "track", "lyrics", "music"]
                    
                    # If asking for artist info but not explicitly searching for songs
                    if any(w in message_lower for w in info_keywords) and not any(w in message_lower for w in music_keywords):
                        logger.debug(f"Skipping juice_search - appears to be artist info request: '{message}'")
                        continue
                    
                    # Additional check: if only "juice" mentioned without song terms, likely not a song search
                    if "juice" in message_lower and not any(w in message_lower for w in music_keywords + ["find", "search", "look"]):
                        logger.debug(f"Skipping juice_search - 'juice' mentioned without song search terms: '{message}'")
                        continue

                confidence = intent_data["confidence"]

                # Extract parameters if needed
                params = {}
                if intent_data.get("extract_param", False):
                    params = IntentDetector._extract_parameters(message_lower, intent_name, matched_pattern)

                # Determine API source for music intents
                api_source = None
                if intent_name.startswith("music_") or intent_name.startswith("juice_"):
                    api_source = IntentDetector.determine_api_source(message_lower)

                logger.info(f"Detected intent: {intent_name} (confidence: {confidence}, api_source: {api_source})")
                return {
                    "intent": intent_name,
                    "confidence": confidence,
                    "params": params,
                    "api_source": api_source
                }

        # No special intent detected - default to chat
        logger.debug("No intent detected - defaulting to chat")
        return {
            "intent": "chat",
            "confidence": 1.0,
            "params": {},
            "api_source": None
        }

    @staticmethod
    def _check_keyword_match(message: str, keywords: List[str]) -> bool:
        """
        Check if any keyword matches the message using word boundaries
        
        Args:
            message: Lowercase message
            keywords: List of keywords to check
            
        Returns:
            True if any keyword matches
        """
        # Remove common punctuation that might interfere
        message_clean = re.sub(r'[^\w\s]', ' ', message)
        
        for keyword in keywords:
            keyword_clean = re.sub(r'[^\w\s]', ' ', keyword.lower())
            
            # Use word boundaries to ensure we match whole words
            pattern = r'\b' + re.escape(keyword_clean) + r'\b'
            if re.search(pattern, message_clean):
                return True
                
        return False

    @staticmethod
    def _check_pattern_match(message: str, patterns: List[str]) -> tuple:
        """
        Check if any pattern matches the message
        
        Args:
            message: Lowercase message
            patterns: List of regex patterns
            
        Returns:
            Tuple of (bool, matched_pattern)
        """
        for pattern in patterns:
            try:
                if re.search(pattern, message, re.IGNORECASE):
                    return True, pattern
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                continue
                
        return False, None

    @staticmethod
    def determine_api_source(message: str) -> Optional[str]:
        """
        Determine which API to use based on message content.

        API Priority Logic:
        - If "soundcloud" explicitly mentioned → "soundcloud"
        - Otherwise → "juice_wrld" (primary)

        Args:
            message: The user's message (lowercase)

        Returns:
            API source: "juice_wrld" or "soundcloud"
        """
        # Priority 1: SoundCloud - ONLY when explicitly mentioned
        if "soundcloud" in message:
            logger.debug("API source: soundcloud (explicitly requested)")
            return "soundcloud"

        # Default: Juice WRLD API is the primary music source
        logger.debug("API source: juice_wrld (default)")
        return "juice_wrld"

    @staticmethod
    def _extract_parameters(message: str, intent: str, pattern: str) -> Dict[str, any]:
        """
        Extract parameters from message based on intent and matched pattern

        Args:
            message: The user's message
            intent: The detected intent
            pattern: The matched regex pattern

        Returns:
            Dictionary of extracted parameters
        """
        params = {}

        try:
            match = re.search(pattern, message, re.IGNORECASE)
            if not match:
                return params

            if intent == "search":
                # Extract search query - use last non-empty group
                if match.lastindex and match.lastindex >= 1:
                    # Find the last capturing group that has content
                    for i in range(match.lastindex, 0, -1):
                        group_content = match.group(i).strip()
                        if group_content:
                            params["query"] = group_content
                            break

            elif intent == "model_switch":
                # Extract model name
                if match.lastindex and match.lastindex >= 1:
                    params["model_name"] = match.group(1).strip()

            elif intent == "remember_preference":
                # Extract preference
                if match.lastindex and match.lastindex >= 1:
                    params["preference"] = match.group(1).strip()

            elif intent == "clear_specific":
                # Extract number of messages
                if match.lastindex and match.lastindex >= 1:
                    params["count"] = int(match.group(1))

            elif intent == "juice_era_filter":
                if match.lastindex and match.lastindex >= 1:
                    params["era"] = match.group(1).strip()

            elif intent == "juice_category_filter":
                if match.lastindex and match.lastindex >= 1:
                    raw = match.group(1).strip().lower()
                    raw = raw.replace(" ", "_")
                    if raw.endswith("s") and raw.startswith("studio_"):
                        raw = "studio_session"
                    params["category"] = raw

            elif intent == "juice_lyric_search":
                if match.lastindex and match.lastindex >= 1:
                    params["phrase"] = match.group(1).strip().strip('"\'')

            elif intent == "juice_producer_filter":
                if match.lastindex and match.lastindex >= 1:
                    params["producer"] = match.group(1).strip()

            elif intent == "juice_song_info":
                if match.lastindex and match.lastindex >= 1:
                    q = match.group(1).strip()
                    if q.isdigit():
                        params["song_id"] = int(q)
                    else:
                        params["query"] = q

                # Determine which metadata the user is asking for
                if "produced" in message:
                    params["info_type"] = "producer"
                elif "where" in message and "recorded" in message:
                    params["info_type"] = "studio"
                elif "when" in message and "recorded" in message:
                    params["info_type"] = "recording_date"
                elif "recorded" in message:
                    params["info_type"] = "recording_date"
                else:
                    params["info_type"] = "details"

            elif intent in ["juice_cover_art", "juice_stream", "juice_collection", "juice_search"]:
                if match.lastindex and match.lastindex >= 1:
                    params["query"] = match.group(1).strip()

            elif intent in ["music_lyrics", "music_search", "music_artist", "music_annotation"]:
                # Extract song/artist name
                if match.lastindex and match.lastindex >= 1:
                    params["query"] = match.group(1).strip()

            logger.debug(f"Extracted parameters for {intent}: {params}")

        except Exception as e:
            logger.warning(f"Error extracting parameters for intent {intent}: {e}")
            # Return empty params on error

        return params

    @staticmethod
    def get_available_intents() -> List[str]:
        """
        Get list of all available intents

        Returns:
            List of intent names
        """
        return list(IntentDetector.INTENTS.keys())

    @staticmethod
    def get_intent_description(intent_name: str) -> Optional[str]:
        """
        Get description for an intent

        Args:
            intent_name: Name of the intent

        Returns:
            Description string or None if intent doesn't exist
        """
        if intent_name in IntentDetector.INTENTS:
            # Use keywords to create description
            keywords = IntentDetector.INTENTS[intent_name]["keywords"][:3]
            return f"Keywords: {', '.join(keywords)}"
        return None