# google_cse_search_split_streamlit.py
# Google CSE ONLY + query splitting by date + AUTO max request guard

import re, io, json, math, time
from datetime import date, timedelta
from typing import List, Dict, Tuple
import concurrent.futures as futures

import requests, pandas as pd, streamlit as st
from bs4 import BeautifulSoup

APP_TITLE = "Google CSE Link Grabber 🔎 — Split by Date + Max Request Guard"
st.set_page_config(page_title=APP_TITLE, layout="wide")

# ----------------- Helpers -----------------

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
    st.download_button("⬇️ CSV", csv, f"{filename_prefix}.csv", "text/csv")
    try:
        import xlsxwriter
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
            df.to_excel(w, index=False, sheet_name="Results")
        st.download_button("⬇️ Excel", buf.getvalue(),
            f"{filename_prefix}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except: pass

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
    else:
        cur=start
        while cur<=end:
            chunks.append((cur,cur,f"{cur:%Y-%m-%d}"))
            cur+=timedelta(days=1)
    return chunks

# ----------------- CSE -----------------

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
    total=max(1,min(int(total),100))
    collected, start_idx, remain=[],1,total
    while remain>0:
        batch=min(remain,10)
        items=search_cse(api_key,cx,query,num=batch,start=start_idx,gl=gl,hl=hl)
        if not items: break
        collected+=items
        remain-=len(items); start_idx+=len(items)
        time.sleep(0.25)
    return collected

def build_query_with_dates(base,d_start,d_end):
    return f"{base.strip()} after:{d_start:%Y-%m-%d} before:{(d_end+timedelta(days=1)):%Y-%m-%d}"

# ----------------- Quota Guard -----------------

def estimate_cse_calls(num_shards, per_shard_limit):
    return num_shards*math.ceil(per_shard_limit/10.0)

# ----------------- Article Extraction -----------------

def extract_article(url):
    try:
        from newsfetch.news import Newspaper
        n=Newspaper(url=url)
        return {
            "article_title":clean_text(getattr(n,"headline","") or ""),
            "article_text":clean_text(getattr(n,"article","") or ""),
            "article_author":", ".join(getattr(n,"authors",[]) or []),
            "article_published":str(getattr(n,"date_publish",""))}
    except: pass
    try:
        r=requests.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
        if r.ok:
            soup=BeautifulSoup(r.text,"html.parser")
            paras=" ".join([p.get_text() for p in soup.find_all("p")])
            return {"article_title":clean_text(soup.title.get_text() if soup.title else ""),
                    "article_text":clean_text(paras),"article_author":"","article_published":""}
    except: pass
    return {"article_title":"","article_text":"","article_author":"","article_published":""}

def enrich_with_articles(items,max_workers=8):
    out=[]
    with futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs={ex.submit(extract_article,it["link"]):it for it in items if it.get("link")}
        for fut,base in futs.items():
            try: base.update(fut.result())
            except: pass
            out.append(base)
    return out

# ----------------- Progress -----------------

def stqdm(iterable,desc="Progress"):
    total=len(iterable); prog=st.progress(0,text=f"{desc}: 0/{total}")
    for i,val in enumerate(iterable,1):
        prog.progress(i/total,text=f"{desc}: {i}/{total}"); yield val
    prog.empty()

# ----------------- Session -----------------

if "results_df" not in st.session_state: st.session_state.results_df=pd.DataFrame()
if "raw_items" not in st.session_state: st.session_state.raw_items=[]
if "filename_prefix" not in st.session_state: st.session_state.filename_prefix="google_cse_split_results"

# ----------------- UI -----------------

st.title(APP_TITLE)
with st.sidebar:
    with st.form("controls"):
        base_query=st.text_input("Kata kunci",value="AI site:kompas.com")
        hl=st.text_input("HL",value="id"); gl=st.text_input("GL",value="id")
        today=date.today()
        start_date=st.date_input("Mulai",value=today-timedelta(days=30))
        end_date=st.date_input("Selesai",value=today)
        granularity=st.selectbox("Shard",["Monthly","Weekly","Daily"])
        per_shard_limit=st.number_input("Hasil per shard",1,100,50)

        # batas request calls
        max_calls=st.number_input("Max Request Calls",min_value=1,value=120,
            help="Batas jumlah request call CSE. Jika estimasi lebih dari ini → error.")

        extract_articles=st.checkbox("Ekstrak artikel",value=False)
        max_workers=st.slider("Thread ekstraksi",1,16,8)

        api_key=st.text_input("CSE API Key",type="password")
        cx=st.text_input("CSE cx",type="password")

        shards_preview=daterange_chunks(start_date,end_date,granularity)
        est_calls=estimate_cse_calls(len(shards_preview),per_shard_limit) if shards_preview else 0
        st.metric("Estimasi panggilan CSE",est_calls)
        submitted=st.form_submit_button("Jalankan")

if submitted:
    shards=daterange_chunks(start_date,end_date,granularity)
    est=estimate_cse_calls(len(shards),per_shard_limit)
    if est>max_calls:
        st.error(f"Estimasi {est} call > Max {max_calls}. Kurangi rentang/per_shard_limit.")
    else:
        all_items=[]
        for (s,e,label) in stqdm(shards,"Shard"):
            q=build_query_with_dates(base_query,s,e)
            items=search_cse_paginated(api_key,cx,q,total=per_shard_limit,gl=gl,hl=hl)
            for it in items: it.update({"shard_label":label,"shard_start":s.isoformat(),"shard_end":e.isoformat()})
            all_items+=items
        if extract_articles: all_items=enrich_with_articles(all_items,max_workers)
        df=to_dataframe(all_items)
        st.session_state.results_df,st.session_state.raw_items=df,all_items
        st.session_state.filename_prefix=f"google_cse_{base_query}_{start_date}_{end_date}".replace(" ","_")

if not st.session_state.results_df.empty:
    df=st.session_state.results_df
    st.success(f"{len(df)} link unik ditemukan")
    st.dataframe(df,use_container_width=True)
    export_buttons(df,st.session_state.filename_prefix)
