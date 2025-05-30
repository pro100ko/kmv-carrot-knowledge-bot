from aiohttp import web
import os
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def health(request):
    """Health check endpoint"""
    logger.info("Health check requested")
    return web.Response(text="OK")

async def root(request):
    """Root endpoint"""
    logger.info("Root endpoint requested")
    return web.Response(text="Bot server is running")

def main():
    """Create and run the web application"""
    app = web.Application()
    
    # Add routes
    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    
    # Get port from environment
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    
    # Run the application
    web.run_app(app, port=port)

if __name__ == "__main__":
    logger.info("Starting minimal test server")
    main()
