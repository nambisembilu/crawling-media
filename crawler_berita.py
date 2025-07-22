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
# (Pastikan semua fungsi get_xxx_article memiliki headers={'User-Agent': ...} di dalamnya)
# ... (kode get_detik_article, get_kompas_article, get_sindonews_article, get_liputan6_article, get_cnn_article) ...
# (Saya asumsikan bagian ini tetap sama dan sudah ada di file app.py Anda dari revisi sebelumnya)

# Hanya untuk memastikan fungsi-fungsi ini ada jika Anda hanya menyalin sebagian:
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
        # st.error(f"Error mengakses URL Detik {url}: {e}") # Nonaktifkan untuk mengurangi spam error di UI
        return None
    except Exception as e:
        # st.error(f"Error parsing Detik article {url}: {e}") # Nonaktifkan untuk mengurangi spam error di UI
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
        # st.error(f"Error mengakses URL Kompas {url}: {e}")
        return None
    except Exception as e:
        # st.error(f"Error parsing Kompas article {url}: {e}")
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
        # st.error(f"Error mengakses URL SindoNews {url}: {e}")
        return None
    except Exception as e:
        # st.error(f"Error parsing SindoNews article {url}: {e}")
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
        # st.error(f"Error mengakses URL Liputan6 {url}: {e}")
        return None
    except Exception as e:
        # st.error(f"Error parsing Liputan6 article {url}: {e}")
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
        # st.error(f"Error mengakses URL CNN Indonesia {url}: {e}")
        return None
    except Exception as e:
        # st.error(f"Error parsing CNN Indonesia article {url}: {e}")
        return None

def crawl_articles(urls):
    results = []
    if not urls:
        return pd.DataFrame(results)
    
    st.info(f"Memulai crawling untuk {len(urls)} URL yang ditemukan...")
    progress_bar = st.progress(0)
    for i, url in enumerate(urls):
        # st.info(f"Mengambil artikel dari: {url}") # Nonaktifkan untuk mengurangi spam info di UI
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

# --- Fungsionalitas Pencarian (Revisi Kedua) ---
def search_for_urls_from_keyword(keyword, num_results=5):
    """
    Melakukan pencarian di Google News untuk mendapatkan URL artikel berdasarkan kata kunci.
    """
    st.info(f"Mencari URL artikel di Google News untuk keyword: '{keyword}'...")
    
    supported_domains = [
        "detik.com", "kompas.com", "sindonews.com", "liputan6.com", "cnnindonesia.com", "tempo.co", "tribunnews.com", "okezone.com", "merdeka.com", "antaranews.com", "republika.co.id"
    ]
    
    encoded_keyword = urllib.parse.quote_plus(keyword)
    # Gunakan parameter &tbm=nws untuk memastikan hasil adalah berita (walaupun news.google.com sudah cukup)
    # Tambahkan parameter &hl=id&gl=ID&ceid=ID:id untuk spesifik Indonesia
    search_url = f"https://www.google.com/search?q={encoded_keyword}&tbm=nws&hl=id&gl=ID&ceid=ID:id"
    
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

        # Coba identifikasi link ke artikel dari hasil pencarian Google reguler (tab berita)
        # Cari semua link yang memiliki atribut 'href' dan bukan link internal Google
        # Google News seringkali membungkus URL asli dalam query parameter 'url' atau mengarahkan via /url?q=
        
        # Periksa tag <a> dengan kelas 'WwrzSb' yang ditemukan di source code terbaru Google News
        # atau tag 'a' di dalam elemen 'article' yang juga punya link judul
        
        # Opsi 1: Cari link di dalam struktur artikel Google News langsung
        # Ini lebih cocok jika kita scraping news.google.com, bukan google.com/search?tbm=nws
        # Karena kita sekarang menggunakan google.com/search?tbm=nws, strukturnya berbeda.
        # Pada google.com/search?tbm=nws, link langsung ke situs berita asli adalah yang paling umum.
        
        # Select link elements by inspecting the actual Google News search results page.
        # Often, the actual link is in `a.WwrzSb` or similar, but the most reliable way 
        # for `google.com/search?tbm=nws` is to look for `a` tags within `div` that have `data-href` or similar,
        # or simply `a` tags with `jsname="hXwDdf"` or `class="l"` (for the main link)
        
        # Update: Google.com/search?tbm=nws often uses a class like 'l' or is directly inside a `div.Ww4FFb`
        # Let's target the primary link to the article.
        
        # Try finding all 'a' tags that likely lead to external sites
        # The main title link on google.com/search?tbm=nws usually has class 'l' or is within `div.g`
        
        # The most reliable links are usually within the main search result blocks
        # Look for div with class like 'g' or 'gG0TJ'. The link itself is often `a` tag directly
        # within it, or a child of `h3` or similar.
        
        # Based on observations for google.com/search?tbm=nws
        # The actual article link is often within a `div` that contains `data-hveid` and the `href` is a direct link.
        # A common pattern is `a` tags with `jsname="YFKh9e"` or just `a` tags inside `div.Ww4FFb` (the main result block)
        
        for link_tag in soup.find_all('a', class_='WwrzSb'): # This class was found in the user's provided snippet, good starting point
            href = link_tag.get('href')
            if href and href.startswith('./read/CBMi'):
                # This is a Google News internal link. We need to parse it.
                full_google_news_url = urllib.parse.urljoin("https://news.google.com/", href)
                
                # Extract the encoded URL from the CBMi parameter
                match = re.search(r'CBMi([A-Za-z0-9-_=]+)', full_google_news_url)
                if match:
                    encoded_data = match.group(1)
                    try:
                        # Add padding if needed for Base64 URL safe decoding
                        missing_padding = len(encoded_data) % 4
                        if missing_padding != 0:
                            encoded_data += '=' * (4 - missing_padding)
                        
                        # Use urlsafe_b64decode for the CBMi format
                        decoded_url_bytes = base64.urlsafe_b64decode(encoded_data)
                        
                        # Try decoding with 'utf-8'. If it fails, try 'latin-1' or 'windows-1252'
                        # Often, it's just plain UTF-8 for URLs. The error `0xae` might indicate
                        # that the string is not a pure URL after decoding.
                        # We'll just catch the error and move on.
                        decoded_url = decoded_url_bytes.decode('utf-8')
                        
                        # Check if the decoded URL is from a supported domain
                        if decoded_url.startswith('http'):
                            for domain in supported_domains:
                                if domain in decoded_url:
                                    if decoded_url not in found_urls:
                                        found_urls.append(decoded_url)
                                        break # Found domain, break from inner loop
                            if len(found_urls) >= num_results:
                                break # Enough results, break from outer loop
                    except (UnicodeDecodeError, Exception) as decode_error:
                        # st.warning(f"Gagal decode Base64 atau format URL tidak valid: {encoded_data}. Error: {decode_error}")
                        continue # Skip this link and try the next one
            elif href and href.startswith('http'):
                # This is a direct external URL. Check if it's from a supported domain.
                for domain in supported_domains:
                    if domain in href:
                        if href not in found_urls:
                            found_urls.append(href)
                            break
                if len(found_urls) >= num_results:
                    break
        
        # Fallback: Look for the 'JtKRv' class which is typically the main article title link
        # This was identified in your original snippet as the actual article link.
        if len(found_urls) < num_results:
            for link_tag in soup.find_all('a', class_='JtKRv'):
                href = link_tag.get('href')
                if href and href.startswith('./read/CBMi'):
                    full_google_news_url = urllib.parse.urljoin("https://news.google.com/", href)
                    match = re.search(r'CBMi([A-Za-z0-9-_=]+)', full_google_news_url)
                    if match:
                        encoded_data = match.group(1)
                        try:
                            missing_padding = len(encoded_data) % 4
                            if missing_padding != 0:
                                encoded_data += '=' * (4 - missing_padding)
                            decoded_url_bytes = base64.urlsafe_b64decode(encoded_data)
                            decoded_url = decoded_url_bytes.decode('utf-8')
                            if decoded_url.startswith('http'):
                                for domain in supported_domains:
                                    if domain in decoded_url:
                                        if decoded_url not in found_urls:
                                            found_urls.append(decoded_url)
                                            break
                                if len(found_urls) >= num_results:
                                    break
                        except (UnicodeDecodeError, Exception) as decode_error:
                            # st.warning(f"Gagal decode Base64 (JtKRv) atau format URL tidak valid: {encoded_data}. Error: {decode_error}")
                            continue
                elif href and href.startswith('http'):
                    for domain in supported_domains:
                        if domain in href:
                            if href not in found_urls:
                                found_urls.append(href)
                                break
                    if len(found_urls) >= num_results:
                        break

    except requests.exceptions.RequestException as e:
        status_code = response.status_code if 'response' in locals() else 'N/A'
        st.error(f"Error saat mencari URL di Google News (Status: {status_code}): {e}. Periksa koneksi internet Anda, coba lagi nanti, atau IP Anda mungkin diblokir.")
    except Exception as e:
        st.error(f"Terjadi kesalahan tidak terduga saat parsing hasil pencarian Google News: {e}. **Sangat disarankan untuk memeriksa struktur HTML Google News secara manual.**")

    unique_urls = list(dict.fromkeys(found_urls)) 
    
    if not unique_urls:
        st.warning(f"""
        **Peringatan Penting:** Tidak ada URL yang ditemukan dari situs berita yang didukung untuk kata kunci **'{keyword}'**.
        Ini mungkin karena:
        * Tidak ada artikel yang sangat relevan dari situs yang didukung muncul di Google News.
        * **Struktur HTML Google News telah berubah signifikan lagi.** Kode **`search_for_urls_from_keyword`** mungkin perlu diperbarui kembali dengan selektor yang baru yang Anda temukan dari **inspeksi manual**.
        * Permintaan Anda mungkin diblokir sementara oleh Google karena aktivitas scraping yang terdeteksi.
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
* Fungsi pencarian URL mengandalkan **web scraping Google News**. Jika Google mengubah struktur halamannya, fungsi ini mungkin perlu diperbarui kembali.
* Lakukan crawling secara bertanggung jawab. Terlalu banyak permintaan dalam waktu singkat dapat menyebabkan IP Anda diblokir oleh Google atau situs berita.
* Jumlah artikel yang dapat di-crawl bergantung pada hasil yang diberikan oleh Google News dan kemampuan crawler untuk mengekstraknya.
""")