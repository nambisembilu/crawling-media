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

if not SERPAPI_KEY.strip():
    st.error("❌ Anda belum mengisi API Key SerpApi. Silakan daftarkan akun di https://serpapi.com/")
    st.stop()

# ---------------------------
# KONFIGURASI STREAMLIT
# ---------------------------
st.set_page_config(page_title="Crawler Berita 🇮🇩", layout="wide")
st.markdown("""
<div style="padding: 1rem; background: #1f2937; color: white; border-radius: 0.5rem; margin-bottom: 2rem;">
  <h1 style="font-size: 2rem; font-weight: bold;">📰 Crawler Berita Indonesia via SerpApi</h1>
  <p style="margin: 0.5rem 0 0;">Cari berita dari portal populer menggunakan kata kunci melalui hasil Google Search.</p>
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
        jumlah = st.number_input("🔢 Jumlah Artikel", min_value=1, max_value=100, value=20)
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
    results = data.get("organic_results", [])
    links = []
    for item in results:
        link = item.get("link")
        title = item.get("title")
        if link and title and any(x in link for x in [
            "cnnindonesia.com", "kompas.com", "liputan6.com", "tempo.co",
            "antaranews.com", "republika.co.id", "viva.co.id"
        ]):
            links.append({"title": title, "url": link})
    return links, None

# ---------------------------
# FUNGSI: PARSE KONTEN ARTIKEL
# ---------------------------
def parse_news_content(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else (soup.title.get_text(strip=True) if soup.title else "Tanpa Judul")
        body = " ".join([p.get_text(strip=True) for p in soup.find_all("p")])
        return {"title": title, "url": url, "content": body}
    except:
        return None

# ---------------------------
# EKSEKUSI UTAMA
# ---------------------------
if run:
    if not keyword.strip():
        st.warning("⚠️ Silakan masukkan kata kunci terlebih dahulu.")
        st.stop()

    st.info("🔍 Mengambil hasil pencarian dari Google via SerpApi...")
    results, error = fetch_links_serpapi(keyword, jumlah)
    if error:
        st.warning(f"⚠️ Gagal mengambil data dari SerpApi: {error}")
        st.stop()

    st.success(f"✅ Ditemukan {len(results)} artikel dari hasil pencarian.")
    st.dataframe(pd.DataFrame(results).head())

    st.info("🧠 Parsing isi artikel dari portal berita...")
    parsed_articles = []
    for r in results:
        parsed = parse_news_content(r["url"])
        if parsed:
            parsed_articles.append(parsed)
        else:
            st.write(f"❌ Gagal parsing: {r['url']}")

    st.success(f"✅ {len(parsed_articles)} artikel berhasil diambil.")
    df_all = pd.DataFrame(parsed_articles)
    st.dataframe(df_all)

    # ---------------------------
    # EXPORT KE EXCEL
    # ---------------------------
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_all.to_excel(writer, index=False, sheet_name="Berita")
    output.seek(0)

    st.download_button(
        label="⬇️ Download Excel",
        data=output,
        file_name=f'berita_serpapi_{keyword}_{datetime.date.today()}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
