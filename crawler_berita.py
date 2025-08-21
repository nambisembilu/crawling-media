# google_cse_search_split_streamlit.py
# Streamlit app to fetch Google Search results using ONLY Google Custom Search JSON API (CSE)
# with query splitting by date ranges (before:/after:). Results are persisted in session_state
# so UI doesn't clear when clicking download buttons.

import re
import io
import json
import time
from datetime import date, timedelta
from typing import List, Dict, Tuple

import requests
import pandas as pd
import streamlit as st

APP_TITLE = "Google CSE Link Grabber 🔎 — Query Splitting (by date ranges)"
st.set_page_config(page_title=APP_TITLE, layout="wide")

# ---------------------------
# Helpers
# ---------------------------

def clean_text(x: str) -> str:
    if not x:
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()

def to_dataframe(items: List[Dict]) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=["title", "link", "snippet", "position", "shard_label", "shard_start", "shard_end"])
    df = pd.DataFrame(items)
    cols = ["title", "link", "snippet", "position", "shard_label", "shard_start", "shard_end"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    df = df.drop_duplicates(subset=["link"]).reset_index(drop=True)
    return df

def export_buttons(df: pd.DataFrame, filename_prefix: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Unduh CSV", data=csv,
        file_name=f"{filename_prefix}.csv", mime="text/csv", key="download_csv")
    try:
        import xlsxwriter
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Results")
        st.download_button("⬇️ Unduh Excel", data=buffer.getvalue(),
            file_name=f"{filename_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_xlsx")
    except Exception:
        st.info("Modul xlsxwriter tidak tersedia. Gunakan CSV atau install xlsxwriter.")

def daterange_chunks(start: date, end: date, granularity: str) -> List[Tuple[date, date, str]]:
    chunks = []
    if start > end:
        return chunks
    if granularity == "Monthly":
        cur = date(start.year, start.month, 1)
        while cur <= end:
            if cur.month == 12:
                nxt = date(cur.year + 1, 1, 1)
            else:
                nxt = date(cur.year, cur.month + 1, 1)
            chunk_start = max(cur, start)
            chunk_end = min(nxt - timedelta(days=1), end)
            label = cur.strftime("%Y-%m")
            chunks.append((chunk_start, chunk_end, label))
            cur = nxt
    elif granularity == "Weekly":
        cur = start
        while cur <= end:
            chunk_start = cur
            chunk_end = min(cur + timedelta(days=6), end)
            label = f"wk_{chunk_start.strftime('%Y-%m-%d')}"
            chunks.append((chunk_start, chunk_end, label))
            cur = chunk_end + timedelta(days=1)
    else:  # Daily
        cur = start
        while cur <= end:
            chunk_start = cur
            chunk_end = cur
            label = cur.strftime("%Y-%m-%d")
            chunks.append((chunk_start, chunk_end, label))
            cur = cur + timedelta(days=1)
    return chunks

# ---------------------------
# Google CSE
# ---------------------------

def search_cse(api_key: str, cx: str, query: str, num: int = 10, start: int = 1,
               gl: str = "id", hl: str = "id") -> List[Dict]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key, "cx": cx, "q": query,
        "num": min(max(num, 1), 10),
        "start": max(start, 1),
        "gl": gl, "hl": hl,
    }
    r = requests.get(url, params=params, timeout=25)
    if r.status_code != 200:
        raise RuntimeError(f"CSE error {r.status_code}: {r.text[:200]}")
    data = r.json()
    items = []
    for i, it in enumerate(data.get("items", []), start=start):
        items.append({
            "title": clean_text(it.get("title")),
            "link": it.get("link"),
            "snippet": clean_text(it.get("snippet")),
            "position": i,
        })
    return items

def search_cse_paginated(api_key: str, cx: str, query: str, total: int,
                         gl: str = "id", hl: str = "id") -> List[Dict]:
    total = max(1, min(int(total), 100))
    collected = []
    start_idx, remaining = 1, total
    while remaining > 0:
        batch = min(remaining, 10)
        items = search_cse(api_key, cx, query, num=batch, start=start_idx, gl=gl, hl=hl)
        if not items:
            break
        collected.extend(items)
        remaining -= len(items)
        start_idx += len(items)
        time.sleep(0.25)
    return collected

def build_query_with_dates(base_query: str, d_start: date, d_end: date) -> str:
    qs = base_query.strip()
    qs += f' after:{d_start.strftime("%Y-%m-%d")} before:{(d_end + timedelta(days=1)).strftime("%Y-%m-%d")}'
    return qs

def run_split_search(api_key: str, cx: str, base_query: str,
                     start_date: date, end_date: date,
                     granularity: str, per_shard_limit: int,
                     gl: str, hl: str) -> List[Dict]:
    shards = daterange_chunks(start_date, end_date, granularity)
    all_items: List[Dict] = []
    for (s, e, label) in stqdm(shards, desc="Memproses shard tanggal"):
        q = build_query_with_dates(base_query, s, e)
        items = search_cse_paginated(api_key, cx, q, total=per_shard_limit, gl=gl, hl=hl)
        for it in items:
            it["shard_label"] = label
            it["shard_start"] = s.isoformat()
            it["shard_end"] = e.isoformat()
        all_items.extend(items)
    return all_items

# ---------------------------
# Simple tqdm for Streamlit
# ---------------------------

def stqdm(iterable, desc="Progress"):
    total = len(iterable)
    progress = st.progress(0, text=f"{desc}: 0/{total}")
    for i, val in enumerate(iterable, start=1):
        progress.progress(i/total, text=f"{desc}: {i}/{total}")
        yield val
    progress.empty()

# ---------------------------
# State init
# ---------------------------

if "results_df" not in st.session_state:
    st.session_state.results_df = pd.DataFrame()
if "raw_items" not in st.session_state:
    st.session_state.raw_items = []
if "filename_prefix" not in st.session_state:
    st.session_state.filename_prefix = "google_cse_split_results"

# ---------------------------
# UI
# ---------------------------

st.title(APP_TITLE)
st.caption("Ambil lebih dari 100 hasil dengan memecah query per rentang tanggal.")

with st.sidebar:
    with st.form("controls"):
        base_query = st.text_input("Kata kunci (mis. `AI site:kompas.com`)")
        hl = st.text_input("HL (bahasa)", value="id")
        gl = st.text_input("GL (geo)", value="id")
        start_date = st.date_input("Mulai", value=date.today() - timedelta(days=30))
        end_date = st.date_input("Selesai", value=date.today())
        granularity = st.selectbox("Granularitas", ["Monthly","Weekly","Daily"], index=0)
        per_shard_limit = st.number_input("Maks hasil/shard (≤100)", 1, 100, 50)
        api_key = st.text_input("CSE API Key", type="password")
        cx = st.text_input("CSE Search Engine ID (cx)", type="password")
        submitted = st.form_submit_button("Jalankan Pencarian")

if submitted:
    if base_query and api_key and cx and start_date <= end_date:
        items = run_split_search(api_key, cx, base_query, start_date, end_date,
                                 granularity, per_shard_limit, gl, hl)
        df = to_dataframe(items)
        st.session_state.results_df = df
        st.session_state.raw_items = items
        safe_name = re.sub(r"\W+", "_", f"{base_query}_{start_date}_{end_date}".lower())
        st.session_state.filename_prefix = f"google_cse_split_{safe_name}"

if not st.session_state.results_df.empty:
    df, items = st.session_state.results_df, st.session_state.raw_items
    st.success(f"Selesai. Ditemukan {len(df)} link unik dari {len(items)} total hasil.")
    st.dataframe(df, use_container_width=True)
    export_buttons(df, filename_prefix=st.session_state.filename_prefix)
    with st.expander("JSON mentah"):
        st.code(json.dumps(items, ensure_ascii=False, indent=2))
else:
    st.info("Isi kata kunci, rentang tanggal, API key & CX, lalu klik **Jalankan Pencarian**.")
