# LangChain Module 1 — Foundations

Notes from notebooks 1.1 to 1.4. Written to be re-read, not just archived.

---

## The one idea that unlocks everything

**A conversation is a list of messages. That's the whole abstraction.**

Every feature in this module is a variation on one question: *who is allowed to append to that list?*

| Feature | Who appends |
| --- | --- |
| Plain model call | You append Human, model appends AI |
| System prompt | You prepend a standing instruction |
| Few-shot | You fake Human/AI pairs to show the pattern |
| Tools | The model appends a *request*, your code appends the *result* |
| Memory | A checkpointer replays the previous list before you append |
| Multimodal | A single message's content becomes a list of blocks |

Once you see the message list, nothing in LangChain is surprising.

---

## 1. Models

### The universal setup

```python
from dotenv import load_dotenv
load_dotenv()  # reads .env into os.environ, returns True
```

Every notebook starts here. `load_dotenv()` does **not** override variables already set in your shell — if a key looks stale, check `os.environ` before blaming the file.

### One initializer, any provider

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(model="openrouter:gemini-3.5-flash-lite", temperature=1)
model = init_chat_model(model="gpt-5-nano", temperature=1.0)
model = init_chat_model(model="claude-sonnet-4-6")
```

The string is `provider:model`, or a bare model name when LangChain can infer the provider. Swapping providers is a one-line change — that's the entire point of `init_chat_model`.

The escape hatch is the direct provider class, when you need a knob the generic interface doesn't expose:

```python
from langchain_google_genai import ChatGoogleGenerativeAI
model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")
```

> **Rule of thumb:** start with `init_chat_model`. Drop to the provider class only when you hit a wall.

### Reading an AIMessage properly

`model.invoke("...")` returns an `AIMessage`. Most people read `.content` and stop. The rest of the object is where the operational information lives:

```python
response = model.invoke("What's the capital of the Moon?")

response.content            # the text you actually wanted
response.response_metadata  # model_name, id, finish_reason, cost, model_provider
response.usage_metadata     # input_tokens, output_tokens, total_tokens, cache_read
response.tool_calls         # [] here, populated when tools are bound
response.id                 # 'lc_run--…' — the LangSmith run id
response.additional_kwargs  # provider extras, e.g. reasoning_details
```

Two fields worth building a habit around:

- **`usage_metadata`** — `input_token_details.cache_read` tells you whether prompt caching hit. Non-zero cache reads are the cheapest wins in this entire stack.
- **`response_metadata['cost']`** — OpenRouter returns real spend per call. Print it while learning; you'll build accurate intuition for what things cost.

`finish_reason` is your control-flow signal: `'stop'` means the model is done, `'tool_calls'` means it wants you to run something.

### Model vs. Agent — the distinction that trips everyone

```python
# MODEL: takes a string, returns an AIMessage
response = model.invoke("What's the capital of the Moon?")
print(response.content)

# AGENT: takes a state dict, returns a state dict
from langchain.agents import create_agent
agent = create_agent(model="openrouter:gemini-3.5-flash-lite")
response = agent.invoke({"messages": [HumanMessage(content="…")]})
print(response["messages"][-1].content)
```

An agent's return value is **the whole conversation**, not a reply. `response["messages"]` contains your input message plus everything generated. This is why you index `[-1]` for the answer.

`create_agent` accepts a model instance *or* a string — `create_agent(model=model)`, `create_agent("gpt-5-nano")`, and `create_agent(model="openrouter:gemini-3.5-flash-lite")` are all valid.

> **Always use `["messages"][-1]`, never `[1]`.** `[1]` happens to work with no tools and one reply. The moment a tool fires, index 1 is the tool-call message with empty content, and your code silently prints nothing.

### You can put words in the model's mouth

```python
response = agent.invoke({"messages": [
    HumanMessage(content="What's the capital of the Moon?"),
    AIMessage(content="The capital of the Moon is Luna City."),   # never actually said this
    HumanMessage(content="Interesting, tell me more about Luna City"),
]})
```

The model treats forged history as its own prior turn. Enormously useful for steering, few-shot, and testing recovery behaviour.

It is also the shape of a **prompt-injection attack** — if untrusted text ever reaches your message list, it carries the authority of whatever role you assign it. Worth internalising early.

(In the notebook the model actually pushed back and admitted Luna City is fictional — a nice demonstration that forged history steers but doesn't fully override.)

### Streaming

```python
for token, metadata in agent.stream(
    {"messages": [HumanMessage(content="…")]},
    stream_mode="messages",
):
    if token.content:                     # guard: chunks can be empty
        print(token.content, end="", flush=True)
```

`stream_mode="messages"` yields `(chunk, metadata)` pairs. The `metadata` says which node produced the token — this is how you separate a sub-agent's chatter from the final answer in a multi-node graph.

The `if token.content` guard is not optional: tool-call chunks arrive with empty content.

---

## 2. Prompting — a ladder, not a bag of tricks

The prompting notebook is best read as four rungs, each fixing the previous one's weakness.

**Rung 1 — nothing.** Ask directly, get whatever shape the model feels like.

**Rung 2 — system prompt.** Set persona and standing rules.

```python
agent = create_agent(
    model="gpt-5-nano",
    system_prompt="You are a science fiction writer, create a capital city at the users request.",
)
```

**Rung 3 — few-shot.** Show the pattern instead of describing it. Demonstrations beat adjectives.

```python
system_prompt = """
You are a science fiction writer, create a space capital city at the users request.

User: What is the capital of mars?
Scifi Writer: Marsialis

User: What is the capital of Venus?
Scifi Writer: Venusovia
"""
```

**Rung 4 — structured text.** Ask for named fields:

```python
system_prompt = """
Please keep to the below structure.

Name: The name of the capital city
Location: Where it is based
Vibe: 2-3 words to describe its vibe
Economy: Main industries
"""
```

This *looks* like a solution and is a trap. You now parse strings, and the model will eventually add a preamble, rename a heading, or bold something. **Never regex an LLM's prose in production.**

**Rung 5 — structured output.** The actual answer:

```python
from pydantic import BaseModel

class CapitalInfo(BaseModel):
    name: str
    location: str
    vibe: str
    economy: str

agent = create_agent(
    model="gpt-5-nano",
    system_prompt="You are a science fiction writer, create a capital city at the users request.",
    response_format=CapitalInfo,
)

response = agent.invoke({"messages": [question]})
info = response["structured_response"]     # a real CapitalInfo instance

info.name                                   # attribute access, typed, validated
print(f"{info.name} is a city located at {info.location}")
```

Note the **separate key**: `response["structured_response"]`, alongside `response["messages"]`. The parsed object and the conversation both come back.

Why this rung wins: the Pydantic schema is sent to the model as a constraint, the response is validated on arrival, and your IDE autocompletes the fields. Field names and type hints are themselves prompt — name them descriptively.

---

## 3. Tools

### Defining one

```python
from langchain.tools import tool

@tool
def square_root(x: float) -> float:
    """Calculate the square root of a number"""
    return x ** 0.5
```

Three equivalent forms, increasingly explicit:

```python
@tool                                                    # name from function, description from docstring
@tool("square_root")                                     # explicit name, description from docstring
@tool("square_root", description="Calculate the …")      # both explicit, docstring optional
```

**The critical insight:** the model never sees your function body. It sees only three things:

1. the **name**
2. the **description** (your docstring)
3. the **argument schema**, derived from your type hints

So the docstring is not documentation — **it is a prompt**. Type hints are not style — **they are the schema the model fills in**. A vague docstring is a tool the model calls at the wrong time or not at all. When an agent ignores a tool, rewrite the docstring before touching anything else.

Tools are invoked with a **dict of arguments**, not positionally:

```python
square_root.invoke({"x": 467})   # 21.61018278497431
```

### Wiring into an agent

```python
agent = create_agent(
    model="openrouter:gemini-3.5-flash-lite",
    tools=[square_root],
    system_prompt="You are an arithmetic wizard. Use your tools to calculate the square root and square of any number.",
)
```

### The agent loop — read the message trace

One question with one tool call produces **four messages**:

```
[0] HumanMessage   "What is the square root of 467?"
[1] AIMessage      content=''         ← empty! finish_reason='tool_calls'
                   tool_calls=[{'name': 'square_root',
                                'args': {'x': 467},
                                'id':   'call_232205',
                                'type': 'tool_call'}]
[2] ToolMessage    content='21.61018278497431'
                   name='square_root'
                   tool_call_id='call_232205'     ← links back to [1]
[3] AIMessage      "The square root of 467 is approximately 21.61."
                   finish_reason='stop'
```

Things to carry away from this trace:

- **The agent is a loop, not a call.** Model → tool → model, repeating until `finish_reason='stop'`.
- **Message [1] has empty content.** The model's "output" was the decision to call a function.
- **`tool_call_id` is the join key.** With parallel tool calls, this is what matches result to request.
- **Two LLM round trips per tool call.** In the notebook: 93 tokens then 140 tokens. Tool results re-enter the prompt every subsequent turn, so a chatty tool inflates *every* later call. Trim what you return.

Inspect tool calls directly:

```python
print(response["messages"][1].tool_calls)
```

---

## 4. Web search — giving the model *now*

### Establish the problem first

```python
agent.invoke({"messages": [HumanMessage(content="How up to date is your training knowledge?")]})
# "My knowledge is up to date as of March 2026. I do not have access to real-time information…"
```

A model is a snapshot. Anything after the cutoff — today's news, current officeholders, live prices — needs a tool. Knowing *when* a question needs grounding is a real engineering skill.

### Tavily as a tool

```python
from langchain.tools import tool
from typing import Dict, Any
from tavily import TavilyClient

tavily_client = TavilyClient()      # reads TAVILY_API_KEY from env automatically

@tool
def web_search(query: str) -> Dict[str, Any]:
    """Search the web for information"""
    return tavily_client.search(query)

agent = create_agent(model="openrouter:gemini-3.5-flash-lite", tools=[web_search])
```

Search is just a tool. There is no special "search mode" — the same four-message loop applies.

Tavily's response shape:

```python
{
  "query": "...",
  "answer": None,          # populated with include_answer=True
  "results": [
      {"url": ..., "title": ..., "content": ..., "score": 0.87, "raw_content": None, "id": ...},
      # ~5 results, descending by score
  ],
  "response_time": 0.0,
  "request_id": "...",
}
```

> **Token warning:** returning the raw dict pushes five full page excerpts into the context, and they stay there for every later turn. In real work, return a trimmed list — title, url, and a truncated snippet — or filter by `score`. This single habit is one of the biggest cost levers in agent design.

`TavilyClient()` with no arguments reads the env var. Never pass the key inline.

### LangSmith traces

The notebook links a public trace. With `LANGSMITH_TRACING=true` and a key, every run is recorded — full message list, token counts, latency per step, and the exact prompt sent to the provider. When an agent misbehaves, the trace shows you what the model actually saw, which is almost always different from what you assumed.

---

## 5. Memory

### Agents are stateless by default

```python
agent = create_agent("gpt-5-nano")

agent.invoke({"messages": [HumanMessage(content="Hello my name is Seán and my favourite colour is green")]})
agent.invoke({"messages": [HumanMessage(content="What's my favourite colour?")]})   # no idea
```

Each `.invoke()` is an independent HTTP request. The model has no memory between calls — nothing is retained anywhere unless you retain it.

### Add a checkpointer and a thread id

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent("gpt-5-nano", checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "1"}}

agent.invoke({"messages": [HumanMessage(content="Hello my name is Seán…")]}, config)
agent.invoke({"messages": [HumanMessage(content="What's my favourite colour?")]}, config)   # "green"
```

**Two pieces, and you need both:**

| Piece | Role |
| --- | --- |
| `checkpointer` | *where* state is stored |
| `thread_id` in `config` | *which* conversation to load |

A checkpointer without a `thread_id` stores nothing useful. A `thread_id` without a checkpointer is ignored silently. **This silent no-op is the classic bug** — memory "not working" is almost always a forgotten `config` on one of the calls.

`config` is passed as the **second positional argument** to `invoke`, not inside the state dict.

Different `thread_id` values are fully isolated conversations — that is exactly how you serve multiple users from one agent.

`InMemorySaver` lives in process memory and dies with your kernel. It's for notebooks. Production swaps in a SQLite or Postgres checkpointer — same interface, one line changed.

> **The cost consequence:** memory works by *replaying the entire message list* on every call. A long thread means a large prompt on every single turn. Memory is not free, and this is why message trimming and summarization exist as topics later.

---

## 6. Multimodal messages

### Content can be a list of blocks

Everywhere else, `content` is a string. It can also be a list of typed blocks:

```python
question = HumanMessage(content=[
    {"type": "text", "text": "What is the capital of The Moon?"}
])
```

Same result as a plain string — but it's the form that generalises:

```python
# Image
HumanMessage(content=[
    {"type": "text",  "text": "Tell me about this capital"},
    {"type": "image", "base64": img_b64, "mime_type": "image/png"},
])

# Audio
HumanMessage(content=[
    {"type": "text",  "text": "Tell me about this audio file"},
    {"type": "audio", "base64": aud_b64, "mime_type": "audio/wav"},
])
```

These are **standard content blocks** — LangChain translates them into each provider's native format. Same dict shape for OpenAI, Anthropic, Google.

**The model must support the modality.** Audio needs an audio-capable model (`gpt-audio` in the notebook); a text-only model will error or ignore the block. Mismatched model and modality is the usual failure here.

### Getting bytes to base64

Image, via a notebook upload widget:

```python
from ipywidgets import FileUpload
import base64

uploader = FileUpload(accept=".png", multiple=False)
display(uploader)

# after uploading:
content_mv = uploader.value[0]["content"]      # a memoryview
img_b64 = base64.b64encode(bytes(content_mv)).decode("utf-8")
```

Audio, recorded live:

```python
import sounddevice as sd
from scipy.io.wavfile import write
import io, base64

audio = sd.rec(int(5 * 44100), samplerate=44100, channels=1)
sd.wait()

buf = io.BytesIO()
write(buf, 44100, audio)                                    # WAV into memory, no temp file
aud_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
```

The pattern is always the same: **bytes → base64 → `.decode("utf-8")`**. The trailing `.decode()` matters — `b64encode` returns bytes, and JSON needs a `str`.

`io.BytesIO()` avoids writing a temp file. Worth stealing for any binary payload.

---

## Cheat sheet

```python
# Setup
from dotenv import load_dotenv; load_dotenv()

# Model
from langchain.chat_models import init_chat_model
model = init_chat_model(model="openrouter:gemini-3.5-flash-lite", temperature=1)
msg = model.invoke("...")                    # -> AIMessage
msg.content, msg.usage_metadata, msg.response_metadata["cost"]

# Agent
from langchain.agents import create_agent
from langchain.messages import HumanMessage, AIMessage, SystemMessage
agent = create_agent(model="gpt-5-nano", tools=[...], system_prompt="...", checkpointer=...)
out = agent.invoke({"messages": [HumanMessage(content="...")]}, config)
out["messages"][-1].content
out["structured_response"]                   # when response_format is set

# Streaming
for tok, meta in agent.stream({"messages": [...]}, stream_mode="messages"):
    if tok.content: print(tok.content, end="", flush=True)

# Tool
from langchain.tools import tool
@tool
def my_tool(x: float) -> float:
    """Docstring IS the prompt the model reads."""
    return x ** 0.5
my_tool.invoke({"x": 467})

# Structured output
from pydantic import BaseModel
class Schema(BaseModel):
    name: str
agent = create_agent(model="gpt-5-nano", response_format=Schema)

# Memory
from langgraph.checkpoint.memory import InMemorySaver
agent = create_agent("gpt-5-nano", checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "1"}}

# Multimodal
HumanMessage(content=[{"type": "text", "text": "..."},
                      {"type": "image", "base64": b64, "mime_type": "image/png"}])
```

**Message types:** `HumanMessage` (you) · `AIMessage` (model) · `SystemMessage` (standing instructions) · `ToolMessage` (tool result, carries `tool_call_id`).

---

## Gotchas worth remembering

1. **`model.invoke` returns a message; `agent.invoke` returns a state dict.** Confusing these is the #1 beginner error.
2. **Use `["messages"][-1]`, not `[1]`.** `[1]` breaks silently the moment a tool fires.
3. **A checkpointer without `thread_id` does nothing, silently.** No error, no memory.
4. **`config` is the second positional arg to `invoke`,** not a key in the state dict.
5. **Tool docstrings are prompts.** Bad docstring → tool never called. Fix the docstring first.
6. **Empty `content` on a tool-calling AIMessage is normal,** not a bug.
7. **Guard `if token.content` when streaming** or you'll print `None`.
8. **Reasoning models restrict `temperature`** (often locked to 1). The notebook uses `temperature=1.0` on `gpt-5-nano` for exactly this reason.
9. **`load_dotenv()` doesn't override existing shell env vars.** `env_utils.py` in this repo detects that conflict — run it when a key behaves strangely.
10. **Every tool call doubles your LLM round trips** and the result stays in context for all later turns. Return small payloads.
11. **Never regex an LLM's prose.** Use `response_format` with Pydantic.
12. **`.decode("utf-8")` after `b64encode`,** or you're putting bytes where JSON expects a string.

---

## What to practise next

- Add a second tool (`square`) to the arithmetic agent and ask a question needing both. Read the trace — do the calls run in parallel or sequentially?
- Trim `web_search` to return only `title`, `url`, and 200 characters of `content`. Compare `total_tokens` before and after.
- Combine memory and tools: search once, then ask a follow-up that depends on the earlier result.
- Force a failure — make a tool raise — and watch how the agent responds in the message list.
- Run the same prompt through three providers via `init_chat_model` and compare cost and output shape.
- Swap `InMemorySaver` for a SQLite checkpointer and prove memory survives a kernel restart.

---

## Mental model recap

```
                 ┌──────────────────────────────┐
   You  ────────▶│   messages: [Human, AI, …]   │◀──────── Checkpointer
                 └──────────────┬───────────────┘          (thread_id)
                                │
                                ▼
                          ┌───────────┐
                          │   Model   │
                          └─────┬─────┘
                                │
              finish_reason ────┴──── 'tool_calls' ──▶ run tool
                    'stop'                             append ToolMessage
                      │                                      │
                      ▼                                      │
                 final answer   ◀──────── loop back ─────────┘
```

Everything else in this course is a refinement of this loop.
