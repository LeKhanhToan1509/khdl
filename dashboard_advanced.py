import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pymongo import MongoClient
import re
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Page config với favicon và layout
st.set_page_config(
    page_title="Job Analytics Dashboard",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com',
        'Report a bug': "https://github.com",
        'About': "# Job Data Analytics Dashboard\nPhân tích dữ liệu việc làm IT tại Việt Nam"
    }
)

# CSS cho giao diện đẹp
st.markdown("""
<style>
    /* Main layout */
    .main {
        padding-top: 1rem;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8fafc !important;
        border-right: 2px solid #e2e8f0 !important;
    }
    
    /* Sidebar title */
    .css-1d391kg h1 {
        color: #1e40af !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
        text-align: center !important;
        margin-bottom: 2rem !important;
        padding: 1rem 0 !important;
        border-bottom: 2px solid #3b82f6 !important;
    }
    
    /* Radio button container */
    .css-1d391kg .stRadio > div {
        flex-direction: column !important;
        gap: 0.5rem !important;
    }
    
    /* Radio button styling */
    .css-1d391kg .stRadio > div > label {
        background: white !important;
        border: 2px solid #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 0.75rem 1rem !important;
        margin: 0.25rem 0 !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        text-align: center !important;
        font-weight: 500 !important;
        color: #475569 !important;
    }
    
    /* Radio button hover */
    .css-1d391kg .stRadio > div > label:hover {
        border-color: #3b82f6 !important;
        background: #eff6ff !important;
        color: #1e40af !important;
    }
    
    /* Active radio button */
    .css-1d391kg .stRadio > div > label[data-checked="true"] {
        background: #3b82f6 !important;
        border-color: #1d4ed8 !important;
        color: white !important;
        font-weight: 600 !important;
    }
    
    /* Hide radio circles */
    .css-1d391kg .stRadio input[type="radio"] {
        display: none !important;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        margin-bottom: 1rem;
    }
    
    .metric-card.blue {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    }
    
    .metric-card.green {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    
    .metric-card.purple {
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
    }
    
    .metric-card.orange {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0;
    }
    
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
    }
    
    h1 {
        color: #1e293b;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        color: #374151;
        font-weight: 600;
        margin-top: 2rem;
    }
    
    h3 {
        color: #4b5563;
        font-weight: 500;
    }
    
    .stSelectbox > div > div {
        background-color: #f1f5f9;
        border-radius: 8px;
    }
    
    .filter-section {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo kết nối database
@st.cache_resource
def init_connection():
    try:
        client = MongoClient("mongodb://root:123456@localhost:27017/")
        db = client.job_data
        # Test connection by listing collections
        db.list_collection_names()
        return db
    except Exception as e:
        st.error(f"❌ Lỗi kết nối database: {e}")
        return None

@st.cache_data(ttl=300)  # Cache 5 phút
def load_data(collection_name=None):
    db = init_connection()
    if db is None:
        return pd.DataFrame()
    
    try:
        all_data = []
        
        if collection_name and collection_name != "Tất cả":
            collection = db[collection_name]
            data = list(collection.find({}))
            all_data.extend(data)
        else:
            collections = db.list_collection_names()
            for coll_name in collections:
                collection = db[coll_name]
                data = list(collection.find({}))
                for doc in data:
                    if 'category' not in doc:
                        doc['category'] = coll_name
                all_data.extend(data)
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        if '_id' in df.columns:
            df = df.drop('_id', axis=1)
        
        # Cải thiện data processing
        if 'salary_avg_million_vnd' in df.columns:
            df['salary_avg_million_vnd'] = pd.to_numeric(df['salary_avg_million_vnd'], errors='coerce').fillna(0)
        
        if 'update_date' in df.columns:
            df['update_date'] = pd.to_datetime(df['update_date'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return pd.DataFrame()

def process_data(df):
    if df.empty:
        return df
    
    # Xử lý và lọc salary (loại bỏ outliers ảo)
    if 'salary_avg_million_vnd' in df.columns:
        # Convert to numeric và loại bỏ values ảo
        df['salary_avg_million_vnd'] = pd.to_numeric(df['salary_avg_million_vnd'], errors='coerce').fillna(0)
        
        # Chỉ giữ lại lương từ 0-200 triệu VNĐ (thực tế)
        df = df[df['salary_avg_million_vnd'] <= 200].copy()
        
        # Loại bỏ những record có lương âm hoặc bằng 0 trong analysis
        df.loc[df['salary_avg_million_vnd'] < 0, 'salary_avg_million_vnd'] = 0
        
        # Tạo salary ranges thực tế
        df['salary_range'] = pd.cut(
            df['salary_avg_million_vnd'], 
            bins=[0, 8, 15, 25, 40, 200], 
            labels=['< 8M', '8-15M', '15-25M', '25-40M', '40M+']
        )
    
    # Xử lý city
    if 'location' in df.columns:
        def get_city(location):
            if pd.isna(location):
                return 'Khác'
            location = str(location)
            if 'Hà Nội' in location:
                return 'Hà Nội'
            elif 'Hồ Chí Minh' in location or 'TPHCM' in location:
                return 'TP.HCM'
            elif 'Đà Nẵng' in location:
                return 'Đà Nẵng'
            elif 'Cần Thơ' in location:
                return 'Cần Thơ'
            else:
                return 'Khác'
        
        df['city'] = df['location'].apply(get_city)
    
    # Xử lý experience
    def get_experience_level(exp_text):
        if pd.isna(exp_text):
            return 'Không yêu cầu'
        
        exp_text = str(exp_text).lower()
        if 'không yêu cầu' in exp_text or 'intern' in exp_text:
            return 'Không yêu cầu'
        elif any(x in exp_text for x in ['1 năm', '2 năm', '1-2', 'junior']):
            return 'Junior (1-2 năm)'
        elif any(x in exp_text for x in ['3 năm', '4 năm', '5 năm', '3-5', 'middle']):
            return 'Middle (3-5 năm)'
        elif any(x in exp_text for x in ['senior', '6 năm', '7 năm', '8 năm', '5+']):
            return 'Senior (5+ năm)'
        else:
            return 'Khác'
    
    if 'experience_years' in df.columns:
        df['experience_level'] = df['experience_years'].apply(get_experience_level)
    
    # Extract numeric experience (giới hạn 0-20 năm)
    def get_exp_numeric(exp_text):
        if pd.isna(exp_text):
            return 0
        exp_text = str(exp_text).lower()
        if 'không yêu cầu' in exp_text:
            return 0
        numbers = re.findall(r'\d+', exp_text)
        if numbers:
            exp_years = int(numbers[0])
            # Giới hạn kinh nghiệm 0-20 năm
            return min(exp_years, 20)
        return 1
    
    if 'experience_years' in df.columns:
        df['exp_numeric'] = df['experience_years'].apply(get_exp_numeric)
    
    return df

def create_metric_card(title, value, color_class="blue"):
    return f"""
    <div class="metric-card {color_class}">
        <p class="metric-value">{value}</p>
        <p class="metric-label">{title}</p>
    </div>
    """

def show_overview_page(df, db):
    st.markdown("## Tổng quan thị trường việc làm")
    
    # Filters - hiển thị thẳng
    st.markdown("### Bộ lọc dữ liệu")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        collections = ["Tất cả"] + db.list_collection_names()
        selected_collection = st.selectbox("Chọn lĩnh vực:", collections, key="overview_collection")
    
    with col2:
        if 'city' in df.columns:
            cities = ['Tất cả'] + sorted(df['city'].unique().tolist())
            selected_city = st.selectbox("Thành phố:", cities, key="overview_city")
    
    with col3:
        if 'salary_avg_million_vnd' in df.columns:
            salary_range = st.slider(
                "Khoảng lương (triệu VNĐ):",
                min_value=0,
                max_value=200,
                value=(0, 200),
                step=5,
                key="overview_salary"
            )
    
    st.markdown("---")  # Ngăn cách giữa filters và charts
    
    # Apply filters
    if 'selected_collection' in locals() and selected_collection != 'Tất cả':
        df = load_data(selected_collection)
        df = process_data(df)
    
    if 'selected_city' in locals() and selected_city != 'Tất cả':
        df = df[df['city'] == selected_city]
    
    if 'salary_range' in locals():
        df = df[
            (df['salary_avg_million_vnd'] >= salary_range[0]) & 
            (df['salary_avg_million_vnd'] <= salary_range[1])
        ]
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(create_metric_card(
            "Tổng số việc làm", 
            f"{len(df):,}", 
            "blue"
        ), unsafe_allow_html=True)
    
    with col2:
        companies = df['company'].nunique() if 'company' in df.columns else 0
        st.markdown(create_metric_card(
            "Số công ty", 
            f"{companies:,}", 
            "green"
        ), unsafe_allow_html=True)
    
    with col3:
        avg_salary = df['salary_avg_million_vnd'].mean() if 'salary_avg_million_vnd' in df.columns else 0
        st.markdown(create_metric_card(
            "Lương TB", 
            f"{avg_salary:.1f}M", 
            "purple"
        ), unsafe_allow_html=True)
    
    with col4:
        categories = df['category'].nunique() if 'category' in df.columns else 0
        st.markdown(create_metric_card(
            "Lĩnh vực", 
            f"{categories}", 
            "orange"
        ), unsafe_allow_html=True)
    
    # Key insights
    st.markdown("### Thông tin tổng quan")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Phân bố theo lĩnh vực")
        if 'category' in df.columns:
            category_counts = df['category'].value_counts()
            fig = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Phân bố theo địa điểm")
        if 'city' in df.columns:
            city_counts = df['city'].value_counts().head(8)
            fig = px.bar(
                x=city_counts.values,
                y=city_counts.index,
                orientation='h',
                color_discrete_sequence=['#3b82f6']
            )
            fig.update_layout(
                xaxis_title="Số lượng job",
                yaxis_title="Thành phố",
                height=400,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Summary stats với styling đẹp
    st.markdown("### 📈 Thống kê nổi bật")
    
    # Tạo 4 cột để hiển thị các thống kê quan trọng
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if 'salary_avg_million_vnd' in df.columns:
            salary_data = df[df['salary_avg_million_vnd'] > 0]
            if not salary_data.empty:
                max_salary = salary_data['salary_avg_million_vnd'].max()
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 1.5rem;
                    border-radius: 15px;
                    color: white;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                    margin-bottom: 1rem;
                ">
                    <h3 style="margin: 0; font-size: 2.5rem; font-weight: bold;">{max_salary:.1f}M</h3>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1rem; opacity: 0.9;">Lương cao nhất</p>
                    <p style="margin: 0; font-size: 0.8rem; opacity: 0.7;">VNĐ/tháng</p>
                </div>
                """, unsafe_allow_html=True)
    
    with col2:
        if 'company' in df.columns and len(df) > 0:
            top_company = df['company'].value_counts()
            if not top_company.empty:
                company_name = top_company.index[0]
                top_count = top_company.iloc[0]
                # Rút gọn tên công ty nếu quá dài
                display_name = company_name[:15] + "..." if len(company_name) > 15 else company_name
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                    padding: 1.5rem;
                    border-radius: 15px;
                    color: white;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                    margin-bottom: 1rem;
                ">
                    <h3 style="margin: 0; font-size: 2.5rem; font-weight: bold;">{top_count}</h3>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1rem; opacity: 0.9;">jobs từ</p>
                    <p style="margin: 0; font-size: 0.8rem; opacity: 0.7; font-weight: 600;">{display_name}</p>
                </div>
                """, unsafe_allow_html=True)
    
    with col3:
        if 'category' in df.columns and len(df) > 0:
            top_category = df['category'].value_counts()
            if not top_category.empty:
                category_name = top_category.index[0]
                top_cat_count = top_category.iloc[0]
                percentage = (top_cat_count / len(df)) * 100
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #fc466b 0%, #3f5efb 100%);
                    padding: 1.5rem;
                    border-radius: 15px;
                    color: white;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                    margin-bottom: 1rem;
                ">
                    <h3 style="margin: 0; font-size: 2.5rem; font-weight: bold;">{top_cat_count}</h3>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1rem; opacity: 0.9;">{category_name}</p>
                    <p style="margin: 0; font-size: 0.8rem; opacity: 0.7;">{percentage:.1f}% tổng jobs</p>
                </div>
                """, unsafe_allow_html=True)
    
    with col4:
        if 'city' in df.columns and len(df) > 0:
            city_data = df['city'].value_counts()
            if not city_data.empty:
                top_city = city_data.index[0]
                city_count = city_data.iloc[0]
                city_percentage = (city_count / len(df)) * 100
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
                    padding: 1.5rem;
                    border-radius: 15px;
                    color: #8b4513;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                    margin-bottom: 1rem;
                ">
                    <h3 style="margin: 0; font-size: 2.5rem; font-weight: bold; color: #8b4513;">{city_count}</h3>
                    <p style="margin: 0.5rem 0 0 0; font-size: 1rem; opacity: 0.9;">jobs tại {top_city}</p>
                    <p style="margin: 0; font-size: 0.8rem; opacity: 0.7;">{city_percentage:.1f}% thị trường</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Thêm insights row
    st.markdown("### 💡 Insights thú vị")
    insight_col1, insight_col2, insight_col3 = st.columns(3)
    
    with insight_col1:
        if 'salary_avg_million_vnd' in df.columns:
            salary_data = df[df['salary_avg_million_vnd'] > 0]
            if not salary_data.empty:
                median_salary = salary_data['salary_avg_million_vnd'].median()
                avg_salary = salary_data['salary_avg_million_vnd'].mean()
                st.info(f"💰 **Lương trung vị**: {median_salary:.1f}M VNĐ\n\n📊 **Lương trung bình**: {avg_salary:.1f}M VNĐ")
    
    with insight_col2:
        if 'experience_years' in df.columns:
            # Phân tích kinh nghiệm
            exp_data = df[df['experience_years'].notna()]
            if not exp_data.empty:
                no_exp_count = len(exp_data[exp_data['experience_years'].str.contains('không yêu cầu|intern', case=False, na=False)])
                exp_percentage = (no_exp_count / len(exp_data)) * 100
                st.success(f"🎯 **Cơ hội cho fresher**: {exp_percentage:.1f}%\n\n📝 {no_exp_count} jobs không yêu cầu kinh nghiệm")
    
    with insight_col3:
        if 'update_date' in df.columns:
            recent_data = df[df['update_date'].notna()]
            if not recent_data.empty:
                latest_date = recent_data['update_date'].max()
                days_ago = (datetime.now() - latest_date).days
                st.warning(f"🕐 **Dữ liệu mới nhất**: {days_ago} ngày trước\n\n📅 Cập nhật: {latest_date.strftime('%d/%m/%Y')}")

def show_analysis_page(df, db):
    st.markdown("## Phân tích chi tiết")
    
    # Filters - hiển thị thẳng  
    st.markdown("### Bộ lọc dữ liệu")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        collections = ["Tất cả"] + db.list_collection_names()
        selected_collection = st.selectbox("Chọn lĩnh vực:", collections, key="analysis_collection")
    
    with col2:
        if 'city' in df.columns:
            cities = ['Tất cả'] + sorted(df['city'].unique().tolist())
            selected_city = st.selectbox("Thành phố:", cities, key="analysis_city")
    
    with col3:
        if 'salary_avg_million_vnd' in df.columns:
            salary_range = st.slider(
                "Khoảng lương (triệu VNĐ):",
                min_value=0,
                max_value=200,
                value=(0, 200),
                step=5,
                key="analysis_salary"
            )
    
    st.markdown("---")  # Ngăn cách giữa filters và charts
    
    # Apply filters
    if 'selected_collection' in locals() and selected_collection != 'Tất cả':
        df = load_data(selected_collection)
        df = process_data(df)
    
    if 'selected_city' in locals() and selected_city != 'Tất cả':
        df = df[df['city'] == selected_city]
    
    if 'salary_range' in locals():
        df = df[
            (df['salary_avg_million_vnd'] >= salary_range[0]) & 
            (df['salary_avg_million_vnd'] <= salary_range[1])
        ]
    
    # Row 1: Salary Analysis
    st.markdown("### Phân tích mức lương")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Histogram - Phân phối lương")
        if 'salary_avg_million_vnd' in df.columns:
            salary_data = df[df['salary_avg_million_vnd'] > 0]
            if not salary_data.empty:
                fig = px.histogram(
                    salary_data,
                    x='salary_avg_million_vnd',
                    nbins=20,
                    color_discrete_sequence=['#3b82f6']
                )
                fig.update_layout(
                    xaxis_title="Lương (triệu VNĐ)",
                    yaxis_title="Số lượng job",
                    showlegend=False,
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Boxplot - So sánh theo lĩnh vực")
        if 'category' in df.columns and 'salary_avg_million_vnd' in df.columns:
            salary_data = df[df['salary_avg_million_vnd'] > 0]
            if not salary_data.empty:
                fig = px.box(
                    salary_data,
                    x='category',
                    y='salary_avg_million_vnd',
                    color_discrete_sequence=['#10b981']
                )
                fig.update_layout(
                    xaxis_title="",
                    yaxis_title="Lương (triệu VNĐ)",
                    height=400
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
    
    # Row 2: Location Analysis
    st.markdown("### Phân tích địa điểm")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Mức lương trung bình theo thành phố")
        if 'city' in df.columns and 'salary_avg_million_vnd' in df.columns:
            salary_by_city = df[df['salary_avg_million_vnd'] > 0].groupby('city')['salary_avg_million_vnd'].mean().sort_values(ascending=True)
            if not salary_by_city.empty:
                fig = px.bar(
                    x=salary_by_city.values,
                    y=salary_by_city.index,
                    orientation='h',
                    color_discrete_sequence=['#f59e0b']
                )
                fig.update_layout(
                    xaxis_title="Lương trung bình (triệu VNĐ)",
                    yaxis_title="Thành phố",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Xu hướng việc làm theo thời gian")
        if 'update_date' in df.columns:
            df_time = df.dropna(subset=['update_date'])
            if not df_time.empty:
                df_time['week'] = df_time['update_date'].dt.to_period('W').dt.start_time
                weekly_jobs = df_time.groupby('week').size().reset_index(name='count')
                
                fig = px.line(
                    weekly_jobs,
                    x='week',
                    y='count',
                    markers=True,
                    color_discrete_sequence=['#3b82f6']
                )
                fig.update_layout(
                    xaxis_title="Tuần",
                    yaxis_title="Số lượng job",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Row 3: Experience & Skills
    st.markdown("### Phân tích kinh nghiệm & kỹ năng")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Mối quan hệ Kinh nghiệm - Lương")
        if all(col in df.columns for col in ['exp_numeric', 'salary_avg_million_vnd', 'city']):
            scatter_data = df[(df['salary_avg_million_vnd'] > 0) & (df['exp_numeric'] >= 0)]
            if not scatter_data.empty:
                try:
                    fig = px.scatter(
                        scatter_data,
                        x='exp_numeric',
                        y='salary_avg_million_vnd',
                        color='city',
                        size='salary_avg_million_vnd',
                        trendline="ols",
                        hover_data=['title', 'company']
                    )
                except ImportError:
                    fig = px.scatter(
                        scatter_data,
                        x='exp_numeric',
                        y='salary_avg_million_vnd',
                        color='city',
                        size='salary_avg_million_vnd',
                        hover_data=['title', 'company']
                    )
                
                fig.update_layout(
                    xaxis_title="Kinh nghiệm (năm)",
                    yaxis_title="Lương (triệu VNĐ)",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Top 15 kỹ năng được yêu cầu")
        if 'skills' in df.columns:
            all_skills = []
            for skills_list in df['skills'].dropna():
                if isinstance(skills_list, list):
                    all_skills.extend(skills_list)
                elif isinstance(skills_list, str):
                    all_skills.append(skills_list)
            
            if all_skills:
                skills_freq = {}
                for skill in all_skills:
                    skills_freq[skill] = skills_freq.get(skill, 0) + 1
                
                top_skills = sorted(skills_freq.items(), key=lambda x: x[1], reverse=True)[:15]
                skills_df = pd.DataFrame(top_skills, columns=['skill', 'count'])
                
                fig = px.bar(
                    skills_df,
                    x='count',
                    y='skill',
                    orientation='h',
                    color_discrete_sequence=['#06b6d4']
                )
                fig.update_layout(
                    xaxis_title="Số lượng job yêu cầu",
                    yaxis_title="",
                    height=400,
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig, use_container_width=True)

def show_storytelling_page(df, db):
    st.markdown("## 📖 Câu chuyện thị trường IT Việt Nam")
    
    # Quick stats overview
    total_jobs = len(df)
    companies = df['company'].nunique() if 'company' in df.columns else 0
    avg_salary = df['salary_avg_million_vnd'].mean() if 'salary_avg_million_vnd' in df.columns else 0
    categories = df['category'].nunique() if 'category' in df.columns else 0
    
    # Opening story
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 3rem;
        border-radius: 20px;
        text-align: center;
        margin: 2rem 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    ">
        <h1 style="color: white; margin-bottom: 1rem; font-size: 2.5rem;">🌟 Khám phá thị trường IT Việt Nam</h1>
        <p style="font-size: 1.3rem; margin: 0; opacity: 0.9;">
            Một hành trình qua những con số và insight thú vị từ hàng nghìn cơ hội việc làm
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key numbers section
    st.markdown("### 📊 Bức tranh tổng quan")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); 
                    color: white; padding: 2rem; border-radius: 15px; text-align: center; 
                    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3);">
            <h2 style="color: white; margin: 0; font-size: 2.5rem;">{total_jobs:,}</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Cơ hội việc làm</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                    color: white; padding: 2rem; border-radius: 15px; text-align: center;
                    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);">
            <h2 style="color: white; margin: 0; font-size: 2.5rem;">{companies:,}</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Công ty tuyển dụng</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
                    color: white; padding: 2rem; border-radius: 15px; text-align: center;
                    box-shadow: 0 8px 25px rgba(245, 158, 11, 0.3);">
            <h2 style="color: white; margin: 0; font-size: 2.5rem;">{avg_salary:.1f}M</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Lương trung bình</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
                    color: white; padding: 2rem; border-radius: 15px; text-align: center;
                    box-shadow: 0 8px 25px rgba(139, 92, 246, 0.3);">
            <h2 style="color: white; margin: 0; font-size: 2.5rem;">{categories}</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Lĩnh vực IT</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Story chapters
    st.markdown("---")
    
    # Chapter 1: Geography
    st.markdown("### 🗺️ Chương 1: Bản đồ cơ hội")
    
    if 'city' in df.columns:
        city_counts = df['city'].value_counts()
        top_city = city_counts.index[0]
        top_city_percent = (city_counts.iloc[0] / len(df)) * 100
        
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = px.pie(
                values=city_counts.values[:5],
                names=city_counts.index[:5],
                title="Phân bố việc làm IT theo thành phố",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown(f"""
            <div style="background: #f0f9ff; border-left: 5px solid #3b82f6; 
                        padding: 2rem; border-radius: 10px; height: 300px; 
                        display: flex; flex-direction: column; justify-content: center;">
                <h4 style="color: #1e40af; margin-bottom: 1rem;">💡 Insight</h4>
                <p style="font-size: 1.1rem; line-height: 1.6; margin: 0;">
                    <strong>{top_city}</strong> chiếm <strong>{top_city_percent:.1f}%</strong> thị trường,
                    cho thấy sự tập trung mạnh mẽ của ngành IT tại các đô thị lớn.
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # Chapter 2: Salary story
    st.markdown("### 💰 Chương 2: Cuộc đua lương bổng")
    
    if 'salary_avg_million_vnd' in df.columns:
        salary_data = df[df['salary_avg_million_vnd'] > 0]
        if not salary_data.empty:
            median_salary = salary_data['salary_avg_million_vnd'].median()
            high_salary_count = len(salary_data[salary_data['salary_avg_million_vnd'] >= 40])
            high_salary_percent = (high_salary_count / len(salary_data)) * 100
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.histogram(
                    salary_data,
                    x='salary_avg_million_vnd',
                    nbins=25,
                    title="Phân phối mức lương trong ngành IT",
                    color_discrete_sequence=['#3b82f6']
                )
                fig.update_layout(
                    xaxis_title="Mức lương (triệu VNĐ/tháng)",
                    yaxis_title="Số lượng vị trí",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown(f"""
                <div style="background: #f0fdf4; border-left: 5px solid #10b981; 
                            padding: 2rem; border-radius: 10px; height: 300px; 
                            display: flex; flex-direction: column; justify-content: center;">
                    <h4 style="color: #059669; margin-bottom: 1rem;">💰 Lương bổng</h4>
                    <p style="margin-bottom: 1rem;"><strong>Lương trung vị:</strong> {median_salary:.1f}M VNĐ</p>
                    <p style="margin: 0;"><strong>Lương cao (≥40M):</strong> {high_salary_percent:.1f}% vị trí</p>
                    <p style="font-size: 0.9rem; color: #6b7280; margin-top: 1rem;">
                        Cơ hội thu nhập cao vẫn còn hạn chế nhưng đáng kỳ vọng.
                    </p>
                </div>
                """, unsafe_allow_html=True)
    
    # Chapter 3: Experience journey
    st.markdown("### 🎯 Chương 3: Hành trình từ Fresher đến Senior")
    
    if 'experience_years' in df.columns:
        fresher_data = df[df['experience_years'].str.contains('không yêu cầu|intern', case=False, na=False)]
        fresher_count = len(fresher_data)
        fresher_percent = (fresher_count / len(df)) * 100
        
        # Experience vs Salary scatter
        if 'exp_numeric' in df.columns:
            scatter_data = df[(df['salary_avg_million_vnd'] > 0) & (df['exp_numeric'] >= 0)]
            if not scatter_data.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    fig = px.scatter(
                        scatter_data,
                        x='exp_numeric',
                        y='salary_avg_million_vnd',
                        color='city' if 'city' in df.columns else None,
                        size='salary_avg_million_vnd',
                        title="Mối quan hệ Kinh nghiệm - Mức lương",
                        hover_data=['title', 'company'] if all(col in df.columns for col in ['title', 'company']) else None
                    )
                    fig.update_layout(
                        xaxis_title="Số năm kinh nghiệm",
                        yaxis_title="Mức lương (triệu VNĐ)",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background: #fef3c7; border-left: 5px solid #f59e0b; 
                                padding: 2rem; border-radius: 10px; height: 300px; 
                                display: flex; flex-direction: column; justify-content: center;">
                        <h4 style="color: #d97706; margin-bottom: 1rem;">🌱 Cơ hội Fresher</h4>
                        <p style="font-size: 1.2rem; margin-bottom: 1rem;">
                            <strong>{fresher_percent:.1f}%</strong> vị trí không yêu cầu kinh nghiệm
                        </p>
                        <p style="margin: 0; color: #92400e;">
                            {fresher_count:,} cơ hội cho người mới bắt đầu sự nghiệp IT
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Chapter 4: Skills that matter
    st.markdown("### 🚀 Chương 4: Kỹ năng vàng")
    
    if 'skills' in df.columns:
        all_skills = []
        for skills_list in df['skills'].dropna():
            if isinstance(skills_list, list):
                all_skills.extend(skills_list)
            elif isinstance(skills_list, str):
                all_skills.append(skills_list)
        
        if all_skills:
            skills_freq = {}
            for skill in all_skills:
                skills_freq[skill] = skills_freq.get(skill, 0) + 1
            
            top_skills = sorted(skills_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            skills_df = pd.DataFrame(top_skills, columns=['Kỹ năng', 'Số lượng job'])
            
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(
                    skills_df,
                    x='Số lượng job',
                    y='Kỹ năng',
                    orientation='h',
                    title="Top 10 kỹ năng được săn đón",
                    color_discrete_sequence=['#06b6d4']
                )
                fig.update_layout(
                    height=400,
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                top_skill = top_skills[0][0]
                top_skill_count = top_skills[0][1]
                st.markdown(f"""
                <div style="background: #ecfdf5; border-left: 5px solid #06b6d4; 
                            padding: 2rem; border-radius: 10px; height: 300px; 
                            display: flex; flex-direction: column; justify-content: center;">
                    <h4 style="color: #0891b2; margin-bottom: 1rem;">🎯 Kỹ năng #1</h4>
                    <p style="font-size: 1.3rem; margin-bottom: 1rem; font-weight: bold; color: #0891b2;">
                        {top_skill}
                    </p>
                    <p style="margin: 0;">
                        Được yêu cầu trong <strong>{top_skill_count}</strong> vị trí việc làm
                    </p>
                </div>
                """, unsafe_allow_html=True)
    
    # Final thoughts
    st.markdown("---")
    st.markdown("### 🎯 Kết luận và hành động")
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                color: white; padding: 3rem; border-radius: 20px; text-align: center; margin: 2rem 0;">
        <h3 style="color: white; margin-bottom: 1.5rem;">💡 Key Takeaways</h3>
        <div style="text-align: left; max-width: 800px; margin: 0 auto;">
            <p><strong>✅ Thị trường đang phát triển mạnh</strong> với hàng nghìn cơ hội đa dạng</p>
            <p><strong>✅ Cơ hội cho mọi level</strong> từ fresher đến senior</p>
            <p><strong>✅ Mức lương cạnh tranh</strong> và có tiềm năng tăng theo kinh nghiệm</p>
            <p><strong>✅ Kỹ năng là chìa khóa</strong> thành công trong ngành</p>
            <p><strong>✅ Tập trung địa lý</strong> tại các thành phố lớn</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action items
    st.markdown("""
    <div style="background: #1f2937; color: white; padding: 2rem; border-radius: 15px; margin: 2rem 0;">
        <h4 style="color: #60a5fa; margin-bottom: 1rem;">🚀 Hành động ngay hôm nay:</h4>
        <ol style="padding-left: 1.5rem; line-height: 1.8;">
            <li>Xác định kỹ năng phù hợp với xu hướng thị trường</li>
            <li>Xây dựng portfolio mạnh với các project thực tế</li>
            <li>Networking và kết nối với cộng đồng IT</li>
            <li>Cập nhật kiến thức thường xuyên theo công nghệ mới</li>
            <li>Chuẩn bị sẵn sàng cho những cơ hội tuyệt vời!</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

def show_advanced_page(df, db):
    
    # Filters - hiển thị thẳng
    st.markdown("### Bộ lọc dữ liệu")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        collections = ["Tất cả"] + db.list_collection_names()
        selected_collection = st.selectbox("Chọn lĩnh vực:", collections, key="advanced_collection")
    
    with col2:
        if 'city' in df.columns:
            cities = ['Tất cả'] + sorted(df['city'].unique().tolist())
            selected_city = st.selectbox("Thành phố:", cities, key="advanced_city")
    
    with col3:
        if 'salary_avg_million_vnd' in df.columns:
            salary_range = st.slider(
                "Khoảng lương (triệu VNĐ):",
                min_value=0,
                max_value=200,
                value=(0, 200),
                step=5,
                key="advanced_salary"
            )
    
    st.markdown("---")  # Ngăn cách giữa filters và charts
    
    # Apply filters
    if 'selected_collection' in locals() and selected_collection != 'Tất cả':
        df = load_data(selected_collection)
        df = process_data(df)
    
    if 'selected_city' in locals() and selected_city != 'Tất cả':
        df = df[df['city'] == selected_city]
    
    if 'salary_range' in locals():
        df = df[
            (df['salary_avg_million_vnd'] >= salary_range[0]) & 
            (df['salary_avg_million_vnd'] <= salary_range[1])
        ]
    
    # Row 1: Companies & Advanced Analysis
    st.markdown("### Phân tích công ty & tương quan")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Top 15 công ty tuyển dụng")
        if 'company' in df.columns:
            top_companies = df['company'].value_counts().head(15)
            fig = px.bar(
                x=top_companies.values,
                y=top_companies.index,
                orientation='h',
                color_discrete_sequence=['#84cc16']
            )
            fig.update_layout(
                xaxis_title="Số lượng job",
                yaxis_title="",
                height=400,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Ma trận tương quan")
        numeric_data = {}
        if 'salary_avg_million_vnd' in df.columns:
            numeric_data['Lương'] = df['salary_avg_million_vnd']
        if 'exp_numeric' in df.columns:
            numeric_data['Kinh nghiệm'] = df['exp_numeric']
        
        if len(numeric_data) >= 2:
            le = LabelEncoder()
            if 'category' in df.columns:
                numeric_data['Lĩnh vực'] = le.fit_transform(df['category'].fillna('Unknown'))
            if 'city' in df.columns:
                numeric_data['Thành phố'] = le.fit_transform(df['city'].fillna('Unknown'))
            
            corr_df = pd.DataFrame(numeric_data)
            corr_matrix = corr_df.corr()
            
            fig = px.imshow(
                corr_matrix,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Row 2: Treemap & Violin Plot
    st.markdown("### Phân tích phân bố đa chiều")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Treemap - Phân bố đa chiều")
        if 'category' in df.columns and 'city' in df.columns:
            treemap_data = df.groupby(['category', 'city']).agg({
                'salary_avg_million_vnd': 'mean',
                'title': 'count'
            }).reset_index()
            treemap_data.columns = ['category', 'city', 'avg_salary', 'job_count']
            treemap_data = treemap_data[treemap_data['job_count'] > 0]
            
            if not treemap_data.empty:
                fig = px.treemap(
                    treemap_data,
                    path=[px.Constant("Việc làm IT"), 'category', 'city'],
                    values='job_count',
                    color='avg_salary',
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Violin Plot - Phân phối lương chi tiết")
        if 'category' in df.columns and 'salary_avg_million_vnd' in df.columns:
            salary_data = df[df['salary_avg_million_vnd'] > 0]
            if not salary_data.empty:
                fig = px.violin(
                    salary_data,
                    x='category',
                    y='salary_avg_million_vnd',
                    box=True,
                    color_discrete_sequence=['#8b5cf6']
                )
                fig.update_layout(
                    xaxis_title="Lĩnh vực",
                    yaxis_title="Lương (triệu VNĐ)",
                    height=400
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)

def main():
    # Header nghiêm túc
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1>Job Data Analytics Dashboard</h1>
        <p style="font-size: 1.2rem; color: #6b7280;">Phân tích xu hướng việc làm IT tại Việt Nam</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar chỉ có navigation
    st.sidebar.title("TopCV")
    
    # Initialize session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Overview'
    
    # Simple navigation without complex state handling
    pages = ["Overview", "Analysis", "Advanced", "Story"]
    page_labels = ["Tổng quan", "Phân tích", "Nâng cao", "Storytelling"]
    
    selected_page = st.sidebar.radio(
        "",
        pages,
        format_func=lambda x: page_labels[pages.index(x)],
        key="main_navigation"
    )
    
    # Update session state immediately
    st.session_state.current_page = selected_page
    
    # Load database connection
    db = init_connection()
    if db is None:
        st.error("Không thể kết nối database. Vui lòng kiểm tra MongoDB.")
        return
    
    # Load initial data
    with st.spinner("Đang tải dữ liệu..."):
        df = load_data()
        
    if df.empty:
        st.error("Không có dữ liệu để hiển thị!")
        return
    
    df = process_data(df)
    
    # Show selected page based on current selection
    if selected_page == "Overview":
        show_overview_page(df, db)
    elif selected_page == "Analysis":
        show_analysis_page(df, db)
    elif selected_page == "Advanced":
        show_advanced_page(df, db)
    elif selected_page == "Story":
        show_storytelling_page(df, db)

if __name__ == "__main__":
    main()