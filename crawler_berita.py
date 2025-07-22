import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
import datetime

# --- API Key NewsData.io ---
NEWSDATA_API_KEY = "ISI_API_KEY_ANDA"

st.set_page_config(page_title="Crawler Berita 🇮🇩", layout="wide")

# --- Tailwind-like Header ---
st.markdown("""
<div style="padding: 1rem; background: #1f2937; color: white; border-radius: 0.5rem; margin-bottom: 2rem;">
  <h1 style="font-size: 2rem; font-weight: bold;">📰 Crawler Berita Indonesia</h1>
  <p style="margin: 0.5rem 0 0;">Cari berita dari berbagai portal menggunakan kata kunci</p>
</div>
""", unsafe_allow_html=True)

# --- Keyword Input ---
col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("🔎 Kata Kunci", placeholder="misalnya: ekonomi pangan", value="ekonomi pangan")
with col2:
    run = st.button("🚀 Jalankan")

# --- Functions ---
def fetch_from_newsdata(keyword):
    url = f"https://newsdata.io/api/1/news?apikey=pub_bac20c629fae4bcf8aec74e5d99a2deb&country=id&language=id&q={keyword}"
    response = requests.get(url)
    if response.status_code != 200:
        return [], "Gagal mengakses NewsData.io"
    data = response.json()
    results = data.get("results", [])
    articles = []
    for item in results:
        articles.append({
            "title": item.get("title"),
            "source": item.get("source_id"),
            "url": item.get("link"),
            "published": item.get("pubDate"),
            "description": item.get("description")
        })
    return articles, None

def fetch_links_duckduckgo(keyword):
    query = f"{keyword} site:cnnindonesia.com OR site:kompas.com"
    url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    links = [a["href"] for a in soup.select(".result__a")]
    return links

def parse_news_content(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        if "cnnindonesia.com" in url:
            title = soup.find("h1").get_text(strip=True)
            body = " ".join([p.get_text(strip=True) for p in soup.select("div.detail_text p")])
        elif "kompas.com" in url:
            title = soup.find("h1").get_text(strip=True)
            body = " ".join([p.get_text(strip=True) for p in soup.select("div.read__content p")])
        else:
            title = soup.title.get_text(strip=True)
            body = ""
        return {"title": title, "url": url, "content": body}
    except:
        return None

# --- Main Logic ---
if run and keyword:
    st.info("📡 Mengambil data dari NewsData.io...")
    newsdata_articles, error = fetch_from_newsdata(keyword)
    if error:
        st.warning(error)
    df_newsdata = pd.DataFrame(newsdata_articles)
    st.success(f"✅ {len(df_newsdata)} artikel ditemukan dari NewsData.io")

    st.info("🌐 Mengambil link dari DuckDuckGo...")
    links = fetch_links_duckduckgo(keyword)
    st.write(f"🔗 {len(links)} link ditemukan dari CNN & Kompas")

    st.info("🧠 Parsing konten berita dari CNN/Kompas...")
    parsed_articles = []
    for link in links:
        parsed = parse_news_content(link)
        if parsed:
            parsed_articles.append(parsed)
    df_parsed = pd.DataFrame(parsed_articles)
    st.success(f"✅ {len(df_parsed)} artikel berhasil diambil dari link")

    # Gabungkan
    df_all = pd.concat([df_newsdata, df_parsed], ignore_index=True)
    st.markdown("### 🗂️ Hasil Crawling Berita")
    st.dataframe(df_all)

    # Export to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_all.to_excel(writer, index=False, sheet_name="Berita")
    output.seek(0)

    st.download_button(
        label="⬇️ Download Excel",
        data=output,
        file_name=f'berita_{keyword}_{datetime.date.today()}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
