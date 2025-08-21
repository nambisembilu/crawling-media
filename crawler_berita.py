# google_search_streamlit.py
# Streamlit app to fetch Google Search results by keyword
# Supports: Google Custom Search JSON API (CSE) and SerpApi
# Usage: streamlit run google_search_streamlit.py

import re
import io
import json
import time
from typing import List, Dict

import requests
import pandas as pd
import streamlit as st

APP_TITLE = "Google Search Link Grabber 🔎"
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
        return pd.DataFrame(columns=["title", "link", "snippet", "source", "position"])
    df = pd.DataFrame(items)
    cols = ["title", "link", "snippet", "source", "position"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    df = df.drop_duplicates(subset=["link"]).reset_index(drop=True)
    return df

def export_buttons(df: pd.DataFrame, filename_prefix: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Unduh CSV", data=csv,
        file_name=f"{filename_prefix}.csv", mime="text/csv")
    try:
        import xlsxwriter
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Results")
        st.download_button("⬇️ Unduh Excel", data=buffer.getvalue(),
            file_name=f"{filename_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception:
        st.info("Modul xlsxwriter tidak tersedia. Gunakan CSV atau install xlsxwriter.")

# ---------------------------
# Providers
# ---------------------------

def search_cse(api_key: str, cx: str, query: str,
               num: int = 10, start: int = 1,
               gl: str = "id", hl: str = "id") -> List[Dict]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": min(max(num, 1), 10),  # max 10 per request
        "start": max(start, 1),
        "gl": gl, "hl": hl,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = []
    for i, it in enumerate(data.get("items", []), start=start):
        items.append({
            "title": clean_text(it.get("title")),
            "link": it.get("link"),
            "snippet": clean_text(it.get("snippet")),
            "source": "CSE",
            "position": i,
        })
    return items

def search_serpapi(api_key: str, query: str,
                   num: int = 10, gl: str = "id", hl: str = "id") -> List[Dict]:
    url = "https://serpapi.com/search.json"
    params = {"engine": "google", "q": query,
              "hl": hl, "gl": gl, "num": num,
              "api_key": api_key}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = []
    for i, it in enumerate(data.get("organic_results", []), start=1):
        items.append({
            "title": clean_text(it.get("title")),
            "link": it.get("link") or it.get("displayed_link"),
            "snippet": clean_text(it.get("snippet")),
            "source": "SerpApi",
            "position": i,
        })
    return items

# ---------------------------
# UI
# ---------------------------

st.title(APP_TITLE)
st.caption("Ambil daftar link dari Google berdasarkan kata kunci. Pilih penyedia: **Google CSE** atau **SerpApi**.")

with st.sidebar:
    st.header("Pengaturan Pencarian")
    provider = st.radio("Penyedia", ["Google CSE", "SerpApi"])
    query = st.text_input("Kata kunci (mis. `pemilu site:kompas.com`)")
    num_results = st.slider("Jumlah hasil", 5, 1000, 10)
    hl = st.text_input("HL (bahasa)", value="id")
    gl = st.text_input("GL (geolokasi)", value="id")

    if provider == "Google CSE":
        api_key = st.text_input("CSE API Key", type="password")
        cx = st.text_input("CSE Search Engine ID (cx)", type="password")
    else:
        serp_key = st.text_input("SerpApi Key", type="password")

    run = st.button("Jalankan Pencarian")

if run:
    if not query:
        st.warning("Masukkan kata kunci terlebih dahulu.")
        st.stop()
    results = []
    if provider == "Google CSE":
        if not api_key or not cx:
            st.error("Isi API Key dan CX dulu.")
            st.stop()
        remaining = num_results
        start = 1
        while remaining > 0:
            batch = min(remaining, 10)
            items = search_cse(api_key, cx, query, num=batch, start=start, gl=gl, hl=hl)
            if not items:
                break
            results.extend(items)
            remaining -= len(items)
            start += len(items)
            time.sleep(0.2)
    else:
        if not serp_key:
            st.error("Isi SerpApi Key dulu.")
            st.stop()
        results = search_serpapi(serp_key, query, num=num_results, gl=gl, hl=hl)

    df = to_dataframe(results)
    st.success(f"Ditemukan {len(df)} hasil")
    st.dataframe(df, use_container_width=True)
    export_buttons(df, filename_prefix=f"google_search_{re.sub(r'\\W+','_',query.lower())}")
    with st.expander("JSON mentah"):
        st.code(json.dumps(results, ensure_ascii=False, indent=2))
else:
    st.info("Masukkan kata kunci, isi API Key, lalu klik **Jalankan Pencarian**.")
