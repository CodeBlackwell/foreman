import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.pipeline import run_pipeline

RAW_DIR = Path(__file__).parent / "raw"


def main() -> None:
    docs = sorted(RAW_DIR.glob("*.md"))
    if not docs:
        print("No documents found in data/raw/")
        return
    for path in docs:
        print(f"Ingesting {path.name}...")
        try:
            run_pipeline(path)
            print(f"  done: {path.name}")
        except Exception as exc:
            print(f"  ERROR: {path.name}: {exc}")


if __name__ == "__main__":
    main()
