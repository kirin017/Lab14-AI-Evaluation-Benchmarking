import asyncio
import json
import os
import math
import hashlib
import re
from typing import List, Dict, Tuple
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# Copying embedding logic from engine/corpus.py to ensure consistency
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)

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

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2))

class MainAgent:
    """
    Real RAG Agent implementing Retrieval and Generation.
    """
    def __init__(self, version: str = "Base", vector_store_path: str = "data/vector_store.json"):
        self.name = f"RealRAGAgent-{version}"
        self.version = version
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Load vector store
        with open(vector_store_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.dimensions = data["dimensions"]
            self.chunks = data["items"]

    async def retrieve(self, question: str, top_k: int = 3) -> List[Dict]:
        query_vec = embed_text(question, dimensions=self.dimensions)
        
        scored_chunks = []
        for chunk in self.chunks:
            sim = cosine_similarity(query_vec, chunk["embedding"])
            scored_chunks.append((sim, chunk))
        
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_chunks[:top_k]]

    async def query(self, question: str) -> Dict:
        # Base version: top_k=1, Optimized: top_k=3
        top_k = 3 if "Optimized" in self.version else 1
        
        # 1. Retrieval
        contexts = await self.retrieve(question, top_k=top_k)
        context_text = "\n\n".join([f"Source {i+1}:\n{c['text']}" for i, c in enumerate(contexts)])
        
        # 2. Generation
        system_prompt = (
            "Bạn là một trợ lý hỗ trợ nội bộ chuyên nghiệp.\n"
            "Chỉ sử dụng thông tin trong phần Context dưới đây để trả lời câu hỏi.\n"
            "Nếu thông tin không có trong Context, hãy trả lời 'Tôi không tìm thấy thông tin trong tài liệu hệ thống.'\n"
            "Trả lời ngắn gọn, chính xác."
        )
        
        user_prompt = (
            f"Context:\n{context_text}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"Lỗi gọi LLM: {str(e)}"

        return {
            "answer": answer,
            "contexts": [c["text"] for c in contexts],
            "retrieved_ids": [c["id"] for c in contexts],
            "metadata": {
                "model": "gpt-4o-mini",
                "sources": list(set([c["source_path"] for c in contexts]))
            }
        }

if __name__ == "__main__":
    load_dotenv()
    agent = MainAgent()
    async def test():
        resp = await agent.query("Level 4 Admin Access cần những ai phê duyệt?")
        print(json.dumps(resp, indent=2, ensure_ascii=False))
    asyncio.run(test())
