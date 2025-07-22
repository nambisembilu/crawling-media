import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
import datetime
import urllib.parse

# ---------------------------
# KONFIGURASI API SERPAPI
# ---------------------------
SERPAPI_KEY = 'ISI_API_KEY_SERPAPI_ANDA'  # Ganti dengan API key asli dari https://serpapi.com/

# Validasi API Key
if not SERPAPI_KEY.strip():
    st.error("❌ Anda belum mengisi API Key SerpApi. Daftar di https://serpapi.com/")

# ---------------------------
# KONFIGURASI STREAMLIT
# ---------------------------
st.set_page_config(page_title="Crawler Berita 🇮🇩", layout="wide")
st.markdown("""
<div style="padding: 1rem; background: #1f2937; color: white; border-radius: 0.5rem; margin-bottom: 2rem;">
  <h1 style="font-size: 2rem; font-weight: bold;">📰 Crawler Berita Indonesia</h1>
  <p style="margin: 0.5rem 0 0;">Menggabungkan SerpApi dan crawling manual dari situs berita populer.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# INPUT FORM
# ---------------------------
with st.container():
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        keyword = st.text_input("🔎 Kata Kunci", placeholder="misalnya: ekonomi pangan", value="")
    with col2:
        jumlah = st.number_input("🔢 Maks Artikel SerpApi", min_value=1, max_value=100, value=20)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("🚀 Jalankan", use_container_width=True)

# ---------------------------
# FUNGSI: FETCH DARI SERPAPI
# ---------------------------
def fetch_links_serpapi(query, max_results=20):
    q = urllib.parse.quote(query)
    url = f"https://serpapi.com/search.json?q={q}&api_key={SERPAPI_KEY}&num={max_results}&hl=id&gl=id"
    r = requests.get(url)
    if r.status_code != 200:
        return [], f"Status {r.status_code} – {r.text}"
    data = r.json()
    organic = data.get("organic_results", [])
    links = []
    for item in organic:
        link = item.get("link")
        title = item.get("title")
        if link and title and any(site in link for site in [
            "cnnindonesia.com", "kompas.com", "liputan6.com", "tempo.co",
            "antaranews.com", "republika.co.id", "viva.co.id"
        ]):
            links.append({"title": title, "url": link})
    return links, None

# ---------------------------
# FUNGSI: CRAWLING MANUAL
# ---------------------------
def crawl_cnn(keyword):
    url = f"https://www.cnnindonesia.com/search/?query={keyword.replace(' ', '+')}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    articles = []
    for a in soup.select("article h2 a"):
        title = a.get_text(strip=True)
        link = a.get("href")
        if link and not link.startswith("http"):
            link = "https:" + link
        articles.append({"title": title, "url": link})
    return articles

def crawl_kompas(keyword):
    url = f"https://www.kompas.com/tag/{keyword.replace(' ', '-')}/"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    return [{"title": a.get_text(strip=True), "url": a.get("href")} 
            for a in soup.select(".latest .article__list__title a")]

def crawl_liputan6(keyword):
    url = f"https://www.liputan6.com/tag/{keyword.replace(' ', '-')}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    return [{"title": a.get_text(strip=True), "url": a.get("href")} 
            for a in soup.select("div.articles--rows--item__desc a.articles--rows--item__title-link")]

def crawl_tempo(keyword):
    url = f"https://www.tempo.co/search?q={keyword.replace(' ', '+')}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    articles = []
    for div in soup.select("div.card.card-type-1"):
        a = div.find("a")
        if a:
            articles.append({"title": a.get_text(strip=True), "url": a.get("href")})
    return articles

def crawl_antaranews(keyword):
    url = f"https://www.antaranews.com/search?q={keyword.replace(' ', '+')}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    articles = []
    for h3 in soup.select("h3"):
        a = h3.find("a")
        if a:
            articles.append({"title": a.get_text(strip=True), "url": a.get("href")})
    return articles

def crawl_republika(keyword):
    url = f"https://www.republika.co.id/tag/{keyword.replace(' ', '-')}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    return [{"title": a.get_text(strip=True), "url": a.get("href")} 
            for a in soup.select("div.teaser_conten1 > h2 > a")]

def crawl_viva(keyword):
    url = f"https://www.viva.co.id/search?q={keyword.replace(' ', '+')}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    articles = []
    for a in soup.select("div.content a"):
        title = a.get_text(strip=True)
        link = a.get("href")
        if title and link:
            articles.append({"title": title, "url": link})
    return articles

def crawl_all_manual(keyword):
    articles = []
    try:
        articles += crawl_cnn(keyword)
        articles += crawl_kompas(keyword)
        articles += crawl_liputan6(keyword)
        articles += crawl_tempo(keyword)
        articles += crawl_antaranews(keyword)
        articles += crawl_republika(keyword)
        articles += crawl_viva(keyword)
    except Exception as e:
        st.warning(f"⚠️ Error crawling manual: {e}")
    return articles

# ---------------------------
# FUNGSI: PARSE KONTEN ARTIKEL
# ---------------------------
def parse_news_content(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        title = (soup.find("h1").get_text(strip=True) 
                 if soup.find("h1") else (soup.title.get_text(strip=True) if soup.title else "Tanpa Judul"))
        content = " ".join(p.get_text(strip=True) for p in soup.find_all("p"))
        return {"title": title, "url": url, "content": content}
    except:
        return None

# ---------------------------
# EKSEKUSI UTAMA
# ---------------------------
if run:
    if not keyword.strip():
        st.warning("⚠️ Silakan masukkan kata kunci terlebih dahulu.")
        st.stop()

    # 1. SerpApi
    st.info("🔍 Mengambil dari SerpApi...")
    serpapi_links, error = fetch_links_serpapi(keyword, jumlah)
    if error:
        st.warning(f"⚠️ SerpApi error: {error}")
        serpapi_links = []  # lanjutkan tanpa data SerpApi

    st.success(f"✅ {len(serpapi_links)} artikel dari SerpApi")
    df_serp = pd.DataFrame(serpapi_links)
    st.dataframe(df_serp)

    # 2. Manual Crawling
    st.info("📡 Mengambil manual crawling...")
    manual_links = crawl_all_manual(keyword)
    st.success(f"✅ {len(manual_links)} artikel dari crawling manual")
    df_manual = pd.DataFrame(manual_links)
    st.dataframe(df_manual)

    # 3. Gabungkan
    st.info("🔗 Menggabungkan hasil...")
    combined = serpapi_links + manual_links
    df_combined = pd.DataFrame(combined)
    st.markdown("### 📑 Daftar Semua Artikel (SerpApi + Manual)")
    st.dataframe(df_combined)

    # 4. Parsing Konten
    st.info("🧠 Parsing isi konten artikel...")
    parsed = []
    for item in combined:
        result = parse_news_content(item["url"])
        if result:
            parsed.append(result)
    st.success(f"✅ {len(parsed)} artikel berhasil diparse")
    df_parsed = pd.DataFrame(parsed)
    st.dataframe(df_parsed)

    # 5. Export to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_parsed.to_excel(writer, index=False, sheet_name="Berita")
    output.seek(0)
    st.download_button(
        label="⬇️ Download Excel",
        data=output,
        file_name=f'berita_{keyword}_{datetime.date.today()}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
