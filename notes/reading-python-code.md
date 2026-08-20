# Reading and Reviewing Python Code

A tutorial built on one real codebase: the chef pipeline in
`notebooks/module-1/`. Every example below is code you already own.

The goal is not "learn Python syntax". The goal is: **someone hands you 10
files you did not write, and you can say what they do and what is wrong with
them.** That is a separate skill from writing code, and it is the one that
actually gets used every day.

---

## Part 0. The three rules of reading unfamiliar code

**Rule 1: Find the entry point. Never start at file one of an alphabetical
list.**

Code is a tree, not a list. Something is the trunk. In Python the trunk is
almost always one of:

- a file with `if __name__ == "__main__":` at the bottom
- the thing named in `[project.scripts]` in `pyproject.toml`
- `main.py`, `app.py`, `cli.py`, `manage.py`

Here it is `my_chef.py`. Start there and let it tell you which files matter.

**Rule 2: Follow the data, not the control flow.**

Beginners read code asking "what happens next". Reviewers read asking "what
shape is the data right now". If you can name the shape at every step, you
understand the program, even if you have not read a single function body.

For this project the whole pipeline is:

```
list[Path]  ->  list[str]  ->  list[str]  ->  Recipe  ->  Coverage  ->  str
  photos        fridge        dish names     recipe      have/missing  markdown
                 items
```

Six shapes. That is the entire program. Everything else is detail.

**Rule 3: Read the boring files first.**

`images.py`, `ranking.py` and `report.py` have no AI in them at all. They are
plain Python you can run in your head. Read those first and you will have
learned 80% of the syntax before you reach the hard parts.

---

## Part 1. The map

Before reading anything, take 60 seconds and list the files with one line
each. Do this by hand, from the module docstrings only. It costs a minute and
saves an hour.

| File | Job | Any AI? |
| --- | --- | --- |
| `my_chef.py` | Entry point. Runs the stages in order. | no |
| `chef/__init__.py` | Makes `chef/` a package; loads `.env`; re-exports. | no |
| `chef/config.py` | Constants: model name, limits, paths, staples. | no |
| `chef/schemas.py` | The data shapes each stage must return. | no |
| `chef/runner.py` | The one place an agent is built. | yes |
| `chef/images.py` | Find image files, encode them. | no |
| `chef/tools.py` | The web search tool the agent can call. | yes |
| `chef/stages.py` | The four model-powered steps. | yes |
| `chef/ranking.py` | Turn coverage into an order. | no |
| `chef/report.py` | Turn the order into markdown. | no |

Notice what this table already tells you: **seven of ten files have no AI in
them.** If the output is wrong, there are seven places to look that you can
debug with `print()` and zero API calls. That is a design property worth
noticing before you read a line.

---

## Part 2. The entry point, line by line

Open `notebooks/module-1/my_chef.py`. Read from the **bottom**.

```python
if __name__ == "__main__":
    main()
```

> **Python concept: `__name__`**
> Every Python file has a variable called `__name__`. When you run a file
> directly (`uv run python my_chef.py`), Python sets it to the string
> `"__main__"`. When some *other* file imports it, Python sets it to the
> module's name instead (`"my_chef"`).
>
> So this line means: *"only call `main()` if I am being run, not if I am
> being imported."* Without it, importing this file to test one function
> would kick off a whole pipeline run and spend your API credits.
>
> Treat these two lines as punctuation. They mean "the program starts here".

Now `main()`:

```python
def main():
    requested = [Path(arg) for arg in sys.argv[1:]]
```

> **Python concept: list comprehension**
> `[Path(arg) for arg in sys.argv[1:]]` is shorthand for:
> ```python
> requested = []
> for arg in sys.argv[1:]:
>     requested.append(Path(arg))
> ```
> Read it right-to-left-ish: "for each arg in that list, make a `Path`, collect
> the results in a new list". You will see this constantly. It is not
> cleverness, it is the normal way to write that loop.

> **Python concept: `sys.argv` and slicing**
> `sys.argv` is the list of words typed on the command line. `sys.argv[0]` is
> always the script name itself, which you never want, so `[1:]` means "from
> index 1 to the end" and drops it.
>
> Slicing rules worth memorising now: `x[1:]` drops the first, `x[:3]` takes
> the first three, `x[-1]` is the last item, `x[:-1]` is everything but the
> last.

```python
    try:
        image_paths = resolve_images(requested)
    except (FileNotFoundError, ValueError) as error:
        sys.exit(str(error))
```

> **Python concept: exceptions**
> When something goes wrong, Python "raises" an exception, which stops
> everything and prints a traceback. `try:` / `except:` catches it.
>
> Note what is caught: `(FileNotFoundError, ValueError)` — a specific tuple,
> not a bare `except:`. **This is a thing to check in every review.** A bare
> `except:` or `except Exception:` catches typos and keyboard interrupts too,
> and hides real bugs. Catching two named types says "I thought about exactly
> what can fail here."
>
> `sys.exit("message")` prints the message and quits with a failure code. It
> is the polite way to die: the user sees one line, not 30 lines of traceback.

Now read `cook()` above it. The whole pipeline is 30 lines because each stage
is one call:

```python
items = see_fridge(image_paths)      # stage 1
names = brainstorm(items)            # stage 2
recipe = fetch_recipe(name)          # stage 3
coverage = score(items, recipe)      # stage 4
ranked = rank(scored)                # stage 5
REPORT_PATH.write_text(render(ranked, items), encoding="utf-8")
```

**Review question you should already be asking:** why is stage 3 and 4 inside
a `try` but stages 1, 2 and 5 are not? Answer is in the comment: stage 3 hits
a live search engine that can fail on any single dish, and by that point in
the run you have already paid for earlier recipes. Losing one dish is
acceptable; losing the run is not. Stages 1 and 2 failing means there is
nothing to continue with anyway.

Good code answers "why is this different here?" in a comment. When it does
not, that is your first review comment.

---

## Part 3. What a "package" actually is

You have two kinds of thing here:

- **module** = one `.py` file. `config.py` is a module.
- **package** = a directory with an `__init__.py`. `chef/` is a package.

`chef/__init__.py` runs when anyone does `import chef` or
`from chef import anything`. That is the key fact — it is not a config file,
it is **code that executes**.

```python
from dotenv import load_dotenv

load_dotenv()

from .config import DEFAULT_IMAGE_DIR, REPORT_PATH  # noqa: E402
```

Three things to understand here.

> **Python concept: relative imports**
> The dot in `from .config import ...` means "from the `config` module *in
> this same package*". Without the dot, Python would go looking for a
> globally installed package called `config` and probably find something
> else. Inside a package, always use the dot.

> **Python concept: import side effects**
> Normally all imports go at the top of a file. Here `load_dotenv()` is
> deliberately squeezed in *between* imports, because `tools.py` builds
> `TavilyClient()` at import time, and that constructor reads
> `TAVILY_API_KEY` from the environment. If `.env` has not been loaded yet,
> that fails.
>
> This is a real ordering dependency, and it is fragile — the kind of thing
> that breaks when someone tidies the imports. Which is why:

> **Python concept: `# noqa: E402`**
> `noqa` = "no quality assurance", a note to the linter. `E402` is the rule
> "module level import not at top of file". This comment says "I know, I meant
> it." When you see a `noqa`, read it as a signpost saying *something unusual
> happened here* — a good place to point your review attention.

Finally, `__all__` is a list of names that `from chef import *` would export.
Its real value is documentation: it is the package's public surface. Anything
not in that list is internal, and you can change it freely.

---

## Part 4. Constants, and the leading underscore

`config.py` is the easiest file in the project, and it teaches two conventions.

```python
MAX_RECIPES = 5
_SEASONING = ["salt", "black salt", ...]
```

> **Convention: ALL_CAPS means constant.**
> Python will not stop you reassigning `MAX_RECIPES`. The capitals are a
> promise between programmers: nobody writes to this at runtime.

> **Convention: a leading underscore means private.**
> `_SEASONING` is not enforced either. It means "this is an implementation
> detail of this module, do not import it elsewhere". `PANTRY_STAPLES` is the
> public name; the eleven `_`-prefixed lists exist only to build it.
>
> Same rule applies to `_client` and `_OPERATORS` in `tools.py`.

```python
LESSON_DIR = Path(__file__).parent.parent
```

> **Python concept: `__file__` and `pathlib`**
> `__file__` is the path of the current source file. `.parent` goes up one
> directory. So this resolves relative to *the code*, not to wherever you
> happened to be standing when you ran the command.
>
> **Review flag:** anything using a bare relative path like `"resources/fridge"`
> is a bug waiting to happen — it only works if you run the program from one
> specific directory. `Path(__file__).parent` is the correct habit.
>
> Also note `LESSON_DIR / "resources" / "fridge"`. `pathlib` overloads the `/`
> operator to join paths, and it produces `\` on Windows and `/` on Linux
> automatically. Never build a path with string concatenation.

---

## Part 5. Classes, without the theory

`schemas.py` is your first class. You do not need object-oriented theory to
read it.

```python
class Fridge(BaseModel):
    """Stage 1 output: what the camera can actually see."""

    items: list[str] = Field(
        description="Ingredient names only, no quantities or packaging"
    )
```

Read it as: **"a `Fridge` is a thing that has an `items`, and `items` is a
list of strings."** That is genuinely all it means here.

> **Python concept: type hints**
> `items: list[str]` is an annotation. Plain Python **does not check it** — it
> is a note for humans and tools. You could assign a number to it and Python
> would shrug.
>
> Pydantic is the exception: `BaseModel` reads those annotations and *does*
> enforce them at runtime. That is the entire point of the library.

> **Python concept: inheritance**
> `class Fridge(BaseModel)` means "`Fridge` is a `BaseModel`, plus my extras".
> `Fridge` gets validation, `.model_dump()`, JSON schema generation, all for
> free. This is the only inheritance in the project, and it is the common
> case: you inherit from a library's base class to opt into its machinery.

The important review insight is in the module docstring:

> Field descriptions are not decoration: they are sent to the model as part of
> the schema.

That is the non-obvious bit. In ordinary Python a docstring is for you. Here,
`description=` is a **prompt**. When reviewing an AI codebase, treat every
`Field(description=...)` as instructions to the model and read it as
critically as you read the system prompt.

---

## Part 6. Functions, defaults, and one trap

`runner.py` is 15 lines of real code and contains a classic.

```python
def ask(schema, system_prompt, messages, tools=None):
    agent = create_agent(
        model=MODEL,
        tools=tools or [],
        ...
    )
```

> **Python trap: mutable default arguments**
> You might think `tools=[]` would be simpler. It is a well-known bug.
> Python evaluates default arguments **once**, when the function is defined,
> not on each call. So every call would share the *same* list object, and if
> anything ever appended to it, the change would persist into the next call.
>
> The fix is exactly what is written here: default to `None`, then convert.
> **`tools=None` plus `tools or []` is the idiom.** Seeing a mutable default
> (`=[]`, `={}`) in a review is an automatic comment.

> **Python concept: `or` returns a value, not a boolean**
> `tools or []` means "`tools` if it is truthy, otherwise `[]`". Falsy values
> in Python: `None`, `False`, `0`, `""`, `[]`, `{}`. So this collapses both
> `None` and an empty list to `[]`.
>
> You will see it again in `report.py`: `", ".join(cov.missing) or "nothing"`
> — if the join produces an empty string, use `"nothing"` instead.

```python
    result = agent.invoke({"messages": messages})
    return result["structured_response"]
```

`result` is a dictionary. `result["structured_response"]` looks up a key.
**Review question: what if that key is missing?** It raises `KeyError`. Here
that is acceptable — it means the model failed to produce structured output,
which is not something the pipeline can paper over. But you should ask the
question every time you see `[...]` indexing rather than `.get(...)`.

---

## Part 7. The best file to practise on

`images.py` has no AI, no network and no state. If you only study one file,
study this one.

```python
def encode_image(image_path: Path) -> tuple[str, str]:
    suffix = image_path.suffix.lower()
    if suffix not in MIME_TYPES:
        raise ValueError(...)
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return encoded, MIME_TYPES[suffix]
```

> **Python concept: returning multiple values**
> `return encoded, MIME_TYPES[suffix]` returns a **tuple** — the comma makes
> the tuple, the parentheses in `tuple[str, str]` are just the annotation.
> The caller unpacks it:
> ```python
> img_b64, mime = encode_image(image_path)
> ```
> Two names on the left, one tuple on the right. Python matches them
> positionally. If the counts do not match, you get a `ValueError` at runtime.

> **Python concept: `in` on a dict checks keys**
> `suffix not in MIME_TYPES` tests the dictionary's **keys**, not its values.
> A very common misreading.

> **Python concept: bytes vs str**
> `read_bytes()` gives raw bytes. `b64encode` takes bytes and returns bytes.
> `.decode("utf-8")` turns bytes into a string. Python keeps these strictly
> separate and will not silently convert. When you hit a `TypeError` mentioning
> "a bytes-like object is required", this is why.

Now the more interesting function:

```python
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found += sorted(
                child
                for child in path.iterdir()
                if child.suffix.lower() in MIME_TYPES
            )
        elif path.exists():
            found.append(path)
        else:
            raise FileNotFoundError(f"No such image or directory: {path}")

    unique = list(dict.fromkeys(found))
```

Four things in nine lines:

1. **`found: list[Path] = []`** — annotating an empty list. Without the
   annotation, tools cannot tell what goes in it.

2. **The comprehension has an `if` at the end.** `[x for x in y if cond]` is
   the filtered form. Read as: "every child, keeping only the ones whose
   suffix is a known image type." Note there are no square brackets inside
   `sorted(...)` — that is a *generator expression*, the lazy version. Same
   meaning, no intermediate list built.

3. **`found += list`** extends in place; `found.append(x)` adds one item.
   Mixing them up is a classic beginner bug: `append` on a list gives you a
   nested list, `+=` on a single item raises `TypeError`.

4. **`list(dict.fromkeys(found))` is the dedupe idiom.** Since Python 3.7,
   dictionaries preserve insertion order. `dict.fromkeys(x)` builds a dict
   using the items as keys — duplicates collapse because keys are unique —
   and converting back to a list gives you *deduped, order preserved*.
   `set(found)` would also dedupe but would scramble the order, which would
   make runs non-reproducible.

Finally:

```python
    return unique[:MAX_IMAGES]
```

Slicing never raises. If `unique` has 2 items and `MAX_IMAGES` is 6, you get
2 back, no error. That is why slicing is preferred over index arithmetic for
"take at most N".

---

## Part 8. Decorators

`tools.py`:

```python
@tool
def web_search(query: str) -> dict:
    """Search the web for information."""
```

> **Python concept: decorators**
> `@tool` above a function means: *"do not just define `web_search`; pass it
> to `tool()` and bind the name `web_search` to whatever comes back."* It is
> exactly equivalent to:
> ```python
> def web_search(query): ...
> web_search = tool(web_search)
> ```
> That is the whole mechanism. A decorator is a function that takes a function
> and returns a replacement.
>
> What LangChain's `tool` returns is an object carrying the function *plus*
> its name, its docstring, and a JSON schema derived from the type hints. That
> is how the model learns the tool exists.

Which produces the single most important review note in this file, already in
the code as a comment:

```python
    # The docstring above is not a comment for humans. It is the tool
    # description the model reads when deciding whether to call this
```

In a normal codebase a bad docstring is untidy. In an agent codebase a bad
docstring is a **bug**, because it is input to the model.

The other lesson here is the error path:

```python
    if not cleaned:
        return {
            "error": "That query was only search operators, ..."
        }
```

It **returns** the error instead of **raising** it. The comment explains why:
a raise aborts the agent loop; a returned dict goes back to the model, which
can read it and retry. This is an agent-specific pattern with no equivalent in
ordinary Python, and it is worth remembering: *errors the model can fix should
be data; errors it cannot should be exceptions.*

---

## Part 9. Sorting

`ranking.py` is six lines of logic that teach three things.

```python
Scored = tuple[Recipe, Coverage]
```

> **Python concept: type alias**
> That is just a name for a type. Writing `list[tuple[Recipe, Coverage]]`
> everywhere is unreadable; `list[Scored]` is not. It creates no new class and
> costs nothing at runtime.

```python
def ratio(coverage: Coverage) -> float:
    total = len(coverage.have) + len(coverage.missing)
    return len(coverage.have) / total if total else 0.0
```

> **Python concept: conditional expression**
> `A if condition else B` is Python's ternary. It reads awkwardly at first
> because the condition is in the middle. Read it as: "give me `A`, unless
> `total` is zero, in which case `0.0`."
>
> The purpose is real: without it, an empty `Coverage` divides by zero and
> crashes the run.

```python
return sorted(scored, key=lambda pair: (-ratio(pair[1]), len(pair[0].ingredients)))
```

This one line deserves a paragraph.

> **`key=`** — `sorted` calls this function on each element and sorts by the
> result, leaving the elements themselves untouched.
>
> **`lambda`** — an anonymous one-expression function. `lambda pair: X` is
> `def f(pair): return X` without the name. Only use it when it is this short.
>
> **The tuple** — returning `(a, b)` as the key sorts by `a` first, and uses
> `b` only to break ties. This is *the* Python idiom for multi-level sorting;
> you do not need a comparator function.
>
> **The minus sign** — `sorted` only goes ascending. Negating a number flips
> it, so `-ratio(...)` gives you highest-coverage-first while the second
> element stays ascending (fewest ingredients first). You could not achieve
> that mixed direction with `reverse=True`.
>
> **`pair[1]` / `pair[0]`** — index into the tuple. Honestly this would read
> better unpacked, and that is a legitimate review comment to leave.

---

## Part 10. Building strings

`report.py` shows the correct way to assemble a long string.

```python
lines = [
    f"# {winner.name}",
    "",
    f"**Ingredient coverage: {ratio(coverage):.0%}** ({covered} of {total})",
]
lines += [f"- {item}" for item in coverage.have]
...
return "\n".join(lines)
```

> **Idiom: collect lines in a list, join once at the end.**
> The obvious alternative is `text += "..."` repeatedly. Python strings are
> immutable, so every `+=` builds a whole new string and copies the old one.
> For a long document that is quadratic. The list-then-join approach is the
> standard fix, and it also reads better: each entry is visibly one line, and
> `""` is visibly a blank line.

> **Python concept: f-string format specs**
> `f"{ratio(coverage):.0%}"` — everything after the `:` is a format spec.
> `.0%` means "multiply by 100, show zero decimal places, add a percent sign".
> So `0.8` renders as `80%`. Other ones worth knowing: `:.2f` (two decimals),
> `:,` (thousands separators), `:>10` (right-align in 10 columns).

> **`enumerate(winner.steps, 1)`** — pairs each item with a counter. The `1`
> is the start value, which is why the method list begins at 1 and not 0. The
> long-hand version with a manual counter variable is always worse.

---

## Part 11. From reading to reviewing

Reading tells you what the code does. Reviewing asks whether it should. Here
is a checklist that works on any Python file. Apply it in this order.

**1. Does the docstring match the body?**
Drift between the two is the single most common defect in real code, and it is
free to spot. `ratio()` says "fraction of non-staple ingredients" — hold on to
that claim, we come back to it.

**2. What happens on the unhappy path?**
For every function, ask: empty input, missing file, network down, model returns
nonsense. `ratio()` handles the empty case explicitly. `cook()` handles the
empty-items case with `sys.exit`. `runner.ask()` does *not* handle a missing
`structured_response` key. Now you know the risk profile without running
anything.

**3. Where does the money go?**
In an AI codebase this replaces "where does the time go". Count the API calls:
`1 + 1 + MAX_RECIPES + MAX_RECIPES` = 12 model calls per run at `MAX_RECIPES=5`.
The `[:MAX_IMAGES]` cap in `images.py` exists for exactly this reason. Any
loop that calls a model is worth a hard look.

**4. What is enforced by code, and what is only requested in a prompt?**
This is the review question unique to AI systems, and it is where the bug in
this project lives.

**5. Could I test this without an API key?**
`images.py`, `ranking.py`, `report.py` — yes. `stages.py` — no. That split is
a quality signal. Code that can only be tested by spending money tends to stay
untested.

---

## Part 12. A worked review: finding the real bug

Let us actually apply question 4 to `stages.py`.

```python
def score(items: list[str], recipe: Recipe) -> Coverage:
    return ask(
        Coverage,
        "You compare a recipe against a fridge. ... Treat these as always "
        f"available and leave them out of both lists entirely: "
        f"{', '.join(PANTRY_STAPLES)}. ...",
        ...
    )
```

Read that as a reviewer, not as a user:

- `PANTRY_STAPLES` is 139 items, about 1,500 characters, pasted into the
  system prompt.
- The rule "leave them out of both lists entirely" is **requested**, not
  **enforced**. Nothing in Python checks the model obeyed.
- The docstring of `ratio()` in `ranking.py` claims it computes the fraction
  of *non-staple* ingredients. But `ratio()` just counts list lengths. It is
  trusting the prompt to have removed the staples. **Two files apart, and the
  guarantee lives in neither of them.**

That is enough to file a review comment on suspicion. But per your own rule,
prove it before you fix it. Look at the generated report:

```
## From your fridge
- potatoes
- oil
- salt          <- in PANTRY_STAPLES
- black pepper  <- in PANTRY_STAPLES

## You still need
- onion         <- in PANTRY_STAPLES
```

Then verify the membership claim directly rather than trusting your memory of
the list:

```python
from chef.config import PANTRY_STAPLES
for x in ["salt", "black pepper", "onion", "olive oil"]:
    print(x, x in PANTRY_STAPLES)
```

All four print `True`. The instruction is being ignored in both directions,
and since `ratio()` is `have / (have + missing)`, the leak changes the score
and therefore changes which recipe wins.

**That is a complete review finding:** a claim in a docstring, a mechanism
that cannot support the claim, and evidence from a real run. Notice the order.
Suspicion came from reading, confirmation came from running. Neither alone
would have been enough.

The general lesson, which is worth more than the bug: **a prompt is a request,
not a guarantee. Anything that must be true should be true in Python.** Set
membership is something Python does perfectly and a language model does
approximately, so it belongs in `ranking.py`, not in a system prompt.

---

## Part 13. Exercises

Do these in order. Each one is small.

1. **Trace by hand.** Start from
   `uv run python notebooks/module-1/my_chef.py notebooks/module-1/chef/images`
   and write down, on paper, every function called in order, with the shape of
   what it returns. Do not run anything. Then check yourself against the
   console output of a real run.

2. **Break something deliberately.** Change `MAX_RECIPES` to 2 in `config.py`
   and predict, before running, exactly which lines of output change. Being
   able to predict the diff is the test of whether you understood.

3. **Read one file cold.** Open `report.py` without the rest of the project
   and write its docstring yourself, from the body only. Compare to the real
   one.

4. **Write a test with no API.** `render()` takes plain objects. Build a
   `Recipe` and a `Coverage` by hand, call `render([(r, c)], ["eggs"])`, and
   print the result. You just tested a third of the pipeline for free. Doing
   this is what makes the "can I test it without an API key" question feel
   real rather than theoretical.

5. **Fix the bug.** Write a `strip_staples(coverage)` function in
   `ranking.py` that removes staples from both lists in Python, and call it
   before `ratio()`. Then delete the staples list from the prompt in
   `stages.py`. Test it with exercise 4's approach — no API calls needed.

6. **Find a second one.** `see_fridge()` returned `water bottle` and
   `aloe vera juice` as food items. Decide whether that is a prompt problem, a
   schema problem, or not a problem. Argue it either way in two sentences.

---

## Appendix. Syntax cheat sheet

Everything used in this project, in one place.

| Syntax | Meaning |
| --- | --- |
| `if __name__ == "__main__":` | Run this only when executed directly |
| `_name` | Private by convention; do not import elsewhere |
| `NAME` | Constant by convention |
| `x: list[str]` | Type hint; not enforced by Python itself |
| `def f() -> str:` | Return type hint |
| `[f(x) for x in xs]` | List comprehension |
| `[x for x in xs if c]` | Filtered comprehension |
| `(x for x in xs)` | Generator; lazy, no list built |
| `xs[1:]`, `xs[:3]`, `xs[-1]` | Slicing: drop first, take three, last item |
| `a, b = f()` | Tuple unpacking |
| `a if c else b` | Conditional expression |
| `a or b` | `a` if truthy, else `b` |
| `f"{x:.0%}"` | Format 0.8 as `80%` |
| `"\n".join(lines)` | Build a string from a list |
| `enumerate(xs, 1)` | Pairs of (counter starting at 1, item) |
| `sorted(xs, key=lambda x: (a, b))` | Sort by `a`, tie-break on `b` |
| `list(dict.fromkeys(xs))` | Dedupe, preserving order |
| `d.setdefault(k, v)` | Set `k` only if absent |
| `@decorator` | Replace the function with `decorator(function)` |
| `from .mod import x` | Import from this package |
| `raise ValueError(msg)` | Signal an error |
| `except (A, B) as e:` | Catch specific errors only |
| `Path(__file__).parent` | Directory of this source file |
| `dir / "a" / "b"` | Join paths, cross-platform |
| `tools=None` then `tools or []` | Avoid the mutable-default trap |
| `# noqa: E402` | Linter silenced deliberately; look closer |

---

## The short version

- Start at the entry point, read bottom-up, follow the data shapes.
- Read the files with no AI in them first; they teach the syntax cheaply.
- Names carry meaning: `_private`, `CONSTANT`, `__dunder__`.
- Docstrings in an agent codebase are prompts. Review them as code.
- For every function ask: what does the unhappy path do?
- Anything that must be true should be enforced in Python, not requested in a
  prompt.
- Suspect from reading, confirm by running. Never one without the other.
