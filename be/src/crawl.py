import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time
import random
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from urllib.parse import urlencode

# List user-agents để rotate (giữ nguyên)
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
]

# Hàm parse salary (giữ nguyên)
def parse_salary(salary_text):
    if not salary_text or 'Thoả thuận' in salary_text or 'N/A' in salary_text:
        return 0
    vnd_match = re.search(r'(\d+(?:,\d+)?)\s*[-–]\s*(\d+(?:,\d+)?)\s*(?:triệu)?', salary_text)
    if vnd_match:
        low, high = map(lambda x: float(x.replace(',', '').replace('.', '')), vnd_match.groups())
        return (low + high) / 2
    usd_match = re.search(r'(\d+(?:,\d+)?)\s*[-–]\s*(\d+(?:,\d+)?)\s*USD', salary_text)
    if usd_match:
        low, high = map(lambda x: float(x.replace(',', '')), usd_match.groups())
        return (low + high) / 2 * 24
    single_vnd = re.search(r'(\d+(?:,\d+)?)\s*(?:triệu)?', salary_text)
    if single_vnd:
        return float(single_vnd.group(1).replace(',', '').replace('.', ''))
    return 0

# Hàm parse update_time (giữ nguyên)
def parse_update_time(update_text):
    if not update_text or 'Đăng' not in update_text:
        return None
    text = re.sub(r'\s+', ' ', update_text.replace('\n', '').strip())
    now = datetime.now()
    
    if 'hôm nay' in text:
        return now.date().isoformat()
    
    years_match = re.search(r'(\d+)\s*năm trước', text)
    if years_match:
        years = int(years_match.group(1))
        return (now.replace(year=now.year - years)).date().isoformat()
    
    months_match = re.search(r'(\d+)\s*tháng trước', text)
    if months_match:
        months = int(months_match.group(1))
        month = now.month - months
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        return now.replace(month=month, year=year).date().isoformat()
    
    weeks_match = re.search(r'(\d+)\s*tuần trước', text)
    if weeks_match:
        weeks = int(weeks_match.group(1))
        return (now - timedelta(weeks=weeks)).date().isoformat()
    
    days_match = re.search(r'(\d+)\s*ngày trước', text)
    if days_match:
        days = int(days_match.group(1))
        return (now - timedelta(days=days)).date().isoformat()
    
    return None

# Crawl chỉ trang 1 (mới nhất)
def crawl_latest_page(base_url, category_name, session):
    jobs_page = crawl_one_page(base_url, 1, session)  # Chỉ page 1
    for job in jobs_page:
        job['category'] = category_name
    print(f"Category {category_name}: Crawled {len(jobs_page)} jobs từ trang 1.")
    return jobs_page

# Hàm crawl_one_page (giữ nguyên)
def crawl_one_page(base_url, page_num, session):
    params = {
        'sort': 'new',
        'type_keyword': '1',
        'page': page_num,
        'sba': '1',
        'domain_knowledge': '3'
    }
    max_retries = 3
    retry_delay = 2
    for attempt in range(max_retries):
        headers = {
            'User-Agent': random.choice(user_agents)
        }
        try:
            response = session.get(base_url, params=params, headers=headers, timeout=10)
            if response.status_code == 429:
                wait_time = retry_delay * (2 ** attempt)
                print(f"429 Too Many Requests trên page {page_num}, attempt {attempt+1}/{max_retries}. Wait {wait_time}s...")
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            job_list = soup.find('div', class_='job-list-search-result')
            if not job_list:
                print(f"Không tìm thấy job-list trên page {page_num}")
                return []
            
            jobs = []
            job_items = job_list.find_all('div', class_='job-item-search-result')
            
            for item in job_items:
                title_span = item.select_one('h3.title span[data-toggle="tooltip"]')
                title = title_span.get('data-original-title', title_span.text.strip() if title_span else 'N/A')
                
                company_span = item.select_one('span.company-name')
                company = company_span.get('data-original-title', company_span.text.strip() if company_span else 'N/A')
                
                salary_label = item.select_one('label.title-salary')
                salary_text = salary_label.text.strip() if salary_label else 'N/A'
                salary_avg = parse_salary(salary_text)
                
                city_span = item.select_one('label.address span.city-text')
                location = city_span.text.strip() if city_span else 'N/A'
                
                exp_span = item.select_one('label.exp span')
                experience = exp_span.text.strip() if exp_span else 'N/A'
                
                update_label = item.select_one('label.label-update')
                update_raw = update_label.text.strip() if update_label else 'N/A'
                update_date = parse_update_time(update_raw)
                
                tag_as = item.select('div.tag a.item-tag')
                skills = [a.text.strip() for a in tag_as] if tag_as else []
                
                timestamp = datetime.now().isoformat()
                jobs.append({
                    'id': f"{title[:50]}_{timestamp}",
                    'timestamp': timestamp,
                    'page': page_num,
                    'title': title,
                    'company': company,
                    'salary_text': salary_text,
                    'salary_avg_million_vnd': round(salary_avg, 2),
                    'location': location,
                    'experience_years': experience,
                    'update_raw': update_raw,
                    'update_date': update_date,
                    'skills': skills
                })
            
            return jobs
        except Exception as e:
            print(f"Lỗi crawl page {page_num} attempt {attempt+1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))
            else:
                return []
    return []

# Lưu vào MongoDB (giữ nguyên, check duplicate)
def save_to_mongo(jobs_new, db_name='job_data', collection_name='jobs'):
    if not jobs_new:
        return 0
    
    client = MongoClient('mongodb://root:123456@localhost:27017/')
    try:
        client.admin.command('ping')
    except ConnectionFailure as e:
        print(f"Lỗi kết nối MongoDB: {e}")
        client.close()
        return 0
    
    db = client[db_name]
    collection = db[collection_name]
    
    jobs_to_insert = []
    for job in jobs_new:
        unique_key = f"{job['title']}_{job['company']}_{job['update_date'] or 'N/A'}"
        if not collection.find_one({'unique_key': unique_key}):
            job['unique_key'] = unique_key
            jobs_to_insert.append(job)
    
    inserted_count = 0
    if jobs_to_insert:
        try:
            inserted_count = len(collection.insert_many(jobs_to_insert, ordered=False).inserted_ids)
            total_docs = collection.count_documents({})
            print(f"Đã lưu {inserted_count} jobs MỚI vào {collection_name}. Tổng: {total_docs}")
        except Exception as e:
            print(f"Lỗi lưu: {e}")
    else:
        print(f"Không có jobs mới ở {collection_name} (trang 1 không update).")
    
    client.close()
    return inserted_count

# List URL (giữ nguyên)
urls = [
    ('https://www.topcv.vn/tim-viec-lam-sales-it-phan-mem-cr1cb5', 'Sales IT Phần Mềm'),
    ('https://www.topcv.vn/tim-viec-lam-marketing-cr92cb99', 'Marketing'),
    ('https://www.topcv.vn/tim-viec-lam-it-infrastructure-and-operations-cr257cb262', 'IT Infrastructure and Operations'),
    ('https://www.topcv.vn/tim-viec-lam-product-management-cr257cb268', 'Product Management'),
    ('https://www.topcv.vn/tim-viec-lam-software-testing-cr257cb259', 'Software Testing'),
    ('https://www.topcv.vn/tim-viec-lam-it-project-management-cr257cb265', 'IT Project Management'),
    ('https://www.topcv.vn/tim-viec-lam-cham-soc-khach-hang-customer-service-cr158cb159', 'Chăm Sóc Khách Hàng Customer Service'),
    ('https://www.topcv.vn/tim-viec-lam-data-science-cr257cb261', 'Data Science'),
    ('https://www.topcv.vn/tim-viec-lam-software-engineering-cr257cb258', 'Software Engineering')
]