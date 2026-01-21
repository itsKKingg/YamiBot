"""
Status Command for YamiBot

Implements the /status command that shows the current status of all AI providers.
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from ..utils.logger import setup_logging

logger = setup_logging(__name__)

class StatusCommand(commands.Cog):
    """
    Discord cog implementing the /status command
    """
    
    def __init__(self, bot):
        """
        Initialize the StatusCommand cog
        
        Args:
            bot: The main bot instance
        """
        self.bot = bot
    
    @app_commands.command(name="status", description="Check the status of AI providers")
    async def status(self, interaction: discord.Interaction):
        """
        Handle the /status command
        
        Args:
            interaction: Discord interaction object
        """
        await interaction.response.defer(thinking=True)
        
        try:
            # Get provider status
            provider_status = self.bot.fallback_manager.get_provider_status()
            
            # Get rate limit info
            rate_limits = self.bot.rate_limiter.get_all_quotas()
            
            # Get fallback info
            fallback_info = self.bot.fallback_manager.get_last_fallback_info()
            
            # Create embed
            embed = self._create_status_embed(provider_status, rate_limits, fallback_info)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error processing /status command: {e}", exc_info=True)
            
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while fetching status information.",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(embed=error_embed)
    
    def _create_status_embed(
        self, provider_status: dict, rate_limits: dict, fallback_info: dict
    ) -> discord.Embed:
        """
        Create a formatted embed for the status information
        
        Args:
            provider_status: Current status of all providers
            rate_limits: Rate limit information for all providers
            fallback_info: Information about recent fallback events
            
        Returns:
            Formatted Discord embed
        """
        embed = discord.Embed(
            title="🔍 YamiBot Status",
            description="Current status of AI providers and system information",
            color=discord.Color.green()
        )
        
        # Add uptime
        if self.bot.start_time:
            uptime = datetime.utcnow() - self.bot.start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
            embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        
        # Add last used provider
        last_provider = fallback_info.get("last_used_provider", "None")
        embed.add_field(name="🔧 Last Provider", value=last_provider.capitalize(), inline=True)
        
        # Add provider status sections
        for provider_name, status_info in provider_status.items():
            status = status_info["status"]
            model = status_info["model"]
            
            # Get status emoji and color
            if status == "available":
                status_emoji = "🟢"
                status_color = discord.Color.green()
            elif status == "rate_limited":
                status_emoji = "🟡"
                status_color = discord.Color.orange()
            else:
                status_emoji = "🔴"
                status_color = discord.Color.red()
            
            # Get rate limit info
            limits = status_info.get("limits", {})
            remaining = status_info.get("remaining", {})
            
            limit_str = ""
            if limits.get("daily"):
                daily_remaining = remaining.get("daily", {}).get("remaining", "N/A")
                limit_str = f"Daily: {daily_remaining}/{limits['daily']}"
            
            if limits.get("rps"):
                if limit_str:
                    limit_str += " | "
                limit_str += f"RPS: {limits['rps']}"
            
            # Create provider status field
            provider_field = (
                f"{status_emoji} **{provider_name.capitalize()}** ({model})\n"
                f"Status: {status}\n"
                f"Limits: {limit_str if limit_str else 'No limits'}"
            )
            
            embed.add_field(
                name=f"🤖 {provider_name.capitalize()}",
                value=provider_field,
                inline=False
            )
        
        # Add fallback information
        if fallback_info.get("last_fallback_reason"):
            embed.add_field(
                name="🔄 Last Fallback",
                value=fallback_info["last_fallback_reason"],
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
    return StatusCommand(bot)