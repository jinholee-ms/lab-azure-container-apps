import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="LLM Planning Monitor", page_icon="🧠", layout="wide")
st.title("🧠 LLM Planning Monitor")
st.caption("Live view of agent planning (sanitized): Plan → Action → Observation → Metrics")

with st.sidebar:
    st.header("Settings")
    default_path = "events.jsonl"
    log_path = st.text_input("Events JSONL path", value=default_path, help="File that your agent callbacks append to (JSON lines).")
    refresh_ms = st.slider("Auto-refresh (ms)", min_value=500, max_value=5000, value=1500, step=100)
    only_session = st.text_input("Filter by session_id (optional)", value="")
    redact = st.toggle("Redact inputs/outputs", value=True)
    st.divider()
    st.markdown("**Event schema**")
    st.code('''{"ts": "...", "session_id": "...", "id": "...", "parent_id": null,
"type": "plan|action|observation|tool_start|tool_end|message|metric",
"label": "...", "summary": "...",
"payload": {...}, "duration_ms": 0}''', language="json")
#st.autorefresh(interval=refresh_ms, key="auto_refresh_key")

def parse_jsonl(path: str):
    p = Path(path)
    if not p.exists():
        return []
    events = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            pass
    return events

def filter_events(evts):
    if only_session:
        evts = [e for e in evts if e.get("session_id") == only_session]
    def key(e):
        try:
            return (pd.to_datetime(e.get("ts")), e.get("id",""))
        except Exception:
            return (datetime.utcnow(), e.get("id",""))
    evts.sort(key=key)
    return evts

def to_df(evts):
    if not evts:
        return pd.DataFrame(columns=["ts","session_id","id","parent_id","type","label","summary","duration_ms","payload"])
    df = pd.DataFrame(evts)
    for col in ["ts","session_id","id","parent_id","type","label","summary"]:
        if col not in df.columns:
            df[col] = ""
    if "duration_ms" not in df.columns: df["duration_ms"] = 0
    if "payload" not in df.columns: df["payload"] = None
    df["ts_dt"] = pd.to_datetime(df["ts"], errors="coerce")
    return df

def build_tree(df):
    nodes = {row["id"]: {**row.to_dict(), "children": []} for _, row in df.iterrows()}
    roots = []
    for _, row in df.iterrows():
        pid = row.get("parent_id")
        nid = row["id"]
        if pid and pid in nodes:
            nodes[pid]["children"].append(nodes[nid])
        else:
            roots.append(nodes[nid])
    return roots

def render_node(node, level=0, redact=True):
    pad = " " * level
    typ = node.get("type", "")
    emoji = {"plan":"📝","action":"⚙️","observation":"👀","tool_start":"🛠️","tool_end":"✅","message":"💬","metric":"📈"}.get(typ, "•")
    header = f"{pad}{emoji} [{typ}] {node.get('label') or node.get('id')}"
    with st.expander(header, expanded=(typ in ("plan","action") and level < 2)):
        st.caption(f"{node.get('ts','')} · id={node.get('id')} · parent={node.get('parent_id')}")
        st.write(node.get("summary",""))
        payload = node.get("payload") or {}
        if payload and not redact:
            st.json(payload)
    for ch in node.get("children", []):
        render_node(ch, level+1, redact=redact)

events_raw = parse_jsonl(log_path)
events = filter_events(events_raw)
df = to_df(events)

c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Live Feed")
    if df.empty:
        st.info("Waiting for events… Append JSON lines to the file to see live updates.")
    else:
        feed = df.sort_values("ts_dt").tail(200)
        for _, r in feed.iterrows():
            with st.container(border=True):
                st.markdown(f"**[{r['type']}]** {r['label'] or r['id']}")
                st.caption(f"{r['ts']} · session={r['session_id']} · parent={r['parent_id']} · duration={int(r.get('duration_ms',0))} ms")
                st.write(r.get("summary",""))
                if not redact and r.get("payload") not in (None, "", {}):
                    st.json(r["payload"])

with c2:
    st.subheader("Plan Tree")
    if df.empty:
        st.info("No nodes yet")
    else:
        for root in build_tree(df):
            render_node(root, 0, redact=redact)

st.divider()

st.subheader("Timeline")
if df.empty:
    st.info("No timeline data")
else:
    spans = []
    starts = {}
    for _, r in df.iterrows():
        if r["type"] == "tool_start":
            starts[r["id"]] = r
        elif r["type"] == "tool_end":
            s = starts.get(r.get("parent_id")) or starts.get(r["id"])
            if s is not None:
                spans.append({
                    "label": f"🛠️ {s.get('label') or s['id']}",
                    "start": s["ts_dt"],
                    "end": r["ts_dt"],
                    "kind": "tool",
                    "session_id": r["session_id"]
                })
    for _, r in df.iterrows():
        if r["type"] in ("plan","action") and r.get("duration_ms", 0) > 0 and pd.notnull(r["ts_dt"]):
            end_ts = r["ts_dt"] + pd.to_timedelta(r["duration_ms"], unit="ms")
            spans.append({
                "label": f"{'📝' if r['type']=='plan' else '⚙️'} {r.get('label') or r['id']}",
                "start": r["ts_dt"],
                "end": end_ts,
                "kind": r["type"],
                "session_id": r["session_id"]
            })
    if spans:
        gdf = pd.DataFrame(spans).dropna(subset=["start","end"])
        gdf = gdf[gdf["end"] >= gdf["start"]]
        chart = alt.Chart(gdf).mark_bar().encode(
            x=alt.X("start:T", title="time"),
            x2=alt.X2("end:T"),
            y=alt.Y("label:N", sort="-x", title="step"),
            color=alt.Color("kind:N", legend=alt.Legend(title="kind")),
            tooltip=["label","kind","start","end","session_id"]
        ).properties(height=max(300, 22*len(gdf)))
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No span events yet (need tool_start/tool_end or duration_ms on plan/action).")

st.subheader("Metrics")
if df.empty:
    st.info("No metrics yet")
else:
    m = df[df["type"] == "metric"]
    cols = st.columns(3)
    def metric_sum(key):
        try:
            return int(sum([(row.get("payload") or {}).get(key, 0) for _, row in m.iterrows()]))
        except Exception:
            return 0
    def metric_mean(key):
        vals = [float((row.get("payload") or {}).get(key, 0)) for _, row in m.iterrows() if (row.get("payload") or {}).get(key) is not None]
        return (sum(vals)/len(vals)) if vals else 0.0

    with cols[0]:
        st.metric("Total input tokens", f"{metric_sum('prompt_tokens'):,}")
        st.metric("Total output tokens", f"{metric_sum('completion_tokens'):,}")
    with cols[1]:
        st.metric("Total tool calls", f"{(df['type']=='tool_start').sum()}")
        st.metric("Avg. tool latency (ms)", f"{metric_mean('tool_latency_ms'):.0f}")
    with cols[2]:
        st.metric("Requests", f"{df[df['type'].isin(['plan','action','message'])]['id'].nunique():,}")
        total_cost = metric_sum('cost_usd')
        st.metric("Total cost ($)", f"{total_cost/1000:.3f}k" if total_cost>1000 else f"{total_cost:.4f}")