"""
Health check server for YamiBot

This module provides a minimal FastAPI HTTP server that runs on port 8000
and responds to health checks from Koyeb or other cloud providers.
"""

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import asyncio
import uvicorn
from typing import Optional

logger = logging.getLogger(__name__)

app = FastAPI(
    title="YamiBot Health Check",
    description="Lightweight health check endpoint for Koyeb deployment",
    version="1.0.0"
)

@app.get("/health", response_class=JSONResponse)
async def health():
    """
    Health check endpoint that returns bot status
    
    Returns:
        JSONResponse with status and bot information
    """
    logger.debug("Health check requested")
    return {"status": "healthy", "bot": "running"}

class HealthCheckServer:
    """
    Manages the FastAPI health check server lifecycle
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self._server: Optional[uvicorn.Server] = None
        self._shutdown_event = asyncio.Event()
    
    def start_server(self):
        """
        Start the FastAPI server in a background task
        """
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False,  # Disable access logs to reduce noise
        )
        
        self._server = uvicorn.Server(config)
        logger.info(f"Starting health check server on {self.host}:{self.port}")
        
        # Start server in background task
        asyncio.create_task(self._run_server())
    
    async def _run_server(self):
        """
        Internal coroutine to run the server
        """
        try:
            await self._server.serve()
        except asyncio.CancelledError:
            logger.info("Health check server task cancelled")
            raise
        except Exception as e:
            logger.error(f"Health check server error: {e}", exc_info=True)
    
    async def stop_server(self):
        """
        Gracefully stop the health check server
        """
        if self._server:
            logger.info("Shutting down health check server...")
            self._server.should_exit = True
            await self._server.shutdown()
            logger.info("Health check server stopped")

# Global health check server instance
_health_server: Optional[HealthCheckServer] = None

def start_health_server(host: str = "0.0.0.0", port: int = 8000) -> HealthCheckServer:
    """
    Start the health check server
    
    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 8000)
    
    Returns:
        HealthCheckServer instance
    """
    global _health_server
    
    if _health_server is None:
        _health_server = HealthCheckServer(host, port)
        _health_server.start_server()
    
    return _health_server

async def stop_health_server():
    """
    Stop the health check server if running
    """
    global _health_server
    
    if _health_server:
        await _health_server.stop_server()
        _health_server = None