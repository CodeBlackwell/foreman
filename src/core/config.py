import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        self.neo4j_password = os.environ.get("NEO4J_PASSWORD", "")
        self.voyage_api_key = os.environ.get("VOYAGE_API_KEY", "")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    def validate(self) -> None:
        missing = [k for k in ("neo4j_password", "voyage_api_key", "anthropic_api_key") if not getattr(self, k)]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing).upper()}")


settings = Settings()
