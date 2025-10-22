from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import json
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
import re
from typing import List, Dict, Any
import asyncio
from contextlib import asynccontextmanager

# Try to import scheduler, if fails create a dummy
try:
    from scheduler import scheduler_instance
    SCHEDULER_AVAILABLE = True
except ImportError:
    print("Warning: Scheduler module not found, running without scheduler")
    SCHEDULER_AVAILABLE = False
    scheduler_instance = None

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if SCHEDULER_AVAILABLE and scheduler_instance:
        print("Starting job scheduler...")
        scheduler_instance.start_scheduler()
    else:
        print("Scheduler not available, skipping...")
    yield
    # Shutdown
    if SCHEDULER_AVAILABLE and scheduler_instance:
        print("Stopping job scheduler...")
        scheduler_instance.stop_scheduler()

app = FastAPI(
    title="Job Data Analytics API", 
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
try:
    client = MongoClient("mongodb://root:123456@localhost:27017/")
    db = client.job_data  # Sửa tên database đúng
    print("Connected to MongoDB successfully")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

def get_data_from_db(collection_name=None):
    """Lấy dữ liệu từ MongoDB và chuyển đổi thành DataFrame"""
    try:
        all_data = []
        
        if collection_name:
            # Lấy từ collection cụ thể
            collection = db[collection_name]
            data = list(collection.find({}))
            all_data.extend(data)
        else:
            # Lấy từ tất cả collections
            collections = db.list_collection_names()
            print(f"Found collections: {collections}")
            
            for coll_name in collections:
                collection = db[coll_name]
                data = list(collection.find({}))
                # Thêm collection name vào data nếu chưa có category
                for doc in data:
                    if 'category' not in doc:
                        doc['category'] = coll_name
                all_data.extend(data)
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        # Xóa cột _id nếu có
        if '_id' in df.columns:
            df = df.drop('_id', axis=1)
        
        print(f"Loaded {len(df)} records from database")
        return df
    except Exception as e:
        print(f"Error getting data from database: {e}")
        return pd.DataFrame()

def preprocess_data(df):
    """Chuẩn hóa và xử lý dữ liệu"""
    if df.empty:
        return df
    
    # Xử lý cột salary_avg_million_vnd
    if 'salary_avg_million_vnd' in df.columns:
        df['salary_avg_million_vnd'] = pd.to_numeric(df['salary_avg_million_vnd'], errors='coerce').fillna(0)
    
    # Xử lý ngày tháng update_date
    if 'update_date' in df.columns:
        df['update_date'] = pd.to_datetime(df['update_date'], errors='coerce')
    
    # Tạo các cột đặc trưng mới
    if 'salary_avg_million_vnd' in df.columns:
        df['salary_range'] = pd.cut(df['salary_avg_million_vnd'], 
                                   bins=[0, 10, 20, 30, 50, float('inf')], 
                                   labels=['<10M', '10-20M', '20-30M', '30-50M', '>50M'])
    
    # Xử lý experience_years
    if 'experience_years' in df.columns:
        df['experience_level'] = df['experience_years'].apply(categorize_experience)
    
    # Xử lý location
    if 'location' in df.columns:
        df['city'] = df['location'].apply(extract_city)
    
    return df

def categorize_experience(exp_text):
    """Phân loại kinh nghiệm"""
    if pd.isna(exp_text):
        return 'Unknown'
    
    exp_text = str(exp_text).lower()
    if 'không yêu cầu' in exp_text or 'intern' in exp_text:
        return 'Entry Level'
    elif any(x in exp_text for x in ['1 năm', '2 năm', 'junior']):
        return 'Junior'
    elif any(x in exp_text for x in ['3 năm', '4 năm', '5 năm', 'senior']):
        return 'Senior'
    else:
        return 'Other'

def extract_city(location_text):
    """Trích xuất thành phố từ địa chỉ"""
    if pd.isna(location_text):
        return 'Unknown'
    
    cities = ['Hà Nội', 'TP Hồ Chí Minh', 'Đà Nẵng', 'Cần Thơ', 'Hải Phòng', 'Biên Hòa']
    for city in cities:
        if city in str(location_text):
            return city
    return 'Other'

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Job Data Analytics API - Ready for data visualization"}

@app.get("/api/collections")
async def get_collections():
    """API lấy danh sách tất cả collections"""
    try:
        collections = db.list_collection_names()
        result = []
        
        for coll_name in collections:
            collection = db[coll_name]
            count = collection.count_documents({})
            result.append({
                "name": coll_name,
                "count": count
            })
        
        return {"collections": result, "total_collections": len(collections)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/summary")
async def get_data_summary(collection: str = None):
    """API lấy thông tin tổng quan về dữ liệu"""
    try:
        df = get_data_from_db(collection)
        if df.empty:
            return {"error": "No data found"}
        
        df = preprocess_data(df)
        
        summary = {
            "total_jobs": len(df),
            "companies": df['company'].nunique() if 'company' in df.columns else 0,
            "categories": df['category'].nunique() if 'category' in df.columns else 0,
            "avg_salary": float(df['salary_avg_million_vnd'].mean()) if 'salary_avg_million_vnd' in df.columns else 0,
            "date_range": {
                "start": df['update_date'].min().isoformat() if 'update_date' in df.columns and not df['update_date'].isna().all() else None,
                "end": df['update_date'].max().isoformat() if 'update_date' in df.columns and not df['update_date'].isna().all() else None
            },
            "collection_used": collection if collection else "all"
        }
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/charts/salary-distribution")
async def get_salary_distribution(collection: str = None):
    """1. Histogram/Boxplot/Violin - Phân phối lương theo category"""
    try:
        df = get_data_from_db(collection)
        if df.empty:
            return {"error": "No data found"}
        
        df = preprocess_data(df)
        
        # Lọc dữ liệu lương hợp lệ
        valid_df = df[df['salary_avg_million_vnd'] > 0].copy()
        
        if valid_df.empty:
            return {"error": "No salary data found"}
        
        # Histogram - Phân phối lương tổng thể
        fig_hist = px.histogram(
            valid_df,
            x='salary_avg_million_vnd',
            nbins=25,
            title="Phân phối mức lương trong ngành IT",
            labels={'salary_avg_million_vnd': 'Lương (triệu VNĐ)', 'count': 'Số lượng công việc'},
            color_discrete_sequence=['#1f77b4']
        )
        fig_hist.update_layout(showlegend=False)
        
        # Boxplot theo category
        fig_box = px.box(
            valid_df,
            x='category',
            y='salary_avg_million_vnd',
            title="So sánh mức lương theo lĩnh vực",
            labels={'category': 'Lĩnh vực', 'salary_avg_million_vnd': 'Lương (triệu VNĐ)'}
        )
        fig_box.update_xaxes(tickangle=45)
        
        # Violin plot theo category
        fig_violin = px.violin(
            valid_df,
            x='category',
            y='salary_avg_million_vnd',
            title="Phân phối chi tiết mức lương theo lĩnh vực",
            labels={'category': 'Lĩnh vực', 'salary_avg_million_vnd': 'Lương (triệu VNĐ)'},
            box=True
        )
        fig_violin.update_xaxes(tickangle=45)
        
        return {
            "histogram": json.loads(fig_hist.to_json()),
            "boxplot": json.loads(fig_box.to_json()),
            "violin": json.loads(fig_violin.to_json()),
            "collection_used": collection if collection else "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/charts/jobs-trend")
async def get_jobs_trend(collection: str = None):
    """2. Line/Area chart - Xu hướng việc làm theo thời gian và category"""
    try:
        df = get_data_from_db(collection)
        if df.empty:
            return {"error": "No data found"}
        
        df = preprocess_data(df)
        
        # Kiểm tra dữ liệu thời gian
        if 'update_date' not in df.columns or df['update_date'].isna().all():
            return {"error": "No valid date data found"}
        
        # Tạo dữ liệu theo tuần
        df['week'] = df['update_date'].dt.to_period('W').dt.start_time
        
        # Line chart - Tổng số job theo tuần
        weekly_jobs = df.groupby('week').size().reset_index(name='count')
        fig_line = px.line(
            weekly_jobs,
            x='week',
            y='count',
            title="Xu hướng số lượng việc làm IT theo tuần",
            labels={'week': 'Tuần', 'count': 'Số lượng công việc'},
            markers=True
        )
        
        # Area chart - Jobs theo category theo tuần
        weekly_category = df.groupby(['week', 'category']).size().reset_index(name='count')
        fig_area = px.area(
            weekly_category,
            x='week',
            y='count',
            color='category',
            title="Xu hướng việc làm theo lĩnh vực",
            labels={'week': 'Tuần', 'count': 'Số lượng công việc', 'category': 'Lĩnh vực'}
        )
        
        # Line chart - Mức lương trung bình theo thời gian
        salary_trend = df[df['salary_avg_million_vnd'] > 0].groupby('week')['salary_avg_million_vnd'].mean().reset_index()
        fig_salary_trend = px.line(
            salary_trend,
            x='week',
            y='salary_avg_million_vnd',
            title="Xu hướng mức lương trung bình theo thời gian",
            labels={'week': 'Tuần', 'salary_avg_million_vnd': 'Lương TB (triệu VNĐ)'},
            markers=True
        )
        
        return {
            "jobs_trend": json.loads(fig_line.to_json()),
            "category_trend": json.loads(fig_area.to_json()),
            "salary_trend": json.loads(fig_salary_trend.to_json()),
            "collection_used": collection if collection else "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/charts/salary-location-analysis")
async def get_salary_location_analysis(collection: str = None):
    """3. Scatter + Regression - Phân tích mối quan hệ lương, địa điểm, kinh nghiệm"""
    try:
        df = get_data_from_db(collection)
        if df.empty:
            return {"error": "No data found"}
        
        df = preprocess_data(df)
        
        # Lọc dữ liệu hợp lệ
        valid_df = df[
            (df['salary_avg_million_vnd'] > 0) & 
            (df['location'].notna()) & 
            (df['experience_years'].notna())
        ].copy()
        
        if valid_df.empty:
            return {"error": "No valid data for analysis"}
        
        # Tạo numeric experience từ text
        def extract_experience_years(exp_text):
            if pd.isna(exp_text):
                return 0
            exp_str = str(exp_text).lower()
            if 'không yêu cầu' in exp_str or 'intern' in exp_str:
                return 0
            numbers = re.findall(r'\d+', exp_str)
            if numbers:
                return int(numbers[0])
            return 1
        
        valid_df['exp_numeric'] = valid_df['experience_years'].apply(extract_experience_years)
        
        # Scatter plot với regression line
        fig_scatter = px.scatter(
            valid_df,
            x='exp_numeric',
            y='salary_avg_million_vnd',
            color='city',
            size='salary_avg_million_vnd',
            hover_data=['title', 'company'],
            title="Mối quan hệ giữa Kinh nghiệm và Mức lương theo Địa điểm",
            labels={'exp_numeric': 'Số năm kinh nghiệm', 'salary_avg_million_vnd': 'Lương (triệu VNĐ)'},
            trendline="ols"
        )
        
        return {
            "scatter_regression": json.loads(fig_scatter.to_json()),
            "collection_used": collection if collection else "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/charts/correlation-heatmap")
async def get_correlation_heatmap(collection: str = None):
    """4. Heatmap tương quan - Phân tích tương quan giữa các yếu tố"""
    try:
        df = get_data_from_db(collection)
        if df.empty:
            return {"error": "No data found"}
        
        df = preprocess_data(df)
        
        # Tạo các biến số từ dữ liệu
        analysis_df = df.copy()
        
        # Biến numeric
        numeric_features = {}
        if 'salary_avg_million_vnd' in analysis_df.columns:
            numeric_features['Lương'] = analysis_df['salary_avg_million_vnd']
        
        # Tạo biến số từ experience
        def extract_experience_years(exp_text):
            if pd.isna(exp_text):
                return 0
            exp_str = str(exp_text).lower()
            if 'không yêu cầu' in exp_str or 'intern' in exp_str:
                return 0
            numbers = re.findall(r'\d+', exp_str)
            if numbers:
                return int(numbers[0])
            return 1
        
        if 'experience_years' in analysis_df.columns:
            numeric_features['Kinh nghiệm (năm)'] = analysis_df['experience_years'].apply(extract_experience_years)
        
        # Mã hóa categorical variables
        le = LabelEncoder()
        if 'category' in analysis_df.columns:
            numeric_features['Lĩnh vực (mã)'] = le.fit_transform(analysis_df['category'].fillna('Unknown'))
        
        if 'location' in analysis_df.columns:
            numeric_features['Địa điểm (mã)'] = le.fit_transform(analysis_df['location'].fillna('Unknown'))
        
        # Số lượng skills
        if 'skills' in analysis_df.columns:
            numeric_features['Số lượng kỹ năng'] = analysis_df['skills'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        # Tạo DataFrame cho correlation
        corr_df = pd.DataFrame(numeric_features)
        corr_matrix = corr_df.corr()
        
        # Heatmap tương quan
        fig_heatmap = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            title="Ma trận tương quan các yếu tố trong dữ liệu việc làm IT",
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1
        )
        
        return {
            "correlation_heatmap": json.loads(fig_heatmap.to_json()),
            "collection_used": collection if collection else "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/charts/treemap-sunburst")
async def get_treemap_sunburst(collection: str = None):
    """5. Treemap/Sunburst - Phân phối công việc theo category, location, salary"""
    try:
        df = get_data_from_db(collection)
        if df.empty:
            return {"error": "No data found"}
        
        df = preprocess_data(df)
        
        # Treemap - Phân phối theo category và city
        treemap_data = df.groupby(['category', 'city']).agg({
            'salary_avg_million_vnd': 'mean',
            'title': 'count'
        }).reset_index()
        treemap_data.columns = ['category', 'city', 'avg_salary', 'job_count']
        treemap_data = treemap_data[treemap_data['job_count'] > 0]
        
        fig_treemap = px.treemap(
            treemap_data,
            path=[px.Constant("Việc làm IT"), 'category', 'city'],
            values='job_count',
            color='avg_salary',
            hover_data=['avg_salary'],
            title="Phân phối việc làm theo lĩnh vực và địa điểm",
            color_continuous_scale='Viridis',
            labels={'avg_salary': 'Lương TB (triệu VNĐ)', 'job_count': 'Số lượng job'}
        )
        
        # Sunburst - Cấu trúc phân cấp category -> experience -> salary_range
        sunburst_data = df.groupby(['category', 'experience_level', 'salary_range']).size().reset_index(name='count')
        sunburst_data = sunburst_data[sunburst_data['count'] > 0]
        
        fig_sunburst = px.sunburst(
            sunburst_data,
            path=['category', 'experience_level', 'salary_range'],
            values='count',
            title="Cấu trúc phân cấp: Lĩnh vực → Kinh nghiệm → Mức lương"
        )
        
        return {
            "treemap": json.loads(fig_treemap.to_json()),
            "sunburst": json.loads(fig_sunburst.to_json()),
            "collection_used": collection if collection else "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/charts/skills-analysis")
async def get_skills_analysis(collection: str = None):
    """6. Skills Analysis - Top kỹ năng được yêu cầu nhiều nhất"""
    try:
        df = get_data_from_db(collection)
        if df.empty:
            return {"error": "No data found"}
        
        # WordCloud từ skills
        all_skills = []
        if 'skills' in df.columns:
            for skills_list in df['skills'].dropna():
                if isinstance(skills_list, list):
                    all_skills.extend(skills_list)
                elif isinstance(skills_list, str):
                    all_skills.append(skills_list)
        
        # Tạo skills frequency
        skills_freq = {}
        for skill in all_skills:
            skills_freq[skill] = skills_freq.get(skill, 0) + 1
        
        # Top skills
        top_skills = sorted(skills_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Tạo bar chart cho top skills
        if top_skills:
            skills_df = pd.DataFrame(top_skills, columns=['skill', 'count'])
            fig_skills = px.bar(
                skills_df,
                x='count',
                y='skill',
                orientation='h',
                title="Top 20 kỹ năng được yêu cầu nhiều nhất",
                labels={'count': 'Số lượng job yêu cầu', 'skill': 'Kỹ năng'}
            )
            fig_skills.update_layout(yaxis={'categoryorder': 'total ascending'})
        else:
            fig_skills = None
        
        return {
            "skills_chart": json.loads(fig_skills.to_json()) if fig_skills else None,
            "skills_data": top_skills,
            "collection_used": collection if collection else "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Job Data Analytics API is running"}

@app.get("/api/crawler/status")
async def get_crawler_status():
    """Get crawler status and countdown to next crawl"""
    try:
        if not SCHEDULER_AVAILABLE or not scheduler_instance:
            # Fallback response when scheduler is not available
            now = datetime.now()
            next_crawl = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now >= next_crawl:
                next_crawl += timedelta(days=1)
            
            time_diff = next_crawl - now
            
            return {
                "crawl_info": {
                    "next_crawl_time": next_crawl.strftime('%Y-%m-%d %H:%M:%S'),
                    "time_until_crawl": {
                        "days": time_diff.days,
                        "hours": time_diff.seconds // 3600,
                        "minutes": (time_diff.seconds % 3600) // 60,
                        "seconds": time_diff.seconds % 60,
                        "total_seconds": int(time_diff.total_seconds())
                    },
                    "crawled_today": False,
                    "current_time": now.strftime('%Y-%m-%d %H:%M:%S')
                },
                "statistics": {
                    "last_crawl_date": None,
                    "last_crawl_records": 0,
                    "crawl_status": "scheduler_unavailable",
                    "scheduled_time": "09:00 daily"
                }
            }
        
        crawl_info = scheduler_instance.get_next_crawl_time()
        
        # Get crawler statistics
        status_doc = scheduler_instance.scheduler_collection.find_one({"type": "daily_crawl"})
        
        result = {
            "crawl_info": crawl_info,
            "statistics": {
                "last_crawl_date": status_doc.get('last_crawl_date') if status_doc else None,
                "last_crawl_records": status_doc.get('last_crawl_records', 0) if status_doc else 0,
                "crawl_status": status_doc.get('crawl_status', 'unknown') if status_doc else 'unknown',
                "scheduled_time": "09:00 daily"
            }
        }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crawler/manual-trigger")
async def manual_trigger_crawl():
    """Manually trigger crawl job if not done today"""
    try:
        if not SCHEDULER_AVAILABLE or not scheduler_instance:
            return {
                "success": False,
                "message": "Scheduler service is not available",
                "error": "scheduler_unavailable"
            }
        
        if scheduler_instance.check_crawled_today():
            return {
                "success": False,
                "message": "Data already crawled today",
                "next_crawl": scheduler_instance.get_next_crawl_time()
            }
        
        # Trigger manual crawl in background
        import threading
        crawl_thread = threading.Thread(target=scheduler_instance.manual_crawl)
        crawl_thread.start()
        
        return {
            "success": True,
            "message": "Manual crawl started",
            "status": "running"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/crawler/today-jobs")
async def get_today_jobs():
    """Get jobs crawled today"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        if not SCHEDULER_AVAILABLE or not scheduler_instance:
            # Fallback: Get recent jobs from regular database
            collections = db.list_collection_names()
            all_recent_jobs = []
            
            for coll_name in collections:
                try:
                    collection = db[coll_name]
                    # Get recent jobs (last 24 hours)
                    yesterday = datetime.now() - timedelta(days=1)
                    recent_jobs = list(collection.find({
                        "update_date": {"$gte": yesterday}
                    }).limit(10))
                    
                    # Add collection info
                    for job in recent_jobs:
                        job['_id'] = str(job['_id'])  # Convert ObjectId to string
                        job['source_collection'] = coll_name
                    
                    all_recent_jobs.extend(recent_jobs)
                except Exception:
                    continue
            
            return {
                "crawl_date": today,
                "total_jobs": len(all_recent_jobs),
                "jobs": all_recent_jobs[:50],  # Limit to 50 for performance
                "collections_with_data": len(collections),
                "crawled_today": False,
                "note": "Scheduler unavailable, showing recent jobs instead"
            }
        
        # Get today's jobs from all collections
        collections = scheduler_instance.db.list_collection_names()
        all_today_jobs = []
        
        for coll_name in collections:
            if coll_name != "scheduler_status":  # Skip scheduler collection
                collection = scheduler_instance.db[coll_name]
                today_jobs = list(collection.find({
                    "crawl_date": today,
                    "is_today": True
                }))
                
                # Add collection info
                for job in today_jobs:
                    job['_id'] = str(job['_id'])  # Convert ObjectId to string
                    job['source_collection'] = coll_name
                
                all_today_jobs.extend(today_jobs)
        
        return {
            "crawl_date": today,
            "total_jobs": len(all_today_jobs),
            "jobs": all_today_jobs[:50],  # Limit to 50 for performance
            "collections_with_data": len([c for c in collections if c != "scheduler_status"]),
            "crawled_today": scheduler_instance.check_crawled_today() if scheduler_instance else False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)