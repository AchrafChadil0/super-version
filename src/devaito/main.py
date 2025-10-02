from fastapi import FastAPI

from src.devaito.api.routes import cache, database

app = FastAPI()

# include routers

app.include_router(cache.router, prefix="/api/v1", tags=["Cache Management"])
app.include_router(database.router, prefix="/api/v1", tags=["Database Management"])
