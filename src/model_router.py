"""
Model Router for YamiBot

This module provides intelligent model selection based on prompt intent,
user preferences, and provider health status.
"""

from typing import Dict, List, Optional, Tuple
import re

from .model_registry import ModelRegistry
from .utils.logger import setup_logging

logger = setup_logging(__name__)


class ModelRouter:
    """
    Intelligent model router that selects the best model based on intent,
    user preferences, and provider health
    """
    
    # Intent to model mapping (in priority order)
    INTENT_MODEL_MAPPING: Dict[str, List[Tuple[str, str]]] = {
        "coding": [
            ("cerebras", "gpt-oss-120b"),
            ("groq", "llama-3.1-405b"),
            ("groq", "llama-3.1-70b"),
            ("sambanova", "gpt-oss-120b")
        ],
        "search": [
            ("google", "gemini-2.0-flash"),
            ("google", "gemini-1.5-pro"),
            ("google", "gemini-1.5-flash")
        ],
        "image_analysis": [
            ("google", "gemini-1.5-pro"),
            ("google", "gemini-2.0-flash")
        ],
        "creative": [
            ("mistral", "mistral-large-2411"),
            ("mistral", "mistral-medium"),
            ("groq", "mixtral-8x7b-32768")
        ],
        "math_logic": [
            ("groq", "llama-3.1-405b"),
            ("cerebras", "gpt-oss-120b"),
            ("google", "gemini-1.5-pro"),
            ("groq", "llama-3.1-70b")
        ],
        "reasoning": [
            ("google", "gemini-1.5-pro"),
            ("groq", "llama-3.1-405b"),
            ("cerebras", "gpt-oss-120b"),
            ("mistral", "mistral-large-2411")
        ],
        "fast": [
            ("groq", "mixtral-8x7b-32768"),
            ("groq", "llama-3.1-8b"),
            ("mistral", "mistral-small"),
            ("google", "gemini-1.5-flash")
        ],
        "general": [
            ("groq", "mixtral-8x7b-32768"),
            ("mistral", "mistral-medium"),
            ("cerebras", "gpt-oss-120b"),
            ("google", "gemini-1.5-flash")
        ],
        "chat": [
            ("groq", "mixtral-8x7b-32768"),
            ("mistral", "mistral-medium"),
            ("cerebras", "gpt-oss-120b")
        ]
    }
    
    def __init__(self, model_registry: ModelRegistry, fallback_manager=None):
        """
        Initialize the model router
        
        Args:
            model_registry: ModelRegistry instance for model metadata
            fallback_manager: Optional FallbackManager for checking provider health
        """
        self.model_registry = model_registry
        self.fallback_manager = fallback_manager
        self._selection_history = []
        
        logger.info("ModelRouter initialized with intelligent routing")
    
    def select_model(
        self,
        intent: str,
        user_preference: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Select the best model for a given intent, with optional user override
        
        Args:
            intent: Detected intent type
            user_preference: Optional user-specified model name
            
        Returns:
            Tuple of (provider, model, selection_reason)
        """
        # If user preference provided, try to use it
        if user_preference:
            provider, model, reason = self.override_model(user_preference)
            if provider and model:
                logger.debug(f"Using user preference: {provider}/{model} for intent={intent}")
                self._track_selection(provider, model, intent, "user_override")
                return provider, model, reason
            
            logger.warning(f"User preference '{user_preference}' invalid, using intent-based routing")
        
        # Use intent-based routing
        provider, model, reason = self.get_best_model_for_intent(intent)
        self._track_selection(provider, model, intent, "intent_routing")
        
        logger.debug(f"Selected {provider}/{model} for intent={intent} ({reason})")
        
        return provider, model, reason
    
    def get_best_model_for_intent(self, intent: str) -> Tuple[str, str, str]:
        """
        Get the primary (best) model for a specific intent
        
        Args:
            intent: Intent type
            
        Returns:
            Tuple of (provider, model, reason)
        """
        intent_lower = intent.lower().strip()
        
        # Get models for this intent from the mapping
        models_for_intent = self.INTENT_MODEL_MAPPING.get(intent_lower, [])
        
        # If no specific mapping, try 'general' or 'chat'
        if not models_for_intent:
            models_for_intent = self.INTENT_MODEL_MAPPING.get("general", [])
            if not models_for_intent:
                models_for_intent = self.INTENT_MODEL_MAPPING.get("chat", [])
        
        # Try each model in priority order until we find an available one
        for provider, model in models_for_intent:
            if self.is_model_available(provider, model):
                reason = f"best_match_{intent}"
                return provider, model, reason
            
            logger.debug(f"Model {provider}/{model} not available, trying next")
        
        # Fallback to any available model if none match intent
        logger.warning(f"No models available for intent {intent}, using fallback")
        return self._get_fallback_model()
    
    def get_fallback_models(self, intent: str) -> List[Tuple[str, str]]:
        """
        Get backup models for a specific intent
        
        Args:
            intent: Intent type
            
        Returns:
            List of (provider, model) tuples for fallback
        """
        intent_lower = intent.lower().strip()
        models_for_intent = self.INTENT_MODEL_MAPPING.get(intent_lower, [])
        
        # Return all models for the intent (excluding the first one which is the primary)
        if len(models_for_intent) > 1:
            return models_for_intent[1:]
        
        # If no specific intent mapping, return general models
        return self.INTENT_MODEL_MAPPING.get("general", [])
    
    def override_model(self, model_name: str) -> Tuple[Optional[str], Optional[str], str]:
        """
        Find and validate a manual model override by name
        
        Args:
            model_name: Model name specified by user
            
        Returns:
            Tuple of (provider, model, reason) or (None, None, reason) if invalid
        """
        # Normalize model name
        model_name_clean = model_name.lower().strip()
        
        # Try to find the model in the registry
        result = self.model_registry.find_model_by_name(model_name_clean)
        
        if result:
            provider, model = result
            
            # Check if model is available
            if self.is_model_available(provider, model):
                logger.info(f"Manual override: {provider}/{model}")
                return provider, model, "manual_override"
            else:
                reason = f"model_unavailable_{provider}"
                logger.warning(f"Manual override '{model_name}' found but provider {provider} is unavailable")
                return None, None, reason
        
        logger.warning(f"Manual override '{model_name}' not found in model registry")
        return None, None, "model_not_found"
    
    def is_model_available(self, provider: str, model: str) -> bool:
        """
        Check if a model's provider is healthy and available
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            True if model is available, False otherwise
        """
        # First, check if the model exists in the registry
        if not self.model_registry.validate_model(provider, model):
            logger.debug(f"Model {provider}/{model} not in registry")
            return False
        
        # Check provider health if fallback_manager is available
        if self.fallback_manager:
            # Check if provider has an open circuit breaker
            if hasattr(self.fallback_manager, 'circuit_breakers'):
                circuit_breaker = self.fallback_manager.circuit_breakers.get(provider)
                if circuit_breaker:
                    # Check if provider can attempt requests
                    if not circuit_breaker.can_attempt():
                        logger.debug(f"Provider {provider} circuit is {circuit_breaker.state.value}, model unavailable")
                        return False
            
            # Check provider status
            provider_status = self.fallback_manager.provider_status.get(provider)
            if provider_status and provider_status != "available":
                logger.debug(f"Provider {provider} status: {provider_status}, model unavailable")
                return False
        
        return True
    
    def _get_fallback_model(self) -> Tuple[str, str, str]:
        """
        Get a fallback model when no specific intent matches
        
        Returns:
            Tuple of (provider, model, reason)
        """
        # Try providers in priority order for any available model
        for provider in self.model_registry.get_all_providers():
            models = self.model_registry.get_provider_models(provider)
            for model in models.keys():
                if self.is_model_available(provider, model):
                    logger.info(f"Using fallback model: {provider}/{model}")
                    return provider, model, "fallback"
        
        # Last resort - return a default even if not available
        logger.error("No models available, returning default")
        return "groq", "mixtral-8x7b-32768", "emergency_fallback"
    
    def _track_selection(self, provider: str, model: str, intent: str, method: str) -> None:
        """
        Track model selection for analytics
        
        Args:
            provider: Selected provider
            model: Selected model
            intent: Intent type
            method: Selection method (e.g., "intent_routing", "user_override")
        """
        self._selection_history.append({
            "provider": provider,
            "model": model,
            "intent": intent,
            "method": method,
            "timestamp": None  # Will be set when used
        })
        
        # Keep history limited to last 1000 selections
        if len(self._selection_history) > 1000:
            self._selection_history = self._selection_history[-1000:]
    
    def get_selection_history(self, limit: int = 10) -> List[Dict[str, any]]:
        """
        Get recent model selection history
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of selection history entries
        """
        return self._selection_history[-limit:]
    
    def get_model_for_capability(self, capability: str) -> Optional[Tuple[str, str]]:
        """
        Get a model that supports a specific capability
        
        Args:
            capability: Required capability (e.g., "web_search", "image_analysis")
            
        Returns:
            Tuple of (provider, model) or None if no model found
        """
        for provider, models in self.model_registry.get_all_models().items():
            for model_name, model_info in models.items():
                capabilities = model_info.get("capabilities", [])
                if capability in capabilities and self.is_model_available(provider, model_name):
                    return provider, model_name
        
        return None
    
    def get_models_by_criteria(
        self,
        max_cost: Optional[str] = None,
        min_speed: Optional[str] = None,
        min_reasoning: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Get models that match specific criteria
        
        Args:
            max_cost: Maximum cost tier (e.g., "low", "medium")
            min_speed: Minimum speed tier (e.g., "high", "very_high")
            min_reasoning: Minimum reasoning tier (e.g., "medium", "high")
            
        Returns:
            List of (provider, model) tuples matching criteria
        """
        matching_models = []
        
        # Cost tier ordering (lower is cheaper)
        cost_tiers = ["very_low", "low", "medium", "high"]
        
        # Speed tier ordering (higher is faster)
        speed_tiers = ["very_low", "low", "medium", "high", "very_high"]
        
        # Reasoning tier ordering (higher is better)
        reasoning_tiers = ["very_low", "low", "medium", "high", "very_high"]
        
        for provider, models in self.model_registry.get_all_models().items():
            for model_name, model_info in models.items():
                # Check cost criteria
                if max_cost:
                    cost = model_info.get("cost", "medium")
                    if cost_tiers.index(cost) > cost_tiers.index(max_cost):
                        continue
                
                # Check speed criteria
                if min_speed:
                    speed = model_info.get("speed", "medium")
                    if speed_tiers.index(speed) < speed_tiers.index(min_speed):
                        continue
                
                # Check reasoning criteria
                if min_reasoning:
                    reasoning = model_info.get("reasoning", "medium")
                    if reasoning_tiers.index(reasoning) < reasoning_tiers.index(min_reasoning):
                        continue
                
                # Check availability
                if self.is_model_available(provider, model_name):
                    matching_models.append((provider, model_name))
        
        return matching_models
    
    def extract_model_override(self, message: str) -> Optional[str]:
        """
        Extract model override from a user message
        
        Args:
            message: User message text
            
        Returns:
            Model name if override detected, None otherwise
        """
        # Pattern to match "use [model] for this" or similar
        patterns = [
            r"use\s+(\S+?(?:-\d+(?:\.\d+)?)*)\s+for\s+this",
            r"use\s+(\S+?(?:-\d+(?:\.\d+)?)*)\s+to\s+\w+",
            r"use\s+(\S+?(?:-\d+(?:\.\d+)?)*)\s*\.?$",
            r"switch\s+to\s+(\S+?(?:-\d+(?:\.\d+)?)*)",
            r"change\s+to\s+(\S+?(?:-\d+(?:\.\d+)?)*)",
        ]
        
        message_lower = message.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                model_name = match.group(1).strip()
                logger.debug(f"Extracted model override: {model_name}")
                return model_name
        
        return None
