import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time
from io import BytesIO

# --- Fungsi Crawler Artikel (Tidak Berubah Signifikan) ---
def get_detik_article(url):
    try:
        response = requests.get(url)
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
        st.error(f"Error accessing URL {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing Detik article {url}: {e}")
        return None

def get_kompas_article(url):
    try:
        response = requests.get(url)
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
        st.error(f"Error accessing URL {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing Kompas article {url}: {e}")
        return None

def get_sindonews_article(url):
    try:
        response = requests.get(url)
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
        st.error(f"Error accessing URL {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing SindoNews article {url}: {e}")
        return None

def get_liputan6_article(url):
    try:
        response = requests.get(url)
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
        st.error(f"Error accessing URL {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing Liputan6 article {url}: {e}")
        return None

def get_cnn_article(url):
    try:
        response = requests.get(url)
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
        st.error(f"Error accessing URL {url}: {e}")
        return None
    except Exception as e:
        st.error(f"Error parsing CNN Indonesia article {url}: {e}")
        return None

# --- Fungsi Crawler Utama (Tidak Berubah) ---
def crawl_articles(urls):
    results = []
    if not urls:
        return pd.DataFrame(results) # Return empty DataFrame if no URLs
    
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
            st.warning(f"URL tidak dikenali atau tidak didukung untuk crawling: {url}")

        if article_data:
            results.append(article_data)
        progress_bar.progress((i + 1) / len(urls))
        time.sleep(0.1)
    return pd.DataFrame(results)

# --- Fungsionalitas Pencarian (BARU) ---
def search_for_urls_from_keyword(keyword, num_results=5):
    """
    Fungsi placeholder untuk mencari URL berdasarkan kata kunci.
    Dalam implementasi nyata, ini akan berinteraksi dengan API pencarian
    (misal: Google Custom Search, Google News API) atau melakukan scraping
    halaman hasil pencarian (lebih kompleks dan berisiko diblokir).

    Untuk demo ini, kita akan mengembalikan URL dummy.
    """
    st.info(f"Mencari URL untuk keyword: '{keyword}'...")
    
    # List domain yang didukung
    supported_domains = [
        "detik.com", "kompas.com", "sindonews.com", "liputan6.com", "cnnindonesia.com"
    ]
    
    found_urls = []
    
    # --- Contoh placeholder: Asumsikan Anda mendapatkan URL ini dari pencarian ---
    # Di dunia nyata, Anda akan menggunakan library seperti 'requests' dan 'BeautifulSoup'
    # untuk mengikis hasil pencarian Google News atau situs berita.
    # Atau lebih baik lagi, gunakan API pencarian jika tersedia.

    # Dummy URLs untuk demonstrasi. Anda perlu menggantinya dengan logika pencarian sungguhan.
    dummy_urls = [
        "https://news.detik.com/berita/d-7451361/laba-bersih-bank-mandiri-rp-40-6-t-di-kuartal-ii-2024-meroket-21-3",
        "https://ekonomi.kompas.com/read/2024/07/22/170000026/menteri-prpr-targetkan-tol-getaci-bagian-cileunyi-garut-rampung-2026",
        "https://nasional.sindonews.com/read/1420239/15/prabowo-gelar-rapat-internal-bersama-jajaran-gerindra-di-kemenhan-1721644788",
        "https://www.liputan6.com/bisnis/read/5651111/harga-minyak-mentah-turun-dipicu-kekhawatiran-permintaan-dan-penguatan-dolar-as",
        "https://www.cnnindonesia.com/ekonomi/20240722165507-92-1160358/rupiah-menguat-ke-rp-16-390-us-dibalik-lonjakan-laba-mandiri",
        # Tambahkan lebih banyak URL dummy atau implementasi pencarian sungguhan di sini
        # Contoh URL yang tidak didukung untuk demonstrasi:
        "https://www.google.com/search?q=dummy", 
        "https://www.facebook.com/posts/dummy"
    ]

    for url in dummy_urls:
        if any(domain in url for domain in supported_domains):
            found_urls.append(url)
            if len(found_urls) >= num_results: # Batasi jumlah hasil
                break
    
    if not found_urls:
        st.warning(f"Tidak ada URL yang ditemukan dari situs berita yang didukung untuk keyword '{keyword}'.")

    return found_urls

# --- Konfigurasi Streamlit UI (Berubah) ---
st.set_page_config(layout="wide", page_title="Crawler Artikel Berita Indonesia")

st.title("🇮🇩 Crawler Artikel Berita Indonesia")
st.write("Aplikasi ini memungkinkan Anda untuk mencari artikel berita berdasarkan kata kunci dan meng-crawl judul, tanggal, dan isinya dari beberapa situs berita populer di Indonesia.")

st.subheader("Masukkan Kata Kunci")
keyword_input = st.text_input(
    "Masukkan kata kunci untuk mencari artikel berita:",
    help="Contoh: 'Bank Mandiri', 'Rupiah', 'Harga Minyak'"
)

num_articles_to_crawl = st.slider(
    "Jumlah artikel yang ingin di-crawl per kata kunci (maksimal 10 untuk demo):",
    min_value=1,
    max_value=10, # Batasi untuk menghindari terlalu banyak crawling
    value=5
)

if st.button("Cari dan Mulai Crawling"):
    if not keyword_input:
        st.warning("Mohon masukkan kata kunci.")
    else:
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
            st.warning("Tidak ada URL yang ditemukan untuk kata kunci tersebut dari situs berita yang didukung.")

st.markdown("---")
st.markdown("Dikembangkan dengan ❤️ oleh [Nama Anda/Komunitas Anda]")
st.markdown("**Catatan:** Fungsi pencarian URL saat ini adalah *placeholder* dan hanya mengembalikan URL contoh. Untuk implementasi sungguhan, Anda perlu menambahkan logika pencarian (misalnya, menggunakan Google News API atau scraping hasil pencarian).")