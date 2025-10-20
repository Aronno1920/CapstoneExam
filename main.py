import uvicorn
from src.utils.config import settings
from src.api.API import app  

if __name__ == "__main__":
    # Allow running via `python main.py`
    if settings.api_reload:
        # Use import string for reload functionality
        uvicorn.run(
            "main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=True,
            log_level=settings.log_level.lower()
        )
    else:
        # Use app object directly for production
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            reload=False,
            log_level=settings.log_level.lower()
        )
