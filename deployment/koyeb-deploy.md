# Koyeb Deployment Guide for YamiBot

This guide provides step-by-step instructions for deploying YamiBot to Koyeb, a serverless platform for running containerized applications.

## Prerequisites

1. **Koyeb Account**: Sign up at [koyeb.com](https://www.koyeb.com/)
2. **GitHub Account**: Your YamiBot code should be in a GitHub repository
3. **Docker**: Installed locally for testing
4. **All API Keys**: You need API keys for all providers (see .env.example)

## Step 1: Prepare Your Repository

1. **Commit all changes** to your GitHub repository
2. **Create a `.env` file** with all required API keys:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

## Step 2: Test Locally with Docker

Before deploying to Koyeb, test your bot locally:

```bash
# Build the Docker image
docker-compose -f deployment/docker-compose.yml build

# Start the bot
docker-compose -f deployment/docker-compose.yml up

# Test the bot in your Discord server
```

## Step 3: Create Koyeb Account and Connect GitHub

1. **Sign up** for Koyeb at [koyeb.com](https://www.koyeb.com/)
2. **Connect your GitHub account**:
   - Go to "Account Settings" → "GitHub Integration"
   - Authorize Koyeb to access your repositories

## Step 4: Create a New Service

1. Click "Create Service" in the Koyeb dashboard
2. Select "GitHub" as the source
3. Choose your YamiBot repository
4. Select the branch you want to deploy (usually `main` or `production`)

## Step 5: Configure Build Settings

1. **Buildpack**: Select "Docker"
2. **Dockerfile**: Set to `deployment/Dockerfile`
3. **Build Context**: Leave as `/`
4. **Build Arguments**: None needed

## Step 6: Configure Environment Variables

Add all required environment variables from your `.env` file:

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_TOKEN` | Your Discord bot token | ✅ |
| `GROQ_API_KEY` | Groq API key | ✅ |
| `CEREBRAS_API_KEY` | Cerebras API key | ✅ |
| `GOOGLE_AI_API_KEY` | Google AI API key | ✅ |
| `OPENROUTER_API_KEY` | OpenRouter API key | ✅ |
| `MISTRAL_API_KEY` | Mistral API key | ✅ |
| `BOT_PREFIX` | Bot command prefix (default: `!`) | ❌ |
| `SYNC_COMMANDS` | Sync commands on startup (default: `true`) | ❌ |
| `DEBUG_MODE` | Enable debug logging (default: `false`) | ❌ |

## Step 7: Configure Resource Settings

1. **Instance Type**: Start with "Small" (1 vCPU, 2GB RAM)
2. **Scaling**: Set to 1 instance (Discord bots typically need only 1 instance)
3. **Regions**: Choose the region closest to your users

## Step 8: Configure Networking

1. **Port**: Set to `8000` (for health checks)
2. **Protocol**: HTTP
3. **Public**: Enable (for health checks)
4. **Paths**: `/health` (health check endpoint)

## Step 9: Deploy the Service

1. Click "Deploy" to start the deployment process
2. Wait for the build to complete (this may take a few minutes)
3. Monitor the logs to ensure the bot starts successfully

## Step 10: Verify Deployment

1. **Check logs**: Look for "Bot is ready and operational" in the logs
2. **Test commands**: Try `/ask`, `/status`, and `/providers` in your Discord server
3. **Monitor health**: The `/health` endpoint should return "YamiBot is healthy"

## Step 11: Set Up Auto-Deploy (Optional)

1. Go to your service settings
2. Enable "Auto-deploy on commit"
3. Select the branch to monitor for changes
4. Save settings

Now your bot will automatically update when you push changes to the selected branch.

## Step 12: Monitoring and Maintenance

### Monitoring
- **Logs**: Available in the Koyeb dashboard
- **Metrics**: CPU, memory, and network usage
- **Alerts**: Set up alerts for errors or high resource usage

### Scaling
- If your bot grows, you can:
  - Increase instance size
  - Add more instances (though Discord bots typically don't need horizontal scaling)
  - Adjust resource limits

### Updates
- Push changes to your GitHub repository
- Koyeb will automatically rebuild and redeploy (if auto-deploy is enabled)
- Monitor the deployment logs for any issues

## Troubleshooting

### Common Issues

1. **Bot doesn't start**:
   - Check that all environment variables are set correctly
   - Verify your Discord token is valid
   - Check the logs for specific error messages

2. **API errors**:
   - Verify all API keys are correct
   - Check that you haven't exceeded rate limits
   - Test each provider individually

3. **Health check failures**:
   - Ensure port 8000 is exposed
   - Check that the health check endpoint is working locally
   - Verify the bot is actually running

4. **Deployment failures**:
   - Check Dockerfile for syntax errors
   - Test building locally first
   - Verify all dependencies are listed in requirements.txt

### Debugging

Enable debug mode by setting `DEBUG_MODE=true` in your environment variables. This will:
- Increase log verbosity
- Provide more detailed error messages
- Help identify configuration issues

## Cost Optimization

1. **Use the free tier** for small bots
2. **Monitor usage** to avoid unnecessary costs
3. **Set appropriate limits** in the rate limiter
4. **Use caching** to reduce API calls
5. **Scale down** when not in use (though Discord bots need to be always on)

## Security Best Practices

1. **Never commit API keys** to your repository
2. **Use Koyeb's secret management** for sensitive data
3. **Rotate API keys** regularly
4. **Monitor for unusual activity**
5. **Keep dependencies updated**

## Support

If you encounter issues:
1. Check the [Koyeb documentation](https://www.koyeb.com/docs)
2. Review the YamiBot logs
3. Test locally to isolate the issue
4. Contact Koyeb support if needed

Happy deploying! 🚀