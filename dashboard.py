import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from pymongo import MongoClient
import re
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="Job Data Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for clean white-blue theme
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        margin-bottom: 1rem;
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
        font-size: 2.2rem;
        font-weight: bold;
        margin: 0;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0;
    }
    h1 {
        color: #1e40af;
        font-weight: 700;
        text-align: center;
    }
    h2, h3 {
        color: #3730a3;
        font-weight: 600;
    }
    .stSelectbox > div > div {
        background-color: #f1f5f9;
    }
</style>
""", unsafe_allow_html=True)

# Database connection
@st.cache_resource
def init_connection():
    """Initialize MongoDB connection"""
    try:
        client = MongoClient("mongodb://root:123456@localhost:27017/")
        db = client.job_data
        # Test connection
        db.list_collection_names()
        return db
    except Exception as e:
        st.error(f"Lỗi kết nối database: {e}")
        return None

@st.cache_data(ttl=300)
def load_data(collection_name=None):
    """Load data from MongoDB"""
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
        
        return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame()

def clean_salary_data(df):
    """Clean và filter salary data để loại bỏ outliers ảo"""
    if df.empty or 'salary_avg_million_vnd' not in df.columns:
        return df
    
    # Convert to numeric
    df['salary_avg_million_vnd'] = pd.to_numeric(df['salary_avg_million_vnd'], errors='coerce').fillna(0)
    
    # Log số lượng data trước khi filter
    original_count = len(df)
    high_salary_count = len(df[df['salary_avg_million_vnd'] > 200])
    
    if high_salary_count > 0:
        st.sidebar.info(f"⚠️ Đã loại bỏ {high_salary_count} job có lương > 200M (dữ liệu không hợp lý)")
    
    # Filter chỉ lấy lương từ 0-200 triệu (thực tế)
    df_filtered = df[df['salary_avg_million_vnd'] <= 200].copy()
    
    # Log kết quả
    filtered_count = len(df_filtered)
    st.sidebar.success(f"✅ Sử dụng {filtered_count}/{original_count} jobs với lương ≤ 200M")
    
    return df_filtered

def preprocess_data(df):
    """Chuẩn hóa và xử lý dữ liệu"""
    if df.empty:
        return df
    
    # Clean salary data first
    df = clean_salary_data(df)
    
    # Xử lý ngày tháng
    if 'update_date' in df.columns:
        df['update_date'] = pd.to_datetime(df['update_date'], errors='coerce')
    
    # Tạo salary ranges thực tế
    if 'salary_avg_million_vnd' in df.columns:
        df['salary_range'] = pd.cut(
            df['salary_avg_million_vnd'], 
            bins=[0, 8, 15, 25, 40, 200], 
            labels=['< 8M', '8-15M', '15-25M', '25-40M', '40M+'],
            include_lowest=True
        )
    
    # Extract city
    if 'location' in df.columns:
        def extract_city(location):
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
        
        df['city'] = df['location'].apply(extract_city)
    
    # Extract experience numeric
    def extract_experience_years(exp_text):
        if pd.isna(exp_text):
            return 0
        exp_str = str(exp_text).lower()
        if 'không yêu cầu' in exp_str or 'intern' in exp_str:
            return 0
        numbers = re.findall(r'\d+', exp_str)
        if numbers:
            return min(int(numbers[0]), 20)  # Cap at 20 years max
        return 1
    
    if 'experience_years' in df.columns:
        df['exp_numeric'] = df['experience_years'].apply(extract_experience_years)
    
    return df

def create_metric_card(title, value, color_class=""):
    return f"""
    <div class="metric-card {color_class}">
        <p class="metric-value">{value}</p>
        <p class="metric-label">{title}</p>
    </div>
    """

def main():
    # Header
    st.title("📊 Job Data Analytics Dashboard")
    st.markdown("### Phân tích dữ liệu việc làm IT tại Việt Nam (Lương thực tế: 0-200M VNĐ)")
    
    # Sidebar
    st.sidebar.title("🎛️ Bộ lọc")
    
    # Load collections
    db = init_connection()
    if db is None:
        st.error("❌ Không thể kết nối database!")
        return
    
    collections = ["Tất cả"] + db.list_collection_names()
    selected_collection = st.sidebar.selectbox("📂 Chọn lĩnh vực:", collections)
    
    # Load and process data
    with st.spinner("🔄 Đang tải và làm sạch dữ liệu..."):
        df = load_data(selected_collection)
        if df.empty:
            st.error("❌ Không có dữ liệu!")
            return
        
        df = preprocess_data(df)
    
    # Additional filters
    st.sidebar.markdown("### 🔍 Bộ lọc nâng cao")
    
    # City filter
    if 'city' in df.columns:
        cities = ['Tất cả'] + sorted(df['city'].unique().tolist())
        selected_city = st.sidebar.selectbox("📍 Thành phố:", cities)
        if selected_city != 'Tất cả':
            df = df[df['city'] == selected_city]
    
    # Realistic salary filter
    if 'salary_avg_million_vnd' in df.columns and len(df) > 0:
        max_salary = min(int(df['salary_avg_million_vnd'].max()), 200)
        salary_range = st.sidebar.slider(
            "💰 Khoảng lương (triệu VNĐ):",
            min_value=0,
            max_value=max_salary,
            value=(0, max_salary)
        )
        df = df[
            (df['salary_avg_million_vnd'] >= salary_range[0]) & 
            (df['salary_avg_million_vnd'] <= salary_range[1])
        ]
    
    # Summary metrics
    st.markdown("## 📈 Tổng quan")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(create_metric_card(
            "Tổng số việc làm", 
            f"{len(df):,}",
            ""
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
        max_salary = df['salary_avg_million_vnd'].max() if 'salary_avg_million_vnd' in df.columns else 0
        st.markdown(create_metric_card(
            "Lương cao nhất", 
            f"{max_salary:.1f}M",
            "orange"
        ), unsafe_allow_html=True)
    
    # Charts section
    st.markdown("## 📊 Biểu đồ phân tích")
    
    # Tab layout
    tab1, tab2, tab3 = st.tabs(["💰 Phân tích lương", "📍 Địa điểm & Kinh nghiệm", "🛠️ Skills & Companies"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Histogram - Phân phối lương thực tế")
            if 'salary_avg_million_vnd' in df.columns:
                salary_data = df[df['salary_avg_million_vnd'] > 0]
                if not salary_data.empty:
                    fig_hist = px.histogram(
                        salary_data,
                        x='salary_avg_million_vnd',
                        nbins=25,
                        title="",
                        color_discrete_sequence=['#3b82f6'],
                        labels={'salary_avg_million_vnd': 'Lương (triệu VNĐ)', 'count': 'Số lượng job'}
                    )
                    fig_hist.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig_hist, use_container_width=True)
                    
                    # Stats
                    st.info(f"""
                    📊 **Thống kê lương:**
                    - Trung bình: {salary_data['salary_avg_million_vnd'].mean():.1f}M
                    - Trung vị: {salary_data['salary_avg_million_vnd'].median():.1f}M  
                    - Min: {salary_data['salary_avg_million_vnd'].min():.1f}M
                    - Max: {salary_data['salary_avg_million_vnd'].max():.1f}M
                    """)
        
        with col2:
            st.markdown("### Boxplot - So sánh theo lĩnh vực")
            if 'category' in df.columns and 'salary_avg_million_vnd' in df.columns:
                salary_by_cat = df[df['salary_avg_million_vnd'] > 0]
                if not salary_by_cat.empty:
                    fig_box = px.box(
                        salary_by_cat,
                        x='category',
                        y='salary_avg_million_vnd',
                        title="",
                        color_discrete_sequence=['#10b981']
                    )
                    fig_box.update_layout(
                        xaxis_title="Lĩnh vực",
                        yaxis_title="Lương (triệu VNĐ)",
                        height=400
                    )
                    fig_box.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_box, use_container_width=True)
        
        # Salary ranges
        st.markdown("### Phân bố theo khoảng lương")
        if 'salary_range' in df.columns:
            range_counts = df['salary_range'].value_counts().sort_index()
            fig_range = px.bar(
                x=range_counts.index,
                y=range_counts.values,
                title="",
                color_discrete_sequence=['#8b5cf6'],
                labels={'x': 'Khoảng lương', 'y': 'Số lượng job'}
            )
            fig_range.update_layout(height=400)
            st.plotly_chart(fig_range, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Phân bố theo thành phố")
            if 'city' in df.columns:
                city_counts = df['city'].value_counts()
                fig_pie = px.pie(
                    values=city_counts.values,
                    names=city_counts.index,
                    title="",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.markdown("### Lương trung bình theo thành phố")
            if 'city' in df.columns and 'salary_avg_million_vnd' in df.columns:
                salary_by_city = df[df['salary_avg_million_vnd'] > 0].groupby('city')['salary_avg_million_vnd'].mean().sort_values(ascending=True)
                fig_city_salary = px.bar(
                    x=salary_by_city.values,
                    y=salary_by_city.index,
                    orientation='h',
                    title="",
                    color_discrete_sequence=['#f59e0b']
                )
                fig_city_salary.update_layout(
                    xaxis_title="Lương TB (triệu VNĐ)",
                    yaxis_title="Thành phố",
                    height=400
                )
                st.plotly_chart(fig_city_salary, use_container_width=True)
        
        # Experience vs Salary
        st.markdown("### Mối quan hệ Kinh nghiệm - Lương")
        if 'exp_numeric' in df.columns and 'salary_avg_million_vnd' in df.columns:
            exp_salary = df[(df['salary_avg_million_vnd'] > 0) & (df['exp_numeric'] >= 0)]
            if not exp_salary.empty:
                try:
                    fig_scatter = px.scatter(
                        exp_salary,
                        x='exp_numeric',
                        y='salary_avg_million_vnd',
                        color='city',
                        size='salary_avg_million_vnd',
                        title="",
                        trendline="ols",
                        hover_data=['title', 'company']
                    )
                except ImportError:
                    fig_scatter = px.scatter(
                        exp_salary,
                        x='exp_numeric',
                        y='salary_avg_million_vnd',
                        color='city',
                        size='salary_avg_million_vnd',
                        title="",
                        hover_data=['title', 'company']
                    )
                
                fig_scatter.update_layout(
                    xaxis_title="Kinh nghiệm (năm)",
                    yaxis_title="Lương (triệu VNĐ)",
                    height=500
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Top kỹ năng được yêu cầu")
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
                    
                    fig_skills = px.bar(
                        skills_df,
                        x='count',
                        y='skill',
                        orientation='h',
                        title="",
                        color_discrete_sequence=['#06b6d4']
                    )
                    fig_skills.update_layout(
                        xaxis_title="Số lượng job",
                        yaxis_title="Kỹ năng",
                        height=500,
                        yaxis={'categoryorder': 'total ascending'}
                    )
                    st.plotly_chart(fig_skills, use_container_width=True)
        
        with col2:
            st.markdown("### Top công ty tuyển dụng")
            if 'company' in df.columns:
                top_companies = df['company'].value_counts().head(15)
                fig_companies = px.bar(
                    x=top_companies.values,
                    y=top_companies.index,
                    orientation='h',
                    title="",
                    color_discrete_sequence=['#84cc16']
                )
                fig_companies.update_layout(
                    xaxis_title="Số lượng job",
                    yaxis_title="Công ty",
                    height=500,
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig_companies, use_container_width=True)
        
        # Xu hướng thời gian
        st.markdown("### Xu hướng việc làm theo thời gian")
        if 'update_date' in df.columns:
            df_time = df.dropna(subset=['update_date'])
            if not df_time.empty:
                df_time['week'] = df_time['update_date'].dt.to_period('W').dt.start_time
                weekly_jobs = df_time.groupby('week').size().reset_index(name='count')
                
                fig_trend = px.line(
                    weekly_jobs,
                    x='week',
                    y='count',
                    title="",
                    markers=True,
                    color_discrete_sequence=['#3b82f6']
                )
                fig_trend.update_layout(
                    xaxis_title="Tuần",
                    yaxis_title="Số lượng job",
                    height=400
                )
                st.plotly_chart(fig_trend, use_container_width=True)
    
    # Data insights
    st.markdown("## 💡 Những con số nổi bật")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'company' in df.columns and len(df) > 0:
            top_company = df['company'].value_counts().index[0]
            top_company_count = df['company'].value_counts().iloc[0]
            st.metric("Công ty tuyển nhiều nhất", top_company, f"{top_company_count} jobs")
    
    with col2:
        if 'category' in df.columns and len(df) > 0:
            top_category = df['category'].value_counts().index[0]
            top_category_count = df['category'].value_counts().iloc[0]
            st.metric("Lĩnh vực hot nhất", top_category, f"{top_category_count} jobs")
    
    with col3:
        if 'city' in df.columns and len(df) > 0:
            top_city = df['city'].value_counts().index[0]
            top_city_count = df['city'].value_counts().iloc[0]
            st.metric("Thành phố có nhiều job nhất", top_city, f"{top_city_count} jobs")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6b7280; padding: 1rem;">
        <p><strong>📊 Job Data Analytics Dashboard</strong></p>
        <p>Powered by Streamlit • Data from MongoDB • Built with ❤️</p>
        <p><em>✅ Đã lọc dữ liệu lương thực tế (0-200M VNĐ)</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()