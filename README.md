# AI Customer Service Agent

An LLM-powered customer support agent for a mobile game, handling bilingual player inquiries (Japanese / Chinese). It combines semantic intent recognition, a FAISS-indexed FAQ knowledge base, hierarchical + vector conversation memory, cost-aware hybrid LLM routing, and automatic escalation to human agents — served through a Gradio web UI.

## Features

- **Semantic intent recognition** — fuzzy keyword + embedding-based classification (JA/ZH) with confidence scoring
- **FAQ knowledge base** — `sentence-transformers` embeddings indexed with FAISS for retrieval-augmented answers
- **Hybrid model scheduler** — routes each query to a Qwen tier (`qwen-turbo` / `qwen-plus` / `qwen3-max`) based on estimated complexity and intent confidence, tracking call counts, latency and cost
- **Hierarchical memory** — short/mid-term memory per session plus a persistent vector memory across sessions
- **Session management** — context continuity and conversation state tracking
- **Human-agent escalation** — automatically queues a ticket for a human when confidence is low, the same issue repeats, or "helpless" keywords are detected
- **Response cache** — TTL-based cache to reduce latency and API cost
- **SQLite user profiles** — account lookup and per-user context
- **Task logging & stats** — request history, response times and workload statistics

## How it works

```
player message (JA/ZH)
        │
        ▼
┌──────────────────┐   ┌──────────────────┐
│ Intent recognizer│──▶│ Response cache   │── hit ──▶ reply
│ (fuzzy + semantic)│   └──────────────────┘
└───────┬──────────┘            │ miss
        ▼                       ▼
┌──────────────────┐   ┌──────────────────────┐
│ Knowledge base   │──▶│ Hybrid model scheduler│──▶ DashScope (Qwen)
│ (FAISS + SBERT)  │   │ FAST/STANDARD/PREMIUM │
└──────────────────┘   └──────────┬───────────┘
        ▲                         │
┌───────┴──────────┐              ▼
│ Hierarchical +   │◀─────── response → session update
│ vector memory    │              │
└──────────────────┘              ▼
                        escalation? ──▶ human-agent queue
```

## Project structure

```
.
├── README.md
├── .gitignore
├── docs/
│   └── Readme.pdf          # original design document
├── src/main5/
│   ├── main.py             # entry point (launches Gradio UI on :7860)
│   ├── engine.py           # CustomerServiceEngine — core orchestration
│   ├── config.py           # central configuration (models, thresholds, keywords)
│   ├── models.py           # dataclasses & enums
│   ├── intent/             # fuzzy + semantic intent recognition
│   ├── llm/                # knowledge base (FAISS), model scheduler, response cache
│   ├── memory/             # semantic analyzer, hierarchical memory, vector memory
│   ├── session/            # session manager
│   ├── human/              # human-agent escalation queue
│   ├── database/           # SQLite user profiles
│   ├── utils/              # email builder, task logger, time-aware helpers
│   └── web/                # Gradio interface
└── tests/                  # ready-made test prompts (copy & paste into the UI)
    ├── standard_run_test.txt
    ├── semantic_similarity_test.txt
    └── complexity_test.txt
```

## Requirements

- Python 3.12
- An [Alibaba Cloud DashScope](https://dashscope.aliyun.com/) API key (Qwen model family)

Third-party packages: `gradio`, `pandas`, `numpy`, `sentence-transformers`, `faiss-cpu`, `openai`.

## Installation

```bash
git clone https://github.com/longray825-spec/personal.git
cd personal/src/main5
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install gradio pandas numpy sentence-transformers faiss-cpu openai
```

## Configuration

1. **API key** — set the environment variable before starting:
   ```bash
   export DASHSCOPE_API_KEY='your_key'    # Windows: set DASHSCOPE_API_KEY=your_key
   ```
   Fallback: put the key in a file named `api_key.txt` next to `main.py`.
   Without a key the engine still runs in a degraded short-answer mode.

2. **Knowledge data (optional)** — point `EXCEL_PATH` in [`src/main5/main.py`](src/main5/main.py) to a support-email export Excel (columns: `メールID`, `メールID枝番`, `本文`). If the file is missing, the system automatically falls back to a built-in sample knowledge base, so the app runs out of the box.

## Usage

```bash
cd src/main5
python main.py
```

Then open **http://127.0.0.1:7860** and start chatting.

## Tests

Files under [`tests/`](tests/) contain ready-made prompts (billing, crash, account, feedback, inquiry scenarios — plus human-escalation triggers) that you can copy-paste directly into the UI. `semantic_similarity_test.txt` covers retrieval robustness; `complexity_test.txt` covers model-routing decisions.

## Privacy

This repository contains **source code only**. The raw QA dataset, user profiles, conversation/memory logs, embeddings and personal files are excluded via `.gitignore` and are not published.

## Notes

- Models are configured in [`src/main5/config.py`](src/main5/config.py) and [`src/main5/llm/model_scheduler.py`](src/main5/llm/model_scheduler.py).
- Escalation thresholds (`CONFIDENCE_THRESHOLD`, `SIMILARITY_THRESHOLD`, helpless keywords) live in `config.py`.
