"""
Providers Command for YamiBot

Implements the /providers command that lists all available AI providers and their details.
"""

import discord
from discord import app_commands
from discord.ext import commands

from ..utils.logger import setup_logging

logger = setup_logging(__name__)

class ProvidersCommand(commands.Cog):
    """
    Discord cog implementing the /providers command
    """
    
    def __init__(self, bot):
        """
        Initialize the ProvidersCommand cog
        
        Args:
            bot: The main bot instance
        """
        self.bot = bot
    
    @app_commands.command(name="providers", description="List all available AI providers")
    async def providers(self, interaction: discord.Interaction):
        """
        Handle the /providers command
        
        Args:
            interaction: Discord interaction object
        """
        await interaction.response.defer(thinking=True)
        
        try:
            # Get provider status
            provider_status = self.bot.fallback_manager.get_provider_status()
            
            # Create embed
            embed = self._create_providers_embed(provider_status)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error processing /providers command: {e}", exc_info=True)
            
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while fetching provider information.",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(embed=error_embed)
    
    def _create_providers_embed(self, provider_status: dict) -> discord.Embed:
        """
        Create a formatted embed for the providers information
        
        Args:
            provider_status: Current status of all providers
            
        Returns:
            Formatted Discord embed
        """
        embed = discord.Embed(
            title="🤖 YamiBot AI Providers",
            description="List of all available AI providers with their capabilities and limits",
            color=discord.Color.blue()
        )
        
        # Add provider priority info
        embed.add_field(
            name="📋 Provider Priority",
            value="Groq → Cerebras → Google → OpenRouter → Mistral",
            inline=False
        )
        
        # Add each provider's details
        priority_order = [
            "groq", "cerebras", "google", "openrouter", "mistral"
        ]
        
        for i, provider_name in enumerate(priority_order, 1):
            if provider_name in provider_status:
                status_info = provider_status[provider_name]
                status = status_info["status"]
                model = status_info["model"]
                limits = status_info["limits"]
                
                # Get status emoji
                if status == "available":
                    status_emoji = "🟢"
                elif status == "rate_limited":
                    status_emoji = "🟡"
                else:
                    status_emoji = "🔴"
                
                # Format limits
                limit_desc = limits.get("description", "No specific limits")
                
                provider_desc = (
                    f"{status_emoji} **Priority {i}**\n"
                    f"Model: `{model}`\n"
                    f"Status: {status}\n"
                    f"Limits: {limit_desc}"
                )
                
                embed.add_field(
                    name=f"🤖 {provider_name.capitalize()}",
                    value=provider_desc,
                    inline=False
                )
        
        # Add fallback explanation
        embed.add_field(
            name="🔄 Fallback System",
            value=(
                "YamiBot automatically falls back to the next available provider "
                "if the current provider is rate-limited, unavailable, or fails. "
                "This ensures maximum reliability and uptime."
            ),
            inline=False
        )
        
        # Add footer
        embed.set_footer(
            text="YamiBot • Multi-Provider AI System"
        )
        
        return embed

def setup(bot):
    """
    Setup function for cog loading
    """
    return ProvidersCommand(bot)