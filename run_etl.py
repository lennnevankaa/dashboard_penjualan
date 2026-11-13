import sys
from pathlib import Path

from database.connection import init_db
from etl import pipeline


def main():
    init_db()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else pipeline.latest_upload()
    if not path or not path.exists():
        print("File tidak ditemukan")
        return
    for result in pipeline.run_all(path):
        print(f"[{result['step']}] {result['message']} ({result['seconds']} dtk)")


if __name__ == "__main__":
    main()