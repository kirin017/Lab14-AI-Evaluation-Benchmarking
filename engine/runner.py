import os
import json
import asyncio
from typing import Dict, Any, Optional

try:
    import aiofiles
except ImportError:
    aiofiles = None

from engine.consensus import build_default_engine, ConsensusEngine
from agent.main_agent import MainAgent


async def run_benchmark_with_results(agent_version: str):
    print(f"[BENCHMARK] Starting benchmark for {agent_version}...")

    # Khởi tạo engine theo env (mock nếu thiếu key)
    consensus_engine = build_default_engine()
    print(
        f"   Judges: {[j.name for j in consensus_engine.judges]}"
    )
    if consensus_engine.arbitrator:
        print(f"   Arbitrator: {consensus_engine.arbitrator.name}")

    golden_set_path = "data/golden_set.jsonl"
    if not os.path.exists(golden_set_path):
        print(f"[ERROR] Missing {golden_set_path}. Run 'python data/synthetic_gen.py' first.")
        return None, None

    if aiofiles is not None:
        async with aiofiles.open(golden_set_path, "r", encoding="utf-8") as f:
            lines = await f.readlines()
    else:
        with open(golden_set_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    dataset = [json.loads(line) for line in lines if line.strip()]
    if not dataset:
        print(f"[ERROR] File {golden_set_path} is empty. Create at least 1 test case.")
        return None, None

    agent = MainAgent(version=agent_version)
    results = []
    total = len(dataset)

    # Batch với batch_size mặc định 5
    batch_size = 5
    for i in range(0, total, batch_size):
        batch = dataset[i : i + batch_size]
        tasks = []
        for case in batch:
            tasks.append(_run_single_test(agent, consensus_engine, case))
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

    #  Tổng hợp metrics
    final_scores = [r["judge"]["final_score"] for r in results]
    agreements = [r["judge"]["agreement_rate"] for r in results]
    conflicts = [r["judge"]["conflict_detected"] for r in results]
    latencies = [r["judge"]["latency_ms"] for r in results if r["judge"].get("latency_ms")]

    avg_score = sum(final_scores) / len(final_scores) if final_scores else 0.0
    avg_agreement = sum(agreements) / len(agreements) if agreements else 0.0
    conflict_rate = sum(conflicts) / len(conflicts) if conflicts else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    #  Phân loại mức độ đồng thuận trung bình
    from collections import Counter
    levels = [r["judge"]["agreement_level"] for r in results]
    most_common_level = Counter(levels).most_common(1)[0][0] if levels else "Unknown"

    # Judge reliability
    reliability = consensus_engine.get_judge_reliability()

    summary = {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": asyncio.get_event_loop().time(),
        },
        "metrics": {
            "avg_score": round(avg_score, 2),
            "avg_agreement_rate": round(avg_agreement, 2),
            "avg_agreement_level": most_common_level,
            "agreement_rate": round(avg_agreement, 2),
            "conflict_rate": round(conflict_rate, 2),
            "avg_judge_latency_ms": round(avg_latency, 2),
        },
        "judge_reliability": reliability,
        "consensus_config": {
            "judges": [j.name for j in consensus_engine.judges],
            "arbitrator": (
                consensus_engine.arbitrator.name if consensus_engine.arbitrator else None
            ),
            "conflict_strategy": consensus_engine.conflict_strategy,
            "tolerance": consensus_engine.tolerance,
        },
    }

    return results, summary


async def _run_single_test(
    agent, consensus_engine: ConsensusEngine, test_case: Dict
) -> Dict[str, Any]:
    import time

    start = time.perf_counter()
    response = await agent.query(test_case["question"])
    latency = round(time.perf_counter() - start, 2)

    judge_result = await consensus_engine.evaluate(
        question=test_case["question"],
        answer=response["answer"],
        ground_truth=test_case.get("expected_answer", ""),
    )

    # Threshold pass/fail
    status = "fail" if judge_result["final_score"] < 3 else "pass"

    return {
        "test_case": test_case["question"],
        "agent_response": response["answer"],
        "latency": latency,
        "judge": judge_result,
        "status": status,
    }


if __name__ == "__main__":
    # Chạy nhanh bằng mock để kiểm tra
    os.environ.setdefault("MOCK_JUDGE", "1")
    results, summary = asyncio.run(run_benchmark_with_results("Test_v1"))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
