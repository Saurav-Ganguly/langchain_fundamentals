"""The one place an agent gets built.

Every stage is the same shape: a system prompt, a schema, optionally a tool,
one user message in, one structured object out. Rather than repeat that
four times, the stages all call `ask` and differ only in their arguments.
"""

from langchain.agents import create_agent

from .config import MODEL


def ask(schema, system_prompt, messages, tools=None):
    """Run a fresh agent and return its structured response.

    Args:
        schema: Pydantic class the answer must conform to.
        system_prompt: Role and rules for this stage.
        messages: The conversation to send, usually one HumanMessage.
        tools: Tools the model may call. None means a single-shot answer.

    Returns:
        An instance of `schema`.
    """
    agent = create_agent(
        model=MODEL,
        tools=tools or [],
        system_prompt=system_prompt,
        response_format=schema,
    )

    # A fresh agent per call means no checkpointer and no shared thread, so
    # stages cannot leak context into each other. Each one sees exactly what
    # its caller hands it, which is what makes them testable in isolation.
    result = agent.invoke({"messages": messages})

    # create_agent puts the parsed object under "structured_response" and
    # leaves the raw message list under "messages" if you need to debug.
    return result["structured_response"]
