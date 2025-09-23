import json, uuid, os
from datetime import datetime
from typing import Optional, Dict, Any
try:
    # LangChain v0.2+
    from langchain_core.callbacks.base import BaseCallbackHandler
except Exception:
    # Fallback for older versions
    from langchain.callbacks.base import BaseCallbackHandler  # type: ignore

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

class JsonlEventLogger(BaseCallbackHandler):
    """
    A simple callback that writes structured, sanitized events to a JSONL file
    for real-time UI consumption.
    You can safely log high-level summaries without dumping chain-of-thought.
    """
    def __init__(self, session_id: Optional[str] = None, path: str = "events.jsonl"):
        self.session_id = session_id or os.getenv("SESSION_ID") or str(uuid.uuid4())
        self.path = path
        self._stack = []  # track tool_run ids etc.

    def _append(self, obj: Dict[str, Any]):
        obj.setdefault("session_id", self.session_id)
        obj.setdefault("ts", _now_iso())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # --- High-level planning (emit sanitized summaries) ---
    def on_chain_start(self, serialized, inputs, **kwargs):
        self._append({
            "type": "plan", "id": str(uuid.uuid4()), "parent_id": None,
            "label": serialized.get("id","chain") if isinstance(serialized, dict) else "chain",
            "summary": f"Chain start with keys: {list((inputs or {}).keys())}",
        })

    def on_chain_end(self, outputs, **kwargs):
        self._append({
            "type": "observation", "id": str(uuid.uuid4()),
            "label": "chain_end",
            "summary": f"Chain produced keys: {list((outputs or {}).keys())}"
        })

    def on_llm_start(self, serialized, prompts, **kwargs):
        # Do NOT log raw prompts; log sanitized counts
        n = len(prompts or [])
        self._append({
            "type": "action", "id": str(uuid.uuid4()),
            "label": "llm_call",
            "summary": f"LLM call with {n} prompt(s)"
        })

    def on_llm_end(self, response, **kwargs):
        try:
            gens = getattr(response, "generations", [[]])
            n_gens = sum(len(g) for g in gens)
            token_usage = (getattr(response, "llm_output", {}) or {}).get("token_usage", {})
        except Exception:
            n_gens, token_usage = 0, {}
        self._append({
            "type": "observation", "id": str(uuid.uuid4()),
            "label": "llm_result",
            "summary": f"LLM returned {n_gens} generation(s)",
            "payload": {"token_usage": token_usage}
        })

    # --- Tools ---
    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_id = str(uuid.uuid4())
        self._stack.append(tool_id)
        name = serialized.get("name","tool") if isinstance(serialized, dict) else "tool"
        self._append({
            "type": "tool_start", "id": tool_id, "parent_id": None,
            "label": name,
            "summary": "Tool started (input redacted)"
        })

    def on_tool_end(self, output, **kwargs):
        parent = self._stack.pop() if self._stack else None
        self._append({
            "type": "tool_end", "id": str(uuid.uuid4()), "parent_id": parent,
            "label": "tool_done",
            "summary": "Tool finished (output redacted)"
        })

    # --- Retriever / Metrics ---
    def on_retriever_end(self, documents, **kwargs):
        self._append({
            "type": "metric", "id": str(uuid.uuid4()),
            "label": "retriever",
            "summary": f"Retrieved {len(documents or [])} docs",
            "payload": {"retrieved_docs": len(documents or [])}
        })