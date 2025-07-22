import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time
import urllib.parse
from io import BytesIO
import base64 # Pastikan ini ada di bagian paling atas file Anda!

# --- Fungsi Crawler Artikel (Biarkan Sama) ---
# ... (kode get_detik_article, get_kompas_article, get_sindonews_article, get_liputan6_article, get_cnn_article) ...
# (Saya asumsikan bagian ini tetap sama dan sudah ada di file app.py Anda)

def get_detik_article(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('h1', class_='detail__title')
        title = title_tag.get_text(strip=True) if title_tag else 'N/A'

        date_tag = soup.find('div', class_='detail__date')
        date_text = date_tag.get_text(strip=True) if date_tag else 'N/A'
        match = re.search(r'(\d{1,2} \w{3} \d{4} \d{2}:\d{2})', date_text)
        if match:
            date_str = match.group(1)
            month_map = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'Mei': '05', 'Jun': '06',
                'Jul': '07', 'Agu': '08', 'Sep': '09', 'Okt': '10', 'Nov': '11', 'Des': '12'
            }
            for abbr, num in month_map.items():
                date_str = date_str.replace(abbr, num)
            try:
                parsed_date = datetime.strptime(date_str, '%d %m %Y %H:%M')
                date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                date = date_text
        else:
            date = date_text

        content_div = soup.find('div', class_='detail__body-text')
        paragraphs = content_div.find_all('p') if content_div else []
        content = "\n".join([p.get_text(strip=True) for p in paragraphs])
        content = re.sub(r'Baca juga:.*', '', content, flags=re.DOTALL)
        content = re.sub(r'Simak Video.*', '', content, flags=re.DOTALL)
        content = content.strip()

        return {'url': url, 'title': title, 'date': date, 'content': content}
    except requests.exceptions.RequestException as e:
        return None
    except Exception as e:
        return None

def get_kompas_article(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('h1', class_='read__title')
        title = title_tag.get_text(strip=True) if title_tag else 'N/A'

        date_tag = soup.find('div', class_='read__time')
        date_text = date_tag.get_text(strip=True) if date_tag else 'N/A'
        match = re.search(r'(\d{2}/\d{2}/\d{4}, \d{2}:\d{2})', date_text)
        if match:
            date_str = match.group(1)
            try:
                parsed_date = datetime.strptime(date_str, '%d/%m/%Y, %H:%M')
                date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                date = date_text
        else:
            date = date_text

        content_div = soup.find('div', class_='read__content')
        paragraphs = content_div.find_all('p') if content_div else []
        content = "\n".join([p.get_text(strip=True) for p in paragraphs])
        content = re.sub(r'Baca juga:.*', '', content, flags=re.DOTALL)
        content = re.sub(r'Baca Juga.*', '', content, flags=re.DOTALL)
        content = re.sub(r'Simak juga.*', '', content, flags=re.DOTALL)
        content = re.sub(r'Pilihan Editor.*', '', content, flags=re.DOTALL)
        content = content.strip()

        return {'url': url, 'title': title, 'date': date, 'content': content}
    except requests.exceptions.RequestException as e:
        return None
    except Exception as e:
        return None

def get_sindonews_article(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('h1', class_='title')
        title = title_tag.get_text(strip=True) if title_tag else 'N/A'

        date_tag = soup.find('time', class_='time')
        date_text = date_tag.get_text(strip=True) if date_tag else 'N/A'
        match = re.search(r'(\d{1,2} \w+ \d{4} - \d{2}:\d{2})', date_text)
        if match:
            date_str = match.group(1)
            month_map = {
                'Januari': '01', 'Februari': '02', 'Maret': '03', 'April': '04', 'Mei': '05', 'Juni': '06',
                'Juli': '07', 'Agustus': '08', 'September': '09', 'Okt': '10', 'November': '11', 'Desember': '12'
            }
            for full, num in month_map.items():
                date_str = date_str.replace(full, num)
            try:
                parsed_date = datetime.strptime(date_str, '%d %m %Y - %H:%M')
                date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                date = date_text
        else:
            date = date_text

        content_div = soup.find('div', class_='desc')
        paragraphs = content_div.find_all('p') if content_div else []
        content = "\n".join([p.get_text(strip=True) for p in paragraphs])
        content = re.sub(r'Lihat juga:.*', '', content, flags=re.DOTALL)
        content = re.sub(r'Jangan Lewatkan!.*', '', content, flags=re.DOTALL)
        content = content.strip()

        return {'url': url, 'title': title, 'date': date, 'content': content}
    except requests.exceptions.RequestException as e:
        return None
    except Exception as e:
        return None

def get_liputan6_article(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('h1', class_='jdl')
        title = title_tag.get_text(strip=True) if title_tag else 'N/A'

        date_tag = soup.find('time', class_='read-info__date')
        date_text = date_tag.get_text(strip=True) if date_tag else 'N/A'
        match = re.search(r'(\d{1,2} \w{3} \d{4}, \d{2}:\d{2})', date_text)
        if match:
            date_str = match.group(1)
            month_map = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'Mei': '05', 'Jun': '06',
                'Jul': '07', 'Agu': '08', 'Sep': '09', 'Okt': '10', 'Nov': '11', 'Des': '12'
            }
            for abbr, num in month_map.items():
                date_str = date_str.replace(abbr, num)
            try:
                parsed_date = datetime.strptime(date_str, '%d %m %Y, %H:%M')
                date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                date = date_text
        else:
            date = date_text

        content_div = soup.find('div', class_='article-content-body__item-content')
        paragraphs = content_div.find_all('p') if content_div else []
        content = "\n".join([p.get_text(strip=True) for p in paragraphs])
        content = re.sub(r'Baca Juga.*', '', content, flags=re.DOTALL)
        content = re.sub(r'Simak berita Liputan6.com lainnya.*', '', content, flags=re.DOTALL)
        content = content.strip()

        return {'url': url, 'title': title, 'date': date, 'content': content}
    except requests.exceptions.RequestException as e:
        return None
    except Exception as e:
        return None

def get_cnn_article(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('h1', class_='detail_title')
        title = title_tag.get_text(strip=True) if title_tag else 'N/A'

        date_tag = soup.find('div', class_='detail_date')
        date_text = date_tag.get_text(strip=True) if date_tag else 'N/A'
        match = re.search(r'(\d{1,2} \w{3} \d{4} \d{2}:\d{2})', date_text)
        if match:
            date_str = match.group(1)
            month_map = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'Mei': '05', 'Jun': '06',
                'Jul': '07', 'Agu': '08', 'Sep': '09', 'Okt': '10', 'Nov': '11', 'Des': '12'
            }
            for abbr, num in month_map.items():
                date_str = date_str.replace(abbr, num)
            try:
                parsed_date = datetime.strptime(date_str, '%d %m %Y %H:%M')
                date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                date = date_text
        else:
            date = date_text

        content_div = soup.find('div', class_='detail_text')
        paragraphs = content_div.find_all('p') if content_div else []
        content = "\n".join([p.get_text(strip=True) for p in paragraphs])
        content = re.sub(r'Baca berita selengkapnya di CNNIndonesia.com', '', content, flags=re.DOTALL)
        content = re.sub(r'Lihat Juga:.*', '', content, flags=re.DOTALL)
        content = content.strip()

        return {'url': url, 'title': title, 'date': date, 'content': content}
    except requests.exceptions.RequestException as e:
        return None
    except Exception as e:
        return None

def crawl_articles(urls):
    results = []
    if not urls:
        return pd.DataFrame(results)
    
    st.info(f"Memulai crawling untuk {len(urls)} URL yang ditemukan...")
    progress_bar = st.progress(0)
    for i, url in enumerate(urls):
        article_data = None
        if "detik.com" in url:
            article_data = get_detik_article(url)
        elif "kompas.com" in url:
            article_data = get_kompas_article(url)
        elif "sindonews.com" in url:
            article_data = get_sindonews_article(url)
        elif "liputan6.com" in url:
            article_data = get_liputan6_article(url)
        elif "cnnindonesia.com" in url:
            article_data = get_cnn_article(url)
        else:
            st.warning(f"URL tidak dikenali atau tidak didukung untuk crawling: {url}. Melewatkan.")

        if article_data:
            results.append(article_data)
        progress_bar.progress((i + 1) / len(urls))
        time.sleep(1.5) 
    return pd.DataFrame(results)

def search_for_urls_from_keyword(keyword, num_results=5):
    """
    Melakukan pencarian di DuckDuckGo untuk mendapatkan URL artikel berdasarkan kata kunci.
    """
    st.info(f"Mencari URL artikel di DuckDuckGo untuk keyword: '{keyword}'...")
    
    supported_domains = [
        "detik.com", "kompas.com", "sindonews.com", "liputan6.com", "cnnindonesia.com", "tempo.co", "tribunnews.com", "okezone.com", "merdeka.com", "antaranews.com", "republika.co.id"
    ]
    
    encoded_keyword = urllib.parse.quote_plus(keyword)
    # DuckDuckGo search URL for news. Using 'ia=news' to filter results by news.
    # Adjust `kp=-2` to disable personalization/tracking if needed, though DDG is privacy-focused by default.
    search_url = f"https://duckduckgo.com/?q={encoded_keyword}&ia=news" 
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Connection': 'keep-alive',
    }
    
    found_urls = []
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, 'html.parser')

        # DuckDuckGo news results typically have `a` tags within `div` elements
        # with classes like 'result__a' or similar for the main link.
        # It's important to inspect DuckDuckGo's news result page's HTML to find the correct selector.
        # As of now, 'result__a' is a common class for the main result link.
        
        # Look for the main article links.
        # Often, the link is directly in an 'a' tag with class 'result__a' or similar.
        # For news results, they sometimes have a specific structure.
        
        # Let's try to find elements that are clearly news articles.
        # Based on a quick inspection of DuckDuckGo news results:
        # Main links are often 'a' tags within 'div.result__body' with class 'result__a'
        # or 'a' tags directly under 'div.result--news'.
        
        # Iterate over all result links
        for link_tag in soup.find_all('a', class_='result__a'):
            href = link_tag.get('href')
            if href and href.startswith('http'):
                # DuckDuckGo often provides direct links.
                # Remove DuckDuckGo's internal redirect if present (e.g., /l/?kh=...&uddg=...)
                if href.startswith('https://duckduckgo.com/l/'):
                    parsed_url = urllib.parse.urlparse(href)
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    if 'uddg' in query_params:
                        actual_url = query_params['uddg'][0]
                        decoded_actual_url = urllib.parse.unquote(actual_url) # URL decode
                        href = decoded_actual_url
                
                for domain in supported_domains:
                    if domain in href:
                        if href not in found_urls:
                            found_urls.append(href)
                            break 
                if len(found_urls) >= num_results:
                    break

    except requests.exceptions.RequestException as e:
        status_code = response.status_code if 'response' in locals() else 'N/A'
        st.error(f"Error saat mencari URL di DuckDuckGo (Status: {status_code}): {e}. Periksa koneksi internet Anda atau coba lagi nanti.")
    except Exception as e:
        st.error(f"Terjadi kesalahan tidak terduga saat parsing hasil pencarian DuckDuckGo: {e}. **Sangat disarankan untuk memeriksa struktur HTML DuckDuckGo secara manual.**")

    unique_urls = list(dict.fromkeys(found_urls)) 
    
    if not unique_urls:
        st.warning(f"""
        **Peringatan Penting:** Tidak ada URL yang ditemukan dari situs berita yang didukung untuk kata kunci **'{keyword}'** di DuckDuckGo.
        Ini mungkin karena:
        * Tidak ada artikel yang sangat relevan dari situs yang didukung muncul di hasil DuckDuckGo.
        * **Struktur HTML DuckDuckGo telah berubah.** Kode **`search_for_urls_from_keyword`** mungkin perlu diperbarui kembali dengan selektor yang baru yang Anda temukan dari **inspeksi manual**.
        """)
        st.info("Saran: Coba kata kunci yang lebih umum (misal: 'ekonomi Indonesia', 'berita politik') atau kurangi jumlah artikel yang diminta.")
    
    return unique_urls[:num_results]

# --- Konfigurasi Streamlit UI (Tetap Sama) ---
st.set_page_config(layout="wide", page_title="Crawler Artikel Berita Indonesia")

st.title("🇮🇩 Crawler Artikel Berita Indonesia")
st.write("Aplikasi ini memungkinkan Anda untuk mencari artikel berita berdasarkan kata kunci dan meng-crawl judul, tanggal, dan isinya dari beberapa situs berita populer di Indonesia.")

st.subheader("Masukkan Kata Kunci")
keyword_input = st.text_input(
    "Masukkan kata kunci untuk mencari artikel berita:",
    help="Contoh: 'makan siang gratis', 'inflasi Indonesia', 'harga minyak dunia'"
)

num_articles_to_crawl = st.slider(
    "Jumlah artikel yang ingin di-crawl (maksimal 20):",
    min_value=1,
    max_value=20, 
    value=5
)

if st.button("Cari dan Mulai Crawling"):
    if not keyword_input:
        st.warning("Mohon masukkan kata kunci.")
    else:
        with st.spinner("Mencari URL dan crawling artikel... Mohon tunggu, proses ini mungkin memakan waktu beberapa detik per artikel."):
            urls_to_crawl = search_for_urls_from_keyword(keyword_input, num_articles_to_crawl)
            
            if urls_to_crawl:
                st.success(f"Ditemukan {len(urls_to_crawl)} URL yang relevan. Memulai crawling...")
                df_articles = crawl_articles(urls_to_crawl)

                if not df_articles.empty:
                    st.subheader("Hasil Crawling")
                    st.dataframe(df_articles)

                    excel_buffer = BytesIO()
                    df_articles.to_excel(excel_buffer, index=False, engine='openpyxl')
                    excel_buffer.seek(0)

                    st.download_button(
                        label="Unduh Data sebagai XLSX",
                        data=excel_buffer,
                        file_name=f"{keyword_input.replace(' ', '_')}_artikel_berita.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                else:
                    st.warning("Tidak ada artikel yang berhasil di-crawl dari URL yang ditemukan.")
            else:
                st.warning("Tidak ada URL yang ditemukan untuk kata kunci tersebut dari situs berita yang didukung. Coba kata kunci lain atau periksa kembali.")

st.markdown("---")
st.markdown("Dikembangkan dengan ❤️ untuk Anda.")
st.markdown("""
**Penting:**
* Fungsi pencarian URL mengandalkan **web scraping DuckDuckGo**. Jika DuckDuckGo mengubah struktur halamannya, fungsi ini mungkin perlu diperbarui kembali.
* Lakukan crawling secara bertanggung jawab. Terlalu banyak permintaan dalam waktu singkat dapat menyebabkan IP Anda diblokir oleh situs berita.
* Jumlah artikel yang dapat di-crawl bergantung pada hasil yang diberikan oleh DuckDuckGo dan kemampuan crawler untuk mengekstraknya.
""")