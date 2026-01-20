# Dockerfile for YamiBot
# Multi-stage build for production-ready AI Discord bot

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy built dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Create logs directory
RUN mkdir -p logs

# Set permissions
RUN chown -R nobody:nogroup /app && \
    chmod -R 755 /app

# Switch to non-root user
USER nobody:nogroup

# Health check endpoint (simple HTTP server for health checks)
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import http.server; import socketserver; \
    class Handler(http.server.BaseHTTPRequestHandler): \
        def do_GET(self): \
            self.send_response(200); \
            self.send_header('Content-type', 'text/plain'); \
            self.end_headers(); \
            self.wfile.write(b'YamiBot is healthy'); \
    with socketserver.TCPServer(('', 8000), Handler) as httpd: \
        httpd.serve_forever()" || exit 1

# Command to run the bot
CMD ["python", "-m", "src.bot"]