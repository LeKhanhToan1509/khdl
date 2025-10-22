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

# Page config
st.set_page_config(
    page_title="Câu chuyện thị trường IT Việt Nam",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS cho storytelling page
st.markdown("""
<style>
    /* Main layout */
    .main {
        padding-top: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    /* Story container */
    .story-container {
        background: white;
        border-radius: 20px;
        padding: 3rem;
        margin: 2rem auto;
        max-width: 1200px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
    }
    
    /* Title styling */
    .story-title {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    
    .story-subtitle {
        font-size: 1.3rem;
        text-align: center;
        color: #6b7280;
        margin-bottom: 3rem;
        font-style: italic;
    }
    
    /* Chapter styling */
    .chapter {
        margin: 4rem 0;
        padding: 2rem;
        border-left: 5px solid #3b82f6;
        background: #f8fafc;
        border-radius: 10px;
    }
    
    .chapter-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 1rem;
    }
    
    .chapter-number {
        font-size: 1rem;
        color: #3b82f6;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    
    /* Insight boxes */
    .insight-box {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 2px solid #3b82f6;
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.15);
    }
    
    .insight-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e40af;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .insight-content {
        font-size: 1.1rem;
        color: #1e293b;
        line-height: 1.7;
    }
    
    /* Highlight numbers */
    .highlight-number {
        font-size: 2.5rem;
        font-weight: 800;
        color: #3b82f6;
        display: inline-block;
        margin: 0 0.5rem;
    }
    
    /* Quote styling */
    .quote {
        background: #f1f5f9;
        border-left: 5px solid #f59e0b;
        padding: 2rem;
        margin: 2rem 0;
        border-radius: 10px;
        font-style: italic;
        font-size: 1.2rem;
        color: #374151;
    }
    
    /* Stats grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 2rem;
        margin: 2rem 0;
    }
    
    .stat-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 8px 30px rgba(0,0,0,0.1);
        border: 1px solid #e5e7eb;
        transition: transform 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
    }
    
    .stat-value {
        font-size: 3rem;
        font-weight: 800;
        color: #3b82f6;
        margin-bottom: 0.5rem;
    }
    
    .stat-label {
        font-size: 1.1rem;
        color: #6b7280;
        font-weight: 500;
    }
    
    /* Call to action */
    .cta-section {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        padding: 3rem;
        border-radius: 20px;
        text-align: center;
        margin: 4rem 0;
    }
    
    .cta-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    .cta-text {
        font-size: 1.3rem;
        margin-bottom: 2rem;
        opacity: 0.9;
    }
    
    /* Hide Streamlit elements */
    .stApp > header {
        background: transparent;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Timeline */
    .timeline-item {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .timeline-title {
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    
    .timeline-content {
        color: #4b5563;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# Database connection functions
@st.cache_resource
def init_connection():
    try:
        client = MongoClient("mongodb://root:123456@localhost:27017/")
        db = client.job_data
        db.list_collection_names()
        return db
    except Exception as e:
        st.error(f"❌ Lỗi kết nối database: {e}")
        return None

@st.cache_data(ttl=300)
def load_data():
    db = init_connection()
    if db is None:
        return pd.DataFrame()
    
    try:
        all_data = []
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
        st.error(f"❌ Lỗi tải dữ liệu: {e}")
        return pd.DataFrame()

def process_data(df):
    if df.empty:
        return df
    
    # Process salary
    if 'salary_avg_million_vnd' in df.columns:
        df['salary_avg_million_vnd'] = pd.to_numeric(df['salary_avg_million_vnd'], errors='coerce').fillna(0)
        df = df[df['salary_avg_million_vnd'] <= 200].copy()
        df.loc[df['salary_avg_million_vnd'] < 0, 'salary_avg_million_vnd'] = 0
    
    # Process city
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
    
    # Process experience
    def get_exp_numeric(exp_text):
        if pd.isna(exp_text):
            return 0
        exp_text = str(exp_text).lower()
        if 'không yêu cầu' in exp_text:
            return 0
        numbers = re.findall(r'\d+', exp_text)
        if numbers:
            exp_years = int(numbers[0])
            return min(exp_years, 20)
        return 1
    
    if 'experience_years' in df.columns:
        df['exp_numeric'] = df['experience_years'].apply(get_exp_numeric)
    
    return df

def main():
    # Load and process data
    df = load_data()
    if df.empty:
        st.error("Không có dữ liệu để hiển thị!")
        return
    
    df = process_data(df)
    
    # Main story container
    st.markdown('<div class="story-container">', unsafe_allow_html=True)
    
    # Title section
    st.markdown("""
    <div class="story-title">Câu chuyện thị trường IT Việt Nam 2025</div>
    <div class="story-subtitle">Hành trình khám phá sâu sắc về cơ hội, thách thức và tương lai của ngành công nghệ</div>
    """, unsafe_allow_html=True)
    
    # Executive Summary
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); 
                color: white; padding: 3rem; border-radius: 20px; margin: 2rem 0; 
                box-shadow: 0 15px 35px rgba(30, 58, 138, 0.3);">
        <h2 style="color: white; margin-bottom: 2rem; text-align: center; font-size: 2rem;">📋 Tóm tắt điều hành</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; text-align: left;">
            <div>
                <h4 style="color: #93c5fd; margin-bottom: 1rem;">🎯 Mục tiêu nghiên cứu</h4>
                <p style="line-height: 1.8; margin: 0;">Phân tích toàn diện thị trường việc làm IT tại Việt Nam, 
                từ đó đưa ra những nhận định chiến lược về xu hướng tuyển dụng, mức lương, 
                kỹ năng được săn đón và cơ hội phát triển nghề nghiệp.</p>
            </div>
            <div>
                <h4 style="color: #93c5fd; margin-bottom: 1rem;">📊 Phạm vi dữ liệu</h4>
                <p style="line-height: 1.8; margin: 0;">Nghiên cứu dựa trên dữ liệu thực tế từ các 
                nền tảng tuyển dụng hàng đầu, bao gồm thông tin về vị trí, lương bổng, địa điểm, 
                kinh nghiệm yêu cầu và kỹ năng cần thiết.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Introduction
    st.markdown("""
    <div class="quote">
    "Trong bối cảnh chuyển đổi số mạnh mẽ và sự bùng nổ của trí tuệ nhân tạo, 
    thị trường IT Việt Nam đang chứng kiến những thay đổi căn bản về cách thức tuyển dụng, 
    yêu cầu kỹ năng và cơ hội nghề nghiệp. Đây không chỉ là cuộc cách mạng công nghệ, 
    mà còn là cuộc cách mạng nhân tài - nơi mà những con số kể lên câu chuyện đầy thú vị 
    về hiện tại và tương lai của ngành công nghệ thông tin."
    </div>
    """, unsafe_allow_html=True)
    
    # Market Context
    st.markdown("""
    <div style="background: #f8fafc; border: 2px solid #e2e8f0; border-radius: 15px; 
                padding: 2rem; margin: 2rem 0;">
        <h3 style="color: #1e293b; margin-bottom: 1.5rem;">🌍 Bối cảnh thị trường</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.5rem;">
            <div style="text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🚀</div>
                <h4 style="color: #3b82f6; margin-bottom: 0.5rem;">Chuyển đổi số</h4>
                <p style="font-size: 0.9rem; color: #64748b; margin: 0;">
                    Các doanh nghiệp tăng cường đầu tư công nghệ
                </p>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🤖</div>
                <h4 style="color: #3b82f6; margin-bottom: 0.5rem;">AI Revolution</h4>
                <p style="font-size: 0.9rem; color: #64748b; margin: 0;">
                    Trí tuệ nhân tạo thay đổi landscape công nghệ
                </p>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🌐</div>
                <h4 style="color: #3b82f6; margin-bottom: 0.5rem;">Remote Work</h4>
                <p style="font-size: 0.9rem; color: #64748b; margin: 0;">
                    Làm việc từ xa trở thành xu hướng chủ đạo
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Chapter 1: Bức tranh tổng quan
    st.markdown("""
    <div class="chapter">
        <div class="chapter-number">Chương 1</div>
        <div class="chapter-title">🌟 Panorama thị trường IT Việt Nam</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Market size analysis
    st.markdown("""
    <div style="background: linear-gradient(135deg, #ecfeff 0%, #cffafe 100%); 
                border-left: 5px solid #06b6d4; padding: 2rem; border-radius: 15px; margin: 2rem 0;">
        <h4 style="color: #0891b2; margin-bottom: 1rem;">📈 Quy mô thị trường</h4>
        <p style="font-size: 1.1rem; line-height: 1.8; margin: 0; color: #164e63;">
            Thị trường IT Việt Nam đang trong giai đoạn tăng trưởng mạnh mẽ, được thúc đẩy bởi 
            chính sách số hóa quốc gia và nhu cầu chuyển đổi số của doanh nghiệp. 
            Việt Nam đã trở thành một trong những điểm đến hấp dẫn cho đầu tư công nghệ 
            và phát triển nhân lực IT chất lượng cao trong khu vực Đông Nam Á.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Statistics overview
    total_jobs = len(df)
    companies = df['company'].nunique() if 'company' in df.columns else 0
    avg_salary = df['salary_avg_million_vnd'].mean() if 'salary_avg_million_vnd' in df.columns else 0
    categories = df['category'].nunique() if 'category' in df.columns else 0
    
    # Stats grid
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{total_jobs:,}</div>
            <div class="stat-label">Cơ hội việc làm</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{companies:,}</div>
            <div class="stat-label">Công ty tuyển dụng</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{avg_salary:.1f}M</div>
            <div class="stat-label">Lương trung bình</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{categories}</div>
            <div class="stat-label">Lĩnh vực IT</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Insight box 1
    st.markdown(f"""
    <div class="insight-box">
        <div class="insight-title">🔍 Phân tích sâu về quy mô thị trường</div>
        <div class="insight-content">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 1.5rem;">
                <div>
                    <h5 style="color: #1e40af; margin-bottom: 0.5rem;">Mật độ cơ hội</h5>
                    <p style="margin: 0;">Với <span class="highlight-number">{total_jobs:,}</span> vị trí việc làm 
                    từ <span class="highlight-number">{companies:,}</span> công ty, tỷ lệ job/công ty 
                    đạt <strong>{(total_jobs/companies if companies > 0 else 0):.1f}</strong> - 
                    cho thấy mỗi công ty trung bình tuyển dụng nhiều vị trí IT.</p>
                </div>
                <div>
                    <h5 style="color: #1e40af; margin-bottom: 0.5rem;">Đa dạng lĩnh vực</h5>
                    <p style="margin: 0;">Thị trường phủ sóng <span class="highlight-number">{categories}</span> 
                    lĩnh vực IT khác nhau, từ phát triển phần mềm truyền thống đến các công nghệ 
                    mới nổi như AI/ML, Blockchain, và IoT.</p>
                </div>
            </div>
            <div style="background: #eff6ff; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #3b82f6;">
                <h5 style="color: #1e40af; margin-bottom: 0.5rem;">💡 Insight chính</h5>
                <p style="margin: 0;">Sự đa dạng này không chỉ phản ánh tính năng động của thị trường 
                mà còn tạo ra nhiều cơ hội cho các chuyên gia IT ở mọi cấp độ và chuyên môn khác nhau. 
                Từ các startup công nghệ đến các tập đoàn đa quốc gia, mọi loại hình doanh nghiệp 
                đều đang tích cực tuyển dụng nhân tài IT.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Market trends analysis
    st.markdown("""
    <div style="margin: 3rem 0;">
        <h4 style="color: #1e293b; margin-bottom: 2rem; text-align: center;">📊 Xu hướng thị trường theo thời gian</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Time-based analysis if data available
    if 'update_date' in df.columns:
        df_time = df.dropna(subset=['update_date'])
        if not df_time.empty:
            # Monthly trend
            df_time['month'] = df_time['update_date'].dt.to_period('M')
            monthly_jobs = df_time.groupby('month').size().reset_index(name='job_count')
            monthly_jobs['month_str'] = monthly_jobs['month'].astype(str)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=monthly_jobs['month_str'], 
                y=monthly_jobs['job_count'],
                mode='lines+markers',
                name='Số lượng job',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=8, color='#1d4ed8')
            ))
            
            fig.update_layout(
                title="Xu hướng đăng tuyển việc làm IT theo tháng",
                xaxis_title="Tháng",
                yaxis_title="Số lượng job",
                height=400,
                template="plotly_white"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Growth analysis
            if len(monthly_jobs) > 1:
                latest_month = monthly_jobs.iloc[-1]['job_count']
                previous_month = monthly_jobs.iloc[-2]['job_count'] if len(monthly_jobs) > 1 else latest_month
                growth_rate = ((latest_month - previous_month) / previous_month * 100) if previous_month > 0 else 0
                
                st.markdown(f"""
                <div style="background: {'#dcfce7' if growth_rate > 0 else '#fef2f2'}; 
                            border-left: 5px solid {'#16a34a' if growth_rate > 0 else '#dc2626'}; 
                            padding: 1.5rem; border-radius: 10px; margin: 1rem 0;">
                    <h5 style="color: {'#15803d' if growth_rate > 0 else '#dc2626'}; margin-bottom: 0.5rem;">
                        {'📈' if growth_rate > 0 else '📉'} Tăng trưởng tháng gần nhất
                    </h5>
                    <p style="margin: 0; font-size: 1.1rem;">
                        Thị trường {' tăng trưởng' if growth_rate > 0 else 'giảm'} 
                        <strong>{abs(growth_rate):.1f}%</strong> so với tháng trước, 
                        cho thấy {'sự năng động và tiềm năng phát triển mạnh mẽ' if growth_rate > 0 else 'sự điều chỉnh tự nhiên của thị trường'}.
                    </p>
                </div>
                """, unsafe_allow_html=True)
    
    # Chapter 2: Phân tích địa lý
    st.markdown("""
    <div class="chapter">
        <div class="chapter-number">Chương 2</div>
        <div class="chapter-title">🗺️ Bản đồ cơ hội: Địa lý kinh tế IT</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Geographic introduction
    st.markdown("""
    <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); 
                border-left: 5px solid #f59e0b; padding: 2rem; border-radius: 15px; margin: 2rem 0;">
        <h4 style="color: #92400e; margin-bottom: 1rem;">🌏 Phân bố địa lý và ý nghĩa kinh tế</h4>
        <p style="font-size: 1.1rem; line-height: 1.8; margin: 0; color: #78350f;">
            Việc phân tích phân bố địa lý của các cơ hội việc làm IT không chỉ cho thấy nơi tập trung 
            các hoạt động công nghệ, mà còn phản ánh chiến lược phát triển kinh tế số của từng vùng miền. 
            Sự bất cân xứng trong phân bố này cũng mở ra những cơ hội đầu tư và phát triển tiềm năng.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # City analysis
    if 'city' in df.columns:
        city_counts = df['city'].value_counts()
        
        # Detailed city analysis
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Enhanced pie chart
            fig = px.pie(
                values=city_counts.values,
                names=city_counts.index,
                title="Phân bố cơ hội việc làm IT theo thành phố",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.4
            )
            fig.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Số job: %{value}<br>Tỷ lệ: %{percent}<extra></extra>'
            )
            fig.update_layout(
                height=500, 
                font_size=12,
                annotations=[dict(text='IT Jobs<br>Distribution', x=0.5, y=0.5, font_size=14, showarrow=False)]
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # City rankings and analysis
            st.markdown("""
            <div style="background: white; border: 2px solid #e5e7eb; border-radius: 15px; 
                        padding: 1.5rem; height: 450px; overflow-y: auto;">
                <h4 style="color: #374151; margin-bottom: 1rem; text-align: center;">🏆 Bảng xếp hạng thành phố</h4>
            """, unsafe_allow_html=True)
            
            for idx, (city, count) in enumerate(city_counts.head(8).items()):
                percentage = (count / len(df)) * 100
                rank_color = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444"][idx] if idx < 4 else "#6b7280"
                st.markdown(f"""
                <div style="display: flex; align-items: center; padding: 0.75rem; 
                            border-bottom: 1px solid #f3f4f6; background: {'#f8fafc' if idx % 2 == 0 else 'white'};">
                    <div style="background: {rank_color}; color: white; width: 30px; height: 30px; 
                                border-radius: 50%; display: flex; align-items: center; 
                                justify-content: center; font-weight: bold; margin-right: 1rem;">
                        {idx + 1}
                    </div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #1f2937;">{city}</div>
                        <div style="color: #6b7280; font-size: 0.9rem;">
                            {count:,} jobs ({percentage:.1f}%)
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Geographic insights
        top_city = city_counts.index[0]
        top_city_count = city_counts.iloc[0]
        top_city_percent = (top_city_count / len(df)) * 100
        
        # Top 3 cities analysis
        top_3_cities = city_counts.head(3)
        top_3_total = top_3_cities.sum()
        top_3_percent = (top_3_total / len(df)) * 100
        
        st.markdown(f"""
        <div class="insight-box">
            <div class="insight-title">📍 Phân tích địa lý chi tiết</div>
            <div class="insight-content">
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 2rem; margin-bottom: 2rem;">
                    <div style="text-align: center; padding: 1.5rem; background: #eff6ff; border-radius: 10px;">
                        <h3 style="color: #1e40af; margin: 0; font-size: 2rem;">{top_city_percent:.1f}%</h3>
                        <p style="margin: 0.5rem 0 0 0; font-weight: 600; color: #3730a3;">Thống trị của {top_city}</p>
                    </div>
                    <div style="text-align: center; padding: 1.5rem; background: #f0fdf4; border-radius: 10px;">
                        <h3 style="color: #166534; margin: 0; font-size: 2rem;">{top_3_percent:.1f}%</h3>
                        <p style="margin: 0.5rem 0 0 0; font-weight: 600; color: #15803d;">Top 3 thành phố</p>
                    </div>
                    <div style="text-align: center; padding: 1.5rem; background: #fef2f2; border-radius: 10px;">
                        <h3 style="color: #dc2626; margin: 0; font-size: 2rem;">{len(city_counts)}</h3>
                        <p style="margin: 0.5rem 0 0 0; font-weight: 600; color: #b91c1c;">Thành phố có cơ hội</p>
                    </div>
                </div>
                
                <div style="background: #f8fafc; padding: 2rem; border-radius: 10px; border-left: 4px solid #3b82f6;">
                    <h5 style="color: #1e40af; margin-bottom: 1rem;">🎯 Insight về tập trung địa lý</h5>
                    <p style="margin-bottom: 1rem;"><strong>Hiện tượng tập trung:</strong> 
                    {top_3_percent:.1f}% cơ hội việc làm IT tập trung tại 3 thành phố lớn nhất, 
                    cho thấy sự tập trung mạnh mẽ của các hoạt động công nghệ.</p>
                    
                    <p style="margin-bottom: 1rem;"><strong>Nguyên nhân:</strong> 
                    Hạ tầng công nghệ phát triển, hệ sinh thái startup sôi động, 
                    và sự hiện diện của các công ty công nghệ lớn.</p>
                    
                    <p style="margin: 0;"><strong>Cơ hội:</strong> 
                    Các thành phố nhỏ hơn đang dần nổi lên với chi phí sống thấp hơn 
                    và chính sách ưu đãi hấp dẫn cho các công ty công nghệ.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Salary comparison by city
        if 'salary_avg_million_vnd' in df.columns:
            salary_by_city = df[df['salary_avg_million_vnd'] > 0].groupby('city').agg({
                'salary_avg_million_vnd': ['mean', 'median', 'count']
            }).round(1)
            salary_by_city.columns = ['avg_salary', 'median_salary', 'job_count']
            salary_by_city = salary_by_city.sort_values('avg_salary', ascending=False).reset_index()
            
            st.markdown("### 💰 So sánh mức lương theo địa điểm")
            
            fig = go.Figure()
            
            # Add average salary bars
            fig.add_trace(go.Bar(
                name='Lương trung bình',
                x=salary_by_city['city'][:8],
                y=salary_by_city['avg_salary'][:8],
                marker_color='#3b82f6',
                yaxis='y',
                offsetgroup=1
            ))
            
            # Add median salary bars
            fig.add_trace(go.Bar(
                name='Lương trung vị',
                x=salary_by_city['city'][:8],
                y=salary_by_city['median_salary'][:8],
                marker_color='#10b981',
                yaxis='y',
                offsetgroup=2
            ))
            
            fig.update_layout(
                title='So sánh mức lương trung bình và trung vị theo thành phố',
                xaxis_title='Thành phố',
                yaxis_title='Mức lương (triệu VNĐ/tháng)',
                barmode='group',
                height=500,
                template='plotly_white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Salary-geography analysis
            highest_salary_city = salary_by_city.iloc[0]['city']
            highest_avg_salary = salary_by_city.iloc[0]['avg_salary']
            
            st.markdown(f"""
            <div style="background: #ecfdf5; border-left: 5px solid #10b981; 
                        padding: 2rem; border-radius: 10px; margin: 2rem 0;">
                <h4 style="color: #059669; margin-bottom: 1rem;">💎 Thành phố có mức lương cao nhất</h4>
                <p style="font-size: 1.2rem; margin-bottom: 1rem;">
                    <strong>{highest_salary_city}</strong> dẫn đầu với mức lương trung bình 
                    <span style="color: #059669; font-weight: bold; font-size: 1.3rem;">{highest_avg_salary:.1f}M VNĐ</span>
                </p>
                <p style="margin: 0; color: #065f46;">
                    Điều này phản ánh chi phí sống cao hơn nhưng cũng cho thấy sự cạnh tranh 
                    gay gắt về nhân tài và mức độ phát triển của ngành công nghệ tại đây.
                </p>
            </div>
            """, unsafe_allow_html=True)    # Chapter 3: Cuộc chiến lương bổng
    st.markdown("""
    <div class="chapter">
        <div class="chapter-number">Chương 3</div>
        <div class="chapter-title">💰 Anatomy của thang lương IT: Từ Entry-level đến C-suite</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Salary introduction
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); 
                border-left: 5px solid #0ea5e9; padding: 2rem; border-radius: 15px; margin: 2rem 0;">
        <h4 style="color: #0369a1; margin-bottom: 1rem;">💡 Tại sao phân tích lương lại quan trọng?</h4>
        <p style="font-size: 1.1rem; line-height: 1.8; margin-bottom: 1rem; color: #164e63;">
            Mức lương không chỉ phản ánh giá trị của một vị trí mà còn cho thấy sức khỏe của toàn bộ 
            hệ sinh thái công nghệ. Nó ảnh hưởng đến quyết định nghề nghiệp, xu hướng di chuyển nhân tài, 
            và sự cạnh tranh giữa các công ty.
        </p>
        <div style="background: #bae6fd; padding: 1rem; border-radius: 8px;">
            <p style="margin: 0; font-style: italic; color: #075985;">
                "Lương bổng trong IT không chỉ là con số, mà là câu chuyện về innovation, 
                scarcity của talent, và future value của công nghệ."
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Salary analysis
    if 'salary_avg_million_vnd' in df.columns:
        salary_data = df[df['salary_avg_million_vnd'] > 0]
        if not salary_data.empty:
            # Advanced salary statistics
            salary_stats = {
                'mean': salary_data['salary_avg_million_vnd'].mean(),
                'median': salary_data['salary_avg_million_vnd'].median(),
                'std': salary_data['salary_avg_million_vnd'].std(),
                'min': salary_data['salary_avg_million_vnd'].min(),
                'max': salary_data['salary_avg_million_vnd'].max(),
                'q25': salary_data['salary_avg_million_vnd'].quantile(0.25),
                'q75': salary_data['salary_avg_million_vnd'].quantile(0.75)
            }
            
            # Salary distribution with multiple views
            col1, col2 = st.columns(2)
            
            with col1:
                # Enhanced histogram
                fig = px.histogram(
                    salary_data,
                    x='salary_avg_million_vnd',
                    nbins=30,
                    title="Phân phối mức lương chi tiết",
                    color_discrete_sequence=['#3b82f6'],
                    opacity=0.7
                )
                
                # Add statistical lines
                fig.add_vline(x=salary_stats['median'], line_dash="dash", 
                             line_color="red", annotation_text=f"Trung vị: {salary_stats['median']:.1f}M")
                fig.add_vline(x=salary_stats['mean'], line_dash="dash", 
                             line_color="green", annotation_text=f"Trung bình: {salary_stats['mean']:.1f}M")
                
                fig.update_layout(
                    xaxis_title="Mức lương (triệu VNĐ/tháng)",
                    yaxis_title="Số lượng vị trí",
                    height=450,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Box plot for quartile analysis
                fig = go.Figure()
                fig.add_trace(go.Box(
                    y=salary_data['salary_avg_million_vnd'],
                    name='Phân phối lương',
                    boxpoints='outliers',
                    marker_color='#10b981',
                    fillcolor='rgba(16, 185, 129, 0.3)'
                ))
                
                fig.update_layout(
                    title="Box Plot - Phân tích tứ phân vị",
                    yaxis_title="Mức lương (triệu VNĐ)",
                    height=450,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Detailed salary brackets analysis
            salary_brackets = [
                (0, 8, "Entry Level", "#ef4444"),
                (8, 15, "Junior", "#f97316"), 
                (15, 25, "Mid-level", "#eab308"),
                (25, 40, "Senior", "#22c55e"),
                (40, 200, "Expert/Lead", "#8b5cf6")
            ]
            
            bracket_analysis = []
            for min_sal, max_sal, level, color in salary_brackets:
                count = len(salary_data[
                    (salary_data['salary_avg_million_vnd'] >= min_sal) & 
                    (salary_data['salary_avg_million_vnd'] < max_sal)
                ])
                percentage = (count / len(salary_data)) * 100
                bracket_analysis.append({
                    'level': level,
                    'range': f"{min_sal}-{max_sal}M",
                    'count': count,
                    'percentage': percentage,
                    'color': color
                })
            
            # Salary bracket visualization
            st.markdown("### 🎯 Phân tích theo khung lương")
            
            col1, col2 = st.columns([3, 2])
            
            with col1:
                fig = px.bar(
                    x=[b['level'] for b in bracket_analysis],
                    y=[b['count'] for b in bracket_analysis],
                    title="Phân bố số lượng việc làm theo khung lương",
                    color=[b['percentage'] for b in bracket_analysis],
                    color_continuous_scale='viridis',
                    text=[f"{b['count']} jobs<br>({b['percentage']:.1f}%)" for b in bracket_analysis]
                )
                fig.update_traces(textposition='inside')
                fig.update_layout(height=400, showlegend=False)
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("""
                <div style="background: white; border: 2px solid #e5e7eb; border-radius: 15px; 
                            padding: 1.5rem; height: 350px; overflow-y: auto;">
                    <h5 style="color: #374151; margin-bottom: 1rem; text-align: center;">📊 Chi tiết khung lương</h5>
                """, unsafe_allow_html=True)
                
                for bracket in bracket_analysis:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; padding: 0.75rem; 
                                margin-bottom: 0.5rem; background: {bracket['color']}20; 
                                border-left: 4px solid {bracket['color']}; border-radius: 8px;">
                        <div style="flex: 1;">
                            <div style="font-weight: 600; color: #1f2937;">{bracket['level']}</div>
                            <div style="color: #6b7280; font-size: 0.9rem;">
                                {bracket['range']} - {bracket['count']:,} jobs ({bracket['percentage']:.1f}%)
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Salary insights
            high_salary_count = len(salary_data[salary_data['salary_avg_million_vnd'] >= 40])
            high_salary_percent = (high_salary_count / len(salary_data)) * 100
            entry_level_count = len(salary_data[salary_data['salary_avg_million_vnd'] < 8])
            entry_level_percent = (entry_level_count / len(salary_data)) * 100
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="timeline-item">
                    <div class="timeline-title">💎 Premium Positions</div>
                    <div class="timeline-content">
                        <span class="highlight-number">{high_salary_percent:.1f}%</span> vị trí có lương ≥ 40M VNĐ
                        <br><strong>Insight:</strong> Cơ hội thu nhập cao vẫn khan hiếm, 
                        phần lớn tập trung ở các vị trí leadership, specialist, hoặc emerging tech.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="timeline-item">
                    <div class="timeline-title">🌱 Entry Opportunities</div>
                    <div class="timeline-content">
                        <span class="highlight-number">{entry_level_percent:.1f}%</span> vị trí entry-level (<8M)
                        <br><strong>Insight:</strong> Thị trường vẫn mở cửa cho người mới, 
                        nhưng cạnh tranh sẽ cao ở phân khúc này.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Salary distribution analysis
            st.markdown(f"""
            <div class="insight-box">
                <div class="insight-title">📈 Phân tích sâu về cấu trúc lương</div>
                <div class="insight-content">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 2rem; margin-bottom: 2rem;">
                        <div style="text-align: center; padding: 1.5rem; background: #fef3c7; border-radius: 10px;">
                            <h4 style="color: #92400e; margin: 0; font-size: 1.8rem;">{salary_stats['median']:.1f}M</h4>
                            <p style="margin: 0.5rem 0 0 0; font-weight: 600; color: #78350f;">Lương trung vị</p>
                            <small style="color: #a16207;">50% người kiếm được mức này</small>
                        </div>
                        <div style="text-align: center; padding: 1.5rem; background: #ecfdf5; border-radius: 10px;">
                            <h4 style="color: #166534; margin: 0; font-size: 1.8rem;">{salary_stats['q75']:.1f}M</h4>
                            <p style="margin: 0.5rem 0 0 0; font-weight: 600; color: #15803d;">Quartile 75%</p>
                            <small style="color: #059669;">Top 25% kiếm được mức này</small>
                        </div>
                        <div style="text-align: center; padding: 1.5rem; background: #eff6ff; border-radius: 10px;">
                            <h4 style="color: #1e40af; margin: 0; font-size: 1.8rem;">{(salary_stats['q75'] - salary_stats['q25']):.1f}M</h4>
                            <p style="margin: 0.5rem 0 0 0; font-weight: 600; color: #3730a3;">IQR Range</p>
                            <small style="color: #4f46e5;">Khoảng cách giữa Q1 và Q3</small>
                        </div>
                        <div style="text-align: center; padding: 1.5rem; background: #fef2f2; border-radius: 10px;">
                            <h4 style="color: #dc2626; margin: 0; font-size: 1.8rem;">{salary_stats['std']:.1f}M</h4>
                            <p style="margin: 0.5rem 0 0 0; font-weight: 600; color: #b91c1c;">Độ lệch chuẩn</p>
                            <small style="color: #dc2626;">Mức độ phân tán lương</small>
                        </div>
                    </div>
                    
                    <div style="background: #f8fafc; padding: 2rem; border-radius: 10px; border-left: 4px solid #3b82f6;">
                        <h5 style="color: #1e40af; margin-bottom: 1rem;">🔍 Những điều thú vị về lương IT</h5>
                        
                        <div style="margin-bottom: 1rem;">
                            <strong>💰 Sự chênh lệch lương:</strong> Độ lệch chuẩn {salary_stats['std']:.1f}M cho thấy 
                            sự chênh lệch lớn giữa các vị trí, phản ánh tính đa dạng của ngành và tầm quan trọng của specialization.
                        </div>
                        
                        <div style="margin-bottom: 1rem;">
                            <strong>📊 Phân phối không đều:</strong> Sự khác biệt giữa trung bình ({salary_stats['mean']:.1f}M) 
                            và trung vị ({salary_stats['median']:.1f}M) cho thấy một số vị trí có mức lương rất cao, kéo trung bình lên.
                        </div>
                        
                        <div style="margin: 0;">
                            <strong>🎯 Sweet spot:</strong> Khoảng {salary_stats['q25']:.1f}M - {salary_stats['q75']:.1f}M 
                            là "vùng an toàn" cho 50% giữa của thị trường, là mục tiêu thực tế cho đa số IT professionals.
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Chapter 4: Kinh nghiệm & Cơ hội
    st.markdown("""
    <div class="chapter">
        <div class="chapter-number">Chương 4</div>
        <div class="chapter-title">🎯 The Career Ladder: Hành trình từ Fresher đến Tech Leader</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Experience introduction
    st.markdown("""
    <div style="background: linear-gradient(135deg, #fef7cd 0%, #fef3c7 100%); 
                border-left: 5px solid #f59e0b; padding: 2rem; border-radius: 15px; margin: 2rem 0;">
        <h4 style="color: #92400e; margin-bottom: 1rem;">🚀 Career progression trong IT</h4>
        <p style="font-size: 1.1rem; line-height: 1.8; margin-bottom: 1rem; color: #78350f;">
            Ngành IT có lẽ là một trong những ngành có career ladder rõ ràng nhất, nhưng cũng đầy thách thức. 
            Mỗi bậc kinh nghiệm không chỉ đơn thuần về số năm làm việc, mà còn về depth of knowledge, 
            leadership skills, và khả năng adapt với công nghệ mới.
        </p>
        <div style="background: #fcd34d; padding: 1rem; border-radius: 8px;">
            <p style="margin: 0; font-style: italic; color: #92400e; font-weight: 500;">
                "Trong IT, 2 năm kinh nghiệm thực sự có thể quý hơn 5 năm kinh nghiệm bình thường. 
                Quality over quantity luôn là nguyên tắc vàng."
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Experience analysis
    if 'experience_years' in df.columns:
        # Count jobs for freshers
        fresher_data = df[df['experience_years'].str.contains('không yêu cầu|intern', case=False, na=False)]
        fresher_count = len(fresher_data)
        fresher_percent = (fresher_count / len(df)) * 100
        
        # Experience vs Salary scatter plot
        if 'exp_numeric' in df.columns and 'salary_avg_million_vnd' in df.columns:
            scatter_data = df[(df['salary_avg_million_vnd'] > 0) & (df['exp_numeric'] >= 0)]
            if not scatter_data.empty:
                fig = px.scatter(
                    scatter_data,
                    x='exp_numeric',
                    y='salary_avg_million_vnd',
                    color='city' if 'city' in df.columns else None,
                    size='salary_avg_million_vnd',
                    title="Mối quan hệ giữa Kinh nghiệm và Mức lương",
                    hover_data=['title', 'company'] if all(col in df.columns for col in ['title', 'company']) else None
                )
                fig.update_layout(
                    xaxis_title="Số năm kinh nghiệm",
                    yaxis_title="Mức lương (triệu VNĐ)",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown(f"""
        <div class="insight-box">
            <div class="insight-title">🌱 Cơ hội cho người mới</div>
            <div class="insight-content">
                Có <span class="highlight-number">{fresher_percent:.1f}%</span> 
                ({fresher_count:,} vị trí) không yêu cầu kinh nghiệm, 
                tạo cơ hội tốt cho sinh viên mới ra trường và những người chuyển ngành.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Chapter 5: Kỹ năng hot nhất
    st.markdown("""
    <div class="chapter">
        <div class="chapter-number">Chương 5</div>
        <div class="chapter-title">🚀 The Skills Economy: Kỹ năng nào đang định hình tương lai IT?</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Skills introduction
    st.markdown("""
    <div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); 
                border-left: 5px solid #10b981; padding: 2rem; border-radius: 15px; margin: 2rem 0;">
        <h4 style="color: #065f46; margin-bottom: 1rem;">⚡ The Skills Revolution</h4>
        <p style="font-size: 1.1rem; line-height: 1.8; margin-bottom: 1rem; color: #064e3b;">
            Trong thời đại mà công nghệ thay đổi với tốc độ chóng mặt, kỹ năng trở thành currency mới 
            của thị trường lao động IT. Không chỉ là hard skills về programming, mà còn bao gồm 
            soft skills, emerging technologies, và khả năng học hỏi liên tục.
        </p>
        <div style="background: #a7f3d0; padding: 1rem; border-radius: 8px;">
            <p style="margin: 0; font-style: italic; color: #064e3b; font-weight: 500;">
                "Trong IT, skill set của bạn hôm qua có thể đã lỗi thời. Nhưng khả năng adapt 
                và học skills mới sẽ không bao giờ lỗi thời."
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Skills analysis
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
            
            fig = px.bar(
                skills_df,
                x='Số lượng job',
                y='Kỹ năng',
                orientation='h',
                title="Top 10 kỹ năng được yêu cầu nhiều nhất",
                color_discrete_sequence=['#06b6d4']
            )
            fig.update_layout(
                height=500,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Top skill insight
            top_skill = top_skills[0][0]
            top_skill_count = top_skills[0][1]
            
            st.markdown(f"""
            <div class="insight-box">
                <div class="insight-title">🎯 Kỹ năng vàng</div>
                <div class="insight-content">
                    <strong>{top_skill}</strong> là kỹ năng được yêu cầu nhiều nhất với 
                    <span class="highlight-number">{top_skill_count}</span> vị trí. 
                    Đây là kim chỉ nam quan trọng cho việc định hướng học tập và phát triển kỹ năng.
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Chapter 6: Lĩnh vực nổi bật
    st.markdown("""
    <div class="chapter">
        <div class="chapter-number">Chương 6</div>
        <div class="chapter-title">⭐ Những lĩnh vực đang lên</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Category analysis
    if 'category' in df.columns:
        category_counts = df['category'].value_counts()
        
        # Create treemap for categories
        fig = px.treemap(
            names=category_counts.index,
            parents=[""] * len(category_counts),
            values=category_counts.values,
            title="Bản đồ phân bố theo lĩnh vực IT"
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Category insights
        top_category = category_counts.index[0]
        top_category_count = category_counts.iloc[0]
        top_category_percent = (top_category_count / len(df)) * 100
        
        # Salary by category
        if 'salary_avg_million_vnd' in df.columns:
            salary_by_category = df[df['salary_avg_million_vnd'] > 0].groupby('category')['salary_avg_million_vnd'].mean().sort_values(ascending=False)
            if not salary_by_category.empty:
                highest_paid_field = salary_by_category.index[0]
                highest_salary = salary_by_category.iloc[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <div class="timeline-item">
                        <div class="timeline-title">Lĩnh vực phổ biến nhất</div>
                        <div class="timeline-content">
                            <strong>{top_category}</strong><br>
                            <span class="highlight-number">{top_category_percent:.1f}%</span> thị trường
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="timeline-item">
                        <div class="timeline-title">Lĩnh vực lương cao nhất</div>
                        <div class="timeline-content">
                            <strong>{highest_paid_field}</strong><br>
                            <span class="highlight-number">{highest_salary:.1f}M</span> VNĐ trung bình
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Final insights and conclusion
    st.markdown("""
    <div class="chapter">
        <div class="chapter-number">Kết luận</div>
        <div class="chapter-title">🎯 Những điều rút ra được</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Key takeaways
    st.markdown("""
    <div class="insight-box">
        <div class="insight-title">🔑 Key Takeaways</div>
        <div class="insight-content">
            <strong>1. Thị trường đang phát triển mạnh:</strong> Với hàng nghìn cơ hội việc làm từ nhiều công ty khác nhau.<br><br>
            <strong>2. Cơ hội cho mọi trình độ:</strong> Từ fresher đến senior đều có chỗ đứng trong thị trường.<br><br>
            <strong>3. Mức lương cạnh tranh:</strong> Ngành IT vẫn duy trì được mức lương hấp dẫn so với các ngành khác.<br><br>
            <strong>4. Kỹ năng là chìa khóa:</strong> Việc nắm vững các công nghệ hot sẽ mở ra nhiều cơ hội hơn.<br><br>
            <strong>5. Tập trung địa lý:</strong> Các thành phố lớn vẫn là trung tâm của ngành công nghệ.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Call to action
    st.markdown("""
    <div class="cta-section">
        <div class="cta-title">🚀 Hành động ngay hôm nay!</div>
        <div class="cta-text">
            Dựa trên những insight này, hãy bắt đầu hành trình phát triển sự nghiệp IT của bạn. 
            Học những kỹ năng hot, xây dựng portfolio mạnh và chuẩn bị cho những cơ hội tuyệt vời đang chờ đợi!
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()