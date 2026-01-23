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

    # Intent definitions with keywords and patterns
    INTENTS = {
        "clear_memory": {
            "keywords": [
                "clear my memory", "clear memory", "erase memory", "forget everything",
                "reset memory", "wipe memory", "clear conversation", "reset conversation",
                "start over", "new conversation", "forget everything", "clear history"
            ],
            "patterns": [
                r"clear\s+(my\s+)?memory",
                r"erase\s+(my\s+)?memory",
                r"forget\s+everything",
                r"reset\s+(my\s+)?(memory|conversation)",
                r"wipe\s+(my\s+)?memory",
                r"start\s+over"
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
                r"what\s+do\s+you\s+remember",
                r"show\s+(my\s+)?memory",
                r"my\s+memory",
                r"show\s+conversation",
                r"what\s+do\s+you\s+know",
                r"conversation\s+history",
                r"what\s+have\s+we\s+discussed",
                r"what\s+did\s+we\s+talk\s+about"
            ],
            "confidence": 0.85
        },
        "search": {
            "keywords": [
                "search for", "look up", "find", "research", "google",
                "search about", "find information about", "look for"
            ],
            "patterns": [
                r"search\s+(for\s+)?(.+)",
                r"look\s+up\s+(.+)",
                r"find\s+(.+)",
                r"research\s+(.+)",
                r"google\s+(.+)"
            ],
            "confidence": 0.9,
            "extract_param": True
        },
        "model_switch": {
            "keywords": [
                "use model", "switch to", "change model", "switch model",
                "use gemini", "use cerebras", "use groq", "use mistral",
                "change to"
            ],
            "patterns": [
                r"use\s+(?:model\s+)?(.+)",
                r"switch\s+(?:to\s+)?(?:model\s+)?(.+)",
                r"change\s+(?:to\s+)?(?:model\s+)?(.+)"
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
                r"available\s+models",
                r"what\s+models",
                r"list\s+models",
                r"which\s+models",
                r"show\s+models",
                r"what\s+ai\s+models"
            ],
            "confidence": 0.9
        },
        "status": {
            "keywords": [
                "status", "how are you", "how are you doing", "stats",
                "bot status", "system status", "health check"
            ],
            "patterns": [
                r"status",
                r"how\s+are\s+you",
                r"how\s+are\s+you\s+doing",
                r"stats",
                r"bot\s+status",
                r"system\s+status",
                r"health\s+check"
            ],
            "confidence": 0.85
        },
        "remember_preference": {
            "keywords": [
                "remember that", "note that", "i prefer", "preference",
                "keep in mind", "remember this"
            ],
            "patterns": [
                r"remember\s+(?:that\s+)?(.+)",
                r"note\s+(?:that\s+)?(.+)",
                r"i\s+prefer\s+(.+)",
                r"keep\s+in\s+mind\s+(.+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "clear_specific": {
            "keywords": [
                "forget last", "forget about", "remove last", "delete last",
                "clear last"
            ],
            "patterns": [
                r"forget\s+last\s+(\d+)\s+messages?",
                r"remove\s+last\s+(\d+)\s+messages?",
                r"delete\s+last\s+(\d+)\s+messages?",
                r"clear\s+last\s+(\d+)\s+messages?"
            ],
            "confidence": 0.9,
            "extract_param": True
        },
        "music_lyrics": {
            "keywords": [
                "lyrics", "lyric", "words to", "what are the lyrics",
                "show me lyrics", "get lyrics", "find lyrics"
            ],
            "patterns": [
                r"lyrics?\s+(?:for\s+)?(.+)",
                r"words?\s+to\s+(.+)",
                r"what\s+are\s+the\s+lyrics?\s+for\s+(.+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "music_search": {
            "keywords": [
                "find song", "search for song", "what song", "play",
                "embed", "soundcloud", "find music", "search music"
            ],
            "patterns": [
                r"find\s+(?:a\s+)?song\s+(?:by\s+)?(.+)",
                r"search\s+(?:for\s+)?(?:a\s+)?song\s+(?:by\s+)?(.+)",
                r"what(?:'s|s)?\s+the\s+song\s+(?:that\s+goes\s+)?(.+)",
                r"play\s+(.+)",
                r"embed\s+(.+)",
                r"soundcloud\s+(.+)",
                r"find\s+music\s+(.+)",
                r"search\s+music\s+(.+)"
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
                r"tell\s+me\s+about\s+(.+)",
                r"who\s+is\s+(.+)",
                r"artist\s+info\s+for\s+(.+)",
                r"artist\s+bio\s+for\s+(.+)"
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        "music_annotation": {
            "keywords": [
                "what does", "meaning of", "explain", "annotation",
                "what's the meaning", "interpretation"
            ],
            "patterns": [
                r"what\s+does\s+(.+)\s+mean",
                r"meaning\s+of\s+(.+)",
                r"explain\s+(.+)",
                r"what(?:'s|s)\s+the\s+meaning\s+of\s+(.+)"
            ],
            "confidence": 0.8,
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

        # Check each intent
        for intent_name, intent_data in IntentDetector.INTENTS.items():
            # Check keyword matches
            keyword_match = False
            for keyword in intent_data["keywords"]:
                if keyword in message_lower:
                    keyword_match = True
                    break

            # Check pattern matches
            pattern_match = False
            matched_pattern = None
            if "patterns" in intent_data:
                for pattern in intent_data["patterns"]:
                    if re.search(pattern, message_lower, re.IGNORECASE):
                        pattern_match = True
                        matched_pattern = pattern
                        break

            # If either keyword or pattern matches
            if keyword_match or pattern_match:
                confidence = intent_data["confidence"]

                # Extract parameters if needed
                params = {}
                if intent_data.get("extract_param", False) and matched_pattern:
                    params = IntentDetector._extract_parameters(message_lower, intent_name, matched_pattern)

                # Determine API source for music intents
                api_source = None
                if intent_name.startswith("music_"):
                    api_source = IntentDetector.determine_api_source(message_lower)

                logger.debug(f"Detected intent: {intent_name} (confidence: {confidence}, api_source: {api_source})")
                return {
                    "intent": intent_name,
                    "confidence": confidence,
                    "params": params,
                    "api_source": api_source
                }

        # No special intent detected - default to chat
        return {
            "intent": "chat",
            "confidence": 1.0,
            "params": {},
            "api_source": None
        }

    @staticmethod
    def determine_api_source(message: str) -> Optional[str]:
        """
        Determine which API to use based on message content.

        API Priority Logic:
        - If "Juice WRLD" mentioned → "juice_wrld" (primary)
        - If "genius" explicitly mentioned → "genius"
        - If "lyrics" without "Juice WRLD" → "genius"
        - If "embed", "soundcloud", or "play" → "soundcloud"
        - Otherwise → None (use default routing)

        Args:
            message: The user's message (lowercase)

        Returns:
            API source: "juice_wrld", "genius", "soundcloud", or None
        """
        # Priority 1: Juice WRLD mentioned - always use Juice WRLD API
        if "juice wrld" in message or "juicewrld" in message:
            logger.debug("API source: juice_wrld (Juice WRLD detected)")
            return "juice_wrld"

        # Priority 2: Explicit Genius request
        if "genius" in message:
            logger.debug("API source: genius (explicitly requested)")
            return "genius"

        # Priority 3: Audio/embed requests - SoundCloud
        if any(keyword in message for keyword in ["embed", "soundcloud", "play this"]):
            logger.debug("API source: soundcloud (audio/embed request)")
            return "soundcloud"

        # Priority 4: Lyrics requests - Genius (non-Juice WRLD)
        if "lyrics" in message:
            logger.debug("API source: genius (lyrics request)")
            return "genius"

        # No specific API determined
        logger.debug("API source: None (use default routing)")
        return None

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
            if intent == "search":
                # Extract search query
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    params["query"] = match.group(2) if match.lastindex >= 1 else match.group(1)

            elif intent == "model_switch":
                # Extract model name
                match = re.search(pattern, message, re.IGNORECASE)
                if match and match.lastindex:
                    params["model_name"] = match.group(1).strip()

            elif intent == "remember_preference":
                # Extract preference
                match = re.search(pattern, message, re.IGNORECASE)
                if match and match.lastindex:
                    params["preference"] = match.group(1).strip()

            elif intent == "clear_specific":
                # Extract number of messages
                match = re.search(pattern, message, re.IGNORECASE)
                if match and match.lastindex:
                    params["count"] = int(match.group(1))

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
