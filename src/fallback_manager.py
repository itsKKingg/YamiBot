"""
Fallback Manager for YamiBot

This module orchestrates the multi-provider API fallback system.
It maintains a list of providers in priority order and handles
fallback logic when providers are rate-limited or unavailable.

Enhanced with circuit breakers and retry logic for improved reliability.
"""

import asyncio
from typing import List, Optional, Dict, Any, Tuple
import time
from datetime import datetime, timedelta

from .providers.base import BaseProvider
from .utils.logger import setup_logging
from .utils.config import Config
from .utils.circuit_breaker import CircuitBreaker, CircuitState
from .utils.retry import retry_with_backoff

logger = setup_logging(__name__)

class ProviderStatus:
    """
    Enum-like class for provider status tracking
    """
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    FAILED = "failed"
    MAINTENANCE = "maintenance"

class FallbackManager:
    """
    Manages multiple AI providers with fallback capability
    """
    
    def __init__(self, config: Config, model_router=None):
        """
        Initialize the fallback manager with configuration

        Args:
            config: Configuration object containing provider settings
            model_router: Optional ModelRouter instance for intelligent routing
        """
        self.config = config
        self.providers: List[BaseProvider] = []
        self.provider_status: Dict[str, str] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}  # NEW: Circuit breakers for each provider
        self.last_fallback_reason: Optional[str] = None
        self.last_used_provider: Optional[str] = None
        self.last_used_model: Optional[str] = None
        self.shared_session = None
        self.model_router = model_router
        self.bot = None  # Reference to bot instance for music API access
        
        # Provider priority order (from highest to lowest)
        # Updated order: Cerebras → SambaNova → Groq → Mistral
        self.provider_priority = [
            "cerebras",
            "sambanova",
            "groq",
            "mistral"
        ]
    
    def set_shared_session(self, session):
        """Set the shared aiohttp session for all providers"""
        self.shared_session = session
        # Update existing providers
        for provider in self.providers:
            provider.set_shared_session(session)
        logger.info("Shared session set for all providers")
        
        # Initialize the system prompt for bot self-awareness
        self._setup_system_prompt()
    
    def _setup_system_prompt(self):
        """
        Set up the comprehensive system prompt for YamiBot self-awareness
        """
        self.SYSTEM_PROMPT = """
🤖 **YOU ARE YAMIBOT - An Intelligent Discord AI Assistant**

=== CORE IDENTITY ===
You are YamiBot, a specialized Discord bot with multiple integrated APIs and features.
You're not just a simple chatbot - you're a feature-rich assistant with deep knowledge of your own capabilities.

=== YOUR CORE FEATURES & CAPABILITIES ===

🎵 **MUSIC SEARCH & LYRICS**
APIs: Genius (lyrics, annotations), SoundCloud (tracks, artists, playlists)
HOW IT WORKS: When users ask for lyrics or music info, you DON'T try to provide it yourself.
Instead, you guide them to use your music feature.

REDIRECT THESE REQUESTS:
- "What are the lyrics to [song]?" → Reply: "Try: search lyrics for [song] [artist]"
- "Find me [song] by [artist]" → Reply: "Try: search for [song] [artist]"
- "Explain the meaning of [song]" → Reply: "Try: explain [song] [artist]"
- "Who is [artist]?" → Reply: "Try: who is [artist] or tell me about [artist]"

EXAMPLES OF MUSIC COMMANDS:
• search lyrics for Be Here by Juice WRLD
• lyrics for Lucid Dreams
• find songs by Juice WRLD
• what artist made Goodbye & Good Riddance

🔍 **WEB SEARCH**
API: Google Gemini with web access
HOW IT WORKS: You can search the internet for real-time information.

REDIRECT THESE REQUESTS:
- "Search for [topic]" → You handle this with web search
- "Look up [information]" → You handle this with web search
- "Find information about [topic]" → You handle this with web search

EXAMPLES:
• search for latest AI developments
• look up how to learn Python
• find information about machine learning

🤖 **AI MODEL SWITCHING**
Available Models:
• Claude (by Anthropic) - Best for: reasoning, analysis, complex thinking
• Google Gemini (by Google) - Best for: web search, creative writing, code
• Mistral AI (by Mistral) - Best for: fast responses, multi-lingual tasks
• Groq (by Groq) - Best for: lightning fast inference, real-time tasks
• Cerebras - Best for: high-speed inference
• SambaNova - Best for: enterprise applications

USER COMMANDS:
- "/model [model_name]" - Switch to specific model (slash command)
- "/models" - List all available models (slash command)
- "use [model] for [task]" - Switch model for specific task
- "switch to Claude" - Informal model switching

ACKNOWLEDGE WHEN SWITCHING:
After switching models, respond like: "✅ Switched to Claude! Claude is great for reasoning and complex analysis."

💾 **CONVERSATION MEMORY**
HOW IT WORKS: You maintain memory of previous messages in this conversation.
Users can:
- "clear my memory" - Reset all conversation history
- "forget the last [n] messages" - Remove recent messages
- "what do you remember" - Show conversation summary
- "show conversation history" - Display all messages

WHEN MEMORY IS MENTIONED:
- Explain that you remember previous messages
- Be specific about what you remember
- Offer to forget things if they ask

🔧 **FEATURE DISCOVERY COMMANDS**
These are slash commands you should tell users about:
- "/help" - Shows all features and how to use them
- "/features" - Detailed feature list and examples
- "/apis" - Shows all integrated APIs and what they do
- "/status" - Bot status and statistics
- "/models" - List available AI models
- "/stats" - Conversation statistics

=== IMPORTANT RULES ===

1. **KNOW YOUR LIMITATIONS**
   - Don't provide full song lyrics (use music API instead)
   - Don't hallucinate song information (use music API instead)
   - Don't provide search results without web access (use search feature)
   - Be honest when you're uncertain

2. **GUIDE USERS TO THE RIGHT FEATURE**
   When a user asks for something you have a specialized feature for:
   - Music search/lyrics → Guide them to music commands
   - Web search → Use your search capability
   - Model switching → Guide them to /model command
   - Memory management → Guide them to memory commands

3. **BE CONVERSATIONAL BUT AWARE**
   - Chat naturally when it's just conversation
   - Be aware of your capabilities
   - Suggest features when they might help
   - Explain what you can do

4. **MODEL SWITCHING AWARENESS**
   - Know you can switch AI models
   - Acknowledge different models' strengths
   - Explain why a model is good for a task
   - Example: "Let me switch to Claude for this complex analysis..."

5. **API AWARENESS**
   When users mention music or search, show you know your APIs:
   - "I can search that using my web search feature..."
   - "I can look that up in Genius and SoundCloud databases..."
   - "Let me use SoundCloud to find that track..."

=== PERSONALITY ===
- Helpful and knowledgeable about your own features
- Honest about your capabilities and limitations
- Enthusiastic about showing what you can do
- User-focused: guide them to the best tool for their need
- Professional but friendly

=== RESPONSE FORMAT ===
When explaining features:
- Use emojis to make it clear and engaging
- Give specific command examples
- Be concise but informative
- Always offer next steps

=== EXAMPLE INTERACTIONS ===

USER: "Can you find me the lyrics to Lucid Dreams?"
YOU: "I have a specialized music feature for that! Try this command:
🎵 **search lyrics for Lucid Dreams Juice WRLD**

This will fetch the lyrics from my Genius and Juice WRLD databases and show you the song info, annotations, and more!"

---

USER: "What models can you use?"
YOU: "Great question! I can switch between these AI models:

🤖 **Available Models:**
• **Claude** - Best for reasoning & analysis
• **Gemini** - Best for web search & creativity
• **Mistral AI** - Great for multi-lingual tasks
• **Groq** - Fastest response times
• **Cerebras** - High-speed inference
• **SambaNova** - Enterprise applications

Use **/model [name]** to switch, or just say 'use Claude for this' and I'll switch! 📊"

---

USER: "Search for the latest AI news"
YOU: "I'll search that for you! 🔍
[Then actually search using web capabilities]"

---

USER: "How many slash commands do I have?"
YOU: "I have 8 slash commands available! Here they are:
🎯 **/help** - All features & how to use them
🎯 **/features** - Detailed feature list
🎯 **/apis** - All integrated APIs
🎯 **/status** - Bot status & uptime
🎯 **/models** - List AI models
🎯 **/model [name]** - Switch models
🎯 **/stats** - Conversation stats
🎯 **/forget** - Clear memory

Try any of them! They'll give you more info. 💡"

=== END OF SYSTEM PROMPT ===
"""
        logger.info("System prompt initialized for YamiBot self-awareness")
    
    async def initialize(self) -> None:
        """
        Initialize all providers and set their initial status.
        Providers that fail to initialize are skipped with a warning.
        """
        logger.info("Initializing providers...")
        
        # Import provider modules (updated provider order)
        from .providers.cerebras_provider import CerebrasProvider
        from .providers.sambanova_provider import SambanovaProvider
        from .providers.groq_provider import GroqProvider
        from .providers.mistral_provider import MistralProvider
        from .providers.google_provider import GoogleProvider

        # Provider classes in priority order: Cerebras → SambaNova → Groq → Mistral → Google
        provider_classes = [
            ("cerebras", CerebrasProvider),
            ("sambanova", SambanovaProvider),
            ("groq", GroqProvider),
            ("mistral", MistralProvider),
            ("google", GoogleProvider)
        ]
        
        # Initialize each provider individually with graceful error handling
        initialized_count = 0
        failed_providers = []
        
        for provider_name, ProviderClass in provider_classes:
            try:
                logger.info(f"Initializing {provider_name} provider...")
                provider = ProviderClass(self.config, self.shared_session)
                self.providers.append(provider)
                self.provider_status[provider.name] = ProviderStatus.AVAILABLE
                
                # NEW: Create circuit breaker for this provider
                self.circuit_breakers[provider_name] = CircuitBreaker(
                    name=provider_name,
                    failure_threshold=5,  # Open after 5 consecutive failures
                    timeout=300  # Try recovery after 5 minutes
                )
                logger.info(f"✓ Successfully initialized {provider_name} provider with circuit breaker")
                initialized_count += 1
                
            except ImportError as e:
                logger.warning(f"✗ Skipping {provider_name} provider: Missing library - {e}")
                failed_providers.append(f"{provider_name} (missing library)")
                continue
                
            except ValueError as e:
                logger.warning(f"✗ Skipping {provider_name} provider: Configuration error - {e}")
                failed_providers.append(f"{provider_name} (config error)")
                continue
                
            except Exception as e:
                logger.warning(f"✗ Skipping {provider_name} provider: {type(e).__name__} - {e}")
                failed_providers.append(f"{provider_name} ({type(e).__name__})")
                continue
        
        # Log summary
        if initialized_count == 0:
            logger.error("CRITICAL: No providers could be initialized!")
            raise RuntimeError("No providers available - cannot start bot")
        
        logger.info(f"Provider initialization complete: {initialized_count}/{len(provider_classes)} providers available")
        logger.info(f"Available providers: {[p.name for p in self.providers]}")
        logger.info(f"Circuit breakers configured for: {list(self.circuit_breakers.keys())}")
        
        if failed_providers:
            logger.warning(f"Failed providers: {', '.join(failed_providers)}")
            logger.info("Bot will continue with available providers")
    
    async def query(self, prompt: str, **kwargs) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Query the AI providers with fallback capability using circuit breakers and retry logic
        
        Args:
            prompt: The user's input prompt
            **kwargs: Additional arguments to pass to providers
            
        Returns:
            Tuple containing:
            - response text (or None if all providers failed)
            - metadata dictionary with provider info, tokens, timing, etc.
        """
        start_time = time.time()
        attempted_providers = []
        fallback_reasons = []
        
        logger.info(f"Processing query: {prompt[:100]}...")
        
        # Try providers in priority order with circuit breaker logic
        for provider in self.providers:
            provider_name = provider.name
            attempted_providers.append(provider_name)
            
            # NEW: Check circuit breaker status first
            if provider_name in self.circuit_breakers:
                breaker = self.circuit_breakers[provider_name]
                
                # Skip provider if circuit is OPEN and not ready for recovery
                if not breaker.can_attempt():
                    reason = f"Provider {provider_name} circuit {breaker.state.value} (skipping)"
                    fallback_reasons.append(reason)
                    logger.debug(f"Skipping {provider_name} (circuit {breaker.state.value})")
                    continue
            
            # Check if provider is marked as unavailable
            status = self.provider_status.get(provider_name, ProviderStatus.AVAILABLE)
            if status != ProviderStatus.AVAILABLE:
                reason = f"Provider {provider_name} is {status}"
                fallback_reasons.append(reason)
                logger.warning(reason)
                continue
            
            try:
                # Check rate limits before making the call
                if not await provider.check_rate_limit():
                    self.provider_status[provider_name] = ProviderStatus.RATE_LIMITED
                    reason = f"Provider {provider_name} rate limited"
                    fallback_reasons.append(reason)
                    logger.warning(reason)
                    continue
                
                logger.info(f"Attempting query with {provider_name} provider")
                
                # Add system prompt to messages for bot self-awareness
                updated_kwargs = kwargs.copy()
                if 'messages' not in updated_kwargs:
                    updated_kwargs['messages'] = []
                
                # Insert system prompt as the first message
                if hasattr(self, 'SYSTEM_PROMPT') and self.SYSTEM_PROMPT:
                    updated_kwargs['messages'] = [
                        {"role": "system", "content": self.SYSTEM_PROMPT}
                    ] + updated_kwargs['messages']
                else:
                    # Default system prompt if not set
                    updated_kwargs['messages'] = [
                        {"role": "system", "content": "You are YamiBot, a helpful Discord AI assistant."}
                    ] + updated_kwargs['messages']
                
                # NEW: Wrap query in retry logic with exponential backoff
                response, metadata = await retry_with_backoff(
                    lambda: provider.query(prompt, **updated_kwargs),
                    max_attempts=3,
                    base_delay=1.0
                )
                
                # Request succeeded - record success in circuit breaker
                if provider_name in self.circuit_breakers:
                    old_state = self.circuit_breakers[provider_name].state
                    self.circuit_breakers[provider_name].record_success()
                    new_state = self.circuit_breakers[provider_name].state
                    
                    # Log state transition if changed
                    if old_state != new_state:
                        logger.info(f"{provider_name}: Circuit transitioned {old_state.value} → {new_state.value} (success)")
                
                # Update metadata with provider info
                metadata.update({
                    "provider": provider_name,
                    "attempted_providers": attempted_providers,
                    "fallback_reasons": fallback_reasons,
                    "response_time": time.time() - start_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    "retry_attempts": metadata.get("retry_count", 1)  # Track retry count
                })
                
                # Update last used provider
                self.last_used_provider = provider_name
                self.last_fallback_reason = None if not fallback_reasons else "; ".join(fallback_reasons)
                
                logger.info(f"Successfully got response from {provider_name}")
                
                return response, metadata
                
            except Exception as e:
                # NEW: Record failure in circuit breaker
                if provider_name in self.circuit_breakers:
                    breaker = self.circuit_breakers[provider_name]
                    old_state = breaker.state
                    breaker.record_failure()
                    new_state = breaker.state
                    
                    # Log state transition if changed
                    if old_state != new_state:
                        logger.warning(
                            f"{provider_name}: Circuit transitioned {old_state.value} → {new_state.value} "
                            f"(failure: {type(e).__name__})"
                        )
                
                # Mark provider as failed
                self.provider_status[provider_name] = ProviderStatus.FAILED
                reason = f"Provider {provider_name} failed: {type(e).__name__}: {str(e)}"
                fallback_reasons.append(reason)
                logger.warning(reason)
                
                # Continue to next provider
                continue
        
        # If we get here, all providers failed
        error_msg = "All providers failed to respond"
        metadata = {
            "error": error_msg,
            "attempted_providers": attempted_providers,
            "fallback_reasons": fallback_reasons,
            "response_time": time.time() - start_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.error(error_msg)
        return None, metadata
    
    async def get_response_with_routing(
        self,
        prompt: str,
        intent: str,
        messages: Optional[List[Dict[str, str]]] = None,
        model_override: Optional[str] = None,
        **kwargs
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Query AI providers with intelligent model routing based on intent
        
        Args:
            prompt: The user's input prompt
            intent: Detected intent type for model selection
            messages: Optional conversation history for context
            model_override: Optional user-specified model name
            **kwargs: Additional arguments to pass to providers
            
        Returns:
            Tuple containing:
            - response text (or None if all providers failed)
            - metadata dictionary with provider/model info, tokens, timing, etc.
        """
        start_time = time.time()
        
        # Select model using model router
        if self.model_router:
            selected_provider, selected_model, selection_reason = self.model_router.select_model(
                intent=intent,
                user_preference=model_override
            )
            
            logger.info(
                f"Model router selected: {selected_provider}/{selected_model} "
                f"(intent={intent}, reason={selection_reason})"
            )
        else:
            # Fallback to default provider if no router
            selected_provider, selected_model, selection_reason = "groq", "mixtral-8x7b-32768", "no_router"
            logger.warning("No model router configured, using default provider")
        
        # Get provider instance
        provider = self._get_provider_by_name(selected_provider)
        
        if not provider:
            logger.error(f"Provider {selected_provider} not available, falling back to default routing")
            return await self.query(prompt, messages=messages, **kwargs)
        
        # Update provider's model if it supports it
        original_model = provider.model
        provider.model = selected_model
        
        # Try the selected provider with fallback to next best models
        try:
            response, metadata = await self.query(prompt, messages=messages, **kwargs)
            
            # Update metadata with routing information
            metadata.update({
                "selected_provider": selected_provider,
                "selected_model": selected_model,
                "selection_reason": selection_reason,
                "intent": intent,
                "model_override": model_override
            })
            
            # Track which model was actually used
            actual_provider = metadata.get("provider", selected_provider)
            if actual_provider == selected_provider:
                self.last_used_model = selected_model
            
            return response, metadata
            
        finally:
            # Restore original model
            provider.model = original_model
    
    def _get_provider_by_name(self, provider_name: str) -> Optional[BaseProvider]:
        """
        Get a provider instance by name
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider instance or None if not found
        """
        provider_name_lower = provider_name.lower().strip()
        
        for provider in self.providers:
            if provider.name.lower() == provider_name_lower:
                return provider
        
        return None
    
    async def get_response(
        self,
        prompt: str,
        intent: Optional[str] = None,
        model_override: Optional[str] = None,
        **kwargs
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Query AI providers with optional model routing
        
        Args:
            prompt: The user's input prompt
            intent: Optional detected intent type for model selection
            model_override: Optional user-specified model name
            **kwargs: Additional arguments to pass to providers
            
        Returns:
            Tuple containing:
            - response text (or None if all providers failed)
            - metadata dictionary with provider/model info, tokens, timing, etc.
        """
        # If intent and model_router are available, use intelligent routing
        if intent and self.model_router and (model_override or intent != "chat"):
            return await self.get_response_with_routing(
                prompt=prompt,
                intent=intent,
                model_override=model_override,
                **kwargs
            )
        
        # Otherwise use standard fallback behavior
        return await self.query(prompt, **kwargs)
    
    def get_provider_status(self) -> Dict[str, Any]:
        """
        Get the current status of all providers including circuit breaker state
        
        Returns:
            Dictionary with provider status information
        """
        status_info = {}
        
        for provider in self.providers:
            provider_name = provider.name
            breaker_status = {}
            
            # Include circuit breaker status if available
            if provider_name in self.circuit_breakers:
                breaker = self.circuit_breakers[provider_name]
                breaker_status = breaker.get_status()
            
            status_info[provider_name] = {
                "status": self.provider_status.get(provider_name, ProviderStatus.AVAILABLE),
                "model": provider.model,
                "limits": provider.get_limits(),
                "remaining": provider.get_remaining_quota(),
                "circuit_breaker": breaker_status,
                "available_for_requests": self._is_provider_available(provider_name)
            }
        
        return status_info
    
    def get_last_fallback_info(self) -> Dict[str, Any]:
        """
        Get information about the last fallback event
        
        Returns:
            Dictionary with fallback information
        """
        return {
            "last_used_provider": self.last_used_provider,
            "last_fallback_reason": self.last_fallback_reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def reset_failed_providers(self) -> None:
        """
        Reset the status of failed providers
        This can be called periodically to give failed providers another chance
        """
        reset_count = 0
        
        for provider in self.providers:
            if self.provider_status.get(provider.name) == ProviderStatus.FAILED:
                self.provider_status[provider.name] = ProviderStatus.AVAILABLE
                reset_count += 1
                logger.info(f"Reset failed status for {provider.name}")
        
        if reset_count > 0:
            logger.info(f"Reset {reset_count} failed providers")