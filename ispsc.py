import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
from fpdf import FPDF
import base64
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="ISPSC Tagudin DMS Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 1rem;
        color: #7f7f7f;
    }
    .stButton>button {
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
    }
    .stButton>button:hover {
        background-color: #0d5d9c;
        color: white;
    }
    .filter-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    .download-button {
        background-color: #28a745;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        text-decoration: none;
        display: inline-block;
        margin: 0.5rem 0;
    }
    .download-button:hover {
        background-color: #218838;
        color: white;
        text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)

# Database connection function
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',
            database='ispsc_tagudin_dms_db',
            user='root',  # Replace with your MySQL username
            password=''   # Replace with your MySQL password
        )
        return connection
    except Error as e:
        st.error(f"Error connecting to MySQL database: {e}")
        return None

# Load data functions
def load_documents_data():
    conn = create_connection()
    if conn:
        query = """
        SELECT d.doc_id, d.title, d.reference, d.status, d.visible_to_all, 
               d.created_at, d.updated_at, d.created_by_name, d.deleted,
               dt.name as doc_type, GROUP_CONCAT(dept.name) as departments
        FROM dms_documents d
        LEFT JOIN document_types dt ON d.doc_type = dt.type_id
        LEFT JOIN document_departments dd ON d.doc_id = dd.doc_id
        LEFT JOIN departments dept ON dd.department_id = dept.department_id
        GROUP BY d.doc_id
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

def load_users_data():
    conn = create_connection()
    if conn:
        query = """
        SELECT u.user_id, u.Username, u.firstname, u.lastname, u.user_email, 
               u.role, u.status, u.created_at, u.updated_at,
               d.name as department
        FROM dms_user u
        LEFT JOIN departments d ON u.department_id = d.department_id
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

def load_announcements_data():
    conn = create_connection()
    if conn:
        query = """
        SELECT announcement_id, title, status, visible_to_all, 
               publish_at, expire_at, created_by_name, created_at
        FROM announcements
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

def load_notifications_data():
    conn = create_connection()
    if conn:
        query = """
        SELECT notification_id, title, type, created_at, related_doc_id
        FROM notifications
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

def load_document_types_data():
    conn = create_connection()
    if conn:
        query = "SELECT type_id, name FROM document_types ORDER BY name"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    return pd.DataFrame()

# Filter functions
def filter_documents(documents_df, status_filter, type_filter, date_range, creator_filter):
    """Filter documents based on selected criteria"""
    filtered_df = documents_df.copy()
    
    if status_filter and status_filter != "All":
        filtered_df = filtered_df[filtered_df['status'] == status_filter]
    
    if type_filter and type_filter != "All":
        filtered_df = filtered_df[filtered_df['doc_type'] == type_filter]
    
    if date_range:
        start_date, end_date = date_range
        if start_date and end_date:
            filtered_df = filtered_df[
                (filtered_df['created_at'].dt.date >= start_date) &
                (filtered_df['created_at'].dt.date <= end_date)
            ]
    
    if creator_filter and creator_filter != "All":
        filtered_df = filtered_df[filtered_df['created_by_name'] == creator_filter]
    
    return filtered_df

def filter_users(users_df, status_filter, role_filter, department_filter, date_range):
    """Filter users based on selected criteria"""
    filtered_df = users_df.copy()
    
    if status_filter and status_filter != "All":
        filtered_df = filtered_df[filtered_df['status'] == status_filter]
    
    if role_filter and role_filter != "All":
        filtered_df = filtered_df[filtered_df['role'] == role_filter]
    
    if department_filter and department_filter != "All":
        filtered_df = filtered_df[filtered_df['department'] == department_filter]
    
    if date_range:
        start_date, end_date = date_range
        if start_date and end_date:
            filtered_df = filtered_df[
                (filtered_df['created_at'].dt.date >= start_date) &
                (filtered_df['created_at'].dt.date <= end_date)
            ]
    
    return filtered_df

def filter_announcements(announcements_df, status_filter, visibility_filter, date_range, creator_filter):
    """Filter announcements based on selected criteria"""
    filtered_df = announcements_df.copy()
    
    if status_filter and status_filter != "All":
        filtered_df = filtered_df[filtered_df['status'] == status_filter]
    
    if visibility_filter and visibility_filter != "All":
        if visibility_filter == "Visible to All":
            filtered_df = filtered_df[filtered_df['visible_to_all'] == 1]
        else:
            filtered_df = filtered_df[filtered_df['visible_to_all'] == 0]
    
    if date_range:
        start_date, end_date = date_range
        if start_date and end_date:
            filtered_df = filtered_df[
                (filtered_df['created_at'].dt.date >= start_date) &
                (filtered_df['created_at'].dt.date <= end_date)
            ]
    
    if creator_filter and creator_filter != "All":
        filtered_df = filtered_df[filtered_df['created_by_name'] == creator_filter]
    
    return filtered_df

def filter_notifications(notifications_df, type_filter, date_range):
    """Filter notifications based on selected criteria"""
    filtered_df = notifications_df.copy()
    
    if type_filter and type_filter != "All":
        filtered_df = filtered_df[filtered_df['type'] == type_filter]
    
    if date_range:
        start_date, end_date = date_range
        if start_date and end_date:
            filtered_df = filtered_df[
                (filtered_df['created_at'].dt.date >= start_date) &
                (filtered_df['created_at'].dt.date <= end_date)
            ]
    
    return filtered_df

# PDF Generation Functions
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'ISPSC Tagudin DMS Analytics Report', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)
    
    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 8, body)
        self.ln()

def create_pdf_report(documents_df, users_df, announcements_df, notifications_df):
    pdf = PDFReport()
    pdf.add_page()
    
    # Report header
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'ISPSC Tagudin DMS Analytics Report', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
    pdf.ln(10)
    
    # Key Metrics
    pdf.chapter_title('Key Metrics')
    
    total_docs = len(documents_df) if not documents_df.empty else 0
    active_users = len(users_df[users_df['status'] == 'active']) if not users_df.empty else 0
    published_announcements = len(announcements_df[announcements_df['status'] == 'published']) if not announcements_df.empty else 0
    recent_notifications = len(notifications_df[notifications_df['created_at'] > (datetime.now() - timedelta(days=7))]) if not notifications_df.empty else 0
    
    metrics_data = [
        ['Metric', 'Value'],
        ['Total Documents', str(total_docs)],
        ['Active Users', str(active_users)],
        ['Published Announcements', str(published_announcements)],
        ['Recent Notifications (7 days)', str(recent_notifications)]
    ]
    
    # Create metrics table
    col_width = pdf.w / 2.5
    row_height = pdf.font_size * 2
    
    for row in metrics_data:
        for item in row:
            pdf.cell(col_width, row_height, item, border=1)
        pdf.ln(row_height)
    
    pdf.ln(10)
    
    # Document Analytics
    pdf.chapter_title('Document Analytics')
    
    if not documents_df.empty:
        # Document status distribution
        status_counts = documents_df['status'].value_counts()
        status_text = "Document Status Distribution:\n"
        for status, count in status_counts.items():
            status_text += f"- {status}: {count} documents\n"
        
        # Document type distribution
        if 'doc_type' in documents_df.columns:
            type_counts = documents_df['doc_type'].value_counts()
            type_text = "\nDocument Types Distribution:\n"
            for doc_type, count in type_counts.items():
                type_text += f"- {doc_type}: {count} documents\n"
        else:
            type_text = ""
        
        pdf.chapter_body(status_text + type_text)
    else:
        pdf.chapter_body("No document data available.")
    
    pdf.ln(5)
    
    # User Analytics
    pdf.chapter_title('User Analytics')
    
    if not users_df.empty:
        # User status distribution
        status_counts = users_df['status'].value_counts()
        status_text = "User Status Distribution:\n"
        for status, count in status_counts.items():
            status_text += f"- {status}: {count} users\n"
        
        # User role distribution
        role_counts = users_df['role'].value_counts()
        role_text = "\nUser Role Distribution:\n"
        for role, count in role_counts.items():
            role_text += f"- {role}: {count} users\n"
        
        pdf.chapter_body(status_text + role_text)
    else:
        pdf.chapter_body("No user data available.")
    
    pdf.ln(5)
    
    # Announcement Analytics
    pdf.chapter_title('Announcement Analytics')
    
    if not announcements_df.empty:
        # Announcement status distribution
        status_counts = announcements_df['status'].value_counts()
        status_text = "Announcement Status Distribution:\n"
        for status, count in status_counts.items():
            status_text += f"- {status}: {count} announcements\n"
        
        # Visibility distribution
        visibility_counts = announcements_df['visible_to_all'].value_counts()
        visibility_text = "\nAnnouncement Visibility:\n"
        for visibility, count in visibility_counts.items():
            vis_name = "Visible to All" if visibility == 1 else "Restricted"
            visibility_text += f"- {vis_name}: {count} announcements\n"
        
        pdf.chapter_body(status_text + visibility_text)
    else:
        pdf.chapter_body("No announcement data available.")
    
    pdf.ln(5)
    
    # System Activity
    pdf.chapter_title('System Activity')
    
    if not notifications_df.empty:
        # Notification type distribution
        type_counts = notifications_df['type'].value_counts()
        type_text = "Notification Types Distribution:\n"
        for n_type, count in type_counts.items():
            type_text += f"- {n_type}: {count} notifications\n"
        
        pdf.chapter_body(type_text)
    else:
        pdf.chapter_body("No notification data available.")
    
    # Save PDF to bytes buffer
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return pdf_bytes

def get_table_download_link(df, filename, link_text):
    """Generates a link to download the data as a CSV file"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

# Load all data
documents_df = load_documents_data()
users_df = load_users_data()
announcements_df = load_announcements_data()
notifications_df = load_notifications_data()
doc_types_df = load_document_types_data()

# Convert date columns
if not documents_df.empty:
    documents_df['created_at'] = pd.to_datetime(documents_df['created_at'])
    documents_df['updated_at'] = pd.to_datetime(documents_df['updated_at'])

if not users_df.empty:
    users_df['created_at'] = pd.to_datetime(users_df['created_at'])
    users_df['updated_at'] = pd.to_datetime(users_df['updated_at'])

if not announcements_df.empty:
    announcements_df['created_at'] = pd.to_datetime(announcements_df['created_at'])
    announcements_df['publish_at'] = pd.to_datetime(announcements_df['publish_at'])
    announcements_df['expire_at'] = pd.to_datetime(announcements_df['expire_at'])

if not notifications_df.empty:
    notifications_df['created_at'] = pd.to_datetime(notifications_df['created_at'])

# Dashboard Header
st.markdown('<h1 class="main-header">ISPSC Tagudin DMS Analytics Dashboard</h1>', unsafe_allow_html=True)

# PDF Export Section
st.markdown("---")
st.markdown("### 📊 Export Analytics Report")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown("**Generate comprehensive PDF report**")
    
with col2:
    st.markdown("**Includes all analytics data**")
    
with col3:
    st.markdown("**Charts and metrics**")
    
with col4:
    st.markdown("**Data tables**")

with col5:
    if st.button('📄 Generate PDF Report', help="Click to generate and download a comprehensive PDF report"):
        with st.spinner('Generating comprehensive PDF report...'):
            pdf_bytes = create_pdf_report(documents_df, users_df, announcements_df, notifications_df)
            
            # Create download link with better styling
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="ispsc_dms_analytics_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf" class="download-button">📥 Download PDF Report</a>'
            st.markdown(href, unsafe_allow_html=True)
            st.success('✅ PDF report generated successfully! Click the download button above.')

# Key Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_docs = len(documents_df) if not documents_df.empty else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{total_docs}</div>
        <div class="metric-label">Total Documents</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    active_users = len(users_df[users_df['status'] == 'active']) if not users_df.empty else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{active_users}</div>
        <div class="metric-label">Active Users</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    published_announcements = len(announcements_df[announcements_df['status'] == 'published']) if not announcements_df.empty else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{published_announcements}</div>
        <div class="metric-label">Published Announcements</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    recent_notifications = len(notifications_df[notifications_df['created_at'] > (datetime.now() - timedelta(days=7))]) if not notifications_df.empty else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{recent_notifications}</div>
        <div class="metric-label">Notifications (Last 7 Days)</div>
    </div>
    """, unsafe_allow_html=True)

# Main content
tab1, tab2, tab3, tab4 = st.tabs(["Documents", "Users", "Announcements", "System Activity"])

with tab1:
    st.header("Document Analytics")
    
    if documents_df.empty:
        st.warning("No document data available.")
    else:
        # Filters Section
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        st.subheader("🔍 Filters")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Status filter
            status_options = ["All"] + list(documents_df['status'].unique())
            status_filter = st.selectbox("Status", status_options)
        
        with col2:
            # Document type filter
            if 'doc_type' in documents_df.columns:
                type_options = ["All"] + list(documents_df['doc_type'].dropna().unique())
                type_filter = st.selectbox("Document Type", type_options)
            else:
                type_filter = "All"
        
        with col3:
            # Date range filter
            min_date = documents_df['created_at'].min().date()
            max_date = documents_df['created_at'].max().date()
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        
        with col4:
            # Creator filter
            creator_options = ["All"] + list(documents_df['created_by_name'].dropna().unique())
            creator_filter = st.selectbox("Created By", creator_options)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters
        filtered_documents = filter_documents(
            documents_df, status_filter, type_filter, date_range, creator_filter
        )
        
        # Show filtered results count
        st.info(f"📊 Showing {len(filtered_documents)} documents (filtered from {len(documents_df)} total)")
        
        # Download filtered data
        if len(filtered_documents) > 0:
            csv = filtered_documents.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="filtered_documents_{datetime.now().strftime("%Y%m%d")}.csv" class="download-button">📥 Download Filtered Documents (CSV)</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Document status distribution
            status_counts = filtered_documents['status'].value_counts()
            fig_status = px.pie(
                values=status_counts.values, 
                names=status_counts.index,
                title="Document Status Distribution"
            )
            st.plotly_chart(fig_status, use_container_width=True)
            
        with col2:
            # Document type distribution
            if 'doc_type' in filtered_documents.columns:
                type_counts = filtered_documents['doc_type'].value_counts()
                fig_type = px.bar(
                    x=type_counts.values,
                    y=type_counts.index,
                    orientation='h',
                    title="Document Types Distribution",
                    labels={'x': 'Count', 'y': 'Document Type'}
                )
                st.plotly_chart(fig_type, use_container_width=True)
        
        # Documents created over time
        filtered_documents['created_date'] = filtered_documents['created_at'].dt.date
        daily_docs = filtered_documents.groupby('created_date').size().reset_index(name='count')
        
        fig_timeline = px.line(
            daily_docs, 
            x='created_date', 
            y='count',
            title="Documents Created Over Time"
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Top document creators
        creator_counts = filtered_documents['created_by_name'].value_counts().head(10)
        fig_creators = px.bar(
            x=creator_counts.values,
            y=creator_counts.index,
            orientation='h',
            title="Top Document Creators",
            labels={'x': 'Number of Documents', 'y': 'Creator'}
        )
        st.plotly_chart(fig_creators, use_container_width=True)
        
        # Filtered data table
        st.subheader("📋 Filtered Documents Data")
        st.dataframe(filtered_documents[['title', 'status', 'doc_type', 'created_by_name', 'created_at']].head(10))

with tab2:
    st.header("User Analytics")
    
    if users_df.empty:
        st.warning("No user data available.")
    else:
        # Filters Section
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        st.subheader("🔍 Filters")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Status filter
            status_options = ["All"] + list(users_df['status'].unique())
            status_filter = st.selectbox("User Status", status_options)
        
        with col2:
            # Role filter
            role_options = ["All"] + list(users_df['role'].unique())
            role_filter = st.selectbox("User Role", role_options)
        
        with col3:
            # Department filter
            if 'department' in users_df.columns:
                dept_options = ["All"] + list(users_df['department'].dropna().unique())
                dept_filter = st.selectbox("Department", dept_options)
            else:
                dept_filter = "All"
        
        with col4:
            # Date range filter
            min_date = users_df['created_at'].min().date()
            max_date = users_df['created_at'].max().date()
            date_range = st.date_input(
                "Registration Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters
        filtered_users = filter_users(
            users_df, status_filter, role_filter, dept_filter, date_range
        )
        
        # Show filtered results count
        st.info(f"👥 Showing {len(filtered_users)} users (filtered from {len(users_df)} total)")
        
        # Download filtered data
        if len(filtered_users) > 0:
            csv = filtered_users.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="filtered_users_{datetime.now().strftime("%Y%m%d")}.csv" class="download-button">📥 Download Filtered Users (CSV)</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # User status distribution
            status_counts = filtered_users['status'].value_counts()
            fig_user_status = px.pie(
                values=status_counts.values, 
                names=status_counts.index,
                title="User Status Distribution"
            )
            st.plotly_chart(fig_user_status, use_container_width=True)
            
        with col2:
            # User role distribution
            role_counts = filtered_users['role'].value_counts()
            fig_user_role = px.pie(
                values=role_counts.values, 
                names=role_counts.index,
                title="User Role Distribution"
            )
            st.plotly_chart(fig_user_role, use_container_width=True)
        
        # Department distribution
        if 'department' in filtered_users.columns:
            dept_counts = filtered_users['department'].value_counts()
            fig_dept = px.bar(
                x=dept_counts.values,
                y=dept_counts.index,
                orientation='h',
                title="Users by Department",
                labels={'x': 'Number of Users', 'y': 'Department'}
            )
            st.plotly_chart(fig_dept, use_container_width=True)
        
        # Users created over time
        filtered_users['created_date'] = filtered_users['created_at'].dt.date
        daily_users = filtered_users.groupby('created_date').size().reset_index(name='count')
        
        fig_user_timeline = px.line(
            daily_users, 
            x='created_date', 
            y='count',
            title="User Registrations Over Time"
        )
        st.plotly_chart(fig_user_timeline, use_container_width=True)
        
        # Filtered data table
        st.subheader("📋 Filtered Users Data")
        st.dataframe(filtered_users[['Username', 'firstname', 'lastname', 'role', 'status', 'department', 'created_at']].head(10))

with tab3:
    st.header("Announcement Analytics")
    
    if announcements_df.empty:
        st.warning("No announcement data available.")
    else:
        # Filters Section
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        st.subheader("🔍 Filters")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Status filter
            status_options = ["All"] + list(announcements_df['status'].unique())
            status_filter = st.selectbox("Announcement Status", status_options)
        
        with col2:
            # Visibility filter
            visibility_options = ["All", "Visible to All", "Restricted"]
            visibility_filter = st.selectbox("Visibility", visibility_options)
        
        with col3:
            # Date range filter
            min_date = announcements_df['created_at'].min().date()
            max_date = announcements_df['created_at'].max().date()
            date_range = st.date_input(
                "Creation Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        
        with col4:
            # Creator filter
            creator_options = ["All"] + list(announcements_df['created_by_name'].dropna().unique())
            creator_filter = st.selectbox("Created By", creator_options)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters
        filtered_announcements = filter_announcements(
            announcements_df, status_filter, visibility_filter, date_range, creator_filter
        )
        
        # Show filtered results count
        st.info(f"📢 Showing {len(filtered_announcements)} announcements (filtered from {len(announcements_df)} total)")
        
        # Download filtered data
        if len(filtered_announcements) > 0:
            csv = filtered_announcements.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="filtered_announcements_{datetime.now().strftime("%Y%m%d")}.csv" class="download-button">📥 Download Filtered Announcements (CSV)</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Announcement status distribution
            status_counts = filtered_announcements['status'].value_counts()
            fig_announce_status = px.pie(
                values=status_counts.values, 
                names=status_counts.index,
                title="Announcement Status Distribution"
            )
            st.plotly_chart(fig_announce_status, use_container_width=True)
            
        with col2:
            # Visibility distribution
            visibility_counts = filtered_announcements['visible_to_all'].value_counts()
            fig_visibility = px.pie(
                values=visibility_counts.values, 
                names=visibility_counts.index.map({1: 'Visible to All', 0: 'Restricted'}),
                title="Announcement Visibility"
            )
            st.plotly_chart(fig_visibility, use_container_width=True)
        
        # Announcements created over time
        filtered_announcements['created_date'] = filtered_announcements['created_at'].dt.date
        daily_announcements = filtered_announcements.groupby('created_date').size().reset_index(name='count')
        
        fig_announce_timeline = px.line(
            daily_announcements, 
            x='created_date', 
            y='count',
            title="Announcements Created Over Time"
        )
        st.plotly_chart(fig_announce_timeline, use_container_width=True)
        
        # Top announcement creators
        creator_counts = filtered_announcements['created_by_name'].value_counts().head(10)
        fig_announce_creators = px.bar(
            x=creator_counts.values,
            y=creator_counts.index,
            orientation='h',
            title="Top Announcement Creators",
            labels={'x': 'Number of Announcements', 'y': 'Creator'}
        )
        st.plotly_chart(fig_announce_creators, use_container_width=True)
        
        # Filtered data table
        st.subheader("📋 Filtered Announcements Data")
        st.dataframe(filtered_announcements[['title', 'status', 'visible_to_all', 'created_by_name', 'created_at']].head(10))

with tab4:
    st.header("System Activity Analytics")
    
    if notifications_df.empty:
        st.warning("No notification data available.")
    else:
        # Filters Section
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        st.subheader("🔍 Filters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Type filter
            type_options = ["All"] + list(notifications_df['type'].unique())
            type_filter = st.selectbox("Notification Type", type_options)
        
        with col2:
            # Date range filter
            min_date = notifications_df['created_at'].min().date()
            max_date = notifications_df['created_at'].max().date()
            date_range = st.date_input(
                "Creation Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters
        filtered_notifications = filter_notifications(
            notifications_df, type_filter, date_range
        )
        
        # Show filtered results count
        st.info(f"🔔 Showing {len(filtered_notifications)} notifications (filtered from {len(notifications_df)} total)")
        
        # Download filtered data
        if len(filtered_notifications) > 0:
            csv = filtered_notifications.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="filtered_notifications_{datetime.now().strftime("%Y%m%d")}.csv" class="download-button">📥 Download Filtered Notifications (CSV)</a>'
            st.markdown(href, unsafe_allow_html=True)
        
        # Notification type distribution
        type_counts = filtered_notifications['type'].value_counts()
        fig_notif_type = px.pie(
            values=type_counts.values, 
            names=type_counts.index,
            title="Notification Types Distribution"
        )
        st.plotly_chart(fig_notif_type, use_container_width=True)
        
        # Notifications over time
        filtered_notifications['created_date'] = filtered_notifications['created_at'].dt.date
        daily_notifications = filtered_notifications.groupby('created_date').size().reset_index(name='count')
        
        fig_notif_timeline = px.line(
            daily_notifications, 
            x='created_date', 
            y='count',
            title="Notifications Over Time"
        )
        st.plotly_chart(fig_notif_timeline, use_container_width=True)
        
        # Filtered activity table
        st.subheader("📋 Filtered System Activity")
        filtered_activity = filtered_notifications.sort_values('created_at', ascending=False).head(10)
        st.dataframe(filtered_activity[['title', 'type', 'created_at']])

# Data summary section
st.header("Data Summary")
summary_col1, summary_col2, summary_col3 = st.columns(3)

with summary_col1:
    st.subheader("Documents Summary")
    if not documents_df.empty:
        st.dataframe(documents_df[['title', 'status', 'created_by_name', 'created_at']].head(5))
        st.markdown(get_table_download_link(documents_df, "documents.csv", "Download Documents Data"), unsafe_allow_html=True)
    else:
        st.info("No document data available.")

with summary_col2:
    st.subheader("Users Summary")
    if not users_df.empty:
        st.dataframe(users_df[['Username', 'role', 'status', 'created_at']].head(5))
        st.markdown(get_table_download_link(users_df, "users.csv", "Download Users Data"), unsafe_allow_html=True)
    else:
        st.info("No user data available.")

with summary_col3:
    st.subheader("Announcements Summary")
    if not announcements_df.empty:
        st.dataframe(announcements_df[['title', 'status', 'created_by_name', 'created_at']].head(5))
        st.markdown(get_table_download_link(announcements_df, "announcements.csv", "Download Announcements Data"), unsafe_allow_html=True)
    else:
        st.info("No announcement data available.")

# Footer
st.markdown("---")
st.markdown("**ISPSC Tagudin Document Management System Analytics** | Built with Streamlit")