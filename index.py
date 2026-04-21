from pathlib import Path

from engine.corpus import build_corpus


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    summary = build_corpus(repo_root=repo_root)
    print(f"Indexed {summary['documents']} documents into {summary['chunks']} chunks.")
    print(f"Chunks manifest: {summary['chunks_output']}")
    if summary["chroma"].get("enabled"):
        print(f"Chroma collection ready: {summary['chroma']['collection_name']}")
    else:
        print(f"Chroma sync skipped: {summary['chroma']['reason']}")


if __name__ == "__main__":
    main()
