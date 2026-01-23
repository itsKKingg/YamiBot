[1mdiff --git a/requirements.txt b/requirements.txt[m
[1mindex c1f3d1a..09b33cc 100644[m
[1m--- a/requirements.txt[m
[1m+++ b/requirements.txt[m
[36m@@ -1,26 +1,31 @@[m
 # YamiBot Requirements[m
[31m-# Production dependencies[m
[32m+[m[32m# Production dependencies with pinned versions for reproducibility[m
[32m+[m[32m# Last updated: 2025-01-23[m
 [m
 # Discord bot framework[m
[31m-discord.py>=2.3.2[m
[32m+[m[32mdiscord.py==2.4.0[m
 [m
 # AI Provider SDKs[m
[31m-groq>=0.5.0[m
[31m-mistralai>=0.0.7[m
[31m-google-generativeai>=0.3.0[m
[31m-aiohttp>=3.9.0[m
[32m+[m[32mgroq==0.13.0[m
[32m+[m[32mmistralai==1.0.4[m
[32m+[m[32mgoogle-generativeai==0.8.3[m
[32m+[m
[32m+[m[32m# HTTP client[m
[32m+[m[32maiohttp==3.10.5[m
 [m
 # Health check server[m
[31m-fastapi>=0.95.0[m
[31m-uvicorn>=0.21.0[m
[32m+[m[32mfastapi==0.115.4[m
[32m+[m[32muvicorn[standard]==0.32.0[m
 [m
 # Utility libraries[m
[31m-python-dotenv>=1.0.0[m
[31m-psutil>=5.9.0[m
[32m+[m[32mpython-dotenv==1.0.1[m
[32m+[m[32mpsutil==6.0.0[m
 [m
[31m-# Development dependencies (commented out for production)[m
[31m-# pytest>=7.0.0[m
[31m-# pytest-asyncio>=0.21.0[m
[31m-# black>=23.0.0[m
[31m-# isort>=5.0.0[m
[31m-# mypy>=1.0.0[m
[32m+[m[32m# Development dependencies (uncomment for development)[m
[32m+[m[32m# pytest==8.3.3[m
[32m+[m[32m# pytest-asyncio==0.24.0[m
[32m+[m[32m# pytest-cov==6.0.0[m
[32m+[m[32m# black==24.10.0[m
[32m+[m[32m# isort==5.13.2[m
[32m+[m[32m# mypy==1.12.1[m
[32m+[m[32m# ruff==0.7.2[m
