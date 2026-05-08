import re
import sqlite3
from datetime import date, datetime
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

DB_NAME = "job_hunt_command_center.db"

ROLE_CATEGORIES = {
    "Intel/OSINT": ["intelligence", "osint", "open-source", "all-source", "threat", "rfis", "collection"],
    "Technical Writer": ["technical writer", "documentation", "sop", "manual", "guide", "procedures"],
    "Strategy/Program Analyst": ["strategy", "program analyst", "briefing", "stakeholder", "roadmap", "requirements"],
    "SCRM/Risk Analyst": ["supply chain", "scrm", "supplier", "risk", "dependencies", "ownership", "foreign influence"],
    "Business Analytics": ["business", "analytics", "sql", "dashboard", "tableau", "powerbi", "operations"],
    "Functional/Lessons Learned Analyst": ["lessons learned", "dotmlpf", "jllis", "capability gap", "oil", "observations"]
}

CANDIDATE_DEFAULT_SIGNALS = {
    "clearance": ["interim top secret", "secret", "ts"],
    "domains": ["national security", "defense", "army", "open-source", "research", "operational analysis", "technical writing"],
    "tools": ["excel", "powerpoint", "word", "sharepoint", "lexisnexis", "forge"],
    "strengths": ["analytical writing", "multi-source research", "sme coordination", "structured reporting", "source evaluation"]
}


def init_db() -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            resume_text TEXT,
            updated_date TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            title TEXT,
            location TEXT,
            work_mode TEXT,
            clearance TEXT,
            experience_requirement TEXT,
            education_requirement TEXT,
            salary_range TEXT,
            deadline TEXT,
            key_skills TEXT,
            responsibilities TEXT,
            status TEXT,
            resume_version TEXT,
            score REAL,
            recommendation TEXT,
            strengths TEXT,
            concerns TEXT,
            rationale TEXT,
            notes TEXT,
            created_date TEXT,
            follow_up_date TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def save_candidate_profile(resume_text: str) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO candidate_profile (id, resume_text, updated_date)
        VALUES (1, ?, ?)
        """,
        (resume_text, str(date.today()))
    )
    conn.commit()
    conn.close()


def load_candidate_profile() -> str:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT resume_text FROM candidate_profile WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else ""


def add_job(job: Dict[str, str]) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO jobs (
            company, title, location, work_mode, clearance, experience_requirement,
            education_requirement, salary_range, deadline, key_skills, responsibilities,
            status, resume_version, score, recommendation, strengths, concerns,
            rationale, notes, created_date, follow_up_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("company", "uncertain"),
            job.get("title", "uncertain"),
            job.get("location", "uncertain"),
            job.get("work_mode", "uncertain"),
            job.get("clearance", "uncertain"),
            job.get("experience_requirement", "uncertain"),
            job.get("education_requirement", "uncertain"),
            job.get("salary_range", "uncertain"),
            job.get("deadline", "uncertain"),
            job.get("key_skills", ""),
            job.get("responsibilities", ""),
            job.get("status", "Found"),
            job.get("resume_version", ""),
            job.get("score", 0),
            job.get("recommendation", "uncertain"),
            job.get("strengths", ""),
            job.get("concerns", ""),
            job.get("rationale", ""),
            job.get("notes", ""),
            str(date.today()),
            job.get("follow_up_date", "")
        )
    )
    conn.commit()
    conn.close()


def load_jobs() -> pd.DataFrame:
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM jobs ORDER BY id DESC", conn)
    conn.close()
    return df


def contains_any(text: str, terms: List[str]) -> bool:
    text_l = text.lower()
    return any(term.lower() in text_l for term in terms)


def extract_first(patterns: List[str], text: str, default: str = "uncertain") -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            return re.sub(r"\s+", " ", value)
    return default


def extract_job_fields(job_text: str) -> Dict[str, str]:
    text = job_text.strip()
    lower = text.lower()

    title = extract_first([
        r"(?:job title|title|position)[:\-]\s*([^\n]+)",
        r"^\s*([A-Z][A-Za-z\-/&\s]{3,80}(?:Analyst|Writer|Specialist|Collector|Researcher))\s*$"
    ], text)

    company = extract_first([
        r"(?:company|employer|organization)[:\-]\s*([^\n]+)",
        r"(?:at|with)\s+([A-Z][A-Za-z0-9&.,\s]{2,60})"
    ], text)

    location = extract_first([
        r"(?:location|job location|work location)[:\-]\s*([^\n]+)",
        r"([A-Z][a-z]+,\s*(?:VA|Virginia|DC|Washington, DC|MD|Maryland))"
    ], text)

    if "remote" in lower:
        work_mode = "Remote"
    elif "hybrid" in lower:
        work_mode = "Hybrid"
    elif "onsite" in lower or "on-site" in lower or "in office" in lower:
        work_mode = "On-site"
    else:
        work_mode = "uncertain"

    clearance = extract_first([
        r"(?:clearance|security clearance required|clearance required)[:\-]?\s*([^\n]+)",
        r"(active\s+(?:secret|top secret|ts/sci|ts\s*/\s*sci)[^\n\.]*)",
        r"(public trust[^\n\.]*)"
    ], text)

    experience = extract_first([
        r"(\d+\+?\s*(?:-|to)?\s*\d*\s*years?[^\n\.]*experience[^\n\.]*)",
        r"(?:minimum|required)\s+(\d+\+?\s*years?[^\n\.]*)"
    ], text)

    education = extract_first([
        r"(Bachelor['’]s degree[^\n\.]*)",
        r"(Master['’]s degree[^\n\.]*)",
        r"(High school[^\n\.]*)"
    ], text)

    salary = extract_first([
        r"(\$\d{2,3},?\d{3}\s*(?:-|–|to)\s*\$?\d{2,3},?\d{3})",
        r"(\$\d{2,3}\s*(?:-|–|to)\s*\$?\d{2,3}\s*/\s*hr)",
        r"salary[^\n:]*[:\-]\s*([^\n]+)"
    ], text)

    deadline = extract_first([
        r"(?:closing date|deadline|closing at)[:\-]?\s*([^\n]+)",
        r"(closing\s+(?:at|on)\s+[^\n]+)"
    ], text)

    skills = []
    for skill in ["Excel", "PowerPoint", "Word", "SharePoint", "SQL", "Python", "Tableau", "PowerBI", "JLLIS", "FORGE", "DOTMLPF-P", "OSINT", "SOP", "briefings", "reports"]:
        if skill.lower() in lower:
            skills.append(skill)

    responsibilities = []
    for line in text.splitlines():
        clean = line.strip(" -*•\t")
        if len(clean) > 25 and contains_any(clean, ["analy", "research", "report", "brief", "coordinate", "collect", "develop", "synthesize", "track"]):
            responsibilities.append(clean)
        if len(responsibilities) >= 6:
            break

    return {
        "company": company,
        "title": title,
        "location": location,
        "work_mode": work_mode,
        "clearance": clearance,
        "experience_requirement": experience,
        "education_requirement": education,
        "salary_range": salary,
        "deadline": deadline,
        "key_skills": ", ".join(skills) if skills else "uncertain",
        "responsibilities": " | ".join(responsibilities) if responsibilities else "uncertain"
    }


def infer_role_category(job_text: str) -> str:
    lower = job_text.lower()
    scores = {category: sum(1 for word in words if word in lower) for category, words in ROLE_CATEGORIES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "General Analyst"


def score_job(job_text: str, resume_text: str, extracted: Dict[str, str]) -> Dict[str, object]:
    lower_job = job_text.lower()
    lower_resume = resume_text.lower()

    strengths: List[str] = []
    concerns: List[str] = []

    # Clearance fit
    if "ts/sci" in lower_job or "ts-sci" in lower_job or "sci required" in lower_job:
        clearance_fit = 35
        concerns.append("Role appears SCI-gated or likely favors candidates with active TS/SCI access.")
    elif "top secret" in lower_job or "ts clearance" in lower_job:
        clearance_fit = 75 if ("top secret" in lower_resume or "interim top secret" in lower_resume) else 45
        strengths.append("Top Secret-related clearance language appears compatible or partially compatible.")
    elif "secret" in lower_job:
        clearance_fit = 90
        strengths.append("Secret clearance requirement appears compatible.")
    elif "public trust" in lower_job or "clearance sponsorship" in lower_job:
        clearance_fit = 95
        strengths.append("Clearance requirement appears flexible or sponsorable.")
    else:
        clearance_fit = 70

    # Experience fit
    years = re.findall(r"(\d+)\+?\s*years?", lower_job)
    max_years = max([int(y) for y in years], default=0)
    if max_years >= 8:
        experience_fit = 20
        concerns.append("Role appears too senior based on stated years of experience.")
    elif max_years >= 5:
        experience_fit = 45
        concerns.append("Role may be above current experience level.")
    elif max_years >= 3:
        experience_fit = 70
        strengths.append("Experience requirement appears reachable with current analytical background.")
    else:
        experience_fit = 90
        strengths.append("Experience level appears well aligned with an early-career candidate.")

    # Domain fit
    domain_terms = ["national security", "defense", "army", "intelligence", "research", "supply chain", "scrm", "risk", "program", "strategy", "technical writing", "lessons learned", "dotmlpf"]
    matched_domains = [term for term in domain_terms if term in lower_job and term in lower_resume]
    domain_fit = min(95, 45 + len(matched_domains) * 10)
    if matched_domains:
        strengths.append(f"Domain overlap found: {', '.join(matched_domains[:4])}.")
    else:
        concerns.append("Limited obvious domain overlap found between resume and job description.")

    # Writing/reporting fit
    writing_terms = ["report", "brief", "summary", "white paper", "presentation", "written", "documentation"]
    writing_fit = 90 if contains_any(lower_job, writing_terms) and contains_any(lower_resume, writing_terms) else 65
    if writing_fit >= 80:
        strengths.append("Strong match on reporting, briefings, documentation, or written deliverables.")

    # Technical/tools fit
    tool_terms = ["excel", "powerpoint", "word", "sharepoint", "sql", "python", "tableau", "powerbi", "jllis", "forge"]
    required_tools = [tool for tool in tool_terms if tool in lower_job]
    resume_tools = [tool for tool in required_tools if tool in lower_resume]
    if not required_tools:
        technical_fit = 70
    else:
        technical_fit = int((len(resume_tools) / len(required_tools)) * 100)
        technical_fit = max(35, technical_fit)
    if required_tools and len(resume_tools) < len(required_tools):
        missing = [tool for tool in required_tools if tool not in resume_tools]
        concerns.append(f"Potential tool gap: {', '.join(missing[:4])}.")
    elif required_tools:
        strengths.append("Tooling overlap appears strong.")

    # Location fit
    if contains_any(lower_job, ["richmond", "arlington", "alexandria", "fairfax", "mclean", "chantilly", "sterling", "washington, dc", "northern virginia", "nova"]):
        location_fit = 90
        strengths.append("Location appears aligned with Richmond/NOVA search target.")
    elif "remote" in lower_job:
        location_fit = 85
    else:
        location_fit = 55

    # Long-term career fit
    career_terms = ["national security", "intelligence", "defense", "law enforcement", "risk", "research", "analysis", "government"]
    career_fit = 80 if contains_any(lower_job, career_terms) else 55

    overall = round((clearance_fit + experience_fit + domain_fit + writing_fit + technical_fit + location_fit + career_fit) / 7, 1)

    flags = []
    if clearance_fit < 50:
        flags.append("too clearance-gated")
    if experience_fit < 50:
        flags.append("possibly too senior")
    if technical_fit < 50:
        flags.append("technical/tool gap")
    if overall >= 75:
        recommendation = "Apply"
        flags.append("worth pursuing")
    elif overall >= 55:
        recommendation = "Borderline"
    else:
        recommendation = "Skip"

    category = infer_role_category(job_text)
    keywords = suggest_keywords(category)

    return {
        "clearance_fit": clearance_fit,
        "experience_fit": experience_fit,
        "domain_fit": domain_fit,
        "writing_fit": writing_fit,
        "technical_fit": technical_fit,
        "location_fit": location_fit,
        "career_fit": career_fit,
        "overall": overall,
        "recommendation": recommendation,
        "strengths": strengths[:3],
        "concerns": concerns[:3],
        "flags": flags,
        "category": category,
        "keywords": keywords,
        "rationale": build_rationale(overall, recommendation, strengths, concerns, flags)
    }


def suggest_keywords(category: str) -> List[str]:
    keyword_bank = {
        "Intel/OSINT": ["open-source research", "source evaluation", "multi-source synthesis", "analytical reporting"],
        "Technical Writer": ["technical documentation", "SOP development", "SME coordination", "documentation lifecycle"],
        "Strategy/Program Analyst": ["strategic analysis", "executive briefings", "stakeholder coordination", "decision-support products"],
        "SCRM/Risk Analyst": ["supply chain risk", "entity research", "relationship mapping", "risk indicators"],
        "Business Analytics": ["data analysis", "trend identification", "stakeholder insights", "Excel"],
        "Functional/Lessons Learned Analyst": ["lessons learned", "DOTMLPF-P", "capability gaps", "operational analysis"],
        "General Analyst": ["analytical writing", "data synthesis", "research", "decision-ready insights"]
    }
    return keyword_bank.get(category, keyword_bank["General Analyst"])


def build_rationale(score: float, recommendation: str, strengths: List[str], concerns: List[str], flags: List[str]) -> str:
    text = f"Recommendation: {recommendation} with an overall score of {score}. "
    if strengths:
        text += "Primary strengths: " + "; ".join(strengths[:2]) + ". "
    if concerns:
        text += "Primary concerns: " + "; ".join(concerns[:2]) + ". "
    if flags:
        text += "Flags: " + ", ".join(flags) + "."
    return text


st.set_page_config(page_title="Job Hunt Command Center", layout="wide")
init_db()

st.title("Job Hunt Command Center")
st.caption("Local job tracking and conservative fit analysis. No paid API required.")

tab_profile, tab_analyze, tab_manual, tab_dashboard = st.tabs([
    "Candidate Profile", "Analyze New Job", "Manual Add", "Dashboard"
])

with tab_profile:
    st.header("Candidate Profile")
    st.write("Paste your resume here once. The app will use it for local, rule-based fit scoring.")
    existing_resume = load_candidate_profile()
    resume_text = st.text_area("Resume / Candidate Profile Text", value=existing_resume, height=350)
    uploaded = st.file_uploader("Optional: upload a .txt resume file", type=["txt"])
    if uploaded is not None:
        resume_text = uploaded.read().decode("utf-8", errors="ignore")
        st.text_area("Uploaded Resume Text", value=resume_text, height=250)
    if st.button("Save Candidate Profile"):
        save_candidate_profile(resume_text)
        st.success("Candidate profile saved locally.")

with tab_analyze:
    st.header("Analyze New Job")
    profile = load_candidate_profile()
    if not profile:
        st.warning("Save your candidate profile first so the app can compare jobs against it.")
    job_text = st.text_area("Paste full job description", height=350)
    if st.button("Analyze Job") and job_text.strip():
        extracted = extract_job_fields(job_text)
        scoring = score_job(job_text, profile, extracted)
        st.session_state["last_analysis"] = {**extracted, **scoring, "job_text": job_text}

    analysis = st.session_state.get("last_analysis")
    if analysis:
        st.subheader("Recommendation")
        col1, col2, col3 = st.columns(3)
        col1.metric("Overall Score", analysis["overall"])
        col2.metric("Recommendation", analysis["recommendation"])
        col3.metric("Resume Category", analysis["category"])

        st.write(analysis["rationale"])

        st.subheader("Extracted Fields")
        extracted_table = pd.DataFrame([
            {"Field": key, "Value": analysis.get(key, "uncertain")}
            for key in ["company", "title", "location", "work_mode", "clearance", "experience_requirement", "education_requirement", "salary_range", "deadline", "key_skills"]
        ])
        st.dataframe(extracted_table, use_container_width=True, hide_index=True)

        st.subheader("Fit Scores")
        score_table = pd.DataFrame([
            ["Clearance", analysis["clearance_fit"]],
            ["Experience", analysis["experience_fit"]],
            ["Domain", analysis["domain_fit"]],
            ["Writing/Reporting", analysis["writing_fit"]],
            ["Technical/Tools", analysis["technical_fit"]],
            ["Location", analysis["location_fit"]],
            ["Long-Term Career", analysis["career_fit"]]
        ], columns=["Category", "Score"])
        st.dataframe(score_table, use_container_width=True, hide_index=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Top Strengths")
            for item in analysis["strengths"]:
                st.write(f"- {item}")
        with col_b:
            st.subheader("Top Concerns")
            for item in analysis["concerns"]:
                st.write(f"- {item}")

        st.subheader("Suggested Keywords")
        st.write(", ".join(analysis["keywords"]))

        with st.form("save_analysis_form"):
            status = st.selectbox("Status", ["Found", "Applied", "Interview", "Rejected"], index=0)
            resume_version = st.text_input("Resume Version Used", value=analysis["category"])
            follow_up = st.text_input("Follow-up Date", placeholder="YYYY-MM-DD")
            notes = st.text_area("Notes", value=analysis["rationale"])
            save = st.form_submit_button("Save Analyzed Job")
            if save:
                add_job({
                    **analysis,
                    "status": status,
                    "resume_version": resume_version,
                    "follow_up_date": follow_up,
                    "notes": notes,
                    "score": analysis["overall"],
                    "strengths": "; ".join(analysis["strengths"]),
                    "concerns": "; ".join(analysis["concerns"]),
                    "rationale": analysis["rationale"]
                })
                st.success("Analyzed job saved to tracker.")

with tab_manual:
    st.header("Manual Add Job Opportunity")
    with st.form("manual_job_form"):
        company = st.text_input("Company")
        title = st.text_input("Job Title")
        location = st.text_input("Location")
        status = st.selectbox("Application Status", ["Found", "Applied", "Interview", "Rejected"])
        score = st.number_input("Overall Score", min_value=0.0, max_value=100.0, value=50.0)
        recommendation = st.selectbox("Recommendation", ["Apply", "Borderline", "Skip"])
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save Manual Job")
        if submitted:
            add_job({
                "company": company,
                "title": title,
                "location": location,
                "status": status,
                "score": score,
                "recommendation": recommendation,
                "notes": notes
            })
            st.success("Manual job saved.")

with tab_dashboard:
    st.header("Dashboard")
    jobs_df = load_jobs()
    if jobs_df.empty:
        st.info("No jobs added yet.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Jobs", len(jobs_df))
        col2.metric("Applications", len(jobs_df[jobs_df["status"] == "Applied"]))
        col3.metric("Interviews", len(jobs_df[jobs_df["status"] == "Interview"]))
        col4.metric("Apply Recommendations", len(jobs_df[jobs_df["recommendation"] == "Apply"]))

        st.subheader("Best-Fit Roles")
        best = jobs_df.sort_values("score", ascending=False).head(10)
        st.dataframe(best, use_container_width=True)

        st.subheader("All Tracked Jobs")
        st.dataframe(jobs_df, use_container_width=True)

        csv = jobs_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name="job_tracker.csv", mime="text/csv")
