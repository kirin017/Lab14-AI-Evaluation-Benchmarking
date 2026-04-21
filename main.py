import asyncio
import json
import os
import time
from dotenv import load_dotenv
from engine.runner import run_benchmark_with_results

load_dotenv()


async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary


async def main():
    v1_results, v1_summary = await run_benchmark_with_results("Agent_V1_Base")
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")

    if not v1_summary or not v2_summary:
        print("[ERROR] Cannot run Benchmark. Check data/golden_set.jsonl.")
        return

    delta_score = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    delta_agreement = (
        v2_summary["metrics"]["avg_agreement_rate"]
        - v1_summary["metrics"]["avg_agreement_rate"]
    )

    print("\n[REGRESSION] --- COMPARISON RESULTS ---")
    print(f"V1 Score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']}")
    print(f"V1 Agreement: {v1_summary['metrics']['avg_agreement_rate']}")
    print(f"V2 Agreement: {v2_summary['metrics']['avg_agreement_rate']}")
    print(f"Delta Score: {'+' if delta_score >= 0 else ''}{delta_score:.2f}")
    print(f"Delta Agreement: {'+' if delta_agreement >= 0 else ''}{delta_agreement:.2f}")

    approved = (
        delta_score >= 0
        and v2_summary["metrics"]["avg_agreement_rate"] >= 0.6
        and v2_summary["metrics"]["conflict_rate"] <= 0.5
    )

    if approved:
        print("[APPROVE] Accept new version")
    else:
        print("[BLOCK] Reject new version")

    # Write reports
    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
