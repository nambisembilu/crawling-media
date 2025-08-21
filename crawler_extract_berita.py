# google_cse_search_split_streamlit.py
# Streamlit app – Google CSE ONLY + query splitting by date + quota estimator + article extraction (news-fetch)
# Jalankan: streamlit run google_cse_search_split_streamlit.py

import re
import io
import json
import math
import time
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
import concurrent.futures as futures

import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

APP_TITLE = "Google CSE Link Grabber 🔎 — Split by Date + Article Extract"
st.set_page_config(page_title=APP_TITLE, layout="wide")

# =========================
# Helpers
# =========================

def clean_text(x: str) -> str:
    if not x:
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()

def to_dataframe(items: List[Dict]) -> pd.DataFrame:
    cols = ["title","link","snippet","position","shard_label","shard_start","shard_end",
            "article_title","article_text","article_author","article_published"]
    if not items:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(items)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    # dedup by link
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
    """Split [start, end] inclusive menjadi shard: Monthly / Weekly / Daily."""
    chunks = []
    if start > end:
        return chunks
    if granularity == "Monthly":
        cur = date(start.year, start.month, 1)
        while cur <= end:
            nxt = date(cur.year + 1, 1, 1) if cur.month == 12 else date(cur.year, cur.month + 1, 1)
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
            label = cur.strftime("%Y-%m-%d")
            chunks.append((cur, cur, label))
            cur = cur + timedelta(days=1)
    return chunks

# =========================
# Google CSE (JSON API)
# =========================

def search_cse(api_key: str, cx: str, query: str, num: int = 10, start: int = 1, gl: str = "id", hl: str = "id") -> List[Dict]:
    """Ambil max 10 hasil untuk satu halaman CSE."""
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

def search_cse_paginated(api_key: str, cx: str, query: str, total: int, gl: str = "id", hl: str = "id") -> List[Dict]:
    """Paginate hingga 100 hasil (limit Google CSE per query)."""
    total = max(1, min(int(total), 100))
    collected, start_idx, remaining = [], 1, total
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
    """Tambahkan operator after:/before: (before pakai end+1 agar inklusif)."""
    return f"{base_query.strip()} after:{d_start:%Y-%m-%d} before:{(d_end + timedelta(days=1)):%Y-%m-%d}"

# =========================
# Estimator Kuota (CSE)
# =========================

def estimate_cse_calls(num_shards: int, per_shard_limit: int) -> int:
    """CSE: 1 panggilan per 10 hasil (dibulatkan ke atas)."""
    per_shard_calls = math.ceil(per_shard_limit / 10.0)
    return num_shards * per_shard_calls

# =========================
# Ekstraksi Artikel (news-fetch)
# =========================

def extract_article_newsfetch(url: str) -> Dict[str, str]:
    """
    Gunakan 'news-fetch' bila tersedia:
      from newsfetch.news import Newspaper
      news = Newspaper(url='...')
      Ambil: headline (title), article (full text), authors, date_publish
    Fallback ke requests+BS4 bila gagal.
    """
    # Coba import bentuk kelas (sesuai dokumentasi PyPI terbaru)
    news = None
    try:
        from newsfetch.news import Newspaper
        news = Newspaper(url=url)  # :contentReference[oaicite:0]{index=0}
        title = clean_text(getattr(news, "headline", "") or "")
        text = clean_text(getattr(news, "article", "") or "")
        authors = clean_text(", ".join(getattr(news, "authors", []) or []) or "")
        published = clean_text(str(getattr(news, "date_publish", "")) or "")
        if text or title:
            return {"article_title": title, "article_text": text, "article_author": authors, "article_published": published}
    except Exception:
        pass

    # Beberapa referensi lama menunjukkan fungsi lowercase `newspaper(url)`:
    try:
        from newsfetch.news import newspaper  # historic variant :contentReference[oaicite:1]{index=1}
        news = newspaper(url)
        # best-effort mapping
        title = clean_text(getattr(news, "headline", "") or getattr(news, "title", "") or "")
        text = clean_text(getattr(news, "article", "") or getattr(news, "text", "") or "")
        authors = clean_text(", ".join(getattr(news, "authors", []) or []) or "")
        published = clean_text(str(getattr(news, "date_publish", "")) or "")
        if text or title:
            return {"article_title": title, "article_text": text, "article_author": authors, "article_published": published}
    except Exception:
        pass

    # Fallback sederhana
    try:
        resp = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            title = clean_text(soup.title.get_text() if soup.title else "")
            paras = [clean_text(p.get_text()) for p in soup.find_all("p")]
            text = clean_text(" ".join([p for p in paras if p]))
            return {"article_title": title, "article_text": text, "article_author": "", "article_published": ""}
    except Exception:
        pass
    return {"article_title": "", "article_text": "", "article_author": "", "article_published": ""}

def enrich_with_articles(items: List[Dict], max_workers: int = 8) -> List[Dict]:
    """Ambil isi artikel paralel (hati-hati rate-limit situs berita)."""
    if not items:
        return items
    out = []
    with futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(extract_article_newsfetch, it["link"]): it for it in items if it.get("link")}
        for i, (fut, base) in enumerate(zip(futs.keys(), futs.values()), start=1):
            try:
                extra = fut.result(timeout=60)
                base.update(extra)
            except Exception:
                # jika error ekstraksi, tetap kembalikan record dasarnya
                pass
            out.append(base)
    return out

# =========================
# Streamlit Progress Helper
# =========================

def stqdm(iterable, desc="Progress"):
    total = len(iterable)
    try:
        prog = st.progress(0, text=f"{desc}: 0/{total}")
        use_text = True
    except TypeError:
        status = st.empty()
        prog = st.progress(0)
        status.write(f"{desc}: 0/{total}")
        use_text = False
    for i, val in enumerate(iterable, start=1):
        if use_text:
            prog.progress(i/total, text=f"{desc}: {i}/{total}")
        else:
            status.write(f"{desc}: {i}/{total}")
            prog.progress(i/total)
        yield val
    try:
        prog.empty()
    except Exception:
        pass

# =========================
# Session State
# =========================

if "results_df" not in st.session_state:
    st.session_state.results_df = pd.DataFrame()
if "raw_items" not in st.session_state:
    st.session_state.raw_items = []
if "filename_prefix" not in st.session_state:
    st.session_state.filename_prefix = "google_cse_split_results"

# =========================
# UI
# =========================

st.title(APP_TITLE)
st.caption("Pecah pencarian per tanggal (Daily/Weekly/Monthly), estimasi kuota CSE, dan ekstraksi isi artikel via news-fetch.")

with st.sidebar:
    with st.form("controls"):
        base_query = st.text_input("Kata kunci / operator", value="AI site:kompas.com")
        col1, col2 = st.columns(2)
        with col1:
            hl = st.text_input("HL (bahasa)", value="id")
        with col2:
            gl = st.text_input("GL (geo)", value="id")

        st.markdown("---")
        st.subheader("Rentang Tanggal")
        today = date.today()
        start_date = st.date_input("Mulai", value=today - timedelta(days=30))
        end_date = st.date_input("Selesai", value=today)
        granularity = st.selectbox("Granularitas shard", ["Monthly","Weekly","Daily"], index=0)

        st.markdown("---")
        per_shard_limit = st.number_input("Maks hasil per shard (≤100)", 1, 100, 50)
        extract_articles = st.checkbox("Ekstrak isi artikel (news-fetch)", value=False, help="Akan menambah banyak request ke situs berita")
        max_workers = st.slider("Paralel ekstraksi (thread)", 1, 16, 8, help="Kurangi jika sering diblokir situs")

        st.markdown("---")
        api_key = st.text_input("CSE API Key", type="password")
        cx = st.text_input("CSE Search Engine ID (cx)", type="password")

        # Estimator kuota (hanya hitung; tidak memanggil API)
        if base_query and start_date <= end_date:
            shards = daterange_chunks(start_date, end_date, granularity)
            estimated_calls = estimate_cse_calls(len(shards), per_shard_limit)
            st.info(f"📊 Estimasi panggilan CSE: **{estimated_calls} call** "
                    f"(shards={len(shards)} × ceil({per_shard_limit}/10))")
        submitted = st.form_submit_button("Jalankan Pencarian")

st.markdown("""
**Cara kerja**
- Pecah rentang tanggal menjadi shard; tiap shard ditambah `after:` dan `before:`.
- Setiap shard ambil ≤100 hasil (CSE limit).  
- Estimasi kuota = jumlah shard × ceil(per_shard_limit / 10).  
- Opsi tambahan mengekstrak isi artikel memakai **news-fetch** (fallback BeautifulSoup).
""")

# Eksekusi
if submitted:
    if not base_query:
        st.warning("Masukkan kata kunci terlebih dahulu.")
    elif not api_key or not cx:
        st.error("Isi **CSE API Key** dan **CX** terlebih dahulu.")
    elif start_date > end_date:
        st.error("Tanggal mulai tidak boleh melebihi tanggal selesai.")
    else:
        shards = daterange_chunks(start_date, end_date, granularity)
        all_items: List[Dict] = []

        # Crawl per shard dengan progress
        for (s, e, label) in stqdm(shards, desc="Memproses shard tanggal"):
            q = build_query_with_dates(base_query, s, e)
            items = search_cse_paginated(api_key, cx, q, total=per_shard_limit, gl=gl or "id", hl=hl or "id")
            for it in items:
                it["shard_label"] = label
                it["shard_start"] = s.isoformat()
                it["shard_end"] = e.isoformat()
            all_items.extend(items)

        if extract_articles and all_items:
            st.write("📥 Mengekstrak isi artikel (ini bisa agak lama)…")
            all_items = enrich_with_articles(all_items, max_workers=max_workers)

        df = to_dataframe(all_items)

        # Persist
        st.session_state.results_df = df
        st.session_state.raw_items = all_items
        safe_name = re.sub(r"\W+", "_", f"{base_query}_{start_date}_{end_date}".lower())
        st.session_state.filename_prefix = f"google_cse_split_{safe_name}"

# Render hasil
if not st.session_state.results_df.empty:
    df, items = st.session_state.results_df, st.session_state.raw_items
    st.success(f"Selesai. Ditemukan {len(df)} link unik dari {len(items)} total hasil (sebelum deduplikasi).")
    st.dataframe(df, use_container_width=True)
    export_buttons(df, filename_prefix=st.session_state.filename_prefix)

    with st.expander("JSON mentah"):
        st.code(json.dumps(items, ensure_ascii=False, indent=2))
else:
    st.info("Isi keyword, API key & CX, set tanggal, lalu klik **Jalankan Pencarian**.")

