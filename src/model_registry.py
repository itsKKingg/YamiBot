"""
Model Registry for YamiBot

This module provides centralized model management for all AI providers.
It maintains metadata for all available models and provides utility functions
for model discovery and validation.
"""

from typing import Dict, List, Optional, Tuple
import re

from .utils.logger import setup_logging

logger = setup_logging(__name__)


class ModelRegistry:
    """
    Centralized registry for AI models across all providers
    """
    
    # Model registry with metadata
    MODEL_REGISTRY: Dict[str, Dict[str, Dict[str, any]]] = {
        "cerebras": {
            "gpt-oss-120b": {
                "name": "Cerebras GPT-OSS 120B",
                "best_for": ["coding", "technical", "analysis"],
                "cost": "low",
                "speed": "medium",
                "reasoning": "high"
            }
        },
        "sambanova": {
            "gpt-oss-120b": {
                "name": "SambaNova GPT-OSS 120B",
                "best_for": ["coding", "general"],
                "cost": "low",
                "speed": "medium",
                "reasoning": "medium"
            }
        },
        "groq": {
            "mixtral-8x7b-32768": {
                "name": "Mixtral 8x7B (Groq)",
                "best_for": ["general", "creative", "fast"],
                "cost": "very_low",
                "speed": "very_high",
                "reasoning": "medium"
            },
            "llama-3.1-8b": {
                "name": "Llama 3.1 8B (Groq)",
                "best_for": ["fast", "simple"],
                "cost": "very_low",
                "speed": "very_high",
                "reasoning": "low"
            },
            "llama-3.1-70b": {
                "name": "Llama 3.1 70B (Groq)",
                "best_for": ["coding", "reasoning", "general"],
                "cost": "low",
                "speed": "high",
                "reasoning": "high"
            },
            "llama-3.1-405b": {
                "name": "Llama 3.1 405B (Groq)",
                "best_for": ["complex", "reasoning", "math"],
                "cost": "medium",
                "speed": "medium",
                "reasoning": "very_high"
            }
        },
        "mistral": {
            "mistral-small": {
                "name": "Mistral Small",
                "best_for": ["creative", "fast", "casual"],
                "cost": "very_low",
                "speed": "very_high",
                "reasoning": "low"
            },
            "mistral-medium": {
                "name": "Mistral Medium",
                "best_for": ["general", "creative"],
                "cost": "low",
                "speed": "high",
                "reasoning": "medium"
            },
            "mistral-large-2411": {
                "name": "Mistral Large",
                "best_for": ["reasoning", "complex", "technical"],
                "cost": "medium",
                "speed": "medium",
                "reasoning": "high"
            }
        },
        "google": {
            "gemini-2.0-flash": {
                "name": "Gemini 2.0 Flash",
                "best_for": ["multimodal", "search", "fast", "vision"],
                "cost": "low",
                "speed": "very_high",
                "reasoning": "high",
                "capabilities": ["web_search", "image_analysis", "document_reading"]
            },
            "gemini-1.5-pro": {
                "name": "Gemini 1.5 Pro",
                "best_for": ["multimodal", "reasoning", "complex"],
                "cost": "medium",
                "speed": "medium",
                "reasoning": "very_high",
                "capabilities": ["web_search", "image_analysis", "document_reading"]
            },
            "gemini-1.5-flash": {
                "name": "Gemini 1.5 Flash",
                "best_for": ["fast", "multimodal", "general"],
                "cost": "very_low",
                "speed": "very_high",
                "reasoning": "medium",
                "capabilities": ["web_search", "image_analysis", "document_reading"]
            }
        }
    }
    
    def __init__(self):
        """Initialize the model registry"""
        self._registry = self.MODEL_REGISTRY
        logger.info(f"ModelRegistry initialized with {self._count_models()} models")
    
    def get_all_models(self) -> Dict[str, Dict[str, Dict[str, any]]]:
        """
        Get all available models from all providers
        
        Returns:
            Dictionary mapping provider names to their models with metadata
        """
        return self._registry.copy()
    
    def get_provider_models(self, provider: str) -> Dict[str, Dict[str, any]]:
        """
        Get models for a specific provider
        
        Args:
            provider: Provider name (e.g., "cerebras", "groq")
            
        Returns:
            Dictionary of models for the provider with metadata
        """
        provider_lower = provider.lower().strip()
        return self._registry.get(provider_lower, {}).copy()
    
    def get_model_info(self, provider: str, model: str) -> Optional[Dict[str, any]]:
        """
        Get metadata for a specific model
        
        Args:
            provider: Provider name (e.g., "cerebras", "groq")
            model: Model name (e.g., "gpt-oss-120b", "llama-3.1-70b")
            
        Returns:
            Dictionary with model metadata or None if not found
        """
        provider_lower = provider.lower().strip()
        model_lower = model.lower().strip()
        
        provider_models = self._registry.get(provider_lower, {})
        return provider_models.get(model_lower)
    
    def find_model_by_name(self, model_name: str) -> Optional[Tuple[str, str]]:
        """
        Find a provider and model by model name (case-insensitive)
        
        Args:
            model_name: Model name to search for (e.g., "gemini-2.0-flash")
            
        Returns:
            Tuple of (provider, model) or None if not found
        """
        model_name_lower = model_name.lower().strip()
        
        # Exact match first
        for provider, models in self._registry.items():
            if model_name_lower in models:
                return (provider, model_name_lower)
        
        # Partial match (if no exact match)
        for provider, models in self._registry.items():
            for model_name in models.keys():
                if model_name_lower in model_name or model_name in model_name_lower:
                    return (provider, model_name)
        
        return None
    
    def validate_model(self, provider: str, model: str) -> bool:
        """
        Check if a specific model exists for a provider
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            True if model exists, False otherwise
        """
        provider_lower = provider.lower().strip()
        model_lower = model.lower().strip()
        
        provider_models = self._registry.get(provider_lower, {})
        return model_lower in provider_models
    
    def get_models_for_intent(self, intent: str) -> List[Tuple[str, str]]:
        """
        Return ranked (provider, model) pairs for a given intent
        
        Args:
            intent: Intent type (e.g., "coding", "search", "fast")
            
        Returns:
            List of (provider, model) tuples ranked by suitability
        """
        intent_lower = intent.lower().strip()
        scored_models = []
        
        # Score each model based on how well it matches the intent
        for provider, models in self._registry.items():
            for model_name, model_info in models.items():
                best_for = model_info.get("best_for", [])
                score = 0
                
                # Check if intent is in best_for list
                if intent_lower in best_for:
                    # Higher score for being in best_for
                    score = 10
                
                # Bonus for reasoning capability
                reasoning = model_info.get("reasoning", "medium")
                if reasoning in ["high", "very_high"]:
                    score += 2
                
                # Bonus for speed depending on intent
                speed = model_info.get("speed", "medium")
                if intent_lower in ["fast", "search"] and speed in ["high", "very_high"]:
                    score += 3
                
                # Bonus for cost efficiency
                cost = model_info.get("cost", "medium")
                if cost in ["very_low", "low"]:
                    score += 1
                
                if score > 0:
                    scored_models.append((score, provider, model_name))
        
        # Sort by score descending, then by cost (cheaper first for same score)
        scored_models.sort(key=lambda x: (-x[0], x[0]))
        
        # Return just the (provider, model) tuples
        return [(provider, model) for score, provider, model in scored_models]
    
    def get_all_providers(self) -> List[str]:
        """
        Get list of all provider names
        
        Returns:
            List of provider names
        """
        return list(self._registry.keys())
    
    def get_provider_count(self) -> int:
        """
        Get number of providers
        
        Returns:
            Number of providers in the registry
        """
        return len(self._registry)
    
    def _count_models(self) -> int:
        """
        Count total number of models across all providers
        
        Returns:
            Total number of models
        """
        return sum(len(models) for models in self._registry.values())
    
    def get_model_capabilities(self, provider: str, model: str) -> List[str]:
        """
        Get capabilities for a specific model
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            List of model capabilities (e.g., ["web_search", "image_analysis"])
        """
        model_info = self.get_model_info(provider, model)
        if model_info:
            return model_info.get("capabilities", [])
        return []
    
    def is_multimodal(self, provider: str, model: str) -> bool:
        """
        Check if a model supports multimodal input
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            True if model is multimodal, False otherwise
        """
        capabilities = self.get_model_capabilities(provider, model)
        return any(cap in capabilities for cap in ["web_search", "image_analysis", "vision"])
