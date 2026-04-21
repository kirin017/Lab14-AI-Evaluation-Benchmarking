from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


SECTION_PATTERN = re.compile(r"^===\s*(.+?)\s*===\s*$", re.MULTILINE)
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


@dataclass
class DocumentRecord:
    doc_id: str
    title: str
    source_path: str
    department: str
    effective_date: str
    access_level: str
    text: str


@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    section_index: int
    section_title: str
    source_path: str
    token_count: int
    text: str


def _extract_header_value(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def _extract_document_metadata(path: Path, text: str) -> DocumentRecord:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else path.stem
    return DocumentRecord(
        doc_id=path.stem,
        title=title,
        source_path=path.as_posix(),
        department=_extract_header_value(text, "Department"),
        effective_date=_extract_header_value(text, "Effective Date"),
        access_level=_extract_header_value(text, "Access"),
        text=text.strip(),
    )


def split_into_sections(text: str) -> List[Tuple[str, str]]:
    matches = list(SECTION_PATTERN.finditer(text))
    if not matches:
        cleaned_text = text.strip()
        return [("full_document", cleaned_text)] if cleaned_text else []

    sections: List[Tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section_title = match.group(1).strip()
        section_body = text[start:end].strip()
        if section_body:
            sections.append((section_title, section_body))
    return sections


def tokenize(text: str) -> List[str]:
    return TOKEN_PATTERN.findall(text.lower())


def embed_text(text: str, dimensions: int = 128) -> List[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        position = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[position] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def build_records(source_dir: Path) -> Tuple[List[DocumentRecord], List[ChunkRecord]]:
    documents: List[DocumentRecord] = []
    chunks: List[ChunkRecord] = []

    for path in sorted(source_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        document = _extract_document_metadata(path, text)
        documents.append(document)

        for section_index, (section_title, section_body) in enumerate(split_into_sections(text), start=1):
            chunk_text = "\n".join([document.title, section_title, section_body]).strip()
            chunks.append(
                ChunkRecord(
                    chunk_id=f"{document.doc_id}:section_{section_index:02d}",
                    doc_id=document.doc_id,
                    section_index=section_index,
                    section_title=section_title,
                    source_path=document.source_path,
                    token_count=len(tokenize(chunk_text)),
                    text=chunk_text,
                )
            )

    return documents, chunks


def _write_jsonl(records: Iterable[object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def _write_vector_store(chunks: Sequence[ChunkRecord], output_path: Path, dimensions: int = 128) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dimensions": dimensions,
        "items": [
            {
                "id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "section_index": chunk.section_index,
                "section_title": chunk.section_title,
                "source_path": chunk.source_path,
                "text": chunk.text,
                "embedding": embed_text(chunk.text, dimensions=dimensions),
            }
            for chunk in chunks
        ],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sync_chroma(chunks: Sequence[ChunkRecord], persist_dir: Path, collection_name: str, dimensions: int = 128) -> Dict[str, object]:
    try:
        import chromadb
    except Exception as error:
        return {"enabled": False, "reason": str(error)}

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine", "dimensions": dimensions},
    )
    collection.add(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        embeddings=[embed_text(chunk.text, dimensions=dimensions) for chunk in chunks],
        metadatas=[
            {
                "doc_id": chunk.doc_id,
                "section_index": chunk.section_index,
                "section_title": chunk.section_title,
                "source_path": chunk.source_path,
            }
            for chunk in chunks
        ],
    )
    return {"enabled": True, "collection_name": collection_name, "size": len(chunks)}


def load_chunks(chunks_path: Path) -> List[Dict[str, object]]:
    if not chunks_path.exists():
        return []
    records: List[Dict[str, object]] = []
    with chunks_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_corpus(
    repo_root: Path | None = None,
    docs_dir: str = "data/docs",
    docs_output: str = "data/docs.jsonl",
    chunks_output: str = "data/chunks.jsonl",
    vector_store_output: str = "data/vector_store.json",
    chroma_dir: str = "chroma_db",
    collection_name: str = "day14_docs",
) -> Dict[str, object]:
    root = repo_root or Path(__file__).resolve().parents[1]
    source_dir = root / docs_dir
    documents, chunks = build_records(source_dir)

    _write_jsonl(documents, root / docs_output)
    _write_jsonl(chunks, root / chunks_output)
    _write_vector_store(chunks, root / vector_store_output)
    chroma_status = _sync_chroma(chunks, root / chroma_dir, collection_name=collection_name)

    return {
        "documents": len(documents),
        "chunks": len(chunks),
        "docs_output": (root / docs_output).as_posix(),
        "chunks_output": (root / chunks_output).as_posix(),
        "vector_store_output": (root / vector_store_output).as_posix(),
        "chroma": chroma_status,
    }
