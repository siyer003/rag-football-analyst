"""Prompt assembly for the generation pipeline."""

from footballanalyst.retrieval.types import RetrievedContext

_SYSTEM_PROMPT = """\
You are a football tactical analyst. Answer the user's question using ONLY \
the numbered context chunks provided below.

Rules:
- Cite every factual claim with [N] where N is the chunk number (e.g. [1], [2]).
- You may cite multiple chunks for a single claim: [1][3].
- If the context does not contain enough information to answer confidently, \
respond with: "not enough information in the provided context."
- Do not invent facts or draw on knowledge outside the provided chunks.
- Never state how an event occurred (e.g. header, volley, penalty, foot used, \
or any other method/manner detail) unless explicitly present in the retrieved \
context; omit the detail rather than infer or guess it.
- Be concise and specific to the match tactics.\
"""


def build_prompt(query: str, context: RetrievedContext) -> tuple[str, str]:
    """Assemble (system_prompt, user_prompt) for the LLM from a query and context.

    Each chunk is numbered from [1] so the LLM can cite them by index.
    No truncation is applied; at v1 corpus scale (top-8 chunks, paragraph-sized
    texts) the total prompt comfortably fits within any supported provider's
    context window. See docs/deferred.md for the deferred truncation note.

    Args:
        query: The natural-language question submitted by the user.
        context: The RetrievedContext returned by the HybridRetriever.

    Returns:
        A (system_prompt, user_prompt) tuple ready for LLMProvider.complete().
    """
    chunk_lines: list[str] = []
    for i, ranked in enumerate(context.chunks, start=1):
        chunk = ranked.chunk
        chunk_lines.append(f"[{i}] (source: {chunk.source})\n{chunk.text}")

    context_block = "\n\n".join(chunk_lines) if chunk_lines else "(no context provided)"
    user_prompt = f"{context_block}\n\nQuestion: {query}"

    return _SYSTEM_PROMPT, user_prompt
