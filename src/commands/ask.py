"""
Ask Command for YamiBot

Implements the /ask command that allows users to query the AI providers.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import time

from ..utils.logger import setup_logging
from ..utils.cache import cache

logger = setup_logging(__name__)

class AskCommand(commands.Cog):
    """
    Discord cog implementing the /ask command
    """
    
    def __init__(self, bot):
        """
        Initialize the AskCommand cog
        
        Args:
            bot: The main bot instance
        """
        self.bot = bot
        
    @app_commands.command(name="ask", description="Ask the AI a question")
    @app_commands.describe(question="Your question for the AI")
    async def ask(self, interaction: discord.Interaction, question: str):
        """
        Handle the /ask command
        
        Args:
            interaction: Discord interaction object
            question: The user's question
        """
        await interaction.response.defer(thinking=True)
        
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"ask:{question[:100]}"  # Use first 100 chars as cache key
            cached_response = cache.get(cache_key)
            
            if cached_response:
                logger.info(f"Cache hit for question: {question[:50]}...")
                response_text, metadata = cached_response
                provider_used = metadata.get("provider", "unknown")
                
                embed = self._create_response_embed(
                    question, response_text, provider_used, metadata, True
                )
                
                await interaction.followup.send(embed=embed)
                return
            
            # Query the fallback manager
            logger.info(f"Processing question from {interaction.user}: {question[:100]}...")
            
            response_text, metadata = await self.bot.fallback_manager.query(question)
            
            if response_text is None:
                error_msg = "Sorry, all AI providers are currently unavailable. Please try again later."
                embed = discord.Embed(
                    title="❌ AI Unavailable",
                    description=error_msg,
                    color=discord.Color.red()
                )
                
                # Add fallback reasons if available
                if metadata.get("fallback_reasons"):
                    reasons = "\n".join(metadata["fallback_reasons"])
                    embed.add_field(name="Details", value=reasons, inline=False)
                
                await interaction.followup.send(embed=embed)
                return
            
            # Cache the response
            cache.set(cache_key, (response_text, metadata), ttl=3600)  # Cache for 1 hour
            
            # Update rate limiter
            provider_used = metadata.get("provider", "unknown")
            if provider_used != "unknown":
                self.bot.rate_limiter.record_request(provider_used)
            
            # Create and send response embed
            embed = self._create_response_embed(
                question, response_text, provider_used, metadata, False
            )
            
            await interaction.followup.send(embed=embed)
            
            logger.info(f"Successfully answered question using {provider_used} provider")
            
        except Exception as e:
            logger.error(f"Error processing /ask command: {e}", exc_info=True)
            
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while processing your request. Please try again later.",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(embed=error_embed)
    
    def _create_response_embed(
        self, question: str, response: str, provider: str, 
        metadata: dict, is_cached: bool
    ) -> discord.Embed:
        """
        Create a formatted embed for the AI response
        
        Args:
            question: The original question
            response: The AI's response
            provider: The provider that was used
            metadata: Additional metadata from the response
            is_cached: Whether this response came from cache
            
        Returns:
            Formatted Discord embed
        """
        # Truncate long responses
        max_response_length = 1000
        truncated_response = response if len(response) <= max_response_length else response[:max_response_length] + "..."
        
        # Create embed
        embed = discord.Embed(
            title="🤖 AI Response",
            description=truncated_response,
            color=discord.Color.blue()
        )
        
        # Add question field
        embed.add_field(
            name="📝 Your Question",
            value=question[:256] + ("..." if len(question) > 256 else ""),
            inline=False
        )
        
        # Add provider info
        provider_info = f"🔧 Provider: {provider.capitalize()}"
        if is_cached:
            provider_info += " (from cache)"
        
        embed.add_field(name="📊 Info", value=provider_info, inline=True)
        
        # Add token info if available
        if metadata.get("total_tokens"):
            token_info = f"🪙 Tokens: {metadata['total_tokens']} ({metadata.get('input_tokens', 0)} in, {metadata.get('output_tokens', 0)} out)"
            embed.add_field(name="📈 Usage", value=token_info, inline=True)
        
        # Add timing info
        response_time = metadata.get("response_time", 0)
        if response_time > 0:
            embed.add_field(
                name="⏱️ Response Time",
                value=f"{response_time:.2f} seconds",
                inline=True
            )
        
        # Add model info
        if metadata.get("model"):
            embed.add_field(
                name="🧠 Model",
                value=metadata["model"],
                inline=True
            )
        
        # Add footer with timestamp
        embed.set_footer(
            text=f"YamiBot • {metadata.get('timestamp', 'Unknown time')}"
        )
        
        return embed

def setup(bot):
    """
    Setup function for cog loading
    """
    return AskCommand(bot)