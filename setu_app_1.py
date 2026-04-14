import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
import json

# ─── Page Config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Setu — Your Bridge to Visa-Sponsored Careers",
    page_icon="🌉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Session State Init ─────────────────────────────────────────────────
if "profile_complete" not in st.session_state:
    st.session_state.profile_complete = False
if "profile" not in st.session_state:
    st.session_state.profile = {}
if "applications" not in st.session_state:
    st.session_state.applications = []

# ─── Custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@400;600;700;800;900&display=swap');
    .stApp { background-color: #0a0c14; }
    section[data-testid="stSidebar"] { background-color: #0d0f17; border-right: 1px solid #1a1d2e; }
    h1, h2, h3 { font-family: 'Outfit', sans-serif !important; color: #e2e6f0 !important; }
    p, li, span, div { color: #c0c5d8; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #12141d; border: 1px solid #252836; border-radius: 8px;
        color: #8890b5; padding: 10px 20px; font-family: 'Outfit', sans-serif;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #00ffa315, #6c5ce710) !important;
        border-color: #00ffa350 !important; color: #00ffa3 !important;
    }
    .stat-card {
        background: linear-gradient(135deg, #12141d, #181b27);
        border: 1px solid #252836; border-radius: 12px; padding: 20px; text-align: center;
    }
    .stat-value { font-size: 36px; font-weight: 800; font-family: 'Outfit', sans-serif; line-height: 1.1; }
    .stat-label { font-size: 11px; color: #6b7094; text-transform: uppercase; letter-spacing: 1.5px; font-family: 'JetBrains Mono', monospace; margin-bottom: 6px; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
    .badge-green { color: #00ffa3; background: #00ffa318; border: 1px solid #00ffa330; }
    .badge-yellow { color: #f7b731; background: #f7b73118; border: 1px solid #f7b73130; }
    .badge-purple { color: #6c5ce7; background: #6c5ce718; border: 1px solid #6c5ce730; }
    .badge-red { color: #fc5c65; background: #fc5c6518; border: 1px solid #fc5c6530; }
    .badge-gray { color: #6b7094; background: #6b709418; border: 1px solid #6b709430; }
    .pipeline-card { background: linear-gradient(135deg, #12141d, #181b27); border: 1px solid #252836; border-radius: 10px; padding: 16px; margin-bottom: 10px; }
    .insight-box { background: linear-gradient(135deg, #f7b73110, #00ffa308); border: 1px solid #f7b73125; border-radius: 12px; padding: 20px; margin-top: 16px; }
    .warning-box { background: linear-gradient(135deg, #fc5c6510, #f7b73108); border: 1px solid #fc5c6525; border-radius: 12px; padding: 20px; margin-top: 16px; }
    .timeline-item { background: linear-gradient(135deg, #12141d, #181b27); border: 1px solid #252836; border-radius: 12px; padding: 18px 22px; margin-bottom: 12px; border-left: 3px solid #00ffa3; }
    .timeline-future { border-left-color: #6c5ce7 !important; }
    div[data-testid="stMetric"] { background: linear-gradient(135deg, #12141d, #181b27); border: 1px solid #252836; border-radius: 12px; padding: 16px; }
    div[data-testid="stMetric"] label { color: #6b7094 !important; font-family: 'JetBrains Mono', monospace !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #00ffa3 !important; font-family: 'Outfit', sans-serif !important; }
    .job-card { background: linear-gradient(135deg, #12141d, #181b27); border: 1px solid #252836; border-radius: 12px; padding: 18px 22px; margin-bottom: 10px; }
    .match-circle { display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; border-radius: 50%; font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    .welcome-card { background: linear-gradient(135deg, #12141d 0%, #1a1f35 50%, #12141d 100%); border: 1px solid #252836; border-radius: 16px; padding: 40px; text-align: center; margin: 20px 0; }
    .profile-card { background: linear-gradient(135deg, #12141d, #181b27); border: 1px solid #00ffa330; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
    .urgency-high { border-left-color: #fc5c65 !important; }
    .urgency-med { border-left-color: #f7b731 !important; }
    .urgency-low { border-left-color: #00ffa3 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Data ────────────────────────────────────────────────────────────────
INDUSTRY_MAP = {
    "AMAZON": "Tech", "GOOGLE": "Tech", "MICROSOFT": "Tech", "META": "Tech",
    "APPLE": "Tech", "NETFLIX": "Tech", "NVIDIA": "Tech", "ADOBE": "Tech",
    "SALESFORCE": "Tech", "ORACLE": "Tech", "IBM": "Tech", "UBER": "Tech",
    "FACEBOOK": "Tech", "ALPHABET": "Tech", "INTEL": "Tech", "CISCO": "Tech",
    "INFOSYS": "Consulting", "TCS": "Consulting", "COGNIZANT": "Consulting",
    "WIPRO": "Consulting", "HCL": "Consulting", "TECH MAHINDRA": "Consulting",
    "DELOITTE": "Consulting", "ACCENTURE": "Consulting", "CAPGEMINI": "Consulting",
    "ERNST": "Consulting", "KPMG": "Consulting", "PWC": "Consulting",
    "JPMORGAN": "Finance", "GOLDMAN": "Finance", "CAPITAL ONE": "Finance",
    "BANK OF AMERICA": "Finance", "WELLS FARGO": "Finance", "CITIBANK": "Finance",
    "MORGAN STANLEY": "Finance", "BARCLAYS": "Finance",
    "WALMART": "Retail", "TARGET": "Retail", "COSTCO": "Retail",
    "JOHNSON": "Healthcare", "PFIZER": "Healthcare", "MERCK": "Healthcare",
}

ALL_SKILLS = ["Python", "SQL", "R", "Tableau", "Power BI", "Excel", "Machine Learning",
    "Deep Learning", "NLP", "Computer Vision", "TensorFlow", "PyTorch", "Scikit-learn",
    "Pandas", "NumPy", "Spark", "Hadoop", "AWS", "GCP", "Azure", "Docker", "Git",
    "Java", "Scala", "C++", "JavaScript", "React", "MongoDB", "PostgreSQL",
    "MySQL", "Snowflake", "dbt", "Airflow", "Kafka", "LLMs", "GenAI", "RAG",
    "Statistics", "A/B Testing", "Data Mining", "ETL", "Data Warehousing"]

def classify_industry(name):
    name = str(name).upper()
    for k, v in INDUSTRY_MAP.items():
        if k in name:
            return v
    return "Other"

@st.cache_data
def load_h1b_data():
    path = "data/h1b_top_sponsors.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        result = pd.DataFrame({
            "Company": df["employer"].str.title(),
            "Industry": df["employer"].apply(classify_industry),
            "Approvals": df["total_approvals"],
            "Denial %": df.get("denial_rate", 0),
            "Median Salary": df["median_salary"].fillna(0).astype(int),
        })
        return result[result["Approvals"] >= 10].head(200)
    else:
        return pd.DataFrame([
            {"Company": "Amazon", "Industry": "Tech", "Approvals": 12804, "Denial %": 3.2, "Median Salary": 165000},
            {"Company": "Google", "Industry": "Tech", "Approvals": 9847, "Denial %": 1.8, "Median Salary": 182000},
            {"Company": "Microsoft", "Industry": "Tech", "Approvals": 8432, "Denial %": 2.1, "Median Salary": 175000},
            {"Company": "Meta", "Industry": "Tech", "Approvals": 5621, "Denial %": 2.5, "Median Salary": 190000},
            {"Company": "Apple", "Industry": "Tech", "Approvals": 4532, "Denial %": 1.5, "Median Salary": 185000},
            {"Company": "Infosys", "Industry": "Consulting", "Approvals": 14200, "Denial %": 8.4, "Median Salary": 95000},
            {"Company": "TCS", "Industry": "Consulting", "Approvals": 11800, "Denial %": 9.1, "Median Salary": 88000},
            {"Company": "Cognizant", "Industry": "Consulting", "Approvals": 8900, "Denial %": 7.2, "Median Salary": 92000},
            {"Company": "Deloitte", "Industry": "Consulting", "Approvals": 6700, "Denial %": 4.1, "Median Salary": 135000},
            {"Company": "JPMorgan", "Industry": "Finance", "Approvals": 4100, "Denial %": 3.0, "Median Salary": 155000},
            {"Company": "Goldman Sachs", "Industry": "Finance", "Approvals": 2800, "Denial %": 2.8, "Median Salary": 170000},
            {"Company": "Capital One", "Industry": "Finance", "Approvals": 2400, "Denial %": 3.5, "Median Salary": 148000},
            {"Company": "Salesforce", "Industry": "Tech", "Approvals": 3200, "Denial %": 2.2, "Median Salary": 172000},
            {"Company": "Nvidia", "Industry": "Tech", "Approvals": 2600, "Denial %": 1.4, "Median Salary": 205000},
            {"Company": "Adobe", "Industry": "Tech", "Approvals": 2200, "Denial %": 1.9, "Median Salary": 175000},
        ])

SALARY_DATA = pd.DataFrame([
    {"Role": "Data Scientist", "OPT": 95000, "H1B": 142000, "US Citizen": 148000},
    {"Role": "Data Analyst", "OPT": 72000, "H1B": 105000, "US Citizen": 108000},
    {"Role": "ML Engineer", "OPT": 110000, "H1B": 168000, "US Citizen": 175000},
    {"Role": "Solutions Analyst", "OPT": 68000, "H1B": 98000, "US Citizen": 102000},
    {"Role": "BI Analyst", "OPT": 65000, "H1B": 95000, "US Citizen": 100000},
    {"Role": "AI Engineer", "OPT": 115000, "H1B": 178000, "US Citizen": 185000},
])

JOBS_DATA = [
    {"Title": "Data Scientist", "Company": "Amazon", "Location": "Seattle, WA", "Salary": "$140K-$180K", "Sponsorship": "H1B + Green Card", "Posted": "2d ago", "Skills": ["Python", "Machine Learning", "SQL", "Statistics"]},
    {"Title": "ML Engineer", "Company": "Google", "Location": "Mountain View, CA", "Salary": "$160K-$210K", "Sponsorship": "H1B + Green Card", "Posted": "1d ago", "Skills": ["Python", "TensorFlow", "GCP", "Deep Learning"]},
    {"Title": "Data Analyst", "Company": "Capital One", "Location": "McLean, VA", "Salary": "$95K-$130K", "Sponsorship": "H1B", "Posted": "3d ago", "Skills": ["SQL", "Python", "Tableau", "Excel"]},
    {"Title": "Solutions Analyst", "Company": "Deloitte", "Location": "Miami, FL", "Salary": "$85K-$120K", "Sponsorship": "H1B", "Posted": "1d ago", "Skills": ["SQL", "Power BI", "Excel", "Statistics"]},
    {"Title": "Data Science Intern to FT", "Company": "JPMorgan", "Location": "New York, NY", "Salary": "$110K-$145K", "Sponsorship": "OPT to H1B", "Posted": "5h ago", "Skills": ["Python", "Machine Learning", "SQL", "Pandas"]},
    {"Title": "Analytics Engineer", "Company": "Salesforce", "Location": "San Francisco, CA", "Salary": "$130K-$165K", "Sponsorship": "H1B + Green Card", "Posted": "4d ago", "Skills": ["SQL", "dbt", "Python", "Snowflake"]},
    {"Title": "AI/ML Researcher", "Company": "Nvidia", "Location": "Santa Clara, CA", "Salary": "$170K-$230K", "Sponsorship": "H1B + Green Card", "Posted": "2d ago", "Skills": ["Python", "PyTorch", "Deep Learning", "NLP"]},
    {"Title": "BI Analyst", "Company": "Walmart", "Location": "Bentonville, AR", "Salary": "$80K-$110K", "Sponsorship": "H1B", "Posted": "6d ago", "Skills": ["SQL", "Tableau", "Python", "Excel"]},
    {"Title": "GenAI Engineer", "Company": "Microsoft", "Location": "Redmond, WA", "Salary": "$155K-$200K", "Sponsorship": "H1B + Green Card", "Posted": "3h ago", "Skills": ["Python", "LLMs", "GenAI", "RAG"]},
    {"Title": "Data Engineer", "Company": "Meta", "Location": "Menlo Park, CA", "Salary": "$150K-$195K", "Sponsorship": "H1B + Green Card", "Posted": "1d ago", "Skills": ["Python", "Spark", "SQL", "Airflow"]},
]

def calc_match(job_skills, user_skills):
    if not user_skills:
        return 50
    j = set(s.lower() for s in job_skills)
    u = set(s.lower() for s in user_skills)
    return min(int((len(j & u) / len(j)) * 100), 99) if j else 50

def get_timeline(grad_date):
    today = date.today()
    opt_start = grad_date + timedelta(days=1)
    unemp = opt_start + timedelta(days=90)
    h1b_reg = date(grad_date.year + 1, 3, 1)
    h1b_res = h1b_reg + timedelta(days=30)
    stem_dl = opt_start + timedelta(days=365)
    h1b_oct = date(h1b_reg.year, 10, 1)

    items = [
        (grad_date, "Graduation & OPT Start", "Apply for post-completion OPT. File I-765 with USCIS.", "🎓"),
        (unemp, "90-Day Employment Deadline", f"Must have employment by {unemp.strftime('%b %d, %Y')} or OPT terminates.", "🚨"),
        (h1b_reg, "H1B Lottery Registration", "Employer registers you. Discuss sponsorship by January.", "🎰"),
        (h1b_res, "Lottery Results", "Selected? File H1B petition. Not selected? Continue on STEM OPT.", "📋"),
        (stem_dl, "STEM OPT Extension Deadline", f"File before {stem_dl.strftime('%b %d, %Y')}. Employer must be E-Verify.", "🔬"),
        (h1b_oct, "H1B Start Date", "If approved, H1B status begins October 1.", "✅"),
    ]
    result = []
    for d, label, desc, icon in items:
        days = (d - today).days
        status = "done" if days < 0 else "upcoming" if days <= 90 else "future"
        urgency = "high" if 0 < days <= 30 else "med" if days <= 90 else "low"
        result.append({"date": d.strftime("%b %d, %Y"), "label": f"{icon} {label}", "desc": desc, "status": status, "days": days, "urgency": urgency})
    return result

h1b_df = load_h1b_data()

# ─── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <div style='display: inline-flex; align-items: center; justify-content: center;
            width: 46px; height: 46px; border-radius: 12px;
            background: linear-gradient(135deg, #FF9933, #ffffff, #138808);
            font-size: 22px;'>🌉</div>
        <div style='font-size: 22px; font-weight: 800; font-family: Outfit, sans-serif; letter-spacing: 2px;'>
            <span style="color: #FF9933;">SE</span><span style="color: #00ffa3;">TU</span></div>
        <div style='font-size: 10px; color: #6b7094; font-family: JetBrains Mono, monospace;'>सेतु · YOUR BRIDGE</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.profile_complete:
        p = st.session_state.profile
        st.markdown("---")
        st.markdown(f"**👤 {p.get('name', '')}**")
        st.markdown(f"*{p.get('degree', '')} {p.get('major', '')}*")
        st.markdown(f"*{p.get('university', '')}*")
        grad = p.get("graduation_date")
        if grad:
            d = (grad - date.today()).days
            st.markdown(f"🎓 **{d} days** to graduation" if d > 0 else "🎓 **Graduated**")
        st.markdown(f"📊 **{len(st.session_state.applications)}** applications")

    st.markdown("---")
    n = len(h1b_df)
    if os.path.exists("data/h1b_top_sponsors.csv"):
        st.markdown(f"📡 <span class='badge badge-green'>REAL DATA</span> · {n:,} companies", unsafe_allow_html=True)
    else:
        st.markdown(f"📡 <span class='badge badge-yellow'>SAMPLE</span> · {n} companies", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("##### H1B Stats FY25")
    st.markdown("🟢 **85,267** petitions")
    st.markdown("🟡 **25.6%** selected")
    st.markdown("🟣 **$142K** median salary")

# ─── Header ──────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='margin-bottom: 0;'>🌉 <span style="color: #FF9933;">SE</span><span style="color: #00ffa3;">TU</span></h1>
<p style='color: #6b7094; margin-top: 4px;'>सेतु · Your bridge to visa-sponsored careers · Powered by real US government data</p>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ONBOARDING (first time)
# ═══════════════════════════════════════════════════════════════════════
if not st.session_state.profile_complete:
    st.markdown("""
    <div class='welcome-card'>
        <div style='font-size: 48px; margin-bottom: 16px;'>🌉</div>
        <h2 style='margin-bottom: 8px;'>Welcome to Setu</h2>
        <p style='font-size: 16px; color: #8890b5;'>Set up your profile in 30 seconds to get personalized visa deadlines and job matches.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 Your Profile")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Your Name", placeholder="e.g. Rahul Sharma")
        university = st.text_input("University", placeholder="e.g. Florida Atlantic University")
        degree = st.selectbox("Degree", ["M.S.", "M.A.", "MBA", "Ph.D.", "B.S.", "B.A."])
        major = st.text_input("Major", placeholder="e.g. Data Science & Analytics")
    with c2:
        graduation_date = st.date_input("Graduation Date", value=date(2026, 5, 15), min_value=date(2024, 1, 1), max_value=date(2030, 12, 31))
        is_stem = st.selectbox("STEM Degree?", ["Yes", "No", "Not sure"])
        target_roles = st.multiselect("Target Roles",
            ["Data Scientist", "Data Analyst", "ML Engineer", "AI Engineer", "Software Engineer",
             "Data Engineer", "BI Analyst", "Solutions Analyst", "Research Scientist", "Product Analyst"],
            default=["Data Scientist", "Data Analyst"])

    st.markdown("### 🛠️ Your Skills")
    skills = st.multiselect("Select skills (for job matching)", ALL_SKILLS, default=["Python", "SQL", "Machine Learning", "Pandas", "Tableau"])

    if st.button("🚀 Launch My Dashboard", type="primary", use_container_width=True):
        if name and university and major:
            st.session_state.profile = {
                "name": name, "university": university, "degree": degree, "major": major,
                "graduation_date": graduation_date, "is_stem": is_stem,
                "target_roles": target_roles, "skills": skills,
            }
            st.session_state.profile_complete = True
            st.rerun()
        else:
            st.error("Please fill in your name, university, and major.")

else:
    # ═══════════════════════════════════════════════════════════════════
    # MAIN APP
    # ═══════════════════════════════════════════════════════════════════
    p = st.session_state.profile
    grad_date = p.get("graduation_date", date(2026, 5, 15))
    user_skills = p.get("skills", [])
    user_name = p.get("name", "Student")

    jobs_list = []
    for job in JOBS_DATA:
        m = calc_match(job["Skills"], user_skills)
        jobs_list.append({**job, "Match %": m, "SkillTags": ", ".join(job["Skills"])})
    jobs_df = pd.DataFrame(jobs_list).sort_values("Match %", ascending=False)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Dashboard", "🏢 H1B Sponsors", "💼 Jobs",
        "📋 Pipeline", "💰 Salaries", "🗓️ Timeline", "👤 Profile"
    ])

    # ═══ DASHBOARD ═══
    with tab1:
        days_left = max((grad_date - date.today()).days, 0)
        opt_start = grad_date + timedelta(days=1)
        unemp_dl = opt_start + timedelta(days=90)
        days_unemp = max((unemp_dl - date.today()).days, 0)
        n_apps = len(st.session_state.applications)
        n_int = len([a for a in st.session_state.applications if a.get("status") == "Interview"])

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("🎓 Graduation", f"{days_left}d", grad_date.strftime("%b %d, %Y"))
        with c2: st.metric("⏱️ Employment Deadline", f"{days_unemp}d", unemp_dl.strftime("%b %d, %Y"))
        with c3: st.metric("🎰 H1B Lottery", f"FY{grad_date.year+2}", f"Mar {grad_date.year+1}")
        with c4: st.metric("📊 Applications", n_apps, f"{n_int} interview(s)")

        if days_left <= 30 and days_left > 0:
            st.markdown(f"""<div class='warning-box'>
                <strong style='color: #fc5c65;'>🚨 {days_left} DAYS TO GRADUATION</strong> — Have you filed your OPT application?
                Contact your international student office immediately if not.</div>""", unsafe_allow_html=True)

        st.markdown("####")
        st.markdown("### Pipeline")
        cols = st.columns(5)
        for col, label, color in zip(cols,
            ["Applied", "Referral", "Interview", "Offer", "Rejected"],
            ["#6b7094", "#6c5ce7", "#f7b731", "#00ffa3", "#fc5c65"]):
            count = len([a for a in st.session_state.applications if a.get("status") == label])
            with col:
                st.markdown(f"<div class='stat-card'><div class='stat-value' style='color:{color};'>{count}</div><div class='stat-label'>{label}</div></div>", unsafe_allow_html=True)

        st.markdown("####")
        left, right = st.columns([1.3, 1])
        with left:
            st.markdown("### 🎯 Top Matches")
            for _, job in jobs_df.head(4).iterrows():
                mc = "#00ffa3" if job["Match %"] >= 70 else "#f7b731"
                st.markdown(f"""<div class='job-card' style='display:flex;justify-content:space-between;align-items:center;'>
                    <div><div style='font-size:14px;font-weight:600;color:#e2e6f0;'>{job['Title']}</div>
                    <div style='font-size:12px;color:#6b7094;'>{job['Company']} · {job['Location']}</div></div>
                    <div class='match-circle' style='color:{mc};background:{mc}18;border:1.5px solid {mc}40;'>{job['Match %']}%</div></div>""", unsafe_allow_html=True)
        with right:
            st.markdown("### 📌 Activity")
            if st.session_state.applications:
                for app in st.session_state.applications[-5:]:
                    st.markdown(f"""<div class='pipeline-card'>
                        <div style='font-size:13px;font-weight:500;color:#e2e6f0;'>{app['role']} @ {app['company']}</div>
                        <div style='font-size:11px;color:#6b7094;'>{app['status']} · {app.get('date','Today')}</div></div>""", unsafe_allow_html=True)
            else:
                st.markdown("*No applications yet — add one in the Pipeline tab!*")

    # ═══ H1B SPONSORS ═══
    with tab2:
        st.markdown(f"### 🏢 H1B Sponsor Database ({len(h1b_df):,} companies)")
        fc1, fc2, fc3 = st.columns([2, 1, 1])
        with fc1: search = st.text_input("🔍 Search", placeholder="Company name...", key="sp_search")
        with fc2: industry = st.selectbox("Industry", ["All"] + sorted(h1b_df["Industry"].unique().tolist()))
        with fc3: sort_by = st.selectbox("Sort", ["Approvals ↓", "Median Salary ↓", "Denial Rate ↑"])

        f = h1b_df.copy()
        if search: f = f[f["Company"].str.contains(search, case=False, na=False)]
        if industry != "All": f = f[f["Industry"] == industry]
        smap = {"Approvals ↓": ("Approvals", False), "Median Salary ↓": ("Median Salary", False), "Denial Rate ↑": ("Denial %", True)}
        sc, sa = smap[sort_by]
        f = f.sort_values(sc, ascending=sa)

        disp = f.copy()
        disp["Median Salary"] = disp["Median Salary"].apply(lambda x: f"${x:,}" if x > 0 else "N/A")
        disp["Approvals"] = disp["Approvals"].apply(lambda x: f"{x:,}")
        st.dataframe(disp[["Company", "Industry", "Approvals", "Denial %", "Median Salary"]], use_container_width=True, hide_index=True, height=500)

        ch1, ch2 = st.columns(2)
        with ch1:
            fig1 = px.bar(f.nlargest(10, "Approvals"), x="Approvals", y="Company", orientation="h", color="Industry",
                color_discrete_map={"Tech": "#00ffa3", "Consulting": "#f7b731", "Finance": "#6c5ce7", "Other": "#8890b5"},
                title="Top 10 H1B Sponsors")
            fig1.update_layout(paper_bgcolor="#0a0c14", plot_bgcolor="#12141d", font_color="#8890b5", yaxis=dict(autorange="reversed"), height=400)
            st.plotly_chart(fig1, use_container_width=True)
        with ch2:
            sf = f[f["Median Salary"] > 0]
            if len(sf) > 0:
                fig2 = px.scatter(sf, x="Denial %", y="Median Salary", size="Approvals", color="Industry", hover_name="Company",
                    color_discrete_map={"Tech": "#00ffa3", "Consulting": "#f7b731", "Finance": "#6c5ce7", "Other": "#8890b5"},
                    title="Denial Rate vs Salary")
                fig2.update_layout(paper_bgcolor="#0a0c14", plot_bgcolor="#12141d", font_color="#8890b5", height=400)
                st.plotly_chart(fig2, use_container_width=True)

    # ═══ JOBS ═══
    with tab3:
        st.markdown("### 💼 Visa-Friendly Jobs")
        sk_preview = ", ".join(user_skills[:5]) + ("..." if len(user_skills) > 5 else "")
        st.markdown(f"*Matched to your skills: {sk_preview}*")
        job_search = st.text_input("🔍 Search jobs...", key="job_s")
        fj = jobs_df.copy()
        if job_search:
            fj = fj[fj["Title"].str.contains(job_search, case=False, na=False) | fj["Company"].str.contains(job_search, case=False, na=False)]
        for _, job in fj.iterrows():
            mc = "#00ffa3" if job["Match %"] >= 70 else "#f7b731" if job["Match %"] >= 40 else "#6b7094"
            bc = "badge-green" if "Green Card" in job["Sponsorship"] else "badge-yellow"
            sk_html = " ".join([f"<span style='padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;font-family:JetBrains Mono,monospace;background:{'#00ffa320' if s.lower() in [x.lower() for x in user_skills] else '#252836'};color:{'#00ffa3' if s.lower() in [x.lower() for x in user_skills] else '#8890b5'};margin-right:4px;'>{s}</span>" for s in job["Skills"]])
            st.markdown(f"""<div class='job-card' style='display:flex;align-items:center;gap:18px;'>
                <div class='match-circle' style='color:{mc};background:{mc}18;border:1.5px solid {mc}40;flex-shrink:0;'>{job['Match %']}%</div>
                <div style='flex:1;'><div style='font-size:16px;font-weight:700;font-family:Outfit,sans-serif;color:#e2e6f0;'>{job['Title']}</div>
                <div style='font-size:13px;color:#8890b5;margin:4px 0 8px;'>{job['Company']} · {job['Location']} · <span style='color:#00ffa3;'>{job['Salary']}</span></div>
                <div>{sk_html}</div></div>
                <div style='text-align:right;flex-shrink:0;'><span class='badge {bc}'>{job['Sponsorship']}</span>
                <div style='font-size:11px;color:#4a5078;margin-top:8px;font-family:JetBrains Mono,monospace;'>{job['Posted']}</div></div></div>""", unsafe_allow_html=True)

    # ═══ PIPELINE ═══
    with tab4:
        st.markdown("### 📋 Application Pipeline")
        with st.expander("➕ Add Application", expanded=len(st.session_state.applications) == 0):
            ac1, ac2, ac3 = st.columns(3)
            with ac1: nc = st.text_input("Company", placeholder="e.g. Amazon")
            with ac2: nr = st.text_input("Role", placeholder="e.g. Data Scientist")
            with ac3: ns = st.selectbox("Status", ["Applied", "Referral", "Interview", "Offer", "Rejected"])
            if st.button("Add", type="primary"):
                if nc and nr:
                    st.session_state.applications.append({"company": nc, "role": nr, "status": ns, "date": date.today().strftime("%b %d")})
                    st.rerun()

        if st.session_state.applications:
            sc = {"Applied": "#6b7094", "Referral": "#6c5ce7", "Interview": "#f7b731", "Offer": "#00ffa3", "Rejected": "#fc5c65"}
            pm = {"Applied": 15, "Referral": 35, "Interview": 60, "Offer": 100, "Rejected": 100}
            bm = {"Applied": "badge-gray", "Referral": "badge-purple", "Interview": "badge-yellow", "Offer": "badge-green", "Rejected": "badge-red"}
            for app in st.session_state.applications:
                c = sc.get(app["status"], "#6b7094")
                pr = pm.get(app["status"], 10)
                b = bm.get(app["status"], "badge-gray")
                st.markdown(f"""<div class='pipeline-card' style='border-left:3px solid {c};'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div><div style='font-size:16px;font-weight:700;font-family:Outfit,sans-serif;color:#e2e6f0;'>{app['role']}</div>
                    <div style='font-size:13px;color:#8890b5;'>{app['company']} · {app['date']}</div></div>
                    <span class='badge {b}'>{app['status'].upper()}</span></div>
                    <div style='margin-top:12px;height:4px;background:#0d0f17;border-radius:2px;'>
                    <div style='height:100%;width:{pr}%;background:linear-gradient(90deg,{c}cc,{c});border-radius:2px;'></div></div></div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div class='welcome-card'><div style='font-size:36px;margin-bottom:12px;'>📋</div><p style='color:#8890b5;'>Add your first application above!</p></div>", unsafe_allow_html=True)

    # ═══ SALARIES ═══
    with tab5:
        st.markdown("### 💰 Salary Intelligence")
        sm = SALARY_DATA.melt(id_vars=["Role"], var_name="Visa Status", value_name="Salary")
        fig3 = px.bar(sm, x="Role", y="Salary", color="Visa Status", barmode="group",
            color_discrete_map={"OPT": "#f7b731", "H1B": "#6c5ce7", "US Citizen": "#00ffa3"}, title="Salary by Role & Visa Status")
        fig3.update_layout(paper_bgcolor="#0a0c14", plot_bgcolor="#12141d", font_color="#8890b5", height=500, yaxis_tickformat="$,.0f",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown("""<div class='insight-box'>
            <strong style='color:#f7b731;'>💡 NEGOTIATION INSIGHT:</strong>
            <span style='color:#8890b5;'> OPT salaries average 22-35% lower than H1B. Target the H1B median during negotiations.</span></div>""", unsafe_allow_html=True)

    # ═══ TIMELINE ═══
    with tab6:
        st.markdown("### 🗓️ Your Personal Visa Timeline")
        st.markdown(f"*{user_name} · {p.get('degree','')} {p.get('major','')} · Graduating {grad_date.strftime('%B %d, %Y')}*")
        for item in get_timeline(grad_date):
            uc = f"urgency-{item['urgency']}"
            bc = {"done": "badge-gray", "upcoming": "badge-green", "future": "badge-purple"}.get(item["status"], "badge-purple")
            dt = f"<span style='font-size:12px;color:#f7b731;font-family:JetBrains Mono,monospace;'>{item['days']}d away</span>" if item["days"] > 0 else ""
            st.markdown(f"""<div class='timeline-item {uc}'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>
                <div><span style='font-size:11px;color:#00ffa3;font-family:JetBrains Mono,monospace;font-weight:600;'>{item['date']}</span>
                <span class='badge {bc}' style='margin-left:8px;'>{item['status'].upper()}</span></div>{dt}</div>
                <div style='font-size:16px;font-weight:700;font-family:Outfit,sans-serif;color:#e2e6f0;'>{item['label']}</div>
                <div style='font-size:13px;color:#8890b5;margin-top:4px;'>{item['desc']}</div></div>""", unsafe_allow_html=True)

        st.markdown("""<div class='warning-box'><strong style='color:#fc5c65;'>⚠️ 90-DAY RULE:</strong>
            <span style='color:#8890b5;'> Exceeding 90 days without employment automatically terminates your OPT. Unpaid internships (20+ hrs/week) count as employment.</span></div>""", unsafe_allow_html=True)

    # ═══ PROFILE ═══
    with tab7:
        st.markdown("### 👤 Your Profile")
        c1, c2 = st.columns(2)
        with c1:
            sk_html = " ".join([f"<span class='badge badge-green' style='margin:2px;'>{s}</span>" for s in user_skills])
            st.markdown(f"""<div class='profile-card'>
                <div style='font-size:18px;font-weight:700;color:#e2e6f0;font-family:Outfit,sans-serif;'>{p.get('name','')}</div>
                <div style='font-size:13px;color:#8890b5;margin-top:4px;'>{p.get('degree','')} {p.get('major','')}</div>
                <div style='font-size:13px;color:#8890b5;'>{p.get('university','')}</div>
                <div style='font-size:13px;color:#8890b5;margin-top:8px;'>Graduation: <strong style='color:#00ffa3;'>{grad_date.strftime('%B %d, %Y')}</strong></div>
                <div style='font-size:13px;color:#8890b5;'>STEM: <strong style='color:#00ffa3;'>{p.get('is_stem','Yes')}</strong></div>
                <div style='margin-top:12px;'>{sk_html}</div></div>""", unsafe_allow_html=True)
        with c2:
            roles_html = " ".join([f"<span class='badge badge-purple' style='margin:2px;'>{r}</span>" for r in p.get('target_roles', [])])
            st.markdown(f"""<div class='profile-card'>
                <div style='font-size:11px;color:#6b7094;font-family:JetBrains Mono,monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;'>Target Roles</div>
                <div>{roles_html}</div>
                <div style='font-size:11px;color:#6b7094;font-family:JetBrains Mono,monospace;text-transform:uppercase;letter-spacing:1px;margin-top:20px;margin-bottom:8px;'>Stats</div>
                <div style='font-size:13px;color:#8890b5;'>Applications: <strong style='color:#00ffa3;'>{len(st.session_state.applications)}</strong></div>
                <div style='font-size:13px;color:#8890b5;'>Skills: <strong style='color:#00ffa3;'>{len(user_skills)}</strong></div>
                <div style='font-size:13px;color:#8890b5;'>Job Matches: <strong style='color:#00ffa3;'>{len([j for j in jobs_list if j["Match %"] >= 50])}</strong></div></div>""", unsafe_allow_html=True)

        if st.button("🔄 Reset Profile"):
            st.session_state.profile_complete = False
            st.session_state.profile = {}
            st.session_state.applications = []
            st.rerun()

# ─── Footer ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""<div style='text-align:center;padding:10px;color:#4a5078;font-size:11px;font-family:JetBrains Mono,monospace;'>
    Setu v2.0 · सेतु · Founded by Kiran Kumar Reddy Konapalli · Built for international students, by international students · Data from US DOL & USCIS</div>""", unsafe_allow_html=True)
