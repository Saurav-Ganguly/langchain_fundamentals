# langchain_fundamentals

My working copy of the LangChain Academy course
[Introduction to LangChain (Python)](https://academy.langchain.com/courses/foundation-introduction-to-langchain-python),
with my own notebooks and experiments alongside the course material.

Upstream: [langchain-ai/lca-lc-foundations](https://github.com/langchain-ai/lca-lc-foundations) (MIT).
The full original course guide is kept here as [COURSE_README.md](COURSE_README.md).

## Setup

Requires Python >=3.12,<3.14 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Saurav-Ganguly/langchain_fundamentals.git
cd langchain_fundamentals
uv sync
```

Create your `.env` from the template and fill in real keys:

```bash
cp example.env .env
```

`.env` is gitignored and must never be committed.

| Key | Needed for |
| --- | --- |
| `OPENAI_API_KEY` | most notebooks |
| `TAVILY_API_KEY` | search tools |
| `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` | Module 1, Lesson 1 only |
| `OPENROUTER_API_KEY` | optional, multi-provider access |
| `LANGSMITH_API_KEY` | optional, tracing and evaluation |

Verify the environment:

```bash
uv run python env_utils.py
```

## Running

```bash
uv run jupyter lab
```

Notebooks live under `notebooks/`:

- `module-1` — chat models, messages, tools, structured output
- `module-2` — agents, MCP servers, multi-agent patterns
- `module-3` — LangGraph, memory, human-in-the-loop, `agent-chat-ui`

My own scratch notebooks are named `try-*.ipynb`.

## Notes to self

- Always `uv run <cmd>`, never bare `python`. Add deps with `uv add`, never `pip install`.
- Notebook outputs are committed. Clear them before committing if a run ever prints a key.
- Module 2 Lesson 1 needs `uvx` on PATH to launch the MCP server.

## License

MIT — see [LICENSE](LICENSE). Course material copyright LangChain, Inc.
