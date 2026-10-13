# Multi-Agent Research System (Python 3.10+)

Offline reference implementation using **three distinct agents** and an orchestrator. No API key or dependencies needed. The agents are deterministic Python components, **not three LLMs**. This is a safe baseline for upgrading to model-based orchestration later.

## Run

```bash
python agent.py "What is the monthly uptime target?"
python agent.py "How much did cloud infrastructure spending increase from 2024 to 2025?"
python agent.py "How much did cloud infrastructure spending increase from 2024 to 2025?" --approve-calculator
python evaluate.py
```

## Features
- Research agent: BM25 retrieval, bounded to top 3 passages.
- Analysis agent: extractive claims and restricted arithmetic tool.
- Verification agent: exact source matching and independent arithmetic recomputation.
- Orchestrator: typed JSON-compatible responses, 3-call budget, bounded retries, ephemeral last-5-query memory.
- Human approval: calculation is withheld unless `--approve-calculator` is supplied. A real app should prompt a human before resuming.
- Prompt injection: document instructions are treated as data and never executed. Test the `attack` document. No guarantee against all attacks if LLMs are added.
- Failure recovery: catches tool errors and retries within budget; no external actions.

## Limitations and next steps
- The verification method only supports extractive claims and one specific derived percentage calculation. It is **not** a general semantic entailment verifier.
- No LLM is required: the prototype demonstrates agent interfaces and safe orchestration rather than model-driven decisions. Add an LLM behind each interface and use JSON Schema validation, a policy engine, and human approval for consequential tools.
- Evaluation `success` is a proxy for citing an expected source, not an independent human-graded factual correctness score. Extend tests with reference answers, adversarial cases, and separate single-agent comparison.
- `estimated_api_cost_usd` is zero because this implementation makes no API calls.
