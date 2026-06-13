from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.neo4j_client import Neo4jClient
from src.api.routes import router as router_route, retrieve as retrieve_route, answer as answer_route, docs as docs_route


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.db = Neo4jClient()
    yield
    app.state.db.close()


app = FastAPI(title="foreman", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router_route.router)
app.include_router(retrieve_route.router)
app.include_router(answer_route.router)
app.include_router(docs_route.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
