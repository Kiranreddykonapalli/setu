import re
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
from supabase import create_client, Client

st.set_page_config(page_title="Setu — The Bridge", page_icon="🌉", layout="wide", initial_sidebar_state="collapsed")

# ─── Supabase Connection ─────────────────────────────────────────────────
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ─── Auth Helper Functions ───────────────────────────────────────────────
def is_valid_email(email):
    """Checks if the string looks like a real email (contains @ and .)"""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def sign_up_user(email, password, user_metadata):
    """Creates a new user and stores their profile info securely."""
    return supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": user_metadata} 
    })

def sign_in_user(email, password):
    """Logs an existing user in."""
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def sign_out_user():
    """Logs the user out."""
    supabase.auth.sign_out()

# ─── Smart Data Handlers (Guest vs. Auth) ───────────────────────────────────
# Initialize temporary storage for guests
if "local_tasks" not in st.session_state: st.session_state.local_tasks = []
if "local_jobs" not in st.session_state: st.session_state.local_jobs = []

def fetch_tasks():
    if st.session_state.get("utype") == "guest":
        return st.session_state.local_tasks
    else:
        return supabase.table("tasks").select("*").execute().data

def add_db_task(title, category, due, priority):
    task_data = {"title": title, "category": category, "due": due, "priority": priority, "completed": False}
    if st.session_state.get("utype") == "guest":
        task_data["id"] = f"guest_{len(st.session_state.local_tasks)}"
        st.session_state.local_tasks.append(task_data)
    else:
        supabase.table("tasks").insert(task_data).execute()

def complete_task(task_id):
    if st.session_state.get("utype") == "guest":
        for t in st.session_state.local_tasks:
            if t["id"] == task_id:
                t["completed"] = True
    else:
        supabase.table("tasks").update({"completed": True}).eq("id", task_id).execute()

def fetch_jobs():
    if st.session_state.get("utype") == "guest":
        return st.session_state.local_jobs
    else:
        return supabase.table("job_tracker").select("*").execute().data

def add_db_job(job_data):
    if st.session_state.get("utype") == "guest":
        job_data["id"] = f"guest_{len(st.session_state.local_jobs)}"
        st.session_state.local_jobs.append(job_data)
    else:
        supabase.table("job_tracker").insert(job_data).execute()

def update_db_jobs(df_records):
    if st.session_state.get("utype") == "guest":
        st.session_state.local_jobs = df_records
    else:
        supabase.table("job_tracker").upsert(df_records).execute()


# ─── State ───────────────────────────────────────────────────────────────
defaults = {"page":"landing","profile":{},"utype":None}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root { --bg:#fafbfc;--bg2:#fff;--bg3:#f4f5f7;--border:#e8ebef;--text:#1a1d26;--text2:#5a6178;--text3:#9098b1;
    --accent:#2563eb;--purple:#7c3aed;--green:#10b981;--amber:#f59e0b;--red:#ef4444; }
.stApp { background: var(--bg) !important; }
section[data-testid="stSidebar"] { background: var(--bg2); border-right: 1px solid var(--border); }
h1,h2,h3,h4 { font-family:'Space Grotesk',sans-serif !important; color:var(--text) !important; font-weight:700 !important; }
p,li,span,div,label { color:var(--text2); font-family:'Instrument Sans',sans-serif; }
.stTabs [data-baseweb="tab-list"] { gap:0; border-bottom:1px solid var(--border); background:transparent; }
.stTabs [data-baseweb="tab"] { background:transparent; border:none; border-bottom:2px solid transparent; color:var(--text3); padding:12px 20px; font-family:'Instrument Sans',sans-serif; font-weight:500; font-size:14px; border-radius:0; }
.stTabs [aria-selected="true"] { background:transparent !important; border-bottom:2px solid var(--accent) !important; color:var(--accent) !important; font-weight:600; }
div[data-testid="stMetric"] { background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,.04); }
div[data-testid="stMetric"] label { color:var(--text3) !important; font-family:'IBM Plex Mono',monospace !important; font-size:11px !important; text-transform:uppercase; letter-spacing:.5px; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color:var(--text) !important; font-family:'Space Grotesk',sans-serif !important; font-weight:700 !important; }
.card { background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:20px; margin-bottom:10px; box-shadow:0 1px 3px rgba(0,0,0,.04); }
.card-green { border-left:3px solid var(--green); } .card-amber { border-left:3px solid var(--amber); }
.card-red { border-left:3px solid var(--red); } .card-purple { border-left:3px solid var(--purple); }
.card-accent { border-left:3px solid var(--accent); }
.tag { display:inline-block; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:600; font-family:'IBM Plex Mono',monospace; }
.tag-blue { color:var(--accent); background:#eff6ff; } .tag-green { color:#059669; background:#ecfdf5; }
.tag-amber { color:#d97706; background:#fffbeb; } .tag-red { color:#dc2626; background:#fef2f2; }
.tag-purple { color:#7c3aed; background:#f5f3ff; } .tag-gray { color:var(--text3); background:var(--bg3); }
.hero { text-align:center; padding:50px 20px 30px; }
.feature-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin:28px 0; }
.feature-item { background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:28px; text-align:center; }
.match-ring { display:inline-flex; align-items:center; justify-content:center; width:46px; height:46px; border-radius:50%; font-size:14px; font-weight:700; font-family:'IBM Plex Mono',monospace; }
.pipeline-bar { height:4px; background:var(--bg3); border-radius:2px; margin-top:12px; overflow:hidden; }
.pipeline-fill { height:100%; border-radius:2px; }
.skill-tag { display:inline-block; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:500; margin:2px; font-family:'IBM Plex Mono',monospace; }
.skill-match { color:#059669; background:#ecfdf5; } .skill-miss { color:var(--text3); background:var(--bg3); }
.auth-card { background:var(--bg2); border:1px solid var(--border); border-radius:16px; padding:32px; text-align:center; }
.task-done { text-decoration:line-through; color:var(--text3) !important; }
.task-overdue { background:#fef2f2 !important; border-color:#fecaca !important; }
.stDataFrame { border-radius:12px; overflow:hidden; border:1px solid var(--border); }
.notif { background:#fef2f2; border:1px solid #fecaca; border-radius:10px; padding:14px 18px; margin-bottom:10px; }
.notif-warn { background:#fffbeb; border-color:#fde68a; }
</style>
""", unsafe_allow_html=True)

# ─── Data ────────────────────────────────────────────────────────────────
INDUSTRY_MAP = {"AMAZON":"Tech","GOOGLE":"Tech","MICROSOFT":"Tech","META":"Tech","APPLE":"Tech",
    "NETFLIX":"Tech","NVIDIA":"Tech","ADOBE":"Tech","SALESFORCE":"Tech","ORACLE":"Tech","IBM":"Tech","UBER":"Tech",
    "INFOSYS":"Consulting","TCS":"Consulting","COGNIZANT":"Consulting","WIPRO":"Consulting",
    "DELOITTE":"Consulting","ACCENTURE":"Consulting","ERNST":"Consulting","KPMG":"Consulting",
    "JPMORGAN":"Finance","GOLDMAN":"Finance","CAPITAL ONE":"Finance","BANK OF AMERICA":"Finance",
    "WELLS FARGO":"Finance","MORGAN STANLEY":"Finance","WALMART":"Retail","TARGET":"Retail",
    "PFIZER":"Healthcare","MERCK":"Healthcare"}

ALL_SKILLS = ["Python","SQL","R","Tableau","Power BI","Excel","Machine Learning","Deep Learning",
    "NLP","TensorFlow","PyTorch","Scikit-learn","Pandas","NumPy","Spark","AWS","GCP","Azure",
    "Docker","Git","Java","JavaScript","MongoDB","PostgreSQL","Snowflake","dbt","Airflow","LLMs","GenAI","RAG",
    "Statistics","A/B Testing","Data Mining","ETL"]

def classify_industry(n):
    n=str(n).upper()
    for k,v in INDUSTRY_MAP.items():
        if k in n: return v
    return "Other"

@st.cache_data
def load_h1b():
    p="data/h1b_top_sponsors.csv"
    if os.path.exists(p):
        df=pd.read_csv(p)
        r=pd.DataFrame({"Company":df["employer"].str.title(),"Industry":df["employer"].apply(classify_industry),
            "Approvals":df["total_approvals"],"Denial %":df.get("denial_rate",0),
            "Median Salary":df["median_salary"].fillna(0).astype(int)})
        return r[r["Approvals"]>=10].head(200)
    return pd.DataFrame([
        {"Company":"Amazon","Industry":"Tech","Approvals":12804,"Denial %":3.2,"Median Salary":165000},
        {"Company":"Google","Industry":"Tech","Approvals":9847,"Denial %":1.8,"Median Salary":182000},
        {"Company":"Microsoft","Industry":"Tech","Approvals":8432,"Denial %":2.1,"Median Salary":175000},
        {"Company":"Meta","Industry":"Tech","Approvals":5621,"Denial %":2.5,"Median Salary":190000},
        {"Company":"Infosys","Industry":"Consulting","Approvals":14200,"Denial %":8.4,"Median Salary":95000},
        {"Company":"Deloitte","Industry":"Consulting","Approvals":6700,"Denial %":4.1,"Median Salary":135000},
        {"Company":"JPMorgan","Industry":"Finance","Approvals":4100,"Denial %":3.0,"Median Salary":155000},
        {"Company":"Capital One","Industry":"Finance","Approvals":2400,"Denial %":3.5,"Median Salary":148000},
        {"Company":"Salesforce","Industry":"Tech","Approvals":3200,"Denial %":2.2,"Median Salary":172000},
        {"Company":"Nvidia","Industry":"Tech","Approvals":2600,"Denial %":1.4,"Median Salary":205000},
        {"Company":"Adobe","Industry":"Tech","Approvals":2200,"Denial %":1.9,"Median Salary":175000},
    ])

SALARY=pd.DataFrame([{"Role":"Data Scientist","OPT":95000,"H1B":142000,"US Citizen":148000},
    {"Role":"Data Analyst","OPT":72000,"H1B":105000,"US Citizen":108000},
    {"Role":"ML Engineer","OPT":110000,"H1B":168000,"US Citizen":175000},
    {"Role":"Solutions Analyst","OPT":68000,"H1B":98000,"US Citizen":102000},
    {"Role":"BI Analyst","OPT":65000,"H1B":95000,"US Citizen":100000},
    {"Role":"AI Engineer","OPT":115000,"H1B":178000,"US Citizen":185000}])

JOBS=[
    {"Title":"Data Scientist","Company":"Amazon","Location":"Seattle, WA","Salary":"$140K-$180K","Sponsorship":"H1B + GC","Posted":"2d","Skills":["Python","Machine Learning","SQL","Statistics"]},
    {"Title":"ML Engineer","Company":"Google","Location":"Mountain View, CA","Salary":"$160K-$210K","Sponsorship":"H1B + GC","Posted":"1d","Skills":["Python","TensorFlow","GCP","Deep Learning"]},
    {"Title":"Data Analyst","Company":"Capital One","Location":"McLean, VA","Salary":"$95K-$130K","Sponsorship":"H1B","Posted":"3d","Skills":["SQL","Python","Tableau","Excel"]},
    {"Title":"Solutions Analyst","Company":"Deloitte","Location":"Miami, FL","Salary":"$85K-$120K","Sponsorship":"H1B","Posted":"1d","Skills":["SQL","Power BI","Excel","Statistics"]},
    {"Title":"Data Science (OPT to FT)","Company":"JPMorgan","Location":"New York, NY","Salary":"$110K-$145K","Sponsorship":"OPT to H1B","Posted":"5h","Skills":["Python","Machine Learning","SQL","Pandas"]},
    {"Title":"Analytics Engineer","Company":"Salesforce","Location":"San Francisco, CA","Salary":"$130K-$165K","Sponsorship":"H1B + GC","Posted":"4d","Skills":["SQL","dbt","Python","Snowflake"]},
    {"Title":"AI/ML Researcher","Company":"Nvidia","Location":"Santa Clara, CA","Salary":"$170K-$230K","Sponsorship":"H1B + GC","Posted":"2d","Skills":["Python","PyTorch","Deep Learning","NLP"]},
    {"Title":"GenAI Engineer","Company":"Microsoft","Location":"Redmond, WA","Salary":"$155K-$200K","Sponsorship":"H1B + GC","Posted":"3h","Skills":["Python","LLMs","GenAI","RAG"]},
    {"Title":"Data Engineer","Company":"Meta","Location":"Menlo Park, CA","Salary":"$150K-$195K","Sponsorship":"H1B + GC","Posted":"1d","Skills":["Python","Spark","SQL","Airflow"]},
]

def calc_match(js,us):
    if not us: return 50
    j,u=set(s.lower() for s in js),set(s.lower() for s in us)
    return min(int((len(j&u)/len(j))*100),99) if j else 50

def get_timeline(gd):
    today=date.today(); opt=gd+timedelta(days=1)
    items=[(gd,"Graduation & OPT Start","File I-765. Processing: 3-5 months.","🎓"),
        (opt+timedelta(days=90),"90-Day Employment Deadline","Must have 20+ hrs/week employment or OPT terminates.","⏰"),
        (date(gd.year+1,3,1),"H1B Lottery Registration","Employer registers you. Discuss sponsorship by January.","🎰"),
        (date(gd.year+1,4,1),"Lottery Results","Selected = file petition. Not selected = STEM OPT.","📋"),
        (opt+timedelta(days=365),"STEM OPT Extension Deadline","File before OPT expires. Employer must use E-Verify.","🔬"),
        (date(gd.year+1,10,1),"H1B Starts","If approved, H1B status begins October 1.","✅")]
    result=[]
    for d,label,desc,icon in items:
        days=(d-today).days
        status="done" if days<0 else "soon" if days<=90 else "future"
        result.append({"date":d.strftime("%b %d, %Y"),"label":f"{icon} {label}","desc":desc,"status":status,"days":days})
    return result

h1b_df=load_h1b()
PL=dict(paper_bgcolor="white",plot_bgcolor="#fafbfc",font_color="#5a6178",font_family="Instrument Sans",
    title_font_family="Space Grotesk",title_font_size=16,margin=dict(l=20,r=20,t=50,b=20))

# ═══════════════════════════════════════════════════════════════════════
# LANDING
# ═══════════════════════════════════════════════════════════════════════
if st.session_state.page=="landing":
    st.markdown("""<div class='hero'>
        <div style='font-size:40px;font-weight:700;font-family:Space Grotesk,sans-serif;color:#1a1d26;letter-spacing:-1px;'>
            🌉 Setu <span style='color:#9098b1;font-weight:400;font-size:22px;'>The Bridge</span></div>
        <p style='font-size:17px;color:#5a6178;max-width:500px;margin:12px auto 0;line-height:1.6;'>
            Your bridge to visa-sponsored careers in America.<br>
            <span style='font-size:13px;color:#9098b1;'>Real government data · Personal deadline tracker · Daily task planner</span></p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class='feature-grid'>
        <div class='feature-item'><div style='font-size:28px;margin-bottom:10px;'>📊</div>
            <div style='font-size:15px;font-weight:700;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>H1B Sponsor Intel</div>
            <div style='font-size:12px;color:#9098b1;margin-top:6px;'>Real approval rates and salaries from US Department of Labor.</div></div>
        <div class='feature-item'><div style='font-size:28px;margin-bottom:10px;'>📅</div>
            <div style='font-size:15px;font-weight:700;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>Daily Planner</div>
            <div style='font-size:12px;color:#9098b1;margin-top:6px;'>Set daily tasks, track progress, get alerts when you fall behind.</div></div>
        <div class='feature-item'><div style='font-size:28px;margin-bottom:10px;'>🎯</div>
            <div style='font-size:15px;font-weight:700;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>Smart Job Match</div>
            <div style='font-size:12px;color:#9098b1;margin-top:6px;'>Jobs matched to your skills from confirmed H1B sponsors.</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    c1,c2,c3=st.columns(3)
    with c1:
        st.markdown("<div class='auth-card'><div style='font-size:24px;margin-bottom:8px;'>👤</div><div style='font-size:16px;font-weight:700;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>Continue as Guest</div><div style='font-size:12px;color:#9098b1;margin-top:4px;'>Explore everything instantly.</div></div>", unsafe_allow_html=True)
        if st.button("Get Started",use_container_width=True,key="g"):
            st.session_state.utype="guest"; st.session_state.page="setup"; st.rerun()
    with c2:
        st.markdown("<div class='auth-card'><div style='font-size:24px;margin-bottom:8px;'>🔑</div><div style='font-size:16px;font-weight:700;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>Sign In</div><div style='font-size:12px;color:#9098b1;margin-top:4px;'>Welcome back! Access your data.</div></div>", unsafe_allow_html=True)
        if st.button("Sign In",use_container_width=True,key="si"):
            st.session_state.page="signin"; st.rerun()
    with c3:
        st.markdown("<div class='auth-card'><div style='font-size:24px;margin-bottom:8px;'>✨</div><div style='font-size:16px;font-weight:700;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>Create Account</div><div style='font-size:12px;color:#9098b1;margin-top:4px;'>Save your data and get alerts.</div></div>", unsafe_allow_html=True)
        if st.button("Sign Up Free",use_container_width=True,type="primary",key="s"):
            st.session_state.utype="signup"; st.session_state.page="setup"; st.rerun()

    st.markdown("---")
    st.markdown("<div style='text-align:center;color:#9098b1;font-size:11px;font-family:IBM Plex Mono,monospace;'>Setu v3.1 · Founded by Kiran Kumar Reddy Konapalli · Built for international students</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# SIGN IN
# ═══════════════════════════════════════════════════════════════════════
elif st.session_state.page=="signin":
    st.markdown("## Welcome back")
    st.markdown("*Sign in to access your dashboard, job tracker, and tasks.*")
    st.markdown("####")

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        si_email=st.text_input("Email",placeholder="you@university.edu",key="si_email")
        si_pw=st.text_input("Password",type="password",placeholder="Your password",key="si_pw")
        st.markdown("####")
        if st.button("Sign In",type="primary",use_container_width=True,key="si_btn"):
            if si_email and si_pw:
                if not is_valid_email(si_email):
                    st.error("Please enter a valid email address.")
                else:
                    try:
                        # REAL AUTHENTICATION
                        response = sign_in_user(si_email, si_pw)
                        st.session_state.user = response.user
                        st.session_state.profile = response.user.user_metadata
                        st.session_state.utype = "user"
                        st.session_state.page = "app"
                        st.rerun()
                    except Exception as e:
                        st.error("Invalid email or password. Please try again.")
            else:
                st.error("Please enter your email and password.")

        st.markdown("####")
        st.markdown("<div style='text-align:center;'><span style='font-size:13px;color:#9098b1;'>Don't have an account?</span></div>", unsafe_allow_html=True)
        if st.button("Create a free account",use_container_width=True,key="si_signup"):
            st.session_state.utype="signup"; st.session_state.page="setup"; st.rerun()
        if st.button("Continue as guest instead",use_container_width=True,key="si_guest"):
            st.session_state.utype="guest"; st.session_state.page="setup"; st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════
elif st.session_state.page=="setup":
    st.markdown("## Set up your profile")
    st.markdown("*30 seconds. Unlocks your personalized dashboard.*")
    if st.session_state.utype=="signup":
        ec1,ec2=st.columns(2)
        with ec1: email=st.text_input("Email",placeholder="you@university.edu")
        with ec2: pw=st.text_input("Password",type="password",placeholder="Create a password")
        st.markdown("---")
    c1,c2=st.columns(2)
    with c1:
        name=st.text_input("Name",placeholder="e.g. Rahul Sharma")
        university=st.text_input("University",placeholder="e.g. Florida Atlantic University")
        degree=st.selectbox("Degree",["M.S.","M.A.","MBA","Ph.D.","B.S.","B.A."])
        major=st.text_input("Major",placeholder="e.g. Data Science & Analytics")
    with c2:
        grad=st.date_input("Graduation date",value=date(2026,5,15),min_value=date(2024,1,1),max_value=date(2030,12,31))
        stem=st.selectbox("STEM degree?",["Yes","No","Not sure"])
        roles=st.multiselect("Target roles",["Data Scientist","Data Analyst","ML Engineer","AI Engineer","Software Engineer","Data Engineer","BI Analyst","Solutions Analyst","Research Scientist","Product Analyst"],default=["Data Scientist","Data Analyst"])
    st.markdown("##### Your skills")
    skills=st.multiselect("Select skills for job matching",ALL_SKILLS,default=["Python","SQL","Machine Learning","Pandas","Tableau"])
    
    if st.button("Launch My Dashboard",type="primary",use_container_width=True):
        if st.session_state.utype == "signup":
            if not email or not pw or not is_valid_email(email):
                st.error("Please enter a valid email address and password.")
            elif name and university and major:
                profile_data = {
                    "name":name, "university":university, "degree":degree, "major":major,
                    "grad":str(grad), "stem":stem, "roles":roles, "skills":skills, "utype":"signup"
                }
                try:
                    # REAL ACCOUNT CREATION
                    response = sign_up_user(email, pw, profile_data)
                    st.session_state.user = response.user
                    st.session_state.profile = profile_data
                    st.session_state.utype = "user"
                    st.session_state.page = "app"
                    st.success("Account created successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating account: {e}")
            else: 
                st.error("Please fill in name, university, and major.")
        else: # GUEST LOGIC
            if name and university and major:
                st.session_state.profile={"name":name,"university":university,"degree":degree,"major":major,
                    "grad":grad,"stem":stem,"roles":roles,"skills":skills,"utype":"guest"}
                st.session_state.page="app"; st.rerun()
            else: 
                st.error("Please fill in name, university, and major.")

# ═══════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════
elif st.session_state.page=="app":
    # --- FETCH DATA ---
    db_tasks = fetch_tasks()
    db_jobs = fetch_jobs()
    
    p=st.session_state.profile
    
    # Handle the date formatting perfectly for both Guests (who have Python dates) and Auth Users (who have strings from JSON)
    gd_raw = p.get("grad", date(2026,5,15))
    if isinstance(gd_raw, str):
        gd = datetime.strptime(gd_raw, "%Y-%m-%d").date()
    else:
        gd = gd_raw
        
    skills=p.get("skills",[]); uname=p.get("name","Student")
    jl=[{**j,"Match":calc_match(j["Skills"],skills)} for j in JOBS]
    jobs_df=pd.DataFrame(jl).sort_values("Match",ascending=False)

    # Top bar
    bar1,bar2=st.columns([8,1])
    with bar1:
        acct="tag-gray" if st.session_state.utype=="guest" else "tag-green"
        lbl="GUEST" if st.session_state.utype=="guest" else "ACCOUNT"
        st.markdown(f"<div style='display:flex;align-items:center;gap:12px;'><span style='font-size:13px;color:#5a6178;'>Welcome, <strong style='color:#1a1d26;'>{uname}</strong></span><span class='tag {acct}'>{lbl}</span></div>", unsafe_allow_html=True)
    with bar2:
        if st.button("Logout",key="lo"):
            if st.session_state.utype != "guest":
                sign_out_user() # Tell Supabase to end the session
            for k in defaults: st.session_state[k]=defaults[k]
            st.session_state.local_tasks = []
            st.session_state.local_jobs = []
            st.rerun()
    st.markdown("---")

    # Check for overdue tasks
    today_str=date.today().strftime("%Y-%m-%d")
    overdue=[t for t in db_tasks if str(t.get("due","")) < today_str and not t.get("completed")]
    due_today=[t for t in db_tasks if str(t.get("due","")) == today_str and not t.get("completed")]

    if overdue:
        st.markdown(f"<div class='notif'>🔴 <strong style='color:#dc2626;'>You have {len(over
