# news_crawler_streamlit.py
# Streamlit app to crawl multiple Indonesian news index pages and filter by keyword
# Author: ChatGPT (Satibi's helper)
# Usage: streamlit run news_crawler_streamlit.py

import re
import time
import math
import random
import traceback
import concurrent.futures as futures
from datetime import datetime
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st

# ---------------------------
# HTTP Session & Helpers
# ---------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id,en;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(DEFAULT_HEADERS)
TIMEOUT = 15  # seconds

def safe_get(url: str) -> Optional[requests.Response]:
    try:
        resp = SESSION.get(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp
        return None
    except Exception:
        return None

def clean_text(x: str) -> str:
    if not x:
        return ""
    return re.sub(r"\s+", " ", x).strip()

def kw_match(s: str, kw: str) -> bool:
    return kw.lower() in s.lower()

def polite_delay(min_s=0.3, max_s=0.9):
    time.sleep(random.uniform(min_s, max_s))

# ---------------------------
# Site-specific Parsers
# ---------------------------

def parse_detik_index(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # detik has articles in a list with class 'media__title' or 'list-content__item'
    for a in soup.select("article a, .media__title a, .list-content__item a"):
        href = a.get("href") or ""
        title = clean_text(a.get_text())
        if not href or not title:
            continue
        # Filter out non-article links
        if "news.detik.com" not in href:
            continue
        items.append({"title": title, "url": href})
    # try to fetch timestamps if present
    for card in soup.select("article"):
        a = card.find("a")
        if not a:
            continue
        href = a.get("href") or ""
        if not href:
            continue
        time_el = card.select_one("span, time")
        if time_el:
            ts = clean_text(time_el.get_text())
        else:
            ts = ""
        for it in items:
            if it["url"] == href and "time" not in it:
                it["time"] = ts
    return items

def parse_liputan6_index(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("article a, .articles--rows--item a, .articles--iridescent-list--text-item__title-link"):
        href = card.get("href") or ""
        title = clean_text(card.get_text())
        if not href or not title:
            continue
        if "liputan6.com" not in href:
            continue
        items.append({"title": title, "url": href})
    # timestamps
    for card in soup.select("time, .articles--rows--item time"):
        ts = clean_text(card.get_text())
        # Won't try to map each; leave blank if unknown
    return items

def parse_kompas_index(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # kompas indeks usually has .article__link or .article__list__title
    for a in soup.select("a.article__link, a.article__list__title, .latest__item a, .articleList a"):
        href = a.get("href") or ""
        title = clean_text(a.get_text())
        if not href or not title:
            continue
        if "kompas.com" not in href:
            continue
        # only news site is being indexed (ignore other subdomains if any)
        if not href.startswith("https://www.kompas.com") and not href.startswith("https://kompas.com"):
            continue
        items.append({"title": title, "url": href})
    return items

def parse_cnnindo_index(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # cnn indonesia nasional index: links under .list media rows
    for a in soup.select("h2.title a, article a, .list a"):
        href = a.get("href") or ""
        title = clean_text(a.get_text())
        if not href or not title:
            continue
        if "cnnindonesia.com" not in href:
            continue
        # keep only nasional section
        if "/nasional/" not in href:
            continue
        items.append({"title": title, "url": href})
    return items

def parse_tempoco_index(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.select("h2 a, .archive a, article a"):
        href = a.get("href") or ""
        title = clean_text(a.get_text())
        if not href or not title:
            continue
        if "tempo.co" not in href:
            continue
        # only nasional
        if "/nasional/" not in href:
            continue
        items.append({"title": title, "url": href})
    return items

# ---------------------------
# Pagination Strategies
# ---------------------------
# Each site may use different pagination patterns. We'll try a few common ones safely.
# The crawler will stop early if a page loads but yields zero items.

def paginated_urls(base: str, pages: int, patterns: List[str]) -> List[str]:
    urls = []
    for i in range(1, pages + 1):
        for pat in patterns:
            url = pat.format(base=base.rstrip("/"), i=i)
            urls.append(url)
    # ensure uniqueness while preserving order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

# Best-effort pagination patterns per site (multiple tried per page index)
DETIK_PATS = [
    "{base}?page={i}",
    "{base}/{i}",
    "{base}?i={i}",
]
LIPUTAN6_PATS = [
    "{base}?page={i}",
    "{base}/{i}",
]
KOMPAS_PATS = [
    "{base}?page={i}",
    "{base}/{i}",
]
CNN_PATS = [
    # CNN nasional index often uses .../indeks/{i}
    "{base}/{i}",
    "{base}?page={i}",
]
TEMPO_PATS = [
    "{base}?page={i}",
    "{base}/{i}",
]

# ---------------------------
# Article Body Fetch (optional)
# ---------------------------

def extract_article_text(url: str) -> str:
    resp = safe_get(url)
    if not resp:
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    # Try common article body selectors
    parts = []
    for sel in [
        "article",
        ".detail__body-text",
        ".read__content",
        ".photo__caption",
        ".content",
        ".post-content",
        ".par",
        ".isi",
        ".main-content",
    ]:
        for el in soup.select(sel):
            txt = clean_text(el.get_text(separator=" "))
            if txt and len(txt) > 80:
                parts.append(txt)
    # fallback: all paragraphs
    if not parts:
        ps = [clean_text(p.get_text()) for p in soup.find_all("p")]
        parts.append(" ".join([p for p in ps if p]))
    body = " ".join(parts)
    body = re.sub(r"\s{2,}", " ", body).strip()
    return body

# ---------------------------
# Crawl Routines
# ---------------------------

def crawl_site(base_url: str, site_name: str, pages: int, parser, patterns: List[str], deep_body: bool, kw: str) -> List[Dict]:
    results = []
    urls = paginated_urls(base_url, pages, patterns)
    seen_urls = set()
    for idx, url in enumerate(urls, start=1):
        resp = safe_get(url)
        polite_delay()
        if not resp:
            continue
        try:
            items = parser(resp.text)
        except Exception:
            items = []
        # Early stop if page loads but yields nothing
        if idx > pages and not items:
            break
        for it in items:
            link = it.get("url", "")
            title = it.get("title", "")
            if not link or not title:
                continue
            if link in seen_urls:
                continue
            seen_urls.add(link)
            # keyword filter on title first
            title_match = kw_match(title, kw) if kw else True
            body_text = ""
            body_match = False
            if deep_body and not title_match:
                # fetch article body to check keyword presence
                body_text = extract_article_text(link)
                body_match = kw_match(body_text, kw)
            if kw:
                if not (title_match or body_match):
                    continue
            results.append({
                "site": site_name,
                "title": title,
                "url": link,
                "match": "title" if title_match else ("body" if body_match else ""),
                "time": it.get("time", ""),
                "snippet": (body_text[:200] + "...") if body_text else "",
                "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
    return results

def crawl_all(kw: str, pages: int, sites: List[str], deep_body: bool) -> pd.DataFrame:
    jobs = []
    with futures.ThreadPoolExecutor(max_workers=min(8, len(sites)*2 or 2)) as ex:
        if "Detik" in sites:
            jobs.append(ex.submit(crawl_site, "https://news.detik.com/indeks", "Detik", pages, parse_detik_index, DETIK_PATS, deep_body, kw))
        if "Liputan6" in sites:
            jobs.append(ex.submit(crawl_site, "https://www.liputan6.com/indeks", "Liputan6", pages, parse_liputan6_index, LIPUTAN6_PATS, deep_body, kw))
        if "Kompas" in sites:
            jobs.append(ex.submit(crawl_site, "https://indeks.kompas.com", "Kompas", pages, parse_kompas_index, KOMPAS_PATS, deep_body, kw))
        if "CNN Indonesia (Nasional)" in sites:
            jobs.append(ex.submit(crawl_site, "https://www.cnnindonesia.com/nasional/indeks", "CNN Indonesia", pages, parse_cnnindo_index, CNN_PATS, deep_body, kw))
        if "Tempo (Nasional)" in sites:
            jobs.append(ex.submit(crawl_site, "https://www.tempo.co/indeks", "Tempo", pages, parse_tempoco_index, TEMPO_PATS, deep_body, kw))
        results = []
        for job in futures.as_completed(jobs):
            try:
                results.extend(job.result())
            except Exception as e:
                st.warning(f"Gagal pada salah satu situs: {e}")
    if not results:
        return pd.DataFrame(columns=["site","title","url","match","time","snippet","crawled_at"])
    df = pd.DataFrame(results).drop_duplicates(subset=["url"]).reset_index(drop=True)
    return df

# ---------------------------
# Streamlit UI
# ---------------------------

st.set_page_config(page_title="Crawler Indeks Berita 🇮🇩", layout="wide")

st.title("Crawler Indeks Berita 🇮🇩")
st.caption("Detik, Liputan6, Kompas, CNN Indonesia (Nasional), Tempo (Nasional) — filter berdasarkan kata kunci.")

with st.sidebar:
    st.header("Pengaturan")
    kw = st.text_input("Kata Kunci (contoh: 'pemilu', 'AI', 'pendidikan')", value="")
    pages = st.slider("Jumlah halaman per situs (best effort)", min_value=1, max_value=5, value=2, help="Coba beberapa pola pagination umum; akan berhenti jika kosong.")
    deep_body = st.checkbox("Cari juga di isi artikel (lebih lambat)", value=False)
    site_opts = [
        "Detik", "Liputan6", "Kompas", "CNN Indonesia (Nasional)", "Tempo (Nasional)"
    ]
    selected_sites = st.multiselect("Pilih situs", site_opts, default=site_opts)

    run_btn = st.button("Jalankan Crawler")

st.markdown("> **Catatan:** Pola pagination setiap situs bisa berubah. Aplikasi ini mencoba beberapa pola umum dan berhenti jika halaman kosong.")

if run_btn:
    if not kw:
        st.warning("Masukkan kata kunci terlebih dahulu.")
        st.stop()
    with st.spinner("Mengambil data..."):
        df = crawl_all(kw, pages, selected_sites, deep_body)
    st.success(f"Selesai. Ditemukan {len(df)} data.")
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        # Download buttons
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Unduh CSV", data=csv, file_name=f"hasil_crawl_{re.sub(r'\\W+','_',kw.lower())}.csv", mime="text/csv")

        try:
            import io
            import xlsxwriter
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Data")
            st.download_button("Unduh Excel", data=output.getvalue(), file_name=f"hasil_crawl_{re.sub(r'\\W+','_',kw.lower())}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception:
            st.info("Modul xlsxwriter tidak tersedia. Gunakan CSV atau install xlsxwriter.")
else:
    st.info("Masukkan kata kunci, pilih situs, lalu klik **Jalankan Crawler**.")

