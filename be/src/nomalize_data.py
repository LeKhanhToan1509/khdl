import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import re
import numpy as np
from sklearn.preprocessing import LabelEncoder

# Kết nối Mongo
client = MongoClient('mongodb://root:123456@localhost:27017/')
db = client['job_data']
collection = db['jobs']

# Load data
data = list(collection.find({}))  # Tất cả docs
df = pd.DataFrame(data)

# Drop _id, id, timestamp, page, update_raw (không cần)
df.drop(['_id', 'id', 'timestamp', 'page', 'update_raw'], axis=1, inplace=True)

# Parse experience_years thành số (mean nếu range)
def parse_experience(exp):
    if pd.isna(exp) or exp == 'N/A' or 'Không yêu cầu' in exp:
        return 0
    match = re.search(r'(\d+)(?:-(\d+))?\s*năm?', exp)
    if match:
        low = int(match.group(1))
        high = int(match.group(2)) if match.group(2) else low
        return (low + high) / 2
    return 0

df['experience_num'] = df['experience_years'].apply(parse_experience)

# Parse update_date thành datetime
df['update_date'] = pd.to_datetime(df['update_date'], errors='coerce')

# Num skills
df['num_skills'] = df['skills'].apply(lambda x: len(x) if isinstance(x, list) else 0)

# Filter: salary >0, update_date từ 2025-10-01 (demo)
df = df[df['salary_avg_million_vnd'] > 0]
df = df[df['update_date'] >= '2025-10-01']

# Handle missing: fillna
df['location'].fillna('Unknown', inplace=True)
df['company'].fillna('Unknown', inplace=True)

# Encode categorical
le_category = LabelEncoder()
df['category_encoded'] = le_category.fit_transform(df['category'])
le_location = LabelEncoder()
df['location_encoded'] = le_location.fit_transform(df['location'])

# Lưu CSV
df.to_csv('normalized_jobs.csv', index=False)
print(f"Normalized data saved: {len(df)} rows. Columns: {df.columns.tolist()}")

client.close()