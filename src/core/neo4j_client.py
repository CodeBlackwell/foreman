from typing import Any
from neo4j import GraphDatabase
from src.core.config import settings


class Neo4jClient:
    def __init__(self) -> None:
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def run(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self._driver.session() as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]

    def vector_search(
        self,
        index_name: str,
        embedding: list[float],
        top_k: int = 5,
        domain_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        if domain_filter:
            query = """
            CALL db.index.vector.queryNodes($index, $top_k, $embedding)
            YIELD node, score
            MATCH (dom:Domain {name: $domain})-[:CONTAINS*1..3]->(node)
            RETURN node, score
            ORDER BY score DESC
            LIMIT $top_k
            """
            return self.run(
                query,
                {"index": index_name, "top_k": top_k * 3, "embedding": embedding, "domain": domain_filter},
            )
        query = """
        CALL db.index.vector.queryNodes($index, $top_k, $embedding)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
        """
        return self.run(query, {"index": index_name, "top_k": top_k, "embedding": embedding})

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "Neo4jClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
