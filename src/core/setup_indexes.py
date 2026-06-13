from src.core.neo4j_client import Neo4jClient

INDEXES = [
    ("step_embedding", "Step", "embedding"),
    ("section_embedding", "Section", "embedding"),
    ("document_embedding", "Document", "embedding"),
]

CONSTRAINTS = [
    ("step_hash_unique", "Step", "content_hash"),
    ("entity_id_unique", "Entity", "canonical_id"),
]


def setup(client: Neo4jClient) -> None:
    for name, label, prop in INDEXES:
        client.run(
            f"CREATE VECTOR INDEX {name} IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.{prop}) "
            f"OPTIONS {{indexConfig: {{`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}}}"
        )
        print(f"index {name}: ok")

    for name, label, prop in CONSTRAINTS:
        client.run(f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE")
        print(f"constraint {name}: ok")


if __name__ == "__main__":
    with Neo4jClient() as client:
        setup(client)
