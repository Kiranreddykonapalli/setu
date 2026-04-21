import re
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
import urllib.request, urllib.parse, json as _json
from supabase import create_client, Client

st.set_page_config(page_title="Setu — The Bridge", page_icon="🌉", layout="wide", initial_sidebar_state="collapsed")

# ─── Supabase Connection ─────────────────────────────────────────────────
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"].strip().strip('"').strip("'")
    key = st.secrets["SUPABASE_KEY"].strip().strip('"').strip("'")
    return create_client(url, key)

supabase = init_connection()

# ─── Auth Helper Functions ───────────────────────────────────────────────
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def sign_up_user(email, password, user_metadata):
    return supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": user_metadata} 
    })

def sign_in_user(email, password):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def sign_out_user():
    supabase.auth.sign_out()

def reset_password_email(email):
    try:
        supabase.auth.reset_password_for_email(
            email,
            options={"redirect_to": "https://setu-bridge.streamlit.app"}
        )
        return True, "✓ Check your email for password reset link"
    except Exception as e:
        if "not found" in str(e).lower():
            return False, "❌ No account with this email"
        return False, f"Error: {str(e)[:80]}"

# ─── Smart Data Handlers ───────────────────────────────────────────────────
if "local_tasks" not in st.session_state: st.session_state.local_tasks = []
if "local_jobs" not in st.session_state: st.session_state.local_jobs = []

def fetch_tasks():
    if st.session_state.get("utype") == "guest":
        return st.session_state.local_tasks
    else:
        user_id = st.session_state.get("user_id")
        if user_id:
            try:
                return supabase.table("tasks").select("*").eq("user_id", user_id).execute().data
            except Exception as e:
                st.error(f"Error fetching tasks: {e}")
                return []
        return []

def add_db_task(title, category, due, priority):
    task_data = {"title": title, "category": category, "due": due, "priority": priority, "completed": False}
    if st.session_state.get("utype") == "guest":
        task_data["id"] = f"guest_{len(st.session_state.local_tasks)}"
        st.session_state.local_tasks.append(task_data)
    else:
        user_id = st.session_state.get("user_id")
        if user_id:
            task_data["user_id"] = user_id
            try:
                supabase.table("tasks").insert(task_data).execute()
            except Exception as e:
                st.error(f"Database Error (Add Task): {e}")

def complete_task(task_id):
    if st.session_state.get("utype") == "guest":
        for t in st.session_state.local_tasks:
            if t["id"] == task_id:
                t["completed"] = True
    else:
        try:
            supabase.table("tasks").update({"completed": True}).eq("id", task_id).execute()
        except Exception as e:
            st.error(f"Database Error (Complete Task): {e}")

def delete_task(task_id):
    if st.session_state.get("utype") == "guest":
        st.session_state.local_tasks = [t for t in st.session_state.local_tasks if t["id"] != task_id]
    else:
        try:
            supabase.table("tasks").delete().eq("id", task_id).execute()
        except Exception as e:
            st.error(f"Database Error (Delete Task): {e}")

def fetch_jobs():
    if st.session_state.get("utype") == "guest":
        return st.session_state.local_jobs
    else:
        user_id = st.session_state.get("user_id")
        if user_id:
            try:
                return supabase.table("job_tracker").select("*").eq("user_id", user_id).execute().data
            except Exception as e:
                st.error(f"Error fetching jobs: {e}")
                return []
        return []

def add_db_job(job_data):
    if st.session_state.get("utype") == "guest":
        job_data["id"] = f"guest_{len(st.session_state.local_jobs)}"
        st.session_state.local_jobs.append(job_data)
    else:
        user_id = st.session_state.get("user_id")
        if user_id:
            job_data["user_id"] = user_id
            try:
                supabase.table("job_tracker").insert(job_data).execute()
            except Exception as e:
                st.error(f"Database Error (Add Job): {e}")

def delete_job(job_id):
    if st.session_state.get("utype") == "guest":
        st.session_state.local_jobs = [j for j in st.session_state.local_jobs if j.get("id") != job_id]
    else:
        try:
            supabase.table("job_tracker").delete().eq("id", job_id).execute()
        except Exception as e:
            st.error(f"Database Error (Delete Job): {e}")

def update_db_jobs(df_records):
    if st.session_state.get("utype") == "guest":
        st.session_state.local_jobs = df_records
    else:
        try:
            supabase.table("job_tracker").upsert(df_records).execute()
        except Exception as e:
            st.error(f"Database Error (Update Jobs): {e}")

# ─── State ───────────────────────────────────────────────────────────────
defaults = {"page":"landing","profile":{},"utype":None,"user_id":None}
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
.profile-icon { display:inline-flex; align-items:center; justify-content:center; width:40px; height:40px; border-radius:50%; background:var(--accent); color:white; font-weight:700; font-size:16px; cursor:pointer; }
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

# ─── Live Job Fetcher (USA Only) ─────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_jobs(query, location):
    """Fetch jobs from USA-only sources"""
    results = []
    
    # Source 1: USAJobs (official US government job board - always USA)
    try:
        loc = location if location else "Florida"
        q = urllib.parse.quote_plus(query)
        l = urllib.parse.quote_plus(loc)
        url = f"https://data.usajobs.gov/api/search?Keyword={q}&LocationName={l}&ResultsPerPage=10"
        req = urllib.request.Request(url, headers={
            "User-Agent": "setu-bridge-app",
            "Host": "data.usajobs.gov"
        })
        with urllib.request.urlopen(req, timeout=6) as r:
            data = _json.loads(r.read())
            items = data.get("SearchResult", {}).get("SearchResultItems", [])
            for item in items:
                j = item.get("MatchedObjectDescriptor", {})
                salary_min = j.get("PositionRemuneration", [{}])[0].get("MinimumRange", "")
                salary_max = j.get("PositionRemuneration", [{}])[0].get("MaximumRange", "")
                salary_str = f"${int(float(salary_min)):,} - ${int(float(salary_max)):,}" if salary_min and salary_max else "See posting"
                loc_list = j.get("PositionLocation", [{}])
                loc_str = loc_list[0].get("LocationName", "USA") if loc_list else "USA"
                results.append({
                    "title": j.get("PositionTitle", ""),
                    "company": j.get("OrganizationName", "US Government"),
                    "location": loc_str,
                    "url": j.get("PositionURI", "#"),
                    "salary": salary_str,
                    "posted": j.get("PublicationStartDate", "")[:10],
                    "tags": ["Government", "Visa-friendly"],
                    "remote": False,
                    "source": "USAJobs"
                })
    except:
        pass

    # Source 2: Remotive (tech jobs, remote, USA companies)
    try:
        q2 = urllib.parse.quote_plus(query)
        url2 = f"https://remotive.com/api/remote-jobs?search={q2}&limit=10"
        req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=6) as r2:
            data2 = _json.loads(r2.read())
            for j in data2.get("jobs", [])[:10]:
                # Filter USA companies only
                geo = j.get("candidate_required_location", "")
                if geo and ("worldwide" not in geo.lower() and "usa" not in geo.lower() 
                    and "us" not in geo.lower() and "united states" not in geo.lower() 
                    and "america" not in geo.lower() and geo.strip() != ""):
                    continue
                results.append({
                    "title": j.get("title", ""),
                    "company": j.get("company_name", ""),
                    "location": geo if geo else "Remote USA",
                    "url": j.get("url", "#"),
                    "salary": j.get("salary", "Competitive"),
                    "posted": j.get("publication_date", "")[:10],
                    "tags": j.get("tags", [])[:4],
                    "remote": True,
                    "source": "Remotive"
                })
    except:
        pass

    return results[:20]

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
    st.markdown("<div style='text-align:center;color:#9098b1;font-size:11px;font-family:IBM Plex Mono,monospace;'>Setu v4.2 · Founded by Kiran Kumar Reddy Konapalli · Built for international students</div>", unsafe_allow_html=True)

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
                        response = sign_in_user(si_email, si_pw)
                        if response and response.user:
                            st.session_state.user = response.user
                            st.session_state.user_id = response.user.id
                            st.session_state.profile = response.user.user_metadata if response.user.user_metadata else {}
                            st.session_state.utype = "user"
                            st.session_state.page = "app"
                            st.success("✓ Signed in successfully!")
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                    except Exception as e:
                        st.error(f"Login failed: {e}")
            else:
                st.error("Please enter your email and password.")

        st.markdown("####")
        if st.button("Forgot Password?",use_container_width=True,key="si_forgot"):
            st.session_state.page="forgot_password"; st.rerun()
        st.markdown("####")
        st.markdown("<div style='text-align:center;'><span style='font-size:13px;color:#9098b1;'>Don't have an account?</span></div>", unsafe_allow_html=True)
        if st.button("Create a free account",use_container_width=True,key="si_signup"):
            st.session_state.utype="signup"; st.session_state.page="setup"; st.rerun()
        if st.button("Continue as guest instead",use_container_width=True,key="si_guest"):
            st.session_state.utype="guest"; st.session_state.page="setup"; st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# FORGOT PASSWORD
# ═══════════════════════════════════════════════════════════════════════
elif st.session_state.page=="forgot_password":
    st.markdown("## Reset your password")
    st.markdown("*Enter your email and we'll send you a password reset link.*")
    st.markdown("####")

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        fp_email=st.text_input("Email address",placeholder="you@university.edu",key="fp_email")
        st.markdown("####")
        if st.button("Send Reset Link",type="primary",use_container_width=True,key="fp_btn"):
            if fp_email:
                if not is_valid_email(fp_email):
                    st.error("Please enter a valid email address.")
                else:
                    success, msg = reset_password_email(fp_email)
                    if success:
                        st.success(msg)
                        st.info("📧 Check your email for the reset link.")
                    else:
                        st.error(msg)
            else:
                st.error("Please enter your email address.")
        st.markdown("####")
        if st.button("Back to Sign In",use_container_width=True,key="fp_signin"):
            st.session_state.page="signin"; st.rerun()

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
            elif len(pw) < 6:
                st.error("Password must be at least 6 characters.")
            elif name and university and major:
                profile_data = {"name":name,"university":university,"degree":degree,"major":major,
                    "grad":str(grad),"stem":stem,"roles":roles,"skills":skills}
                try:
                    response = sign_up_user(email, pw, profile_data)
                    if response and response.user:
                        st.session_state.user = response.user
                        st.session_state.user_id = response.user.id
                        st.session_state.profile = profile_data
                        st.session_state.utype = "user"
                        st.session_state.page = "app"
                        st.success("✓ Account created successfully!")
                        st.rerun()
                    else:
                        st.error("Error creating account. Please try again.")
                except Exception as e:
                    if "already registered" in str(e).lower() or "user already exists" in str(e).lower():
                        st.error("📧 This email is already registered. Please sign in instead.")
                    else:
                        st.error(f"Sign Up Error: {e}")
            else:
                st.error("Please fill in name, university, and major.")
        else:
            if name and university and major:
                st.session_state.profile={"name":name,"university":university,"degree":degree,"major":major,
                    "grad":grad,"stem":stem,"roles":roles,"skills":skills}
                st.session_state.page="app"; st.rerun()
            else:
                st.error("Please fill in name, university, and major.")

# ═══════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════
elif st.session_state.page=="app":
    db_tasks = fetch_tasks()
    db_jobs = fetch_jobs()
    
    p=st.session_state.profile
    
    gd_raw = p.get("grad", date(2026,5,15))
    if isinstance(gd_raw, str):
        try: gd = datetime.strptime(gd_raw, "%Y-%m-%d").date()
        except: gd = date(2026,5,15)
    else:
        gd = gd_raw if isinstance(gd_raw, date) else date(2026,5,15)
        
    skills=p.get("skills",[]); uname=p.get("name","Student")
    user_initial = uname[0].upper() if uname else "S"
    jl=[{**j,"Match":calc_match(j["Skills"],skills)} for j in JOBS]
    jobs_df=pd.DataFrame(jl).sort_values("Match",ascending=False)

    bar1,bar2,bar3=st.columns([7,1,1])
    with bar1:
        acct="tag-gray" if st.session_state.utype=="guest" else "tag-green"
        lbl="GUEST" if st.session_state.utype=="guest" else "ACCOUNT"
        st.markdown(f"<div style='display:flex;align-items:center;gap:12px;'><span style='font-size:13px;color:#5a6178;'>Welcome, <strong style='color:#1a1d26;'>{uname}</strong></span><span class='tag {acct}'>{lbl}</span></div>", unsafe_allow_html=True)
    with bar2:
        st.markdown(f"<div class='profile-icon'>{user_initial}</div>", unsafe_allow_html=True)
    with bar3:
        if st.button("Logout",key="lo"):
            if st.session_state.utype != "guest":
                try: sign_out_user()
                except: pass
            for k in defaults: st.session_state[k]=defaults[k]
            st.session_state.local_tasks = []
            st.session_state.local_jobs = []
            st.rerun()
    st.markdown("---")

    today_str=date.today().strftime("%Y-%m-%d")
    overdue=[t for t in db_tasks if str(t.get("due","")) < today_str and not t.get("completed")]
    due_today=[t for t in db_tasks if str(t.get("due","")) == today_str and not t.get("completed")]

    if overdue:
        st.markdown(f"<div class='notif'>🔴 <strong style='color:#dc2626;'>You have {len(overdue)} overdue task(s)!</strong> Check your Daily Planner.</div>", unsafe_allow_html=True)
    if due_today:
        st.markdown(f"<div class='notif notif-warn'>🟡 <strong style='color:#d97706;'>{len(due_today)} task(s) due today.</strong> Stay on track!</div>", unsafe_allow_html=True)

    tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8,tab9,tab10=st.tabs(["Overview","H1B Sponsors","Jobs","Job Tracker","Daily Planner","Salaries","Timeline","Profile","🤖 AI Resume","🎯 AI Job Finder"])

    with tab1:
        dl=max((gd-date.today()).days,0); opt_s=gd+timedelta(days=1); unemp=opt_s+timedelta(days=90); du=max((unemp-date.today()).days,0)
        na=len(db_jobs); ni=len([a for a in db_jobs if a.get("Status") in ["Phone Screen","Technical Interview","Onsite"]])
        pending_tasks=len([t for t in db_tasks if not t.get("completed")])

        c1,c2,c3,c4,c5=st.columns(5)
        with c1: st.metric("Graduation",f"{dl}d",gd.strftime("%b %Y"))
        with c2: st.metric("Employment deadline",f"{du}d",unemp.strftime("%b %Y"))
        with c3: st.metric("H1B Lottery",f"FY{gd.year+2}",f"Mar {gd.year+1}")
        with c4: st.metric("Applications",na,f"{ni} interviews")
        with c5: st.metric("Tasks pending",pending_tasks,f"{len(overdue)} overdue")

        if dl<=45 and dl>0:
            st.markdown(f"<div class='card card-red'><strong style='color:#ef4444;'>⚠️ {dl} days to graduation</strong> — Have you filed your OPT application?</div>", unsafe_allow_html=True)

        st.markdown("####")
        left,right=st.columns([1.4,1])
        with left:
            st.markdown("##### Top job matches")
            for _,j in jobs_df.head(4).iterrows():
                mc="#10b981" if j["Match"]>=70 else "#f59e0b"
                st.markdown(f"<div class='card' style='display:flex;justify-content:space-between;align-items:center;padding:14px 18px;'><div><div style='font-size:14px;font-weight:600;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>{j['Title']}</div><div style='font-size:12px;color:#9098b1;'>{j['Company']} · {j['Salary']}</div></div><div class='match-ring' style='color:{mc};background:{mc}12;border:2px solid {mc};'>{j['Match']}%</div></div>", unsafe_allow_html=True)
        with right:
            st.markdown("##### Today's tasks")
            todays=[t for t in db_tasks if str(t.get("due",""))==today_str and not t.get("completed")]
            if todays:
                for t in todays[:5]:
                    cat_colors={"Visa":"tag-red","Job Search":"tag-blue","Learning":"tag-purple","Personal":"tag-gray"}
                    tc=cat_colors.get(t.get("category",""),"tag-gray")
                    st.markdown(f"<div class='card' style='padding:12px 18px;'><div style='display:flex;justify-content:space-between;align-items:center;'><span style='font-size:13px;color:#1a1d26;'>{t['title']}</span><span class='tag {tc}'>{t.get('category','')}</span></div></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='card' style='text-align:center;padding:30px;'><p style='color:#9098b1;font-size:13px;'>No tasks for today. Add some in Daily Planner!</p></div>", unsafe_allow_html=True)

    with tab2:
        st.markdown(f"##### H1B Sponsors — {len(h1b_df):,} companies")
        fc1,fc2,fc3=st.columns([2,1,1])
        with fc1: search=st.text_input("Search",placeholder="Company name...",key="s1")
        with fc2: ind=st.selectbox("Industry",["All"]+sorted(h1b_df["Industry"].unique().tolist()))
        with fc3: sb=st.selectbox("Sort",["Approvals","Salary","Denial Rate"])
        f=h1b_df.copy()
        if search: f=f[f["Company"].str.contains(search,case=False,na=False)]
        if ind!="All": f=f[f["Industry"]==ind]
        sm={"Approvals":("Approvals",False),"Salary":("Median Salary",False),"Denial Rate":("Denial %",True)}
        sc,sa=sm[sb]; f=f.sort_values(sc,ascending=sa)
        disp=f.copy(); disp["Median Salary"]=disp["Median Salary"].apply(lambda x:f"${x:,}" if x>0 else "—"); disp["Approvals"]=disp["Approvals"].apply(lambda x:f"{x:,}")
        st.dataframe(disp[["Company","Industry","Approvals","Denial %","Median Salary"]],use_container_width=True,hide_index=True,height=450)
        ch1,ch2=st.columns(2)
        with ch1:
            fig=px.bar(f.nlargest(10,"Approvals"),x="Approvals",y="Company",orientation="h",color="Industry",
                color_discrete_map={"Tech":"#2563eb","Consulting":"#f59e0b","Finance":"#7c3aed","Other":"#9098b1"},title="Top 10 sponsors")
            fig.update_layout(**PL,yaxis=dict(autorange="reversed"),height=400); st.plotly_chart(fig,use_container_width=True)
        with ch2:
            sf=f[f["Median Salary"]>0]
            if len(sf)>0:
                fig2=px.scatter(sf,x="Denial %",y="Median Salary",size="Approvals",color="Industry",hover_name="Company",
                    color_discrete_map={"Tech":"#2563eb","Consulting":"#f59e0b","Finance":"#7c3aed","Other":"#9098b1"},title="Denial vs salary")
                fig2.update_layout(**PL,height=400); st.plotly_chart(fig2,use_container_width=True)

    # ─── JOBS TAB (LIVE USA ONLY) ─────────────────────────────────────────
    with tab3:
        st.markdown("##### Live visa-friendly jobs — USA only 🇺🇸")
        sk_p=", ".join(skills[:4])+("..." if len(skills)>4 else "")
        st.markdown(f"*Matched to: {sk_p}*")

        # ── Auto-detect location from university ──
        UNIVERSITY_LOCATIONS = {
            "florida atlantic": "Boca Raton, FL",
            "fau": "Boca Raton, FL",
            "university of florida": "Gainesville, FL",
            "uf": "Gainesville, FL",
            "florida international": "Miami, FL",
            "fiu": "Miami, FL",
            "university of miami": "Miami, FL",
            "florida state": "Tallahassee, FL",
            "fsu": "Tallahassee, FL",
            "university of south florida": "Tampa, FL",
            "usf": "Tampa, FL",
            "mit": "Boston, MA",
            "harvard": "Boston, MA",
            "stanford": "San Francisco, CA",
            "carnegie mellon": "Pittsburgh, PA",
            "cmu": "Pittsburgh, PA",
            "georgia tech": "Atlanta, GA",
            "gatech": "Atlanta, GA",
            "university of texas": "Austin, TX",
            "ut austin": "Austin, TX",
            "university of michigan": "Ann Arbor, MI",
            "university of illinois": "Chicago, IL",
            "uiuc": "Chicago, IL",
            "columbia": "New York, NY",
            "nyu": "New York, NY",
            "new york university": "New York, NY",
            "university of washington": "Seattle, WA",
            "uw seattle": "Seattle, WA",
            "university of california": "California",
            "ucla": "Los Angeles, CA",
            "usc": "Los Angeles, CA",
            "uc san diego": "San Diego, CA",
            "ucsd": "San Diego, CA",
            "uc berkeley": "San Francisco, CA",
            "berkeley": "San Francisco, CA",
            "purdue": "Indianapolis, IN",
            "penn state": "Philadelphia, PA",
            "university of pennsylvania": "Philadelphia, PA",
            "upenn": "Philadelphia, PA",
            "northeastern": "Boston, MA",
            "boston university": "Boston, MA",
            "bu": "Boston, MA",
            "university of chicago": "Chicago, IL",
            "northwestern": "Chicago, IL",
            "duke": "Durham, NC",
            "unc": "Charlotte, NC",
            "nc state": "Raleigh, NC",
            "arizona state": "Phoenix, AZ",
            "asu": "Phoenix, AZ",
            "university of arizona": "Phoenix, AZ",
            "ohio state": "Columbus, OH",
            "osu": "Columbus, OH",
        }

        # Detect location from profile university
        user_univ = p.get("university", "").lower()
        auto_location = "Florida"  # default for FAU students
        for key, loc in UNIVERSITY_LOCATIONS.items():
            if key in user_univ:
                auto_location = loc
                break

        jcol1, jcol2 = st.columns([3,1])
        with jcol1:
            js = st.text_input("Search jobs", placeholder="e.g. Data Scientist, ML Engineer, Python...", key="js")
        with jcol2:
            job_location = st.text_input("Location", value=auto_location, key="jloc",
                help="Auto-detected from your university. Change to search anywhere in USA.")

        if auto_location != "Florida":
            st.markdown(f"<div style='font-size:12px;color:#2563eb;margin-bottom:8px;font-family:IBM Plex Mono,monospace;'>📍 Showing jobs near <strong>{auto_location}</strong> based on your university</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size:12px;color:#2563eb;margin-bottom:8px;font-family:IBM Plex Mono,monospace;'>📍 Showing jobs near <strong>Florida (FAU area)</strong> + Remote USA jobs</div>", unsafe_allow_html=True)

        search_query = js if js else (p.get("roles", ["Data Scientist"])[0] if p.get("roles") else "Data Scientist")
        loc_val = job_location if job_location else auto_location

        with st.spinner("🔍 Fetching live USA jobs..."):
            live_jobs = fetch_live_jobs(search_query, loc_val)

        if live_jobs:
            st.markdown(f"<div style='font-size:12px;color:#10b981;margin-bottom:14px;font-family:IBM Plex Mono,monospace;'>✅ {len(live_jobs)} live USA jobs found · Refreshed hourly · Click Apply Now to apply directly</div>", unsafe_allow_html=True)
            for j in live_jobs:
                title    = j.get("title", "")
                company  = j.get("company", "")
                loc_j    = j.get("location", "USA")
                url_j    = j.get("url", "#")
                tags     = j.get("tags", [])
                remote   = j.get("remote", False)
                posted   = str(j.get("posted", ""))[:10] if j.get("posted") else "Recently"
                salary   = j.get("salary", "")
                source   = j.get("source", "")
                remote_badge = "<span class='tag tag-green'>🌐 Remote</span>" if remote else "<span class='tag tag-blue'>📍 On-site</span>"
                source_badge = f"<span class='tag tag-gray'>{source}</span>" if source else ""
                skills_html  = " ".join([f"<span class='skill-tag skill-match'>{t}</span>" for t in tags[:4]])
                salary_html  = f"<span style='color:#2563eb;font-weight:600;font-size:13px;'>{salary}</span>" if salary and salary != "Competitive" else ""
                st.markdown(f"""
                <div class='card' style='padding:18px 22px;margin-bottom:10px;'>
                  <div style='display:flex;justify-content:space-between;align-items:flex-start;gap:16px;'>
                    <div style='flex:1;'>
                      <div style='font-size:15px;font-weight:600;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>{title}</div>
                      <div style='font-size:13px;color:#5a6178;margin:4px 0 8px;'>{company} &nbsp;·&nbsp; {loc_j} &nbsp; {salary_html}</div>
                      <div style='margin-bottom:6px;'>{skills_html} &nbsp; {remote_badge} &nbsp; {source_badge}</div>
                    </div>
                    <div style='text-align:right;flex-shrink:0;min-width:110px;'>
                      <div style='font-size:11px;color:#9098b1;margin-bottom:10px;font-family:IBM Plex Mono,monospace;'>📅 {posted}</div>
                      <a href='{url_j}' target='_blank'
                         style='display:inline-block;background:#2563eb;color:white;padding:8px 16px;
                                border-radius:8px;font-size:12px;font-weight:600;text-decoration:none;
                                font-family:Instrument Sans,sans-serif;'>Apply Now →</a>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("💡 Live job feed unavailable right now — showing curated visa-friendly jobs.")
            fj=jobs_df.copy()
            if js: fj=fj[fj["Title"].str.contains(js,case=False,na=False)|fj["Company"].str.contains(js,case=False,na=False)]
            for _,j in fj.iterrows():
                mc="#10b981" if j["Match"]>=70 else "#f59e0b" if j["Match"]>=40 else "#9098b1"
                tc="tag-green" if "GC" in j["Sponsorship"] else "tag-blue"
                skh=" ".join([f"<span class='skill-tag {'skill-match' if s.lower() in [x.lower() for x in skills] else 'skill-miss'}'>{s}</span>" for s in j["Skills"]])
                st.markdown(f"<div class='card' style='display:flex;align-items:center;gap:18px;padding:16px 20px;'><div class='match-ring' style='color:{mc};background:{mc}12;border:2px solid {mc};flex-shrink:0;'>{j['Match']}%</div><div style='flex:1;'><div style='font-size:15px;font-weight:600;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>{j['Title']}</div><div style='font-size:13px;color:#5a6178;margin:3px 0 8px;'>{j['Company']} · {j['Location']} · <span style='color:#2563eb;'>{j['Salary']}</span></div><div>{skh}</div></div><div style='text-align:right;flex-shrink:0;'><span class='tag {tc}'>{j['Sponsorship']}</span><div style='font-size:11px;color:#9098b1;margin-top:6px;'>{j['Posted']} ago</div></div></div>", unsafe_allow_html=True)

    with tab4:
        st.markdown("##### Job application tracker")
        st.markdown("*Your personal spreadsheet. Track every application.*")

        with st.expander("Add new entry",expanded=len(db_jobs)==0):
            r1,r2,r3,r4=st.columns(4)
            with r1: tr_company=st.text_input("Company",placeholder="e.g. Amazon",key="tr_co")
            with r2: tr_role=st.text_input("Position",placeholder="e.g. Data Scientist",key="tr_ro")
            with r3: tr_location=st.text_input("Location",placeholder="e.g. Seattle, WA",key="tr_loc")
            with r4: tr_salary=st.text_input("Salary range",placeholder="e.g. $120K-$150K",key="tr_sal")
            r5,r6,r7,r8=st.columns(4)
            with r5: tr_applied=st.date_input("Date applied",value=date.today(),key="tr_ad")
            with r6: tr_status=st.selectbox("Status",["Applied","Phone Screen","Technical Interview","Onsite","Offer","Rejected","Ghosted","Withdrawn"],key="tr_st")
            with r7: tr_sponsor=st.selectbox("H1B Sponsor?",["Yes","No","Unknown","Checking"],key="tr_sp")
            with r8: tr_source=st.selectbox("Source",["LinkedIn","Company Site","Indeed","Handshake","Referral","Career Fair","Other"],key="tr_src")
            tr_notes=st.text_input("Notes",placeholder="e.g. Referral from John...",key="tr_nt")
            tr_followup=st.date_input("Follow-up date",value=date.today()+timedelta(days=7),key="tr_fu")
            if st.button("Add to tracker",type="primary",key="tr_add"):
                if tr_company and tr_role:
                    add_db_job({"Company":tr_company,"Position":tr_role,"Location":tr_location,"Salary":tr_salary,
                        "Applied":str(tr_applied),"Status":tr_status,"H1B Sponsor":tr_sponsor,
                        "Source":tr_source,"Notes":tr_notes,"Follow-up":str(tr_followup)})
                    st.rerun()

        if db_jobs:
            tracker_df=pd.DataFrame(db_jobs)
            display_cols=[c for c in ["Company","Position","Location","Salary","Applied","Status","H1B Sponsor","Source","Notes","Follow-up"] if c in tracker_df.columns]
            if display_cols:
                total=len(tracker_df)
                interviewing=len(tracker_df[tracker_df["Status"].isin(["Phone Screen","Technical Interview","Onsite"])]) if "Status" in tracker_df.columns else 0
                offers=len(tracker_df[tracker_df["Status"]=="Offer"]) if "Status" in tracker_df.columns else 0
                rejected=len(tracker_df[tracker_df["Status"].isin(["Rejected","Ghosted"])]) if "Status" in tracker_df.columns else 0
                sponsors=len(tracker_df[tracker_df["H1B Sponsor"]=="Yes"]) if "H1B Sponsor" in tracker_df.columns else 0

                s1,s2,s3,s4,s5=st.columns(5)
                with s1: st.markdown(f"<div class='card' style='text-align:center;padding:14px;'><div style='font-size:24px;font-weight:700;font-family:Space Grotesk,sans-serif;'>{total}</div><div style='font-size:10px;color:#9098b1;font-family:IBM Plex Mono,monospace;text-transform:uppercase;'>Total</div></div>", unsafe_allow_html=True)
                with s2: st.markdown(f"<div class='card' style='text-align:center;padding:14px;'><div style='font-size:24px;font-weight:700;color:#f59e0b;'>{interviewing}</div><div style='font-size:10px;color:#9098b1;font-family:IBM Plex Mono,monospace;text-transform:uppercase;'>Interviewing</div></div>", unsafe_allow_html=True)
                with s3: st.markdown(f"<div class='card' style='text-align:center;padding:14px;'><div style='font-size:24px;font-weight:700;color:#10b981;'>{offers}</div><div style='font-size:10px;color:#9098b1;font-family:IBM Plex Mono,monospace;text-transform:uppercase;'>Offers</div></div>", unsafe_allow_html=True)
                with s4: st.markdown(f"<div class='card' style='text-align:center;padding:14px;'><div style='font-size:24px;font-weight:700;color:#ef4444;'>{rejected}</div><div style='font-size:10px;color:#9098b1;font-family:IBM Plex Mono,monospace;text-transform:uppercase;'>Rejected</div></div>", unsafe_allow_html=True)
                with s5: st.markdown(f"<div class='card' style='text-align:center;padding:14px;'><div style='font-size:24px;font-weight:700;color:#2563eb;'>{sponsors}</div><div style='font-size:10px;color:#9098b1;font-family:IBM Plex Mono,monospace;text-transform:uppercase;'>H1B Sponsors</div></div>", unsafe_allow_html=True)

                st.markdown("####")
                edited_df=st.data_editor(tracker_df[display_cols],use_container_width=True,hide_index=True,num_rows="dynamic",key="tracker_editor")
                if st.button("Save changes to Database",type="primary",key="save_tracker"):
                    updated_records = edited_df.to_dict("records")
                    update_db_jobs(updated_records)
                    st.success("Tracker saved!")
                csv=tracker_df[display_cols].to_csv(index=False)
                st.download_button("Download as CSV",csv,"setu_job_tracker.csv","text/csv",key="dl_csv")
        else:
            st.markdown("<div class='card' style='text-align:center;padding:40px;'><div style='font-size:28px;margin-bottom:8px;'>📋</div><p style='color:#9098b1;'>Your job tracker is empty. Add your first application above!</p></div>", unsafe_allow_html=True)

    with tab5:
        st.markdown("##### Daily planner")
        st.markdown("*Set tasks, track your progress, stay accountable.*")

        with st.expander("Add new task",expanded=False):
            tc1,tc2,tc3=st.columns([3,1,1])
            with tc1: task_title=st.text_input("What do you need to do?",placeholder="e.g. Apply to 3 companies...",key="tt")
            with tc2: task_cat=st.selectbox("Category",["Job Search","Visa","Learning","Personal"],key="tc")
            with tc3: task_due=st.date_input("Due date",value=date.today(),key="td")
            task_priority=st.selectbox("Priority",["High","Medium","Low"],key="tp")
            if st.button("Add task",type="primary",key="at"):
                if task_title:
                    add_db_task(task_title, task_cat, str(task_due), task_priority)
                    st.rerun()

        if db_tasks:
            overdue_tasks=[t for t in db_tasks if str(t.get("due",""))<today_str and not t.get("completed")]
            today_tasks=[t for t in db_tasks if str(t.get("due",""))==today_str and not t.get("completed")]
            upcoming_tasks=[t for t in db_tasks if str(t.get("due",""))>today_str and not t.get("completed")]
            done_tasks=[t for t in db_tasks if t.get("completed")]

            if overdue_tasks:
                st.markdown(f"###### 🔴 Overdue ({len(overdue_tasks)})")
                for t in overdue_tasks:
                    pri_colors={"High":"tag-red","Medium":"tag-amber","Low":"tag-gray"}
                    pc=pri_colors.get(t.get("priority",""),"tag-gray")
                    col1,col2,col3=st.columns([7,1,1])
                    with col1:
                        st.markdown(f"<div class='card task-overdue' style='padding:12px 18px;'><div style='display:flex;justify-content:space-between;align-items:center;'><span style='font-size:13px;color:#1a1d26;'>{t['title']}</span><div><span class='tag {pc}'>{t.get('priority','')}</span> <span class='tag tag-red'>Overdue</span></div></div><div style='font-size:11px;color:#9098b1;margin-top:4px;'>Due: {t.get('due','')}</div></div>", unsafe_allow_html=True)
                    with col2:
                        if st.button("✓",key=f"done_{t.get('id','')}",help="Mark complete"):
                            complete_task(t["id"]); st.rerun()
                    with col3:
                        if st.button("🗑️",key=f"del_{t.get('id','')}",help="Delete"):
                            delete_task(t["id"]); st.rerun()

            if today_tasks:
                st.markdown(f"###### 🟡 Today ({len(today_tasks)})")
                for t in today_tasks:
                    cat_colors={"Visa":"tag-red","Job Search":"tag-blue","Learning":"tag-purple","Personal":"tag-gray"}
                    cc=cat_colors.get(t.get("category",""),"tag-gray")
                    col1,col2,col3=st.columns([7,1,1])
                    with col1:
                        st.markdown(f"<div class='card card-amber' style='padding:12px 18px;'><div style='display:flex;justify-content:space-between;align-items:center;'><span style='font-size:13px;color:#1a1d26;'>{t['title']}</span><span class='tag {cc}'>{t.get('category','')}</span></div></div>", unsafe_allow_html=True)
                    with col2:
                        if st.button("✓",key=f"done_t_{t.get('id','')}",help="Mark complete"):
                            complete_task(t["id"]); st.rerun()
                    with col3:
                        if st.button("🗑️",key=f"del_t_{t.get('id','')}",help="Delete"):
                            delete_task(t["id"]); st.rerun()

            if upcoming_tasks:
                st.markdown(f"###### 🔵 Upcoming ({len(upcoming_tasks)})")
                for t in upcoming_tasks:
                    cat_colors={"Visa":"tag-red","Job Search":"tag-blue","Learning":"tag-purple","Personal":"tag-gray"}
                    cc=cat_colors.get(t.get("category",""),"tag-gray")
                    col1,col2,col3=st.columns([7,1,1])
                    with col1:
                        st.markdown(f"<div class='card' style='padding:12px 18px;'><div style='display:flex;justify-content:space-between;align-items:center;'><span style='font-size:13px;color:#1a1d26;'>{t['title']}</span><span class='tag {cc}'>{t.get('category','')}</span></div><div style='font-size:11px;color:#9098b1;margin-top:4px;'>Due: {t.get('due','')}</div></div>", unsafe_allow_html=True)
                    with col2:
                        if st.button("✓",key=f"done_u_{t.get('id','')}",help="Mark complete"):
                            complete_task(t["id"]); st.rerun()
                    with col3:
                        if st.button("🗑️",key=f"del_u_{t.get('id','')}",help="Delete"):
                            delete_task(t["id"]); st.rerun()

            if done_tasks:
                with st.expander(f"Completed ({len(done_tasks)})"):
                    for t in done_tasks:
                        st.markdown(f"<div class='card' style='padding:10px 18px;opacity:0.5;'><span style='font-size:13px;text-decoration:line-through;color:#9098b1;'>✓ {t['title']}</span></div>", unsafe_allow_html=True)

            total=len(db_tasks); done=len(done_tasks)
            if total>0:
                pct=int(done/total*100)
                st.markdown(f"<div style='margin-top:16px;'><div style='font-size:12px;color:#5a6178;margin-bottom:6px;'>Progress: <strong>{pct}%</strong> ({done}/{total})</div><div class='pipeline-bar' style='height:8px;'><div class='pipeline-fill' style='width:{pct}%;background:#10b981;'></div></div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='card' style='text-align:center;padding:40px;'><div style='font-size:28px;margin-bottom:8px;'>📅</div><p style='color:#9098b1;'>No tasks yet. Add your first task above!</p></div>", unsafe_allow_html=True)

    with tab6:
        st.markdown("##### Salary benchmarks")
        sm=SALARY.melt(id_vars=["Role"],var_name="Visa Status",value_name="Salary")
        fig=px.bar(sm,x="Role",y="Salary",color="Visa Status",barmode="group",
            color_discrete_map={"OPT":"#f59e0b","H1B":"#7c3aed","US Citizen":"#10b981"},title="Annual salary by role and visa status")
        fig.update_layout(**PL,height=480,yaxis_tickformat="$,.0f",legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5))
        st.plotly_chart(fig,use_container_width=True)
        st.markdown("<div class='card card-amber'><span class='tag tag-amber'>Negotiation tip</span><p style='margin-top:8px;font-size:14px;line-height:1.6;'>OPT salaries average <strong>22-35% lower</strong> than H1B. Once on H1B, salaries normalize within 1-2 years. Always benchmark against the H1B median.</p></div>", unsafe_allow_html=True)

    with tab7:
        st.markdown("##### Your visa timeline")
        st.markdown(f"*{uname} · {p.get('degree','')} {p.get('major','')} · Graduating {gd.strftime('%B %d, %Y')}*")
        for item in get_timeline(gd):
            if item["status"]=="done": border="border-left:3px solid #d1d5db;"; tc="tag-gray"; tt="DONE"
            elif item["status"]=="soon":
                border=f"border-left:3px solid {'#ef4444' if item['days']<=30 else '#f59e0b'};"
                tc="tag-red" if item["days"]<=30 else "tag-amber"; tt=f"{item['days']}d"
            else: border="border-left:3px solid #2563eb;"; tc="tag-blue"; tt=f"{item['days']}d"
            st.markdown(f"<div class='card' style='{border}padding:16px 20px;'><div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'><span style='font-size:12px;color:#2563eb;font-family:IBM Plex Mono,monospace;font-weight:600;'>{item['date']}</span><span class='tag {tc}'>{tt}</span></div><div style='font-size:15px;font-weight:600;color:#1a1d26;font-family:Space Grotesk,sans-serif;'>{item['label']}</div><div style='font-size:13px;color:#5a6178;margin-top:4px;'>{item['desc']}</div></div>", unsafe_allow_html=True)
        st.markdown("<div class='card card-red'><span class='tag tag-red'>Critical rule</span><p style='margin-top:8px;font-size:14px;line-height:1.6;'>The <strong>90-day unemployment clock</strong> starts on your OPT start date. Exceeding 90 days without employment automatically terminates OPT. Unpaid internships (20+ hrs/week) count.</p></div>", unsafe_allow_html=True)

    # ─── PROFILE TAB (EDITABLE) ───────────────────────────────────────────
    with tab8:
        st.markdown("##### Your profile")
        st.markdown("*Edit your information anytime.*")

        if st.session_state.utype == "guest":
            st.info("💾 Create an account to save your profile permanently.")

        st.markdown("---")

        if "edit_profile" not in st.session_state:
            st.session_state.edit_profile = False

        col_hdr, col_btn = st.columns([6,1])
        with col_hdr:
            st.markdown("##### Your information")
        with col_btn:
            btn_label = "✏️ Edit" if not st.session_state.edit_profile else "✕ Cancel"
            if st.button(btn_label, key="edit_toggle"):
                st.session_state.edit_profile = not st.session_state.edit_profile
                st.rerun()

        if st.session_state.edit_profile:
            pe1, pe2 = st.columns(2)
            with pe1:
                new_name  = st.text_input("Name", value=p.get("name",""), key="p_name")
                new_univ  = st.text_input("University", value=p.get("university",""), key="p_univ")
                deg_opts  = ["M.S.","M.A.","MBA","Ph.D.","B.S.","B.A."]
                cur_deg   = p.get("degree","M.S.")
                deg_idx   = deg_opts.index(cur_deg) if cur_deg in deg_opts else 0
                new_degree= st.selectbox("Degree", deg_opts, index=deg_idx, key="p_deg")
                new_major = st.text_input("Major", value=p.get("major",""), key="p_major")
            with pe2:
                cur_grad = p.get("grad", date(2026,5,15))
                if isinstance(cur_grad, str):
                    try: cur_grad = datetime.strptime(cur_grad, "%Y-%m-%d").date()
                    except: cur_grad = date(2026,5,15)
                new_grad = st.date_input("Graduation date", value=cur_grad,
                    min_value=date(2024,1,1), max_value=date(2032,12,31), key="p_grad")
                stem_opts = ["Yes","No","Not sure"]
                cur_stem  = p.get("stem","Yes")
                stem_idx  = stem_opts.index(cur_stem) if cur_stem in stem_opts else 0
                new_stem  = st.selectbox("STEM degree?", stem_opts, index=stem_idx, key="p_stem")
                role_opts = ["Data Scientist","Data Analyst","ML Engineer","AI Engineer","Software Engineer",
                             "Data Engineer","BI Analyst","Solutions Analyst","Research Scientist","Product Analyst"]
                new_roles = st.multiselect("Target roles", role_opts, default=p.get("roles",[]), key="p_roles")

            st.markdown("##### Your skills")
            new_skills = st.multiselect("Skills", ALL_SKILLS, default=p.get("skills",[]), key="p_skills")

            if st.button("💾 Save changes", type="primary", use_container_width=True, key="save_profile"):
                updated = {"name":new_name,"university":new_univ,"degree":new_degree,
                    "major":new_major,"grad":str(new_grad),"stem":new_stem,
                    "roles":new_roles,"skills":new_skills}
                st.session_state.profile = updated
                if st.session_state.utype == "user":
                    try: supabase.auth.update_user({"data": updated})
                    except: pass
                st.session_state.edit_profile = False
                st.success("✅ Profile updated!")
                st.rerun()
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Name:** {p.get('name','N/A')}")
                st.markdown(f"**University:** {p.get('university','N/A')}")
                st.markdown(f"**Degree:** {p.get('degree','N/A')}")
                st.markdown(f"**Major:** {p.get('major','N/A')}")
            with col2:
                st.markdown(f"**Graduation:** {gd.strftime('%B %d, %Y')}")
                st.markdown(f"**STEM Degree:** {p.get('stem','N/A')}")
                st.markdown(f"**Target Roles:** {', '.join(p.get('roles',[]))}")
            st.markdown("---")
            st.markdown("##### Your Skills")
            skills_display = " ".join([f"<span class='tag tag-blue'>{s}</span>" for s in p.get("skills",[])])
            st.markdown(skills_display if skills_display else "*No skills added yet.*", unsafe_allow_html=True)


    # ─── AI RESUME TAB ────────────────────────────────────────────────────
    with tab9:
        st.markdown("##### 🤖 AI Resume Builder")
        st.markdown("*Upload your resume — AI will improve it for visa-sponsored US jobs.*")

        def call_groq(prompt, system="You are an expert US resume coach for international students on OPT/H1B visas."):
            full_prompt = f"{system}\n\n{prompt}"
            # Try Gemini first
            try:
                gemini_key = st.secrets["GEMINI_API_KEY"]
                gemini_key = str(gemini_key).strip().strip('"').strip("'")
                req_data = _json.dumps({
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.7}
                }).encode()
                req = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}",
                    data=req_data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = _json.loads(r.read())
                    return data["candidates"][0]["content"]["parts"][0]["text"], None
            except KeyError:
                pass
            except Exception as e1:
                return None, f"Gemini error: {str(e1)}"
            # Try Groq fallback
            try:
                groq_key = st.secrets["GROQ_API_KEY"]
                groq_key = str(groq_key).strip().strip('"').strip("'")
                req_data = _json.dumps({
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                    "max_tokens": 2000, "temperature": 0.7
                }).encode()
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=req_data,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = _json.loads(r.read())
                    return data["choices"][0]["message"]["content"], None
            except KeyError:
                return None, "Add GEMINI_API_KEY or GROQ_API_KEY to Streamlit Secrets."
            except Exception as e2:
                return None, f"Groq error: {str(e2)}"

        if "resume_text" not in st.session_state: st.session_state.resume_text = ""
        if "improved_resume" not in st.session_state: st.session_state.improved_resume = ""
        if "resume_feedback" not in st.session_state: st.session_state.resume_feedback = ""

        st.markdown("---")
        st.markdown("#### Step 1: Add your resume")
        input_method = st.radio("How do you want to add your resume?",
            ["📋 Paste resume text", "✍️ Build from profile"],
            horizontal=True, key="resume_input_method")

        if input_method == "📋 Paste resume text":
            resume_input = st.text_area("Paste your resume here", height=300,
                placeholder="Paste your full resume text here...", key="resume_paste")
            if resume_input:
                st.session_state.resume_text = resume_input
        else:
            default_resume = f"""{p.get('name', 'Your Name')}
{p.get('degree', 'M.S.')} {p.get('major', 'Data Science')} | {p.get('university', 'University')}
Graduation: {gd.strftime('%B %Y')} | OPT/H1B Visa Candidate

SKILLS
{', '.join(p.get('skills', []))}

TARGET ROLES: {', '.join(p.get('roles', []))}

EDUCATION
{p.get('degree', 'M.S.')} in {p.get('major', 'Data Science')}
{p.get('university', 'University')} | Expected {gd.strftime('%B %Y')}
GPA: (add your GPA)

EXPERIENCE
(Add your work experience here)

PROJECTS
(Add your projects here)

CERTIFICATIONS
(Add your certifications here)"""
            resume_input = st.text_area("Edit your resume",
                value=st.session_state.resume_text if st.session_state.resume_text else default_resume,
                height=350, key="resume_edit")
            if resume_input:
                st.session_state.resume_text = resume_input

        st.markdown("---")
        st.markdown("#### Step 2: Choose what AI should do")
        r9c1, r9c2 = st.columns(2)
        with r9c1:
            target_role = st.text_input("Target job role",
                value=p.get("roles",["Data Scientist"])[0] if p.get("roles") else "Data Scientist", key="r9_role")
            target_company_type = st.selectbox("Target company type",
                ["Any (H1B sponsor)", "Big Tech (FAANG)", "Consulting", "Finance/Banking", "Startup", "Government"], key="r9_company")
        with r9c2:
            improvement_type = st.selectbox("What to improve",
                ["Full resume rewrite", "Make it ATS-friendly", "Add quantified achievements",
                 "Tailor for OPT/visa sponsorship", "Improve summary/objective section"], key="r9_improve")
            yoe = st.selectbox("Years of experience",
                ["0-1 years (New grad)", "1-3 years", "3-5 years", "5+ years"], key="r9_yoe")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            improve_btn = st.button("✨ Improve My Resume", type="primary", use_container_width=True, key="r9_improve_btn")
        with col_btn2:
            feedback_btn = st.button("📊 Get Resume Score & Feedback", use_container_width=True, key="r9_feedback_btn")

        if improve_btn:
            if not st.session_state.resume_text.strip():
                st.error("Please add your resume first!")
            else:
                with st.spinner("🤖 AI is improving your resume..."):
                    prompt = f"""TASK: {improvement_type}
TARGET ROLE: {target_role} at {target_company_type}
EXPERIENCE: {yoe}
STUDENT: {p.get('degree','')} {p.get('major','')} from {p.get('university','')}
SKILLS: {', '.join(p.get('skills',[]))}

ORIGINAL RESUME:
{st.session_state.resume_text}

Optimize for ATS, use strong action verbs, quantified achievements, highlight OPT/STEM OPT eligibility.
Output ONLY the improved resume text, ready to copy-paste."""
                    result, err = call_groq(prompt)
                    if result:
                        st.session_state.improved_resume = result
                    else:
                        st.error(f"AI Error: {err}")

        if feedback_btn:
            if not st.session_state.resume_text.strip():
                st.error("Please add your resume first!")
            else:
                with st.spinner("🤖 AI is analyzing your resume..."):
                    prompt = f"""Analyze this resume for a {target_role} position.

RESUME:
{st.session_state.resume_text}

STUDENT: {p.get('degree','')} {p.get('major','')} from {p.get('university','')}, graduating {gd.strftime('%B %Y')}

Provide:
1. **Overall Score**: X/100
2. **ATS Score**: X/100
3. **Top 3 Strengths**
4. **Top 3 Critical Improvements**
5. **Missing Keywords** for {target_role}
6. **Visa/OPT Tips**
7. **One-Line Verdict**: Ready to apply?"""
                    result, err = call_groq(prompt)
                    if result:
                        st.session_state.resume_feedback = result
                    else:
                        st.error(f"AI Error: {err}")

        if st.session_state.resume_feedback:
            st.markdown("---")
            st.markdown("#### 📊 Resume Analysis")
            st.markdown(st.session_state.resume_feedback)
            st.session_state.resume_feedback = ""

        if st.session_state.improved_resume:
            st.markdown("---")
            st.markdown("#### ✨ Your Improved Resume")
            st.markdown("<div style='background:#ecfdf5;border:1px solid #6ee7b7;border-radius:8px;padding:10px 16px;margin-bottom:12px;font-size:12px;color:#059669;'>✅ AI-improved resume ready! Copy below or download.</div>", unsafe_allow_html=True)
            st.text_area("Copy your improved resume", value=st.session_state.improved_resume, height=500, key="improved_output")
            st.download_button("⬇️ Download Resume", st.session_state.improved_resume,
                f"{p.get('name','resume').replace(' ','_')}_resume.txt", "text/plain", key="dl_resume")

        st.markdown("---")
        st.markdown("#### 💡 Quick Resume Tips for OPT Students")
        tips = [
            ("✅ Include OPT status", "Add 'Authorized to work in the US (OPT/STEM OPT)' in your header"),
            ("✅ Quantify everything", "'Improved performance by 40%' beats 'improved performance'"),
            ("✅ ATS keywords", "Match exact keywords from job descriptions"),
            ("✅ 1-page rule", "New grads: keep it 1 page. Recruiters scan in 6 seconds"),
            ("✅ Projects count", "Side projects, Kaggle, GitHub replace work experience for new grads"),
        ]
        for title, tip in tips:
            st.markdown(f"<div class='card card-accent' style='padding:12px 18px;'><strong style='color:#1a1d26;'>{title}</strong><br><span style='font-size:13px;'>{tip}</span></div>", unsafe_allow_html=True)

    # ─── AI JOB FINDER TAB ────────────────────────────────────────────────
    with tab10:
        st.markdown("##### 🎯 AI Job Finder + Cover Letter Generator")
        st.markdown("*AI analyzes your profile and finds best-fit jobs + writes cover letters.*")

        if "ai_jobs" not in st.session_state: st.session_state.ai_jobs = []
        if "cover_letter" not in st.session_state: st.session_state.cover_letter = ""
        if "selected_job_title" not in st.session_state: st.session_state.selected_job_title = ""
        if "selected_job_company" not in st.session_state: st.session_state.selected_job_company = ""

        has_resume = bool(st.session_state.get("resume_text","").strip())
        if not has_resume:
            st.warning("💡 Go to **🤖 AI Resume** tab first and add your resume for better job matching!")

        st.markdown("---")
        st.markdown("#### Step 1: Configure your job search")
        f10c1, f10c2, f10c3 = st.columns(3)
        with f10c1:
            f10_role = st.text_input("Target role",
                value=p.get("roles",["Data Scientist"])[0] if p.get("roles") else "Data Scientist", key="f10_role")
        with f10c2:
            univ_lower = p.get("university","").lower()
            auto_loc = "Florida"
            uni_loc_map = {"florida atlantic":"Boca Raton, FL","fau":"Boca Raton, FL","mit":"Boston, MA",
                "stanford":"San Francisco, CA","georgia tech":"Atlanta, GA","columbia":"New York, NY",
                "nyu":"New York, NY","university of washington":"Seattle, WA","university of texas":"Austin, TX",
                "carnegie mellon":"Pittsburgh, PA","university of michigan":"Ann Arbor, MI",
                "university of florida":"Gainesville, FL","florida international":"Miami, FL",
                "northeastern":"Boston, MA","arizona state":"Phoenix, AZ","ohio state":"Columbus, OH"}
            for k, v in uni_loc_map.items():
                if k in univ_lower:
                    auto_loc = v
                    break
            f10_loc = st.text_input("Location", value=auto_loc, key="f10_loc")
        with f10c3:
            f10_exp = st.selectbox("Experience level",
                ["Entry level (0-2 yrs)", "Mid level (2-5 yrs)", "Senior (5+ yrs)"], key="f10_exp")

        f10c4, f10c5 = st.columns(2)
        with f10c4:
            f10_visa = st.selectbox("Visa requirement",
                ["Must sponsor H1B", "OPT accepted", "Any visa-friendly"], key="f10_visa")
        with f10c5:
            f10_skills = st.text_input("Your key skills", value=", ".join(p.get("skills",[])), key="f10_skills")

        find_btn = st.button("🔍 Find My Best-Fit Jobs with AI", type="primary",
            use_container_width=True, key="f10_find")

        if find_btn:
            with st.spinner("🤖 AI is finding your best job matches across the USA..."):
                resume_context = f"\nMy Resume:\n{st.session_state.resume_text}" if has_resume else ""
                prompt = f"""You are a career advisor for international students seeking US jobs.

STUDENT PROFILE:
- Name: {p.get('name','')}
- Degree: {p.get('degree','')} {p.get('major','')} from {p.get('university','')}
- Graduating: {gd.strftime('%B %Y')}
- Skills: {f10_skills}
- Target Role: {f10_role}
- Location: {f10_loc}
- Experience: {f10_exp}
- Visa Need: {f10_visa}
{resume_context}

Generate 8 specific REAL job opportunities this student should apply to RIGHT NOW.

For each job use this format:

**Job N: [Exact Job Title]**
- 🏢 Company: [Real company known for H1B sponsorship]
- 📍 Location: [City, State or Remote]
- 💰 Salary: [Realistic range]
- 🎯 Why You Match: [2 sentences specific to this student]
- 🔧 Key Skills Needed: [5 skills]
- 🔗 Apply At: [Real URL - linkedin.com/jobs, company careers page]
- ✅ Visa: [H1B/OPT/STEM OPT friendly]
- ⚡ Urgency: [Apply immediately / Good timing / Plan ahead]

Focus on real companies that sponsor H1B in {f10_loc} and nationally. Mix big tech, consulting, finance."""

                result, err = call_groq(prompt)
                if result:
                    st.session_state.ai_jobs = result
                else:
                    st.error(f"AI Error: {err}. Make sure GROQ_API_KEY is set in Streamlit Secrets.")

        if st.session_state.ai_jobs:
            st.markdown("---")
            st.markdown("#### 🎯 Your AI-Matched Jobs")
            st.markdown(st.session_state.ai_jobs)

            st.markdown("---")
            st.markdown("#### ✉️ Generate Personalized Cover Letter")
            cl_c1, cl_c2 = st.columns(2)
            with cl_c1:
                cl_job_title = st.text_input("Job title", placeholder="e.g. Data Scientist", key="cl_title")
            with cl_c2:
                cl_company = st.text_input("Company name", placeholder="e.g. Amazon", key="cl_company")
            cl_tone = st.selectbox("Tone", ["Professional & confident", "Enthusiastic & energetic",
                "Concise & direct", "Story-driven & personal"], key="cl_tone")
            cl_btn = st.button("✉️ Write My Cover Letter", type="primary", use_container_width=True, key="cl_btn")

            if cl_btn:
                if not cl_job_title or not cl_company:
                    st.error("Please enter job title and company!")
                else:
                    with st.spinner("🤖 Writing your personalized cover letter..."):
                        resume_ctx = f"\nResume:\n{st.session_state.resume_text}" if has_resume else f"\nSkills: {f10_skills}"
                        prompt = f"""Write a powerful cover letter for this international student.

STUDENT: {p.get('name','')} | {p.get('degree','')} {p.get('major','')} from {p.get('university','')}
Graduating: {gd.strftime('%B %Y')} | On OPT visa | Skills: {f10_skills}
{resume_ctx}

JOB: {cl_job_title} at {cl_company}
TONE: {cl_tone}

Rules:
- 3-4 paragraphs, under 300 words
- Do NOT start with "I am writing to apply"
- Include 2-3 specific quantified achievements
- Mention OPT status naturally: "I am authorized to work in the US (OPT)"
- Strong call to action closing

Output ONLY the cover letter, ready to send."""
                        result, err = call_groq(prompt)
                        if result:
                            st.session_state.cover_letter = result
                            st.session_state.selected_job_title = cl_job_title
                            st.session_state.selected_job_company = cl_company
                        else:
                            st.error(f"AI Error: {err}")

        if st.session_state.cover_letter:
            st.markdown("---")
            st.markdown(f"#### ✉️ Cover Letter — {st.session_state.selected_job_title} at {st.session_state.selected_job_company}")
            st.markdown("<div style='background:#eff6ff;border:1px solid #93c5fd;border-radius:8px;padding:10px 16px;margin-bottom:12px;font-size:12px;color:#1d4ed8;'>✅ AI-written cover letter ready! Review, personalize, and send.</div>", unsafe_allow_html=True)
            st.text_area("Your cover letter", value=st.session_state.cover_letter, height=450, key="cl_output")
            st.download_button("⬇️ Download Cover Letter", st.session_state.cover_letter,
                f"cover_letter_{st.session_state.selected_job_company.replace(' ','_')}.txt",
                "text/plain", key="dl_cl")

        st.markdown("---")
        st.markdown("#### 🚀 Job Search Strategy for OPT Students")
        strategies = [
            ("📅 Apply early", "H1B cap opens March 1. Need a job offer by then. Start applying Sept-Oct."),
            ("🎯 Target H1B sponsors", "Focus on companies with 50+ H1B approvals/year. Check the H1B Sponsors tab."),
            ("🤝 Referrals win", "60% of jobs are filled via referrals. Connect with alumni on LinkedIn."),
            ("📊 Volume matters", "Apply to 10-15 jobs/week minimum. Track in your Job Tracker tab."),
            ("💼 LinkedIn is key", "Recruiters search daily. Add 'OPT' and target skills to your headline."),
            ("🏃 Consulting firms", "Deloitte, Accenture, Infosys sponsor heavily and hire international students."),
        ]
        sc1, sc2 = st.columns(2)
        for i, (title, tip) in enumerate(strategies):
            with sc1 if i % 2 == 0 else sc2:
                st.markdown(f"<div class='card card-accent' style='padding:12px 18px;'><strong style='color:#1a1d26;font-size:13px;'>{title}</strong><br><span style='font-size:12px;color:#5a6178;'>{tip}</span></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div style='text-align:center;color:#9098b1;font-size:11px;font-family:IBM Plex Mono,monospace;'>Setu v4.3 · Founded by Kiran Kumar Reddy Konapalli · Built for international students · Powered by Groq AI</div>", unsafe_allow_html=True)
