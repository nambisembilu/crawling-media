import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
import datetime

# ---------------------------
# KONFIGURASI API
# ---------------------------
NEWSDATA_API_KEY = 'pub_e1f8e0f44ae641dbbf8843c814329a1f'  # GANTI dengan API key asli Anda dari https://newsdata.io/register

# ---------------------------
# CEK API KEY
# ---------------------------
if not NEWSDATA_API_KEY or not NEWSDATA_API_KEY.strip():
    st.error("❌ Anda belum mengisi API Key NewsData.io. Silakan daftarkan akun di https://newsdata.io/register")
    st.stop()

# ---------------------------
# KONFIGURASI STREAMLIT
# ---------------------------
st.set_page_config(page_title="Crawler Berita 🇮🇩", layout="wide")
st.markdown("""
<div style="padding: 1rem; background: #1f2937; color: white; border-radius: 0.5rem; margin-bottom: 2rem;">
  <h1 style="font-size: 2rem; font-weight: bold;">📰 Crawler Berita Indonesia</h1>
  <p style="margin: 0.5rem 0 0;">Cari berita dari berbagai portal populer menggunakan kata kunci tertentu.</p>
</div>
""", unsafe_allow_html=True)

# Input UI
with st.container():
    col1, col2, col3 = st.columns([3, 1, 1])  # Ubah proporsi agar tombol tidak terlalu sempit

    with col1:
        keyword = st.text_input("🔎 Kata Kunci", placeholder="misalnya: ekonomi pangan", value="")

    with col2:
        max_pages = st.number_input("📄 Jumlah Halaman API", min_value=1, max_value=100, value=5)

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)  # Untuk memberi jarak agar tombol di tengah vertikal
        run = st.button("🚀 Jalankan", use_container_width=True)

# ---------------------------
# FUNGSI UTAMA
# ---------------------------
def fetch_from_newsdata(keyword, max_pages=5):
    all_articles = []
    if not keyword.strip():
        return [], "Keyword kosong. Harap masukkan kata kunci."

    for page in range(1, max_pages + 1):
        url = f"https://newsdata.io/api/1/news?apikey={NEWSDATA_API_KEY}&country=id&language=id&q={keyword}"
        response = requests.get(url)
        if response.status_code != 200:
            try:
                # Ambil semua isi JSON error dan tampilkan detail
                full_error = response.json()
                return all_articles, f"Status {response.status_code} – {full_error}"
            except Exception as e:
                # Jika bukan JSON, tampilkan plain text
                return all_articles, f"Status {response.status_code} – {response.text}"
        
        # Normal response
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
        for item in results:
            all_articles.append({
                "title": item.get("title"),
                "source": item.get("source_id"),
                "url": item.get("link"),
                "published": item.get("pubDate"),
                "description": item.get("description")
            })
    return all_articles, None


def fetch_links_duckduckgo(keyword):
    query = f"{keyword} site:cnnindonesia.com OR site:kompas.com OR site:liputan6.com OR site:tempo.co OR site:antaranews.com OR site:republika.co.id OR site:viva.co.id"
    url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        # Coba tampilkan HTML yang diterima (maks 3000 karakter)
        debug_html = soup.prettify()[:3000]
        st.expander("🔎 Debug HTML DuckDuckGo").code(debug_html, language="html")

        # Coba selector default
        links = [a["href"] for a in soup.select(".result__a")]
        if not links:
            # Fallback selector alternatif (untuk berjaga-jaga)
            links = [a["href"] for a in soup.find_all("a", href=True) if "cnnindonesia" in a["href"] or "kompas.com" in a["href"]]

        return links
    except Exception as e:
        st.warning(f"❌ Error DuckDuckGo: {e}")
        return []

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
        elif "liputan6.com" in url:
            title = soup.find("h1").get_text(strip=True)
            body = " ".join([p.get_text(strip=True) for p in soup.select("div.read__content p")])
        elif "tempo.co" in url:
            title = soup.find("h1").get_text(strip=True)
            body = " ".join([p.get_text(strip=True) for p in soup.select("div.read__content p")])
        elif "antaranews.com" in url:
            title = soup.find("h1").get_text(strip=True)
            body = " ".join([p.get_text(strip=True) for p in soup.select("div.read__content p")])
        elif "republika.co.id" in url:
            title = soup.find("h1").get_text(strip=True)
            body = " ".join([p.get_text(strip=True) for p in soup.select("div.read__content p")])
        elif "viva.co.id" in url:
            title = soup.find("h1").get_text(strip=True)
            body = " ".join([p.get_text(strip=True) for p in soup.select("div.read__content p")])
        elif "kompas.com" in url:
            title = soup.find("h1").get_text(strip=True)
            body = " ".join([p.get_text(strip=True) for p in soup.select("div.read__content p")])
        else:
            title = soup.title.get_text(strip=True) if soup.title else "Tanpa Judul"
            body = ""
        return {"title": title, "url": url, "content": body}
    except:
        return None

# ---------------------------
# EKSEKUSI UTAMA
# ---------------------------
if run and keyword:
    # 1. Ambil dari API NewsData.io
    st.info("📡 Mengambil data dari NewsData.io...")
    newsdata_articles, error = fetch_from_newsdata(keyword, max_pages=max_pages)
    if error:
        st.warning(f"⚠️ ERROR NewsData.io: {error}")
    else:
        st.success(f"✅ {len(newsdata_articles)} artikel ditemukan dari NewsData.io")
        st.dataframe(pd.DataFrame(newsdata_articles).head())

    # 2. Ambil link dari DuckDuckGo
    st.info("🌐 Mengambil link dari DuckDuckGo...")
    links = fetch_links_duckduckgo(keyword)
    st.write(f"🔗 {len(links)} link ditemukan dari DuckDuckGo")
    if not links:
        st.warning("⚠️ DuckDuckGo tidak mengembalikan hasil.")

    # 3. Parse konten dari CNN/Kompas
    st.info("🧠 Parsing artikel dari CNN & Kompas...")
    parsed_articles = []
    for link in links:
        parsed = parse_news_content(link)
        if parsed:
            parsed_articles.append(parsed)
        else:
            st.write(f"❌ Gagal parsing: {link}")
    st.success(f"✅ {len(parsed_articles)} artikel berhasil di-parse.")
    st.dataframe(pd.DataFrame(parsed_articles).head())

    # 4. Gabungkan semua
    df_all = pd.DataFrame(newsdata_articles + parsed_articles)
    st.markdown("### 🗂️ Total Artikel")
    st.dataframe(df_all)

    # 5. Export ke Excel
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
