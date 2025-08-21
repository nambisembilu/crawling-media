# google_cse_search_streamlit.py
# Streamlit app to fetch Google Search results using ONLY Google Custom Search JSON API (CSE)
# Usage: streamlit run google_cse_search_streamlit.py

import re
import io
import json
import time
from typing import List, Dict

import requests
import pandas as pd
import streamlit as st

APP_TITLE = "Google CSE Link Grabber 🔎 (Only CSE)"
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
        return pd.DataFrame(columns=["title", "link", "snippet", "position"])
    df = pd.DataFrame(items)
    cols = ["title", "link", "snippet", "position"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
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
    r = requests.get(url, params=params, timeout=20)
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
    """Paginate CSE requests up to 100 results (Google limit)."""
    total = max(1, min(int(total), 100))  # hard cap at 100
    collected = []
    start = 1
    remaining = total
    while remaining > 0:
        batch = min(remaining, 10)
        items = search_cse(api_key, cx, query, num=batch, start=start, gl=gl, hl=hl)
        if not items:
            break
        collected.extend(items)
        remaining -= len(items)
        start += len(items)
        time.sleep(0.2)  # polite delay
    return collected

# ---------------------------
# UI
# ---------------------------

st.title(APP_TITLE)
st.caption("Ambil daftar link dari Google menggunakan **Google Custom Search JSON API (CSE)** saja.")

with st.sidebar:
    st.header("Pengaturan Pencarian")
    query = st.text_input("Kata kunci / operator (mis. `pemilu site:kompas.com`)")
    num_results = st.number_input("Jumlah hasil (maks 100)", min_value=1, max_value=500, value=20, step=1)
    hl = st.text_input("HL (bahasa)", value="id")
    gl = st.text_input("GL (geolokasi)", value="id")
    st.markdown("---")
    api_key = st.text_input("CSE API Key", type="password")
    cx = st.text_input("CSE Search Engine ID (cx)", type="password")
    st.markdown("---")
    run = st.button("Jalankan Pencarian")

st.markdown("""
**Tips Keyword**
- Batasi domain: `site:kompas.com`, `site:detik.com`
- Cocokkan frasa: gunakan kutip dua, mis. `"kecerdasan buatan"`
- Kecualikan istilah: `-hoaks`
""")

if run:
    if not query:
        st.warning("Masukkan kata kunci terlebih dahulu.")
        st.stop()
    if not api_key or not cx:
        st.error("Isi **CSE API Key** dan **CX** terlebih dahulu.")
        st.stop()

    try:
        results = search_cse_paginated(api_key, cx, query, total=num_results, gl=gl or "id", hl=hl or "id")
        df = to_dataframe(results)
        st.success(f"Berhasil! Ditemukan {len(df)} hasil.")
        if df.empty:
            st.stop()
        st.dataframe(df, use_container_width=True)
        export_buttons(df, filename_prefix=f"google_cse_{re.sub(r'\\W+','_',query.lower())}")
        with st.expander("Lihat JSON mentah"):
            st.code(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as e:
        st.error(f"Gagal mengambil hasil: {e}")
        st.stop()
else:
    st.info("Masukkan kata kunci, isi API key & CX, lalu klik **Jalankan Pencarian**.")
