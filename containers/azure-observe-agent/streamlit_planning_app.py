import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime, date
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="Planning Tasks", page_icon="🗂️", layout="wide")

DATA_PATH = Path("tasks.json")

STATUSES = ["Backlog", "Planned", "In Progress", "Blocked", "Done"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]

@dataclass
class Task:
    id: str
    title: str
    status: str
    start_date: str  # YYYY-MM-DD
    due_date: str    # YYYY-MM-DD
    assignee: str = ""
    priority: str = "Medium"
    progress: int = 0  # 0~100
    tags: List[str] = None
    description: str = ""
    depends_on: List[str] = None

    def to_dict(self):
        d = asdict(self)
        # Ensure lists are lists
        d["tags"] = self.tags or []
        d["depends_on"] = self.depends_on or []
        return d

def load_tasks() -> pd.DataFrame:
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = []
    if not raw:
        return pd.DataFrame(columns=[
            "id","title","status","start_date","due_date","assignee",
            "priority","progress","tags","description","depends_on"
        ])
    df = pd.DataFrame(raw)
    # Normalize potential missing columns
    for col in ["tags","depends_on"]:
        if col not in df.columns:
            df[col] = [[] for _ in range(len(df))]
    return df

def save_tasks(df: pd.DataFrame):
    records = df.to_dict(orient="records")
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def ensure_sample_data():
    if DATA_PATH.exists():
        return
    sample = [
        Task(id="T-001", title="Define scope & OKRs", status="Planned",
             start_date=str(date.today()), due_date=str(date.today()), assignee="PM",
             priority="High", progress=40, tags=["planning", "OKR"], description="Kickoff & OKRs").to_dict(),
        Task(id="T-002", title="Design system sketch", status="In Progress",
             start_date=str(date.today()), due_date=str(date.today().replace(day=date.today().day)+pd.Timedelta(days=7)), assignee="Alice",
             priority="High", progress=60, tags=["design"], description="UI/UX exploration", depends_on=["T-001"]).to_dict(),
        Task(id="T-003", title="API spec v1", status="Backlog",
             start_date=str(date.today()), due_date=str(date.today()), assignee="Bob",
             priority="Medium", progress=0, tags=["backend","spec"]).to_dict(),
        Task(id="T-004", title="PoC pipeline", status="Blocked",
             start_date=str(date.today()), due_date=str(date.today()), assignee="Data",
             priority="Critical", progress=10, tags=["data","ml"], description="Waiting for creds", depends_on=["T-001","T-003"]).to_dict(),
        Task(id="T-005", title="Release 0.1", status="Done",
             start_date=str(date.today()), due_date=str(date.today()), assignee="DevOps",
             priority="Medium", progress=100, tags=["release"]).to_dict(),
    ]
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)

ensure_sample_data()

# ---- SIDEBAR ----
st.sidebar.title("Filters")
df_all = load_tasks()

# Build filter options dynamically
assignees = sorted(a for a in df_all["assignee"].dropna().unique() if a != "")
selected_assignees = st.sidebar.multiselect("Assignees", assignees, default=assignees)
selected_status = st.sidebar.multiselect("Status", STATUSES, default=STATUSES)
selected_priority = st.sidebar.multiselect("Priority", PRIORITIES, default=PRIORITIES)
tag_options = sorted(set(tag for tags in df_all["tags"].dropna() for tag in (tags if isinstance(tags, list) else [])))
selected_tags = st.sidebar.multiselect("Tags", tag_options)

start_min = pd.to_datetime(df_all["start_date"].min()).date() if not df_all.empty else date.today()
due_max = pd.to_datetime(df_all["due_date"].max()).date() if not df_all.empty else date.today()
date_range = st.sidebar.date_input("Date window (start ~ due)", value=(start_min, due_max))

search_text = st.sidebar.text_input("Search in title/description", value="")

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    f = df.copy()
    # Normalize types
    f["start_date"] = pd.to_datetime(f["start_date"]).dt.date
    f["due_date"] = pd.to_datetime(f["due_date"]).dt.date
    if selected_assignees:
        f = f[f["assignee"].isin(selected_assignees)]
    if selected_status:
        f = f[f["status"].isin(selected_status)]
    if selected_priority:
        f = f[f["priority"].isin(selected_priority)]
    if selected_tags:
        f = f[f["tags"].apply(lambda arr: any(t in (arr or []) for t in selected_tags))]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_win, end_win = date_range
        f = f[(f["due_date"] >= start_win) & (f["start_date"] <= end_win)]
    if search_text:
        s = search_text.lower()
        f = f[f["title"].str.lower().str.contains(s) | f["description"].str.lower().str.contains(s)]
    return f

# ---- ADD TASK FORM ----
with st.sidebar.expander("➕ Add task"):
    with st.form("add_task_form", clear_on_submit=True):
        new_id = st.text_input("ID", value=f"T-{len(df_all)+1:03d}")
        new_title = st.text_input("Title", value="")
        new_status = st.selectbox("Status", STATUSES, index=1)
        col1, col2 = st.columns(2)
        with col1:
            new_start = st.date_input("Start date", value=date.today())
        with col2:
            new_due = st.date_input("Due date", value=date.today())
        new_assignee = st.text_input("Assignee", value="")
        new_priority = st.selectbox("Priority", PRIORITIES, index=1)
        new_progress = st.slider("Progress", 0, 100, 0)
        new_tags = st.text_input("Tags (comma-separated)", value="")
        new_depends = st.text_input("Depends on (IDs comma-separated)", value="")
        new_desc = st.text_area("Description", value="")
        submitted = st.form_submit_button("Add")
        if submitted:
            rec = {
                "id": new_id.strip(),
                "title": new_title.strip(),
                "status": new_status,
                "start_date": str(new_start),
                "due_date": str(new_due),
                "assignee": new_assignee.strip(),
                "priority": new_priority,
                "progress": int(new_progress),
                "tags": [t.strip() for t in new_tags.split(",") if t.strip()],
                "description": new_desc.strip(),
                "depends_on": [d.strip() for d in new_depends.split(",") if d.strip()],
            }
            if not rec["id"] or not rec["title"]:
                st.warning("ID and Title are required.")
            elif rec["id"] in df_all["id"].values:
                st.error("ID already exists.")
            else:
                df_all = pd.concat([df_all, pd.DataFrame([rec])], ignore_index=True)
                save_tasks(df_all)
                st.success(f"Added task {rec['id']}")

# ---- MAIN ----
st.title("🗂️ Planning Tasks")
st.caption("Kanban • Timeline • Table • Insights — simple, local, and fast")

tabs = st.tabs(["📋 Board", "🗓️ Timeline", "🧾 Table", "📊 Insights"])

# Filtered view
view_df = apply_filters(df_all)

# ===== Board Tab =====
with tabs[0]:
    st.subheader("Kanban Board")
    cols = st.columns(len(STATUSES))
    for i, status in enumerate(STATUSES):
        with cols[i]:
            st.markdown(f"#### {status}")
            subset = view_df[view_df["status"] == status]
            if subset.empty:
                st.info("No tasks")
            for _, row in subset.sort_values(by=["priority","due_date"]).iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['id']} · {row['title']}**")
                    st.progress(int(row.get("progress", 0)))
                    st.caption(f"👤 {row.get('assignee','') or '-'} · ⏳ {row['start_date']} → {row['due_date']} · 🔖 {', '.join(row.get('tags', []) or [])}")
                    with st.expander("Edit / Move"):
                        # Inline lightweight editor
                        new_status = st.selectbox("Move to", STATUSES, index=STATUSES.index(row["status"]), key=f"mv_{row['id']}")
                        new_progress = st.slider("Progress", 0, 100, int(row.get("progress",0)), key=f"pr_{row['id']}")
                        new_priority = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(row.get("priority","Medium")), key=f"pry_{row['id']}")
                        new_assignee = st.text_input("Assignee", value=row.get("assignee",""), key=f"as_{row['id']}")
                        new_due = st.date_input("Due date", value=pd.to_datetime(row["due_date"]).date(), key=f"due_{row['id']}")
                        upd = st.button("Update", key=f"upd_{row['id']}")
                        if upd:
                            df_all.loc[df_all["id"] == row["id"], ["status","progress","priority","assignee","due_date"]] = [
                                new_status, int(new_progress), new_priority, new_assignee, str(new_due)
                            ]
                            save_tasks(df_all)
                            st.success("Updated")

# ===== Timeline Tab =====
with tabs[1]:
    st.subheader("Timeline (Gantt)")
    if view_df.empty:
        st.info("No tasks to display")
    else:
        gantt = view_df.copy()
        gantt["start"] = pd.to_datetime(gantt["start_date"])
        gantt["end"] = pd.to_datetime(gantt["due_date"])
        gantt["label"] = gantt["id"] + " · " + gantt["title"]
        # Color by status
        chart = alt.Chart(gantt).mark_bar().encode(
            x=alt.X("start:T", title="Start"),
            x2=alt.X2("end:T"),
            y=alt.Y("label:N", title="Task", sort="-x"),
            color=alt.Color("status:N", legend=alt.Legend(title="Status")),
            tooltip=["id","title","assignee","priority","status","start_date","due_date","progress"]
        ).properties(height=max(320, 24*len(gantt)))
        st.altair_chart(chart, use_container_width=True)

# ===== Table Tab =====
with tabs[2]:
    st.subheader("Editable Table")
    st.caption("Use the editor below, then click **Save changes** to persist to tasks.json")
    editable = view_df.copy()
    # Ensure proper dtypes for editor
    editable["tags"] = editable["tags"].apply(lambda x: ", ".join(x or []))
    editable["depends_on"] = editable["depends_on"].apply(lambda x: ", ".join(x or []))
    edited = st.data_editor(
        editable,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "progress": st.column_config.ProgressColumn("progress", min_value=0, max_value=100, format="%d%%"),
            "start_date": st.column_config.DateColumn("start_date"),
            "due_date": st.column_config.DateColumn("due_date"),
        },
        use_container_width=True,
        key="data_editor"
    )
    if st.button("💾 Save changes"):
        # Merge edits back by ID
        df_new = df_all.copy()
        for _, r in edited.iterrows():
            rid = r["id"]
            # Update or insert
            rec = r.to_dict()
            rec["tags"] = [t.strip() for t in (rec.get("tags") or "").split(",") if t.strip()]
            rec["depends_on"] = [t.strip() for t in (rec.get("depends_on") or "").split(",") if t.strip()]
            if (df_new["id"] == rid).any():
                for k, v in rec.items():
                    df_new.loc[df_new["id"] == rid, k] = [v]
            else:
                df_new = pd.concat([df_new, pd.DataFrame([rec])], ignore_index=True)
        save_tasks(df_new)
        st.success("Saved to tasks.json")

# ===== Insights Tab =====
with tabs[3]:
    st.subheader("Insights")
    if view_df.empty:
        st.info("No data")
    else:
        colA, colB, colC = st.columns(3)
        with colA:
            st.metric("Total tasks", len(view_df))
            by_status = view_df.groupby("status")["id"].count().reset_index(name="count")
            chart = alt.Chart(by_status).mark_bar().encode(
                x=alt.X("status:N", sort=STATUSES),
                y="count:Q",
                tooltip=["status","count"]
            ).properties(height=240)
            st.altair_chart(chart, use_container_width=True)
        with colB:
            avg_progress = int(view_df["progress"].astype(int).mean()) if not view_df.empty else 0
            st.metric("Avg. progress", f"{avg_progress}%")
            by_priority = view_df.groupby("priority")["id"].count().reset_index(name="count")
            chart = alt.Chart(by_priority).mark_bar().encode(
                x=alt.X("priority:N", sort=PRIORITIES),
                y="count:Q",
                tooltip=["priority","count"]
            ).properties(height=240)
            st.altair_chart(chart, use_container_width=True)
        with colC:
            overdue = (pd.to_datetime(view_df["due_date"]) < pd.Timestamp.today().normalize()) & (view_df["status"] != "Done")
            st.metric("Overdue", int(overdue.sum()))
            if overdue.any():
                st.write("Overdue list:")
                st.dataframe(view_df.loc[overdue, ["id","title","assignee","due_date","status"]], use_container_width=True)

    st.divider()
    with st.expander("⚠️ Dependency risks"):
        # Simple risk: if a task depends on another that's not Done, flag it.
        risk_rows = []
        ids_to_status = {r["id"]: r["status"] for _, r in df_all.iterrows()}
        for _, r in view_df.iterrows():
            deps = r.get("depends_on", []) or []
            for d in deps:
                if ids_to_status.get(d) != "Done":
                    risk_rows.append({"task": r["id"], "depends_on": d, "dep_status": ids_to_status.get(d, "Missing")})
        if risk_rows:
            st.dataframe(pd.DataFrame(risk_rows), use_container_width=True)
        else:
            st.success("No dependency risks detected.")

st.sidebar.download_button("⬇️ Download tasks.json", data=open(DATA_PATH, "rb"), file_name="tasks.json", mime="application/json")
st.sidebar.caption("Data is stored locally in tasks.json next to this app.")