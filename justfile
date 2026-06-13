slide:
    open pitch-slide.html

dev:
    -lsof -ti:8001 | xargs kill -9 2>/dev/null
    -lsof -ti:8501 | xargs kill -9 2>/dev/null
    uv run uvicorn src.api.app:app --port 8001 --reload &
    uv run streamlit run scripts/demo_ui.py

ingest:
    uv run python data/seed.py

test:
    uv run pytest tests/

typecheck:
    uv run mypy src/

setup-indexes:
    uv run python -m src.core.setup_indexes

demo:
    uv run python scripts/demo.py

deploy:
    git push origin master
    ssh root@5.78.198.79 "cd /opt/foreman && git pull && docker compose up -d --build"
