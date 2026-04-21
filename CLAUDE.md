# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An AI Evaluation Factory for benchmarking RAG (Retrieval-Augmented Generation) agents. The system creates golden datasets, runs benchmarks comparing agent versions, and uses a multi-judge consensus engine (GPT-4o-mini + Gemini) to score responses on a 1-5 scale.

## Commands

**Setup:**
```bash
pip install -r requirements.txt
cp .env.example .env  # then fill in API keys
```

**Generate golden dataset (required before benchmarking):**
```bash
python data/synthetic_gen.py
```

**Run full benchmark (compares V1_Base vs V2_Optimized):**
```bash
python main.py
```

**Run with mock judges (no API keys needed):**
```bash
MOCK_JUDGE=1 python main.py
```

**Validate submission format:**
```bash
python check_lab.py
```

**Test agent in isolation:**
```bash
python agent/main_agent.py
```

**Test runner with mock:**
```bash
MOCK_JUDGE=1 python -m engine.runner
```

## Architecture

### Data Flow

```
data/docs/*.txt
     ↓ [corpus.py: build_corpus()]  — hash-based 128-dim embeddings
data/vector_store.json + data/chunks.jsonl
     ↓ [data/synthetic_gen.py]
data/golden_set.jsonl  (74 test cases: easy/medium/hard)
     ↓ [engine/runner.py: run_benchmark_with_results()]
         ├── agent/main_agent.py → retrieve() + generate (GPT-4o-mini)
         └── engine/consensus.py → multi-judge scoring
reports/summary.json + reports/benchmark_results.json
```

### Key Components

**`agent/main_agent.py` — RAG Pipeline**
- `MainAgent.retrieve(question, top_k)`: cosine similarity search over `data/vector_store.json`
- `MainAgent.query(question)`: retrieval → GPT-4o-mini generation
- `Agent_V1_Base` uses `top_k=1`; `Agent_V2_Optimized` uses `top_k=3`

**`engine/consensus.py` — Multi-Judge Consensus**
- Runs 2 judges in parallel via `asyncio.gather()`
- Conflict resolution: score diff ≤1.0 → mean; ≤2.0 → median; >2.0 → call arbitrator (3-judge median)
- Agreement rate = 70% pairwise agreement + 30% variance smoothness

**`engine/llm_judge.py` — Judge Implementations**
- `SingleLLMJudge`: supports OpenAI, Google (OpenAI-compatible endpoint), Anthropic providers
- Scores on two dimensions: accuracy + tone (1–5 scale), parses JSON with regex fallback
- `MockJudge`: deterministic seed-based scoring; activated by `MOCK_JUDGE=1` or missing API keys

**`engine/runner.py` — Benchmark Orchestration**
- Loads `data/golden_set.jsonl`, batches cases (batch_size=5), runs agent + consensus per case
- Returns aggregated metrics: `avg_score`, `avg_agreement_rate`, `conflict_rate`, `avg_latency_ms`

**`engine/corpus.py` — Embedding & Corpus Building**
- Reads `.txt` files from `data/docs/`, splits on `=== Title ===` pattern
- `embed_text()`: SHA256-based deterministic 128-dim embedding (no external model needed)

**`data/synthetic_gen.py` — Golden Dataset Generator**
- Generates 74 test cases across 5 document categories + cross-doc + expert hard cases
- Outputs: `data/golden_set.jsonl`, `data/docs.jsonl`, `data/chunks.jsonl`, `data/vector_store.json`

**`check_lab.py` — Submission Validator**
- Checks for required output files and validates JSON schemas before grading

**`main.py` — Entry Point**
- Runs both agent versions, calculates delta, applies release gate logic (V2 must not regress vs V1)
- Outputs to `reports/summary.json` and `reports/benchmark_results.json`

## Environment Variables

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | GPT-4o-mini judge + arbitrator + agent generation |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Gemini flash-lite judge |
| `ANTHROPIC_API_KEY` | Optional future Claude judge |
| `MOCK_JUDGE=1` | Bypass all LLM judge API calls with deterministic mock |

## Output Files

- `reports/summary.json` — aggregated benchmark metrics with metadata
- `reports/benchmark_results.json` — per-case detailed results
- `analysis/failure_analysis.md` — failure categorization (required for submission)
