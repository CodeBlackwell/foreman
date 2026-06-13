from fastapi import Request
from src.core.neo4j_client import Neo4jClient


def get_db(request: Request) -> Neo4jClient:
    return request.app.state.db  # type: ignore[no-any-return]
