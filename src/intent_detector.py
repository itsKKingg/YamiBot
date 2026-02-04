"""
Intent Detector for YamiBot

This module classifies user intent from natural language messages.
Supports keyword-based classification and intelligent routing across multiple APIs.
"""

from typing import Dict, Optional, List, Any, Tuple
import re

from .utils.logger import setup_logging

logger = setup_logging(__name__)


class IntentDetector:
    """
    Detects user intent from natural language messages and multimodal context.
    Intelligently routes requests to specialized APIs (Juice WRLD, Genius, SoundCloud, Gemini).
    """

    # Intent definitions with keywords and patterns (ordered by priority/specificity)
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
        
        # ============ MODEL ROUTING & ANALYSIS ============
        "math_code_analysis": {
            "keywords": [
                "solve", "calculate", "equation", "formula", "python code", 
                "javascript code", "debug code", "analyze code", "explain code"
            ],
            "patterns": [
                r"\b(?:solve|calculate|math)\s+([^?]+)",
                r"\b(?:write|create|generate)\s+(?:a\s+)?(?:[\w\s]+\s+)?(?:code|script|function|program)\b",
                r"\bdebug\s+([^?]+)",
                r"\banalyze\s+([^?]+)",
                r"\bexplain\s+this\s+code\b"
            ],
            "confidence": 0.9,
            "extract_param": True
        },

        # ============ JUICE WRLD API (PRIMARY MUSIC SOURCE) ============
        "juice_random": {
            "keywords": ["random track", "random song", "random juice", "shuffle juice"],
            "patterns": [r"\brandom\s+(?:juice\s+)?(?:track|song)\b", r"\b(?:juice\s+)?radio\b", r"\bshuffle\b"],
            "confidence": 0.9
        },
        "juice_stats": {
            "keywords": ["juice stats", "database stats", "overall stats", "song stats"],
            "patterns": [r"\bhow\s+many\s+(?:juice\s+)?songs?\b", r"\b(?:juice\s+)?stats\b", r"\bdatabase\s+stats\b"],
            "confidence": 0.85
        },
        "juice_eras_list": {
            "keywords": ["list eras", "era list", "era timeline"],
            "patterns": [r"\blist\s+all\s+eras\b", r"\bshow\s+all\s+eras\b", r"\beras\b", r"\bera\s+timeline\b"],
            "confidence": 0.8
        },
        "juice_era_filter": {
            "keywords": ["songs from era", "from era", "era songs"],
            "patterns": [r"\bsongs?\s+from\s+([^?]+?)(?:\s+era)?\b", r"\bfrom\s+the\s+([^?]+?)\s+era\b", r"\b([^?]+?)\s+era\s+songs\b"],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_category_filter": {
            "keywords": ["unreleased songs", "unreleased tracks", "unsurfaced songs", "released songs", "studio sessions"],
            "patterns": [r"\b(?:show\s+me\s+)?(released|unreleased|unsurfaced|studio_session|studio\s+sessions?)\s+(?:songs?|tracks?)\b", r"\bsongs?\s+in\s+(released|unreleased|unsurfaced|studio_session)\b"],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_lyric_search": {
            "keywords": ["find lyrics with", "songs with lyric", "songs containing", "lyrics with"],
            "patterns": [r"\bfind\s+lyrics\s+with\s+([^?]+)", r"\bsongs?\s+containing\s+([^?]+)", r"\bsongs?\s+with\s+lyrics?\s+([^?]+)", r"\blyrics?\s+search\s+([^?]+)"],
            "confidence": 0.9,
            "extract_param": True
        },
        "juice_producer_filter": {
            "keywords": ["produced by", "songs produced by"],
            "patterns": [r"\bsongs?\s+produced\s+by\s+([^?]+)", r"\bwhat\s+was\s+produced\s+by\s+([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_song_info": {
            "keywords": ["song details", "who produced", "bpm of", "tempo of", "key of", "scale of"],
            "patterns": [r"\bwho\s+produced\s+([^?]+)\b", r"\bwhen\s+was\s+([^?]+)\s+recorded\b", r"\bwhere\s+was\s+([^?]+)\s+recorded\b", r"\bdetails\s+for\s+([^?]+)", r"\bsong\s+details\s+for\s+([^?]+)", r"\b(?:bpm|tempo|key|scale)\s+(?:of|for)\s+([^?]+)", r"\b(?:song\s+)?id\s+(\d+)\b"],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_cover_art": {
            "keywords": ["cover art", "artwork", "album art"],
            "patterns": [r"\b(?:cover\s+art|artwork|album\s+art)\s+(?:for\s+)?([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_stream": {
            "keywords": ["streaming link", "listen link", "download link"],
            "patterns": [r"\b(?:streaming\s+link|listen\s+link|download\s+link)\s+(?:for\s+)?([^?]+)", r"\blisten\s+to\s+([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_collection": {
            "keywords": ["zip of", "archive of", "collection of"],
            "patterns": [r"\b(?:make|generate|create)\s+(?:a\s+)?(?:zip|archive)\s+(?:of\s+)?([^?]+)", r"\bdownload\s+(?:a\s+)?(?:zip|archive)\s+(?:of\s+)?([^?]+)", r"\bzip\s+of\s+([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        },

        # ============ SPECIALIZED MUSIC SEARCH ============
        "music_search": {
            "keywords": ["soundcloud search", "find on soundcloud", "soundcloud track"],
            "patterns": [r"\bsoundcloud\s+(?:search\s+)?([^?]+)", r"\bfind\s+(?:on\s+)?soundcloud\s+([^?]+)", r"\bfind\s+(?:a\s+)?song\s+(?:by\s+)?([^?]+)", r"\bsearch\s+(?:for\s+)?(?:a\s+)?song\s+(?:by\s+)?([^?]+)", r"\bwhat(?:'s|s)?\s+the\s+song\s+(?:that\s+goes\s+)?([^?]+)", r"\bfind\s+music\s+([^?]+)", r"\bsearch\s+music\s+([^?]+)", r"\bfind\s+track\s+([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        },
        "juice_search": {
            "keywords": ["find juice song", "search juice", "juice track", "play juice"],
            "patterns": [r"\b(?:search|find|play)\s+(?:for\s+)?(?:juice\s+(?:song|track)\s+)?([^?]+?)(?:\s+(?:by|from)\s+juice)?\b", r"\bfind\s+(?:me\s+)?(?:juice\s+(?:song|track)\s+)?([^?]+?)(?:\s+(?:by|from)\s+juice)?\b", r"\b(?:search|find)\s+(?:a\s+)?song\s+([^?]+?)(?:\s+(?:by|from)\s+juice)?\b", r"\b(?:search|find)\s+(?:a\s+)?(?:song|track)\s+(?:by\s+)?juice\s+([^?]+)\b"],
            "confidence": 0.8,
            "extract_param": True
        },
        "smart_juice_query": {
            "keywords": [
                "lyrics to", "album", "featured artists", "produced by", "era",
                "sad juice songs", "hype juice songs", "juice stats", "top juice songs",
                "who's on", "streaming links", "juice biography", "zip archive",
                "random juice song", "playlist recommendations"
            ],
            "patterns": [
                # Lyrics
                r"\b(lyrics?|lyric)\b.*\b(?:to|for)\s+(.+)",
                r"\b(.+?)\s+lyrics?\b",
                # Album
                r"\b(?:album|mixtape|ep|project)\s+(.+)",
                r"\bfrom\s+(?:the\s+)?(?:album|mixtape|project)\s+(.+)",
                # Featured
                r"\bwho'?s?\s+on\s+(.+?)\s+with\s+juice",
                r"\bwho'?s?\s+featured\s+on\s+(.+)",
                # Producer
                r"\bproduced\s+by\s+(.+)",
                r"\bproducer\s+(.+)",
                r"\bbeat\s+by\s+(.+)",
                # Era
                r"\b(?:era|period|time)\s+(.+)",
                r"\bfrom\s+(.+?)\s+era",
                # Category/Mood
                r"\b(sad|hype|introspective|emotional|party|chill|melodic|aggressive)\s+juice\s+songs?\b",
                # Stats
                r"\b(stats?|statistics|numbers|info)\b.*\bjuice",
                r"\bjuice\s+wrld\s+(stats?|statistics|numbers)",
                # Charts
                r"\b(top|chart|ranking|most\s+popular)\b.*\bjuice",
                # Streaming
                r"\b(stream|play|listen|spotify|apple\s+music|soundcloud)\b.*\b(.+)",
                # Related
                r"\b(similar|related|like|artists?\s+like)\b.*\bjuice",
                # Biography
                r"\b(bio|biography|life|story|background|about)\b.*\bjuice",
                r"\btell\s+me\s+about\s+juice\s+wrld",
                # Archive
                r"\b(zip|archive|download\s+all|discography)\b",
                # Random
                r"\b(random|surprise|any|unexpected)\b.*\bjuice\s+songs?\b",
                # Playlist
                r"\b(playlist|recommendations?|suggestions?)\b.*\bjuice",
            ],
            "confidence": 0.85,
            "extract_param": True
        },
        
        # ============ WEB SEARCH ============
        "search": {
            "keywords": ["search for", "look up", "google", "what is", "who is", "when was"],
            "patterns": [r"\bsearch\s+(for\s+)?([^?]+)", r"\blook\s+up\s+([^?]+)", r"\bgoogle\s+([^?]+)", r"\bwhat\s+is\s+(?!the\s+lyrics|the\s+meaning)([^?]+)", r"\bwho\s+is\s+(?!artist|singer|rapper|produced)([^?]+)", r"\bwhen\s+was\s+(?!recorded|released)([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        },

        # ============ GENERIC MUSIC INTENTS ============
        "music_lyrics": {
            "keywords": ["lyrics for", "words to", "what are the lyrics", "find lyrics"],
            "patterns": [r"\b(?:lyrics?|words?)\s+(?:for|of|to)\s+([^?]+)", r"\bwhat\s+are\s+the\s+lyrics?\s+for\s+([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        },
        "music_artist": {
            "keywords": ["artist info", "artist bio", "tell me about artist"],
            "patterns": [r"\btell\s+me\s+about\s+(?:the\s+artist\s+|the\s+singer\s+|the\s+rapper\s+)?([^?]+)", r"\bwho\s+is\s+(?:the\s+artist\s+|the\s+singer\s+|the\s+rapper\s+)([^?]+)", r"\bartist\s+info\s+for\s+([^?]+)", r"\bartist\s+bio\s+for\s+([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        },
        "music_annotation": {
            "keywords": ["meaning of", "explain lyrics", "lyric meaning"],
            "patterns": [r"\bwhat\s+does\s+([^?]+)\s+mean\b", r"\bmeaning\s+of\s+([^?]+)", r"\bexplain\s+(?:lyrics?|song)\s+([^?]+)", r"\bwhat(?:'s|s)\s+the\s+meaning\s+of\s+([^?]+)", r"\bannotation\s+for\s+([^?]+)"],
            "confidence": 0.8,
            "extract_param": True
        },

        # ============ SYSTEM ============
        "model_switch": {
            "keywords": ["use model", "switch to model", "change model"],
            "patterns": [r"\buse\s+(?:model\s+)?([^?]+)", r"\bswitch\s+(?:to\s+)?(?:model\s+)?([^?]+)", r"\bchange\s+(?:to\s+)?(?:model\s+)?([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        },
        "model_list": {
            "keywords": ["available models", "list models", "show models"],
            "patterns": [r"\bavailable\s+models\b", r"\bwhat\s+models\b", r"\blist\s+models\b"],
            "confidence": 0.9
        },
        "status": {
            "keywords": ["bot status", "system status", "health check"],
            "patterns": [r"\bstatus\b", r"\bbot\s+status\b", r"\bsystem\s+status\b", r"\bhealth\s+check\b", r"\bhow\s+are\s+you\s+doing\b"],
            "confidence": 0.85
        },
        "remember_preference": {
            "keywords": ["remember that", "note that", "i prefer"],
            "patterns": [r"\bremember\s+(?:that\s+)?([^?]+)", r"\bnote\s+(?:that\s+)?([^?]+)", r"\bi\s+prefer\s+([^?]+)"],
            "confidence": 0.85,
            "extract_param": True
        }
    }

    @staticmethod
    def classify_intent(message: str, attachments: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Classify the intent of a user message with multi-API routing and context awareness.
        """
        message_lower = message.lower().strip()
        logger.debug(f"🎯 Classifying intent for message: '{message}'")
        attachment_info = IntentDetector._detect_attachments(attachments)

        implicit_music = IntentDetector._detect_implicit_music(message_lower)
        if implicit_music:
            logger.info(f"🎵 Detected implicit music intent: {implicit_music['intent']}")
            implicit_music["attachment_info"] = attachment_info
            return implicit_music

        # Try each intent and log matches
        matched_intents = []
        
        for intent_name, intent_data in IntentDetector.INTENTS.items():
            keyword_match = IntentDetector._check_keyword_match(message_lower, intent_data["keywords"])
            pattern_match, matched_pattern = IntentDetector._check_pattern_match(message_lower, intent_data.get("patterns", []))
            
            if keyword_match or pattern_match:
                if intent_name == "juice_search" and IntentDetector._is_artist_info_request(message_lower):
                    logger.debug(f"🚫 Skipping juice_search - detected as artist info request: '{message}'")
                    continue

                confidence = intent_data["confidence"]
                if attachment_info["has_attachments"]:
                    if intent_name == "math_code_analysis" and any(t in attachment_info["types"] for t in ["image", "document"]):
                        confidence = min(1.0, confidence + 0.1)

                params = {}
                if intent_data.get("extract_param", False):
                    params = IntentDetector._extract_parameters(message_lower, intent_name, matched_pattern)
                    logger.debug(f"📝 Extracted parameters for {intent_name}: {params}")

                api_source = IntentDetector.determine_api_source(message_lower, intent_name)
                
                match_info = {
                    "intent": intent_name,
                    "confidence": confidence,
                    "params": params,
                    "api_source": api_source,
                    "attachment_info": attachment_info,
                    "keyword_match": keyword_match,
                    "pattern_match": pattern_match is not None
                }
                matched_intents.append(match_info)
                
                logger.info(f"🎯 Intent match: {intent_name} (confidence: {confidence}, api_source: {api_source}, keyword: {keyword_match}, pattern: {pattern_match is not None})")

        # Return the first (highest priority) match
        if matched_intents:
            selected_intent = matched_intents[0]
            logger.info(f"✅ Selected intent: {selected_intent['intent']} (final choice)")
            return selected_intent

        if attachment_info["has_attachments"]:
            logger.info(f"📎 Detected multimodal intent with attachments: {attachment_info['types']}")
            return {"intent": "multimodal", "confidence": 0.8, "params": {"types": attachment_info["types"]}, "api_source": "gemini", "attachment_info": attachment_info}

        logger.info(f"💬 No command intent detected - routing to chat: '{message[:50]}...'")
        return {"intent": "chat", "confidence": 1.0, "params": {}, "api_source": "llm", "attachment_info": attachment_info}

    @staticmethod
    def _detect_attachments(attachments: Optional[List[Any]]) -> Dict[str, Any]:
        """Detect multimodal attachments and their types"""
        if not attachments: return {"has_attachments": False, "types": [], "count": 0}
        types = []
        for att in attachments:
            content_type = getattr(att, "content_type", "") or ""
            filename = getattr(att, "filename", "").lower()
            if "image" in content_type or any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]): types.append("image")
            elif "video" in content_type or any(filename.endswith(ext) for ext in [".mp4", ".mov", ".webm", ".mkv"]): types.append("video")
            elif "audio" in content_type or any(filename.endswith(ext) for ext in [".mp3", ".wav", ".ogg", ".m4a", ".flac"]): types.append("audio")
            elif "text" in content_type or any(filename.endswith(ext) for ext in [".txt", ".py", ".js", ".json", ".md", ".pdf", ".csv"]): types.append("document")
        return {"has_attachments": True, "types": list(set(types)), "count": len(attachments)}

    @staticmethod
    def _detect_implicit_music(message: str) -> Optional[Dict[str, Any]]:
        """Detect implicit music requests like 'Rental by Juice'"""
        if any(w in message for w in ["produced by", "directed by", "recorded by"]): return None
        match = re.search(r"\b(.+?)\s+by\s+([^?]+?)\b", message, re.IGNORECASE)
        if match:
            song, artist = match.group(1).strip(), match.group(2).strip()
            intent = "music_lyrics" if any(w in message for w in ["lyrics", "words"]) else "music_search"
            is_juice = any(name in artist.lower() for name in ["juice", "999", "jarad", "juice wrld"])
            if is_juice:
                intent = "juice_lyric_search" if "lyrics" in message else "juice_search"
                return {"intent": intent, "confidence": 0.9, "params": {"query": song, "artist": artist}, "api_source": "juice_wrld"}
            elif artist.lower() in ["xxxtentacion", "lil uzi vert", "polo g", "trippie redd"]:
                return {"intent": intent, "confidence": 0.85, "params": {"query": f"{song} {artist}", "song": song, "artist": artist}, "api_source": "genius" if intent == "music_lyrics" else "juice_wrld"}
            else:
                return {"intent": intent, "confidence": 0.8, "params": {"query": f"{song} {artist}", "song": song, "artist": artist}, "api_source": "genius" if intent == "music_lyrics" else "juice_wrld"}
        bpm_match = re.search(r"\b(?:bpm|tempo|key|scale)\s+(?:of|for)\s+([^?]+)", message, re.IGNORECASE)
        if bpm_match: return {"intent": "juice_song_info", "confidence": 0.9, "params": {"query": bpm_match.group(1).strip(), "info_type": "details"}, "api_source": "juice_wrld"}
        return None

    @staticmethod
    def determine_api_source(message: str, intent: Optional[str] = None) -> str:
        """Intelligently determine which API to route the request to with detailed logging."""
        message_lower = message.lower()
        
        # Log routing decision
        logger.debug(f"🔍 Determining API source for intent '{intent}' and message: '{message[:50]}...'")
        
        # Specific routing logic with detailed logging
        if "gemini" in message_lower or intent == "math_code_analysis":
            logger.debug(f"📍 Route: Gemini (explicit mention or math_code_analysis)")
            return "gemini"
            
        if "soundcloud" in message_lower:
            logger.debug(f"📍 Route: SoundCloud (explicit mention)")
            return "soundcloud"
            
        if intent == "music_lyrics":
            if any(w in message_lower for w in ["juice", "lucid dreams", "rental", "all girls"]):
                logger.debug(f"📍 Route: Juice WRLD (lyrics for Juice WRLD song)")
                return "juice_wrld"
            else:
                logger.debug(f"📍 Route: Genius (general lyrics request)")
                return "genius"
                
        if "juice" in message_lower or (intent and intent.startswith("juice_")):
            logger.debug(f"📍 Route: Juice WRLD (Juice WRLD mention or intent)")
            return "juice_wrld"
            
        if intent and intent.startswith("music_"):
            logger.debug(f"📍 Route: Juice WRLD (music intent)")
            return "juice_wrld"
            
        # Default routing - log as LLM for chat
        logger.debug(f"📍 Route: LLM (default chat routing)")
        return "llm"

    @staticmethod
    def _is_artist_info_request(message: str) -> bool:
        """Check if message is asking for artist info rather than a song"""
        info_keywords = ["birthday", "death", "age", "born", "information", "about", "bio", "biography", "when did", "when was"]
        music_keywords = ["song", "track", "lyrics", "music"]
        if any(w in message for w in info_keywords) and not any(w in message for w in music_keywords): return True
        if "juice" in message and not any(w in message for w in music_keywords + ["find", "search", "look", "play"]): return True
        return False

    @staticmethod
    def _check_keyword_match(message: str, keywords: List[str]) -> bool:
        """Check keyword match with word boundaries and punctuation cleanup"""
        message_clean = re.sub(r'[^\w\s]', ' ', message)
        for keyword in keywords:
            keyword_clean = re.sub(r'[^\w\s]', ' ', keyword.lower())
            pattern = r'\b' + re.escape(keyword_clean) + r'\b'
            if re.search(pattern, message_clean): return True
        return False

    @staticmethod
    def _check_pattern_match(message: str, patterns: List[str]) -> Tuple[bool, Optional[str]]:
        """Check regex pattern matches"""
        for pattern in patterns:
            try:
                if re.search(pattern, message, re.IGNORECASE): return True, pattern
            except re.error as e: continue
        return False, None

    @staticmethod
    def _extract_parameters(message: str, intent: str, pattern: str) -> Dict[str, Any]:
        """Extract parameters based on intent and matched pattern"""
        params = {}
        try:
            match = re.search(pattern, message, re.IGNORECASE)
            if not match: return params
            def get_best_group(m):
                if m.lastindex and m.lastindex >= 1:
                    for i in range(m.lastindex, 0, -1):
                        content = m.group(i).strip()
                        if content: return content
                return ""
            if intent in ["search", "math_code_analysis"]: params["query"] = get_best_group(match)
            elif intent == "model_switch": params["model_name"] = match.group(1).strip()
            elif intent == "remember_preference": params["preference"] = match.group(1).strip()
            elif intent == "clear_specific": params["count"] = int(match.group(1))
            elif intent == "juice_era_filter": params["era"] = match.group(1).strip()
            elif intent == "juice_category_filter":
                raw = match.group(1).strip().lower().replace(" ", "_")
                if raw.endswith("s") and raw.startswith("studio_"): raw = "studio_session"
                params["category"] = raw
            elif intent == "juice_lyric_search": params["phrase"] = match.group(1).strip().strip('"\'')
            elif intent == "juice_producer_filter": params["producer"] = match.group(1).strip()
            elif intent == "juice_song_info":
                q = match.group(1).strip()
                if q.isdigit(): params["song_id"] = int(q)
                else: params["query"] = q
                if "produced" in message: params["info_type"] = "producer"
                elif "recorded" in message: params["info_type"] = "recording_date"
                elif any(w in message for w in ["bpm", "tempo"]): params["info_type"] = "bpm"
                elif any(w in message for w in ["key", "scale"]): params["info_type"] = "key"
                else: params["info_type"] = "details"
            elif intent in ["juice_cover_art", "juice_stream", "juice_collection", "juice_search"]: params["query"] = match.group(1).strip()
            elif intent in ["music_lyrics", "music_search", "music_artist", "music_annotation"]: params["query"] = match.group(1).strip()
        except Exception as e: pass
        return params

    @staticmethod
    def get_available_intents() -> List[str]:
        return list(IntentDetector.INTENTS.keys())
