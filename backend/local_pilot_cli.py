import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agent import answer_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask Local Pilot about a selected path.")
    parser.add_argument("path", help="Selected file or folder path")
    parser.add_argument(
        "--question",
        default="Summarize this selected item.",
        help="Question to ask about the selected path",
    )
    args = parser.parse_args()

    result = answer_question(args.path, args.question)
    print(result["answer"])
    print("\nSources:")
    for source in result["sources"]:
        print(f"- {source}")


if __name__ == "__main__":
    main()
