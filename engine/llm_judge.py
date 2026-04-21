import os
import json
import re
from typing import Dict, Any, Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None


class SingleLLMJudge:
    """
    Wrapper cho một LLM Judge đơn lẻ.
    Hỗ trợ OpenAI và Anthropic với prompt rubric chuẩn hóa.
    """

    def __init__(
        self,
        name: str,
        model: str,
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.name = name
        self.model = model
        self.provider = provider.lower()
        self.api_key = api_key or self._default_api_key()
        self.client = None

        if self.provider == "openai" or self.provider == "google":
            if AsyncOpenAI is None:
                raise ImportError("Package 'openai' is required for OpenAI / Google provider.")
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=base_url)
        elif self.provider == "anthropic":
            if AsyncAnthropic is None:
                raise ImportError("Package 'anthropic' is required for Anthropic provider.")
            self.client = AsyncAnthropic(api_key=self.api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _default_api_key(self) -> Optional[str]:
        if self.provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        if self.provider == "google":
            return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def evaluate(
        self,
        question: str,
        answer: str,
        ground_truth: str,
    ) -> Dict[str, Any]:
        """
        Chấm điểm câu trả lời trên thang 1-5 với 2 tiêu chí: accuracy & tone.
        Trả về dict: {score, reasoning, dimensions}.
        """
        system_prompt = (
            "Bạn là một chuyên gia đánh giá chất lượng câu trả lời của AI Agent.\n"
            "Hãy chấm điểm theo thang 1-5 dựa trên các tiêu chí sau:\n"
            "1. accuracy (độ chính xác so với Ground Truth): 1=rất sai, 3=đúng một phần, 5=hoàn toàn chính xác.\n"
            "2. tone (tính chuyên nghiệp, lịch sự, cấu trúc rõ ràng): 1=kém, 3=trung bình, 5=xuất sắc.\n\n"
            "Quy tắc bắt buộc:\n"
            "- Trả về KẾT QUẢ DUY NHẤT dưới dạng JSON hợp lệ.\n"
            '- Cấu trúc: {"score": <int 1-5>, "reasoning": "<ngắn gọn>", "dimensions": {"accuracy": <int>, "tone": <int>}}\n'
            "- Không thêm bất kỳ text nào ngoài JSON."
        )

        user_prompt = (
            f"### Câu hỏi:\n{question}\n\n"
            f"### Câu trả lời cần đánh giá:\n{answer}\n\n"
            f"### Ground Truth:\n{ground_truth}\n\n"
            "Hãy đánh giá và trả về JSON theo yêu cầu."
        )

        raw = await self._call_api(system_prompt, user_prompt)
        return self._parse_response(raw)

    async def check_position_bias(
        self,
        response_a: str,
        response_b: str,
        question: str,
        ground_truth: str,
    ) -> Dict[str, Any]:
        """
        Kiểm tra position bias bằng cách đổi chỗ thứ tự A/B và so sánh điểm.
        """
        score_ab = await self.evaluate(
            question=question,
            answer=f"[Response A]\n{response_a}\n\n[Response B]\n{response_b}",
            ground_truth=ground_truth,
        )
        score_ba = await self.evaluate(
            question=question,
            answer=f"[Response A]\n{response_b}\n\n[Response B]\n{response_a}",
            ground_truth=ground_truth,
        )
        bias_detected = abs(score_ab["score"] - score_ba["score"]) >= 2
        return {
            "bias_detected": bias_detected,
            "score_ab": score_ab["score"],
            "score_ba": score_ba["score"],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "openai" or self.provider == "google":
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=512,
            )
            return response.choices[0].message.content or ""

        if self.provider == "anthropic":
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=512,
                temperature=0.0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            if isinstance(response.content, list) and len(response.content) > 0:
                return getattr(response.content[0], "text", str(response.content[0]))
            return str(response.content)

        raise ValueError(f"Unsupported provider: {self.provider}")

    def _parse_response(self, raw_text: str) -> Dict[str, Any]:
        raw = raw_text.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        elif raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        score = data.get("score")
        dims = data.get("dimensions", {})
        acc = dims.get("accuracy")
        tone = dims.get("tone")

        if not isinstance(score, int) or not (1 <= score <= 5):
            if isinstance(acc, int) and isinstance(tone, int):
                score = round((acc + tone) / 2)
            else:
                score = 3
        score = max(1, min(5, int(score)))

        return {
            "score": score,
            "reasoning": data.get("reasoning", "No reasoning provided."),
            "dimensions": {
                "accuracy": acc if isinstance(acc, int) else score,
                "tone": tone if isinstance(tone, int) else score,
            },
        }


class MockJudge:
    """
    Judge giả lập dùng khi thiếu API key hoặc chạy unit test.
    Đảm bảo deterministic để kiểm tra consensus logic.
    """

    def __init__(self, name: str = "mock", seed: int = 42):
        self.name = name
        self.model = "mock"
        self.provider = "mock"
        self._seed = seed + hash(name)

    async def evaluate(self, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        import hashlib

        combined = f"{self.name}:{question}:{answer}:{ground_truth}"
        h = int(hashlib.md5(combined.encode()).hexdigest(), 16)
        # Sinh điểm từ 2-5 để tránh trivial
        score = 2 + ((h + self._seed) % 4)
        return {
            "score": score,
            "reasoning": f"Mock evaluation from {self.name}. Score={score}.",
            "dimensions": {"accuracy": score, "tone": score},
        }
