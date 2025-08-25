# google_cse_search_auto_optimize.py
# Streamlit – Google CSE ONLY + query splitting + Max Request Guard + Auto Optimize
# Jalankan: streamlit run google_cse_search_auto_optimize.py

import re, io, json, math, time
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
import concurrent.futures as futures

import requests, pandas as pd, streamlit as st
from bs4 import BeautifulSoup

APP_TITLE = "Media Crawler - ID"
st.set_page_config(page_title=APP_TITLE, layout="wide")

# =========================
# Helpers
# =========================
def clean_text(x: str) -> str:
    if not x: return ""
    return re.sub(r"\s+", " ", str(x)).strip()

def to_dataframe(items: List[Dict]) -> pd.DataFrame:
    cols = ["title","link","snippet","position","shard_label","shard_start","shard_end",
            "article_title","article_text","article_author","article_published"]
    if not items: return pd.DataFrame(columns=cols)
    df = pd.DataFrame(items)
    for c in cols:
        if c not in df: df[c] = ""
    return df[cols].drop_duplicates(subset=["link"]).reset_index(drop=True)

def export_buttons(df: pd.DataFrame, filename_prefix: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Unduh CSV", csv, f"{filename_prefix}.csv", "text/csv", key="dl_csv")
    try:
        import xlsxwriter
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
            df.to_excel(w, index=False, sheet_name="Results")
        st.download_button("⬇️ Unduh Excel", buf.getvalue(),
            f"{filename_prefix}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_xlsx")
    except Exception:
        st.info("Modul xlsxwriter tidak tersedia. Gunakan CSV atau install xlsxwriter.")

def daterange_chunks(start: date, end: date, granularity: str):
    chunks=[]
    if start>end: return chunks
    if granularity=="Monthly":
        cur=date(start.year,start.month,1)
        while cur<=end:
            nxt=date(cur.year+1,1,1) if cur.month==12 else date(cur.year,cur.month+1,1)
            chunks.append((max(cur,start),min(nxt-timedelta(days=1),end),cur.strftime("%Y-%m")))
            cur=nxt
    elif granularity=="Weekly":
        cur=start
        while cur<=end:
            chunk_end=min(cur+timedelta(days=6),end)
            chunks.append((cur,chunk_end,f"wk_{cur:%Y-%m-%d}"))
            cur=chunk_end+timedelta(days=1)
    else:  # Daily
        cur=start
        while cur<=end:
            chunks.append((cur,cur,f"{cur:%Y-%m-%d}"))
            cur+=timedelta(days=1)
    return chunks

# =========================
# Google CSE
# =========================
def search_cse(api_key,cx,query,num=10,start=1,gl="id",hl="id"):
    url="https://www.googleapis.com/customsearch/v1"
    r=requests.get(url,params={
        "key":api_key,"cx":cx,"q":query,
        "num":min(max(num,1),10),"start":max(start,1),
        "gl":gl,"hl":hl},timeout=25)
    r.raise_for_status()
    data=r.json()
    return [{
        "title":clean_text(it.get("title")),
        "link":it.get("link"),
        "snippet":clean_text(it.get("snippet")),
        "position":i
    } for i,it in enumerate(data.get("items",[]),start=start)]

def search_cse_paginated(api_key,cx,query,total,gl="id",hl="id"):
    total=max(1,min(int(total),100))  # CSE hard cap per query
    collected, start_idx, remain=[],1,total
    while remain>0:
        batch=min(remain,10)
        items=search_cse(api_key,cx,query,num=batch,start=start_idx,gl=gl,hl=hl)
        if not items: break
        collected+=items
        remain-=len(items); start_idx+=len(items)
        time.sleep(0.20)
    return collected

def build_query_with_dates(base,d_start,d_end):
    # before pakai end+1 agar inklusif
    return f"{base.strip()} after:{d_start:%Y-%m-%d} before:{(d_end+timedelta(days=1)):%Y-%m-%d}"

# =========================
# Request & Results Estimator
# =========================
def estimate_calls_and_results(n_shards:int, per_shard_limit:int)->Tuple[int,int]:
    """Return (estimated_calls, estimated_results_cap)."""
    calls = n_shards * math.ceil(per_shard_limit/10.0)
    results_cap = n_shards * per_shard_limit
    return calls, results_cap

def max_per_shard_limit_under_calls(n_shards:int, max_calls:int)->int:
    """Kembalikan limit per shard maksimum (≤100) yang tidak melampaui max_calls."""
    if n_shards<=0: return 0
    k = max_calls // n_shards           # k = max ceil(L/10) yang diperbolehkan
    if k<=0: return 0
    return min(100, 10*k)               # L ≤ 10*k dan ≤100

# =========================
# Article Extraction (optional)
# =========================
def extract_article(url):
    try:
        from newsfetch.news import Newspaper
        n=Newspaper(url=url)
        return {
            "article_title":clean_text(getattr(n,"headline","") or ""),
            "article_text":clean_text(getattr(n,"article","") or ""),
            "article_author":clean_text(", ".join(getattr(n,"authors",[]) or []) or ""),
            "article_published":clean_text(str(getattr(n,"date_publish","")) or "")
        }
    except Exception:
        pass
    # Fallback sederhana
    try:
        r=requests.get(url,timeout=20,headers={"User-Agent":"Mozilla/5.0"})
        if r.ok:
            soup=BeautifulSoup(r.text,"html.parser")
            paras=" ".join(p.get_text() for p in soup.find_all("p"))
            return {
                "article_title":clean_text(soup.title.get_text() if soup.title else ""),
                "article_text":clean_text(paras),
                "article_author":"", "article_published":""
            }
    except Exception:
        pass
    return {"article_title":"","article_text":"","article_author":"","article_published":""}

def enrich_with_articles(items,max_workers=8):
    out=[]
    with futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs={ex.submit(extract_article,it["link"]):it for it in items if it.get("link")}
        for fut,base in futs.items():
            try: base.update(fut.result(timeout=60))
            except Exception: pass
            out.append(base)
    return out

# =========================
# Progress helper
# =========================
def stqdm(iterable,desc="Progress"):
    total=len(iterable)
    prog=st.progress(0,text=f"{desc}: 0/{total}")
    for i,val in enumerate(iterable,1):
        prog.progress(i/total,text=f"{desc}: {i}/{total}")
        yield val
    prog.empty()

# =========================
# Auto Optimize
# =========================
def plan_auto_optimize(start_date:date, end_date:date, target_links:int, max_calls:int):
    """
    Cari kombinasi paling hemat:
      - Coba granularity: Monthly → Weekly → Daily
      - Hitung jumlah shard & limit per shard maksimum yang muat di max_calls
      - Pilih limit minimal yang cukup untuk mencapai target (tanpa melampaui max_calls)
    Return: (granularity, per_shard_limit, n_shards, est_calls, est_results_cap)
    """
    for gran in ["Monthly","Weekly","Daily"]:
        shards = daterange_chunks(start_date, end_date, gran)
        n_shards = len(shards)
        Lmax = max_per_shard_limit_under_calls(n_shards, max_calls)
        if Lmax <= 0:
            continue
        # berapa L minimum agar cap hasil ≥ target?
        L_needed = math.ceil(max(1, target_links) / max(1, n_shards))
        L = min(Lmax, max(10, L_needed))         # ambil minimal yang cukup, tapi ≥10 dan ≤Lmax
        est_calls, est_cap = estimate_calls_and_results(n_shards, L)
        if est_calls <= max_calls and est_cap >= target_links:
            return gran, L, n_shards, est_calls, est_cap
    # jika semua gagal, kembalikan rencana terbaik (maksimal yang muat)
    # pilih granularity dengan est_cap tertinggi tanpa melewati max_calls
    best = None
    for gran in ["Monthly","Weekly","Daily"]:
        shards = daterange_chunks(start_date, end_date, gran)
        n_shards = len(shards)
        Lmax = max_per_shard_limit_under_calls(n_shards, max_calls)
        if Lmax <= 0: continue
        est_calls, est_cap = estimate_calls_and_results(n_shards, Lmax)
        cand = (gran, Lmax, n_shards, est_calls, est_cap)
        if (best is None) or (cand[4] > best[4]):  # bandingkan est_cap
            best = cand
    return best  # bisa None bila max_calls terlalu kecil

def run_split_search(api_key,cx,base_query,start_date,end_date,granularity,per_shard_limit,gl,hl, extract=False, max_workers=8):
    shards = daterange_chunks(start_date, end_date, granularity)
    all_items=[]
    for (s,e,label) in stqdm(shards,"Memproses shard"):
        q=build_query_with_dates(base_query,s,e)
        items=search_cse_paginated(api_key,cx,q,total=per_shard_limit,gl=gl,hl=hl)
        for it in items:
            it.update({"shard_label":label,"shard_start":s.isoformat(),"shard_end":e.isoformat()})
        all_items+=items
    if extract and all_items:
        st.write("📥 Mengekstrak isi artikel…")
        all_items = enrich_with_articles(all_items, max_workers=max_workers)
    return all_items

# =========================
# Session State
# =========================
if "results_df" not in st.session_state: st.session_state.results_df=pd.DataFrame()
if "raw_items" not in st.session_state: st.session_state.raw_items=[]
if "filename_prefix" not in st.session_state: st.session_state.filename_prefix="google_cse_results"

# =========================
# UI
# =========================
st.title(APP_TITLE)
st.caption("Optimasi otomatis untuk mencapai target link dengan request minimal, CSE-only.")

with st.sidebar:
    with st.form("controls"):
        base_query = st.text_input("Kata kunci / operator", value="AI site:kompas.com")
        hl = st.text_input("HL (bahasa)", value="id")
        gl = st.text_input("GL (geo)", value="id")

        st.markdown("---")
        today=date.today()
        start_date = st.date_input("Mulai", value=today - timedelta(days=30))
        end_date   = st.date_input("Selesai", value=today)

        colg1,colg2 = st.columns(2)
        with colg1:
            granularity = st.selectbox("Granularitas", ["Monthly","Weekly","Daily"], index=0)
        with colg2:
            per_shard_limit = st.number_input("Hasil/shard (≤100)", 1, 100, 50)

        st.markdown("---")
        max_calls = st.number_input("Max Request Calls (CSE)", min_value=1, value=300,
            help="Batas jumlah request call CSE. Estimasi tidak boleh melebihi ini.")
        target_links = st.number_input("Target jumlah link", min_value=1, value=1000)

        st.markdown("---")
        extract_articles = st.checkbox("Ekstrak isi artikel (news-fetch)", value=False)
        max_workers = st.slider("Thread ekstraksi", 1, 16, 8)

        st.markdown("---")
        api_key = st.text_input("CSE API Key", type="password")
        cx = st.text_input("CSE cx", type="password")

        # Estimator realtime (untuk setting manual)
        shards_preview = daterange_chunks(start_date, end_date, granularity)
        est_calls_manual, est_results_cap_manual = estimate_calls_and_results(len(shards_preview), per_shard_limit) if shards_preview else (0,0)

        m1,m2,m3 = st.columns(3)
        m1.metric("Jumlah shard", len(shards_preview))
        m2.metric("Estimasi request", est_calls_manual)
        m3.metric("Maks hasil terambil", est_results_cap_manual)

        submitted = st.form_submit_button("Jalankan (Manual)")
        auto_btn  = st.form_submit_button("🚀 Auto Optimize")

# ========== Eksekusi Manual ==========
if submitted:
    if not base_query or not api_key or not cx:
        st.error("Isi **kata kunci, API key, dan CX** terlebih dahulu.")
    else:
        est_calls, _ = estimate_calls_and_results(len(shards_preview), per_shard_limit)
        if est_calls > max_calls:
            st.error(f"Estimasi {est_calls} call > batas {max_calls}. Kurangi rentang, naikkan granularitas, atau kecilkan hasil/shard.")
        else:
            items = run_split_search(api_key,cx,base_query,start_date,end_date,granularity,per_shard_limit,gl,hl, extract_articles, max_workers)
            df = to_dataframe(items)
            st.session_state.results_df, st.session_state.raw_items = df, items
            safe = re.sub(r"\W+","_", f"{base_query}_{start_date}_{end_date}".lower())
            st.session_state.filename_prefix = f"google_cse_manual_{safe}"

# ========== Eksekusi Auto Optimize ==========
if auto_btn:
    if not base_query or not api_key or not cx:
        st.error("Isi **kata kunci, API key, dan CX** terlebih dahulu.")
    else:
        plan = plan_auto_optimize(start_date, end_date, target_links, max_calls)
        if not plan:
            st.error("Tidak ada rencana yang muat di batas request (max_calls terlalu kecil).")
        else:
            gran_opt, L_opt, n_shards, est_calls, est_cap = plan
            st.info(f"Rencana: **{gran_opt}** | hasil/shard **{L_opt}** | shard **{n_shards}** | "
                    f"estimasi request **{est_calls}** | estimasi maksimal hasil **{est_cap}**")
            items = run_split_search(api_key,cx,base_query,start_date,end_date,gran_opt,L_opt,gl,hl, extract_articles, max_workers)
            df = to_dataframe(items)
            st.session_state.results_df, st.session_state.raw_items = df, items
            safe = re.sub(r"\W+","_", f"{base_query}_{start_date}_{end_date}".lower())
            st.session_state.filename_prefix = f"google_cse_auto_{safe}"

# ========== Render hasil ==========
if not st.session_state.results_df.empty:
    df = st.session_state.results_df
    items = st.session_state.raw_items
    st.success(f"Ditemukan {len(df)} link unik dari {len(items)} total hasil (sebelum deduplikasi).")
    st.dataframe(df, use_container_width=True)
    export_buttons(df, st.session_state.filename_prefix)
else:
    st.info("Atur parameter di sidebar lalu klik **Jalankan (Manual)** atau **🚀 Auto Optimize**.")

