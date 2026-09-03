import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import router
from app.database import initialize_database


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
initialize_database()

app = FastAPI(title="Runelix Product API")
app.include_router(router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled application error for %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    elapsed = time.perf_counter() - started
    logger.info("%s %s -> %s (%.3fs)", request.method, request.url.path, response.status_code, elapsed)
    return response


@app.get("/")
def read_root():
    return {"message": "Runelix Product API"}
