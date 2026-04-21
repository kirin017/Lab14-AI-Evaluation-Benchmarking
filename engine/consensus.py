import os
import asyncio
import statistics
import time
from typing import Dict, Any, List
from collections import defaultdict

from engine.llm_judge import SingleLLMJudge, MockJudge, AsyncOpenAI, AsyncAnthropic


class ConsensusEngine:
    """
    Multi-Judge Consensus Engine với Calibration & Conflict Resolution.

    Features:
    - Gọi song song nhiều SingleLLMJudge.
    - Tính Agreement Rate dựa trên pairwise agreement + variance penalty.
    - Tự động xử lý xung đột (mean -> median -> arbitrator).
    - Theo dõi lịch sử để tính reliability (EMA/variance) của từng judge.
    """

    def __init__(
        self,
        judges: List[SingleLLMJudge],
        tolerance: float = 1.0,
        conflict_strategy: str = "median_then_arbitrator",
        arbitrator: SingleLLMJudge = None,
    ):
        if len(judges) < 2:
            raise ValueError("ConsensusEngine yêu cầu ít nhất 2 judges.")
        self.judges = judges
        self.tolerance = tolerance
        self.conflict_strategy = conflict_strategy
        self.arbitrator = arbitrator
        self._history: Dict[str, List[float]] = defaultdict(list)

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
        Chạy nhiều judge, tính agreement và tự động giải quyết xung đột.
        Trả về dict chứa final_score, agreement_rate, individual_scores, ...
        """
        start_time = time.perf_counter()

        # 1. Gọi song song các judge chính
        tasks = [j.evaluate(question, answer, ground_truth) for j in self.judges]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        individual_scores: Dict[str, Any] = {}
        numeric_scores: List[float] = []

        for judge, result in zip(self.judges, raw_results):
            if isinstance(result, Exception):
                individual_scores[judge.name] = {
                    "score": 3,
                    "reasoning": f"Judge error: {str(result)}",
                    "error": True,
                }
            else:
                individual_scores[judge.name] = result
                numeric_scores.append(result.get("score", 3))
                self._history[judge.name].append(result.get("score", 3))

        # 2. Calibration: tính Agreement Rate
        agreement_rate = self._calculate_agreement_rate(numeric_scores)

        # 3. Conflict detection & resolution
        conflict_detected = False
        resolution_method = "mean_consensus"
        final_score = 3.0

        if len(numeric_scores) >= 2:
            diff = max(numeric_scores) - min(numeric_scores)
            if diff <= self.tolerance:
                final_score = statistics.mean(numeric_scores)
            else:
                conflict_detected = True
                # Xung đột nhẹ: dùng median (ít nhạy cảm với outlier)
                if diff <= self.tolerance * 2:
                    final_score = statistics.median(numeric_scores)
                    resolution_method = "median_conflict"
                else:
                    # Xung đột nặng: gọi arbitrator nếu có
                    if (
                        self.conflict_strategy == "median_then_arbitrator"
                        and self.arbitrator is not None
                    ):
                        arb_result = await self.arbitrator.evaluate(
                            question, answer, ground_truth
                        )
                        arb_score = arb_result.get("score", 3)
                        combined = numeric_scores + [arb_score]
                        final_score = statistics.median(combined)
                        resolution_method = "arbitrator_median"
                        individual_scores["arbitrator"] = arb_result
                    elif self.conflict_strategy == "mean":
                        final_score = statistics.mean(numeric_scores)
                        resolution_method = "mean_conflict"
                    else:
                        final_score = statistics.median(numeric_scores)
                        resolution_method = "median_heavy_conflict"
        elif numeric_scores:
            final_score = numeric_scores[0]
            resolution_method = "single_judge"

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "final_score": round(final_score, 2),
            "agreement_rate": round(agreement_rate, 2),
            "agreement_level": self._get_agreement_level(agreement_rate),
            "individual_scores": individual_scores,
            "resolution_method": resolution_method,
            "conflict_detected": conflict_detected,
            "latency_ms": latency_ms,
        }

    def get_judge_reliability(self) -> Dict[str, Any]:
        """
        Tính reliability và bias của từng judge dựa trên lịch sử điểm.
        - Reliability: Ổn định (variance thấp).
        - Bias: Độ lệch trung bình so với Consensus.
        """
        stats: Dict[str, Any] = {}
        for name, scores in self._history.items():
            if len(scores) < 2:
                stats[name] = {"reliability": 1.0, "avg_score": round(sum(scores)/len(scores) if scores else 3.0, 2)}
            else:
                var = statistics.variance(scores)
                reliability = round(max(0.0, 1.0 - (var / 4.0)), 2)
                stats[name] = {
                    "reliability": reliability,
                    "avg_score": round(statistics.mean(scores), 2),
                    "samples": len(scores)
                }
        return stats

    def _get_agreement_level(self, rate: float) -> str:
        if rate >= 0.9: return "Very High"
        if rate >= 0.7: return "High"
        if rate >= 0.5: return "Moderate"
        return "Low/Conflict"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _calculate_agreement_rate(self, scores: List[float]) -> float:
        n = len(scores)
        if n <= 1:
            return 1.0

        pairwise_pairs = 0
        pairwise_agree = 0
        for i in range(n):
            for j in range(i + 1, n):
                pairwise_pairs += 1
                if abs(scores[i] - scores[j]) <= self.tolerance:
                    pairwise_agree += 1

        pairwise_rate = pairwise_agree / pairwise_pairs if pairwise_pairs else 1.0

        # Variance penalty: std max ~2.0 (1 vs 5)
        std_dev = statistics.stdev(scores) if n > 1 else 0.0
        variance_factor = max(0.0, 1.0 - (std_dev / 2.0))

        # Trọng số: 70% pairwise, 30% variance smoothness
        return 0.7 * pairwise_rate + 0.3 * variance_factor


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------
def build_default_engine(use_mock: bool = False) -> ConsensusEngine:
    """
    Tạo Consensus Engine mặc định:
    - Judge 1: gpt-4o-mini (OpenAI)
    - Judge 2: gemini-2.5-flash-preview-05-20 (Google)
    - Arbitrator: gpt-4o-mini (OpenAI)

    Nếu thiếu API key hoặc package, tự động fallback sang MockJudge.
    Có thể bắt buộc mock bằng biến môi trường MOCK_JUDGE=1.
    """
    if use_mock or os.getenv("MOCK_JUDGE", "0") == "1":
        j1 = MockJudge(name="mock-openai", seed=42)
        j2 = MockJudge(name="mock-google", seed=77)
        arb = MockJudge(name="mock-arb", seed=99)
        return ConsensusEngine(judges=[j1, j2], arbitrator=arb)

    judges: List[SingleLLMJudge] = []

    if AsyncOpenAI is not None and os.getenv("OPENAI_API_KEY"):
        judges.append(
            SingleLLMJudge(
                name="gpt-4o-mini",
                model="gpt-4o-mini",
                provider="openai",
            )
        )

    if AsyncOpenAI is not None and (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    ):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        judges.append(
            SingleLLMJudge(
                name="gemini-3.1-flash-lite",
                model="gemini-flash-lite-latest",
                provider="google",
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=api_key,
            )
        )

    if len(judges) < 2:
        # Fallback sang mock nếu không đủ key
        return build_default_engine(use_mock=True)

    arbitrator = None
    if AsyncOpenAI is not None and os.getenv("OPENAI_API_KEY"):
        arbitrator = SingleLLMJudge(
            name="gpt-4o-mini-arb",
            model="gpt-4o-mini",
            provider="openai",
        )

    return ConsensusEngine(
        judges=judges,
        tolerance=1.0,
        conflict_strategy="median_then_arbitrator",
        arbitrator=arbitrator,
    )
