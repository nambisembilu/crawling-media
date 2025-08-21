# google_cse_search_split_streamlit.py
# Streamlit app to fetch Google Search results using ONLY Google Custom Search JSON API (CSE)
# with query splitting by date ranges (before:/after:).
# Usage: streamlit run google_cse_search_split_streamlit.py

import re
import io
import json
import time
import math
from datetime import datetime, date, timedelta
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
    # de-duplicate by link
    df = df.drop_duplicates(subset=["link"]).reset_index(drop=True)
    return df

def export_buttons(df: pd.DataFrame, filename_prefix: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Unduh CSV",
        data=csv,
        file_name=f"{filename_prefix}.csv",
        mime="text/csv",
    )
    try:
        import xlsxwriter
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Results")
        st.download_button(
            "⬇️ Unduh Excel",
            data=buffer.getvalue(),
            file_name=f"{filename_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception:
        st.info("Modul xlsxwriter tidak tersedia. Gunakan CSV atau install xlsxwriter.")

def daterange_chunks(start: date, end: date, granularity: str) -> List[Tuple[date, date, str]]:
    """Split [start, end] into ranges by granularity: 'Monthly', 'Weekly', or 'Daily'.
       Returns list of (chunk_start, chunk_end, label). chunk_end is inclusive.
    """
    chunks = []
    if start > end:
        return chunks
    if granularity == "Monthly":
        cur = date(start.year, start.month, 1)
        while cur <= end:
            # end of month
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
        # week chunks starting on start's day
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

def search_cse(api_key: str, cx: str, query: str, num: int = 10, start: int = 1, gl: str = "id", hl: str = "id") -> List[Dict]:
    """Fetch up to 10 results for a given page using Google CSE"""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": min(max(num, 1), 10),  # Google CSE: 1..10 per request
        "start": max(start, 1),
        "gl": gl,
        "hl": hl,
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

def search_cse_paginated(api_key: str, cx: str, query: str, total: int, gl: str = "id", hl: str = "id") -> List[Dict]:
    """Paginate CSE requests up to 100 results (Google limit per query)."""
    total = max(1, min(int(total), 100))  # hard cap at 100
    collected = []
    start_idx = 1
    remaining = total
    while remaining > 0:
        batch = min(remaining, 10)
        items = search_cse(api_key, cx, query, num=batch, start=start_idx, gl=gl, hl=hl)
        if not items:
            break
        collected.extend(items)
        remaining -= len(items)
        start_idx += len(items)
        time.sleep(0.25)  # polite delay
    return collected

def build_query_with_dates(base_query: str, d_start: date, d_end: date) -> str:
    """Use Google's before:/after: operators. Inclusive range."""
    # Format YYYY-MM-DD
    qs = base_query.strip()
    qs += f' after:{d_start.strftime("%Y-%m-%d")} before:{(d_end + timedelta(days=1)).strftime("%Y-%m-%d")}'
    return qs

def run_split_search(api_key: str, cx: str, base_query: str, start_date: date, end_date: date,
                     granularity: str, per_shard_limit: int, gl: str, hl: str) -> List[Dict]:
    shards = daterange_chunks(start_date, end_date, granularity)
    all_items: List[Dict] = []
    for (s, e, label) in stqdm(shards, desc="Memproses shard tanggal"):
        q = build_query_with_dates(base_query, s, e)
        items = search_cse_paginated(api_key, cx, q, total=per_shard_limit, gl=gl, hl=hl)
        # attach shard info
        for it in items:
            it["shard_label"] = label
            it["shard_start"] = s.isoformat()
            it["shard_end"] = e.isoformat()
        all_items.extend(items)
    return all_items

# ---------------------------
# Simple tqdm for Streamlit
# ---------------------------

from contextlib import contextmanager

@contextmanager
def stqdm(iterable, desc="Progress"):
    total = len(iterable)
    progress = st.progress(0, text=f"{desc}: 0/{total}")
    try:
        for i, val in enumerate(iterable, start=1):
            yield val
            progress.progress(i/total, text=f"{desc}: {i}/{total}")
    finally:
        progress.empty()

# ---------------------------
# UI
# ---------------------------

st.title(APP_TITLE)
st.caption("Ambil lebih dari 100 hasil **dengan memecah query per rentang tanggal** (harian/mingguan/bulanan). Setiap shard (rentang) bisa mengambil hingga 100 hasil (limit Google CSE per query).")

with st.sidebar:
    st.header("Pengaturan Pencarian")
    base_query = st.text_input("Kata kunci / operator (mis. `AI site:kompas.com`)")
    colq1, colq2 = st.columns(2)
    with colq1:
        hl = st.text_input("HL (bahasa)", value="id")
    with colq2:
        gl = st.text_input("GL (geolokasi)", value="id")

    st.markdown("---")
    st.subheader("Rentang Tanggal")
    today = date.today()
    default_start = today.replace(day=1) - timedelta(days=30)  # default: kira-kira 2 bulan terakhir
    start_date = st.date_input("Mulai", value=default_start)
    end_date = st.date_input("Selesai", value=today)
    granularity = st.selectbox("Granularitas shard", ["Monthly", "Weekly", "Daily"], index=0, help="Semakin kecil (Daily) semakin banyak shard dan request.")

    st.markdown("---")
    per_shard_limit = st.number_input("Maks hasil per shard (cap 100)", min_value=1, max_value=100, value=50, step=1, help="Google CSE maksimal 100 per query.")
    st.caption("Total hasil ≈ jumlah_shard × per_shard_limit (setelah deduplikasi bisa berkurang).")

    st.markdown("---")
    api_key = st.text_input("CSE API Key", type="password")
    cx = st.text_input("CSE Search Engine ID (cx)", type="password")

    run = st.button("Jalankan Pencarian")

st.markdown("""
**Cara kerja**
- Aplikasi memecah rentang tanggal menjadi **shard** (harian/mingguan/bulanan).
- Untuk setiap shard, query ditambah operator: `after:YYYY-MM-DD before:YYYY-MM-DD`.
- Tiap shard diambil maksimal *per_shard_limit* hasil (maks 100).  
- Semua hasil digabung lalu di-*deduplicate* berdasarkan link.
""")

if run:
    if not base_query:
        st.warning("Masukkan kata kunci terlebih dahulu.")
        st.stop()
    if not api_key or not cx:
        st.error("Isi **CSE API Key** dan **CX** terlebih dahulu.")
        st.stop()
    if start_date > end_date:
        st.error("Tanggal mulai tidak boleh melebihi tanggal selesai.")
        st.stop()

    with st.spinner("Mengambil data..."):
        items = run_split_search(api_key, cx, base_query, start_date, end_date, granularity, per_shard_limit, gl or "id", hl or "id")
        df = to_dataframe(items)

    st.success(f"Selesai. Ditemukan {len(df)} link unik dari {len(items)} total hasil (sebelum deduplikasi).")
    st.dataframe(df, use_container_width=True)

    # Export
    if not df.empty:
        safe_name = re.sub(r"\W+", "_", f"{base_query}_{start_date}_{end_date}".lower())
        export_buttons(df, filename_prefix=f"google_cse_split_{safe_name}")

    with st.expander("Lihat JSON mentah"):
        st.code(json.dumps(items, ensure_ascii=False, indent=2))
else:
    st.info("Isi kata kunci, rentang tanggal, API key & CX, lalu klik **Jalankan Pencarian**.")
