import uvicorn
from src.utils.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.API:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )
