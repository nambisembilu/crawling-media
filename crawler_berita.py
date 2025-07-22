import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time
from io import BytesIO
import urllib.parse # Untuk encode kata kunci

# --- Fungsi Crawler Artikel ---
# Menambahkan header User-Agent ke setiap permintaan untuk simulasi browser
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
        st.error(f"Error mengakses URL Detik {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing Detik article {url}: {e}")
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
        st.error(f"Error mengakses URL Kompas {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing Kompas article {url}: {e}")
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
                'Juli': '07', 'Agustus': '08', 'September': '09', 'Oktober': '10', 'November': '11', 'Desember': '12'
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
        st.error(f"Error mengakses URL SindoNews {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing SindoNews article {url}: {e}")
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
        st.error(f"Error mengakses URL Liputan6 {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing Liputan6 article {url}: {e}")
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
        st.error(f"Error mengakses URL CNN Indonesia {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing CNN Indonesia article {url}: {e}")
        return None


def crawl_articles(urls):
    results = []
    if not urls:
        return pd.DataFrame(results)
    
    st.info(f"Memulai crawling untuk {len(urls)} URL yang ditemukan...")
    progress_bar = st.progress(0)
    for i, url in enumerate(urls):
        st.info(f"Mengambil artikel dari: {url}")
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
        time.sleep(1.5) # Perpanjang delay untuk lebih sopan ke website, terutama setelah scraping Google News
    return pd.DataFrame(results)

# --- Fungsionalitas Pencarian (Diperbaiki) ---
def search_for_urls_from_keyword(keyword, num_results=5):
    """
    Melakukan pencarian di Google News untuk mendapatkan URL artikel berdasarkan kata kunci.
    """
    st.info(f"Mencari URL artikel di Google News untuk keyword: '{keyword}'...")
    
    supported_domains = [
        "detik.com", "kompas.com", "sindonews.com", "liputan6.com", "cnnindonesia.com"
    ]
    
    # Encode kata kunci untuk URL
    encoded_keyword = urllib.parse.quote_plus(keyword)
    # URL Google News dengan parameter pencarian dan bahasa Indonesia
    search_url = f"https://news.google.com/search?q={encoded_keyword}&hl=id&gl=ID&ceid=ID:id"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8', # Prioritaskan bahasa Inggris, lalu Indonesia
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Connection': 'keep-alive',
    }
    
    found_urls = []
    try:
        response = requests.get(search_url, headers=headers, timeout=15) # Tingkatkan timeout
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, 'html.parser')

        # Coba identifikasi tautan artikel lebih fleksibel
        # Tautan artikel Google News sering berada di dalam tag <a> yang memiliki href yang tidak kosong,
        # dan merupakan bagian dari "kartu" berita.
        # Biasanya, mereka memiliki struktur seperti <a href="./articles/..." ...>
        
        # Pendekatan 1: Cari semua link yang href-nya dimulai dengan "./articles/"
        for link in soup.find_all('a', href=re.compile(r'^\./articles/')):
            relative_url = link.get('href')
            full_url = urllib.parse.urljoin("https://news.google.com/", relative_url)
            
            # Tambahkan hanya jika dari domain yang didukung
            for domain in supported_domains:
                if domain in full_url:
                    if full_url not in found_urls: # Hindari duplikasi langsung
                        found_urls.append(full_url)
                        break
            if len(found_urls) >= num_results:
                break
        
        # Pendekatan 2 (jika Pendekatan 1 kurang berhasil): Cari semua <a> yang punya role="heading" atau <h3>
        # dan cek parent-nya atau linknya
        if len(found_urls) < num_results: # Lanjutkan jika belum cukup
            for h3_tag in soup.find_all('h3'):
                link_tag = h3_tag.find('a', href=True)
                if link_tag:
                    full_url = link_tag.get('href')
                    if full_url and full_url.startswith('./articles/'):
                        full_url = urllib.parse.urljoin("https://news.google.com/", full_url)

                    if full_url and full_url.startswith('http'):
                        for domain in supported_domains:
                            if domain in full_url:
                                if full_url not in found_urls:
                                    found_urls.append(full_url)
                                    break
                    if len(found_urls) >= num_results:
                        break

    except requests.exceptions.RequestException as e:
        st.error(f"Error saat mencari URL di Google News: {e}. Periksa koneksi internet Anda atau coba lagi nanti. Server mungkin memblokir permintaan.")
        st.info(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
    except Exception as e:
        st.error(f"Terjadi kesalahan tidak terduga saat parsing hasil pencarian Google News: {e}")

    # Hapus duplikat dan pastikan jumlahnya sesuai permintaan
    unique_urls = list(dict.fromkeys(found_urls)) 
    
    if not unique_urls:
        st.warning(f"""
        Tidak ada URL yang ditemukan dari situs berita yang didukung untuk kata kunci **'{keyword}'**.
        Ini mungkin karena:
        * Tidak ada artikel yang sangat relevan muncul di Google News dari situs yang didukung.
        * Struktur HTML Google News telah berubah secara signifikan (perlu update kode `search_for_urls_from_keyword`).
        * Permintaan Anda mungkin diblokir sementara oleh Google.
        """)
        st.info("Coba kata kunci yang lebih umum (misal: 'ekonomi Indonesia') atau kurangi jumlah artikel yang diminta.")
    
    return unique_urls[:num_results]

# --- Konfigurasi Streamlit UI ---
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
            # 1. Cari URL berdasarkan kata kunci
            urls_to_crawl = search_for_urls_from_keyword(keyword_input, num_articles_to_crawl)
            
            if urls_to_crawl:
                st.success(f"Ditemukan {len(urls_to_crawl)} URL yang relevan. Memulai crawling...")
                # 2. Lakukan crawling pada URL yang ditemukan
                df_articles = crawl_articles(urls_to_crawl)

                if not df_articles.empty:
                    st.subheader("Hasil Crawling")
                    st.dataframe(df_articles)

                    # Bagian untuk ekspor ke XLSX
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