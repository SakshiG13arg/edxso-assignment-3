import os, io, re, json, time
from typing import Dict, Any, List
import streamlit as st
from pypdf import PdfReader
from docx import Document

st.set_page_config(page_title="Interview Accelerator", page_icon="🎯", layout="wide")

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.main { background:#f7f8fc; }
.block-container {padding-top: 1.5rem; max-width: 1250px;}
.hero {padding: 24px 28px; border-radius: 20px; background: linear-gradient(135deg,#111827,#312e81); color:white; margin-bottom:20px;}
.hero h1 {margin:0 0 8px 0; font-size:2.15rem;}
.hero p {margin:0; opacity:.88;}
.card {background:white;border:1px solid #e5e7eb;border-radius:16px;padding:18px 20px;margin-bottom:14px;box-shadow:0 3px 14px rgba(15,23,42,.05);}
.badge {display:inline-block;padding:5px 10px;border-radius:999px;background:#eef2ff;color:#3730a3;font-size:.82rem;font-weight:600;margin:3px;}
.metric {font-size:2rem;font-weight:750;}
.small {color:#64748b;font-size:.9rem;}
.qbox {background:#111827;color:white;border-radius:18px;padding:22px;font-size:1.16rem;line-height:1.55;}
.answer {background:#f1f5f9;border-radius:14px;padding:16px;margin-top:10px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# State
# -----------------------------
DEFAULT_JD = """AI Engineer Intern

We are looking for an AI Engineer Intern to build practical AI applications.
Responsibilities:
- Develop Python services and APIs.
- Build machine learning and LLM-powered applications.
- Work with RAG, embeddings, vector databases and retrieval pipelines.
- Evaluate AI outputs and improve reliability.
- Collaborate with engineers and communicate technical decisions.

Required:
Python, machine learning fundamentals, REST APIs, Git, problem solving.

Preferred:
LLMs, RAG, FastAPI, vector databases, Docker, cloud deployment.

The candidate should demonstrate strong learning ability, communication and practical project experience."""

def init_state():
    defaults = {
        "screen":"setup", "jd":"", "resume":"", "analysis":None,
        "interview":None, "report":None, "session_started":False
    }
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
init_state()

# -----------------------------
# File parsing
# -----------------------------
def extract_file(uploaded):
    if not uploaded: return ""
    name=uploaded.name.lower()
    data=uploaded.read()
    try:
        if name.endswith(".pdf"):
            reader=PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        if name.endswith(".docx"):
            doc=Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        return data.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Unable to parse file: {e}"

# -----------------------------
# LLM provider
# -----------------------------
def call_llm(system: str, user: str) -> str:
    provider=os.getenv("LLM_PROVIDER","demo").lower()
    if provider=="gemini":
        try:
            from google import genai
            client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
            r=client.models.generate_content(model=model, contents=f"SYSTEM:\n{system}\n\nUSER:\n{user}")
            return r.text
        except Exception as e:
            st.warning(f"Gemini unavailable; using deterministic fallback. ({e})")
    if provider=="ollama":
        try:
            import requests
            model=os.getenv("OLLAMA_MODEL","llama3.2")
            r=requests.post("http://localhost:11434/api/chat", json={
                "model":model,"stream":False,
                "messages":[{"role":"system","content":system},{"role":"user","content":user}]
            }, timeout=90)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except Exception as e:
            st.warning(f"Ollama unavailable; using deterministic fallback. ({e})")
    return ""

def json_from_llm(system,user):
    raw=call_llm(system,user)
    if raw:
        raw=re.sub(r"```json|```","",raw).strip()
        try: return json.loads(raw)
        except: pass
    return None

# -----------------------------
# Deterministic analysis fallback
# -----------------------------
SKILLS=["python","machine learning","deep learning","llm","llms","rag","fastapi","rest api","apis","sql",
        "pandas","numpy","scikit-learn","docker","git","github","vector database","qdrant","faiss","bm25",
        "embeddings","nlp","streamlit","postgresql","mongodb","cloud","aws","azure","system design",
        "data analysis","statistics","plotly","matplotlib","generative ai","genai"]

def clean_words(text): return set(re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,30}", text.lower()))

def heuristic_analysis(jd,resume):
    jd_low=jd.lower(); res_low=resume.lower()
    required=[s for s in SKILLS if s in jd_low]
    matched=[s for s in required if s in res_low]
    missing=[s for s in required if s not in res_low]
    fit=round(100*len(matched)/max(1,len(required)))
    title="AI Engineer Intern"
    m=re.search(r"(?im)^(?:role|position|job title)\s*[:\-]\s*(.+)$",jd)
    if m: title=m.group(1).strip()
    responsibilities=[]
    for line in jd.splitlines():
        x=line.strip(" -*•\t")
        if len(x)>18 and any(w in x.lower() for w in ["develop","build","work","create","evaluate","design","collaborate","deploy"]):
            responsibilities.append(x)
    responsibilities=responsibilities[:8] or ["Build and evaluate practical AI solutions.","Develop Python services and APIs.","Work with AI/ML and communicate technical decisions."]
    return {
      "role":title,"responsibilities":responsibilities,
      "required_skills":required[:12],"preferred_skills":[s for s in ["llms","rag","fastapi","docker","cloud","vector database"] if s in jd_low],
      "technical_competencies":[s.title() for s in required if s in ["python","machine learning","llm","llms","rag","fastapi","rest api","apis","sql","docker","vector database","embeddings","nlp","data analysis"]],
      "behavioural_competencies":["Problem Solving","Communication","Learning Ability","Decision Making"],
      "experience_expectations":"Internship/project-level practical experience with evidence of hands-on implementation.",
      "keywords":sorted(set(required)),
      "candidate_skills":sorted(set(s for s in SKILLS if s in res_low)),
      "relevant_experience":extract_relevant(resume),
      "relevant_projects":extract_projects(resume),
      "strengths":matched[:8],
      "missing_skills":missing[:8],
      "weak_areas":["Production-scale deployment" if "docker" not in res_low and "cloud" not in res_low else "Production reliability and monitoring",
                    "Technical depth should be validated through interview"],
      "claims_to_probe":find_claims(resume),
      "fit":fit,
      "fit_explanation":"Score = matched JD skills / identified JD skills, used as a transparent prototype heuristic. LLM mode provides richer semantic analysis."
    }

def extract_relevant(text):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    return lines[:5] if lines else ["No structured experience section detected."]

def extract_projects(text):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    hits=[x for x in lines if any(w in x.lower() for w in ["project","rag","chatbot","agent","analyzer","machine learning","ai"])]
    return hits[:8] or ["Project details will be probed during the interview."]

def find_claims(text):
    pats=r"\b\d{1,3}%\b|\b\d+\+\b|\b\d+\s*(?:ms|seconds?|users?|rows?|datasets?|problems?)\b"
    return re.findall(pats,text,flags=re.I)[:10]

def analyze(jd,resume):
    system="""You are an interview-product analyst. Return ONLY valid JSON with keys:
role,responsibilities,required_skills,preferred_skills,technical_competencies,behavioural_competencies,
experience_expectations,keywords,candidate_skills,relevant_experience,relevant_projects,strengths,
missing_skills,weak_areas,claims_to_probe,fit,fit_explanation.
fit is 0-100. Compare only the supplied JD and resume. Do not invent candidate experience."""
    user=f"JOB DESCRIPTION:\n{jd}\n\nRESUME:\n{resume}"
    out=json_from_llm(system,user)
    return out if out and "fit" in out else heuristic_analysis(jd,resume)

# -----------------------------
# Interview engine
# -----------------------------
def make_questions(a):
    role=a["role"]
    strengths=a["strengths"][:4]
    missing=a["missing_skills"][:3]
    projects=a["relevant_projects"][:3]
    return [
      {"level":"Screening","q":f"Walk me through the project or experience in your resume that is most relevant to the {role} role. What problem did you solve and what was your contribution?","focus":"resume relevance"},
      {"level":"Screening","q":f"Why are you interested in {role}, and which part of the job description best matches what you want to work on?","focus":"motivation"},
      {"level":"Competency","q":f"Explain one technical decision you made in a project involving {strengths[0] if strengths else 'Python'}. What alternatives did you consider, and why did you choose your approach?","focus":"technical reasoning"},
      {"level":"Competency","q":f"Suppose the system you built started producing unreliable outputs in production. How would you diagnose and improve it?","focus":"problem solving"},
      {"level":"Deep-Dive","q":f"Let's go deeper into your resume claims. Pick one measurable result you mention and explain exactly how you measured it, including the baseline and evaluation metric.","focus":"claim verification"},
      {"level":"Deep-Dive","q":f"If the data or user traffic changed significantly from your project assumptions, what part of your solution would fail first and how would you redesign it?","focus":"systems thinking"},
    ]

def evaluate_answer(question,answer,level,a):
    if not answer.strip():
        return {"score":0,"strengths":[],"weaknesses":["No answer was captured."],"followup":"Could you give me a concise answer and explain your reasoning?"}
    # LLM path
    system="""You evaluate an interview answer. Return ONLY JSON:
score (0-100), strengths (array), weaknesses (array), followup (string).
Evaluate relevance, correctness, specificity, reasoning, evidence and communication. Be actionable."""
    user=f"ROLE: {a['role']}\nLEVEL: {level}\nQUESTION: {question}\nANSWER: {answer}"
    out=json_from_llm(system,user)
    if out: return out
    words=answer.split()
    score=min(95,max(35,45+min(35,len(words)//4)+(10 if any(x in answer.lower() for x in ["because","trade-off","metric","baseline","why","however"]) else 0)))
    strengths=["Directly addressed the question"] if len(words)>12 else ["Attempted the question"]
    weaknesses=[]
    if len(words)<35: weaknesses.append("Add more concrete technical detail and reasoning.")
    if not any(c.isdigit() for c in answer): weaknesses.append("Where possible, quantify impact or evaluation results.")
    if level=="Deep-Dive" and not any(x in answer.lower() for x in ["trade","failure","edge","metric","baseline"]):
        weaknesses.append("A deep-dive answer should discuss assumptions, trade-offs or failure cases.")
    followup=("What evidence or metric would you use to validate that decision?" if level!="Screening"
              else "What was your specific contribution, and how did you verify that it worked?")
    return {"score":score,"strengths":strengths,"weaknesses":weaknesses,"followup":followup}

def build_report(interview,a):
    ev=interview["evaluations"]
    scores=[x["score"] for x in ev] or [0]
    overall=round(sum(scores)/len(scores))
    cats={
      "Role Fit": min(100,round(overall*.95+a["fit"]*.05)),
      "Technical Knowledge": round(sum(x["score"] for x in ev if x["level"]!="Screening")/max(1,len([x for x in ev if x["level"]!="Screening"]))),
      "Problem Solving": round(overall*.95),
      "Communication": round(overall*.9+5),
      "Confidence": round(overall*.85+8),
      "Depth of Understanding": round(overall*.9),
      "Behavioural Fit": round(overall*.92),
    }
    gaps=[]
    gaps += [f"Review {x.title()}" for x in a["missing_skills"][:5]]
    gaps += [w for x in ev for w in x.get("weaknesses",[])][:5]
    if not gaps: gaps=["Practice deeper technical justification and measurable evidence."]
    readiness="Strong Candidate" if overall>=82 else "Interview Ready" if overall>=68 else "Needs Preparation" if overall>=50 else "Not Ready"
    return {"overall":overall,"competencies":cats,"evaluations":ev,
            "strengths":list(dict.fromkeys([s for x in ev for s in x.get("strengths",[])]+a["strengths"]))[:8],
            "weaknesses":list(dict.fromkeys([w for x in ev for w in x.get("weaknesses",[])]+a["weak_areas"]))[:8],
            "gaps":gaps[:10],"readiness":readiness}

# -----------------------------
# Voice component
# -----------------------------
def voice_widget():
    st.markdown("""
    <div class="card">
    <b>🎙️ Voice interview</b>
    <p class="small">Use the browser microphone to speak. Your browser converts speech to text, which is then evaluated by the interview engine.</p>
    <button onclick="startRec()" style="padding:10px 16px;border:0;border-radius:10px;background:#4f46e5;color:white;cursor:pointer;">🎤 Start speaking</button>
    <button onclick="stopRec()" style="padding:10px 16px;border:0;border-radius:10px;margin-left:8px;cursor:pointer;">⏹ Stop</button>
    <div id="status" style="margin-top:10px;color:#64748b"></div>
    <textarea id="speech" placeholder="Transcript will appear here..." style="width:100%;min-height:110px;margin-top:8px;padding:10px;border-radius:10px;border:1px solid #ddd;"></textarea>
    <script>
    let recognition;
    function startRec(){
      const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
      if(!SR){document.getElementById('status').innerText='Speech recognition is not supported in this browser. Use Chrome/Edge or type your answer.';return;}
      recognition=new SR(); recognition.lang='en-IN'; recognition.interimResults=true;
      recognition.onstart=()=>document.getElementById('status').innerText='Listening...';
      recognition.onresult=(e)=>{let s='';for(let i=e.resultIndex;i<e.results.length;i++)s+=e.results[i][0].transcript;document.getElementById('speech').value=s;};
      recognition.onerror=(e)=>document.getElementById('status').innerText='Microphone error: '+e.error;
      recognition.onend=()=>document.getElementById('status').innerText='Stopped. Copy/use the transcript below.';
      recognition.start();
    }
    function stopRec(){if(recognition) recognition.stop();}
    </script>
    </div>
    """, unsafe_allow_html=True)
    # Native Streamlit fallback input ensures transcript reaches Python reliably
    return st.text_area("Voice transcript / answer", key="voice_answer", height=120, placeholder="If browser speech recognition is unavailable, type your answer here.")

def speak_button(text):
    safe=text.replace("\\","\\\\").replace("`","\\`").replace("\n"," ")
    st.components.v1.html(f"""
    <button onclick="speechSynthesis.cancel(); speechSynthesis.speak(new SpeechSynthesisUtterance(`{safe}`));"
    style="padding:9px 14px;border:1px solid #c7d2fe;border-radius:9px;background:white;cursor:pointer;">🔊 Speak question</button>
    """,height=50)

# -----------------------------
# UI helpers
# -----------------------------
def nav():
    tabs=["setup","role","candidate","interview","results"]
    labels=["1. Setup","2. Role","3. Candidate","4. Interview","5. Results"]
    cols=st.columns(5)
    for c,k,l in zip(cols,tabs,labels):
        if c.button(l, use_container_width=True, disabled=(k=="results" and st.session_state.report is None)):
            st.session_state.screen=k
            st.rerun()

st.markdown('<div class="hero"><h1>🎯 Interview Accelerator</h1><p>Personalized AI interview practice from your Job Description + Resume.</p></div>',unsafe_allow_html=True)
nav()

# SETUP
if st.session_state.screen=="setup":
    st.subheader("Build your personalized interview")
    st.write("Upload or paste a JD and resume. The prototype then creates a role-aware interview plan.")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("### Job Description")
        f=st.file_uploader("Upload JD",type=["pdf","docx","txt"],key="jdu")
        if f: st.session_state.jd=extract_file(f)
        st.session_state.jd=st.text_area("Paste JD",value=st.session_state.jd or DEFAULT_JD,height=330)
    with c2:
        st.markdown("### Resume")
        f=st.file_uploader("Upload Resume",type=["pdf","docx","txt"],key="resu")
        if f: st.session_state.resume=extract_file(f)
        st.session_state.resume=st.text_area("Paste resume",value=st.session_state.resume,height=330)
    if st.button("🚀 Analyze JD + Resume",type="primary",use_container_width=True):
        if len(st.session_state.jd.strip())<80 or len(st.session_state.resume.strip())<80:
            st.error("Please provide a meaningful JD and resume.")
        else:
            with st.spinner("Analyzing role and candidate..."):
                st.session_state.analysis=analyze(st.session_state.jd,st.session_state.resume)
            st.session_state.screen="role"; st.rerun()

# ROLE
elif st.session_state.screen=="role":
    a=st.session_state.analysis
    st.subheader("Role Analysis")
    st.markdown(f"### {a['role']}")
    c1,c2,c3=st.columns(3)
    c1.metric("Job Fit",f"{a['fit']}%")
    c2.metric("JD Skills",len(a["required_skills"]))
    c3.metric("Missing / weak",len(a["missing_skills"])+len(a["weak_areas"]))
    l,r=st.columns(2)
    with l:
        st.markdown("#### Key responsibilities")
        for x in a["responsibilities"]: st.write("•",x)
        st.markdown("#### Required skills")
        st.write(" ".join(f'<span class="badge">{x}</span>' for x in a["required_skills"]) or "Not detected",unsafe_allow_html=True)
    with r:
        st.markdown("#### Technical competencies")
        for x in a["technical_competencies"]: st.write("•",x)
        st.markdown("#### Behavioural competencies")
        for x in a["behavioural_competencies"]: st.write("•",x)
        st.markdown("#### Important keywords")
        st.write(", ".join(a["keywords"]))
    st.info(a["fit_explanation"])
    if st.button("Continue to Candidate Analysis",type="primary"): st.session_state.screen="candidate"; st.rerun()

# CANDIDATE
elif st.session_state.screen=="candidate":
    a=st.session_state.analysis
    st.subheader("Candidate Analysis")
    l,r=st.columns(2)
    with l:
        st.markdown("### Strong match")
        for x in a["strengths"]: st.write("✅",x)
        st.markdown("### Missing / weak")
        for x in a["missing_skills"]: st.write("⚠️",x)
        for x in a["weak_areas"]: st.write("⚠️",x)
    with r:
        st.markdown("### Relevant projects / experience")
        for x in a["relevant_projects"]: st.write("•",x)
        st.markdown("### Claims to probe")
        st.write(", ".join(a["claims_to_probe"]) if a["claims_to_probe"] else "No numeric claims detected.")
        st.markdown("### Candidate skills detected")
        st.write(", ".join(a["candidate_skills"]))
    st.divider()
    st.markdown(f"### Job Fit: **{a['fit']}%**")
    st.progress(a["fit"]/100)
    if st.button("🎙️ Start Adaptive Interview",type="primary",use_container_width=True):
        qs=make_questions(a)
        st.session_state.interview={"questions":qs,"index":0,"answers":[],"evaluations":[],"current":qs[0]}
        st.session_state.screen="interview"; st.rerun()

# INTERVIEW
elif st.session_state.screen=="interview":
    a=st.session_state.analysis
    iv=st.session_state.interview
    if iv["index"]>=len(iv["questions"]):
        st.session_state.report=build_report(iv,a)
        st.session_state.screen="results"; st.rerun()
    q=iv["current"]
    progress=iv["index"]/len(iv["questions"])
    st.subheader("AI Interview Simulator")
    c1,c2,c3=st.columns(3)
    c1.metric("Level",q["level"])
    c2.metric("Question",f"{iv['index']+1}/{len(iv['questions'])}")
    c3.metric("Progress",f"{round(progress*100)}%")
    st.progress(progress)
    st.markdown(f'<div class="qbox"><b>AI Interviewer · {q["level"]}</b><br><br>{q["q"]}</div>',unsafe_allow_html=True)
    speak_button(q["q"])
    answer=voice_widget()
    if st.button("Submit Answer →",type="primary",use_container_width=True):
        if not answer.strip():
            st.error("Please provide an answer.")
        else:
            with st.spinner("Evaluating answer and adapting the next question..."):
                ev=evaluate_answer(q["q"],answer,q["level"],a)
            iv["answers"].append(answer)
            iv["evaluations"].append({"question":q["q"],"answer":answer,"level":q["level"],**ev})
            iv["index"]+=1
            # Dynamic follow-up replaces the next planned question when appropriate
            if ev.get("followup") and iv["index"]<len(iv["questions"]) and ev["score"]<70:
                base=iv["questions"][iv["index"]]
                iv["questions"][iv["index"]]={"level":base["level"],"q":ev["followup"],"focus":"adaptive follow-up"}
            if iv["index"]<len(iv["questions"]): iv["current"]=iv["questions"][iv["index"]]
            st.rerun()
    if iv["evaluations"]:
        last=iv["evaluations"][-1]
        st.markdown(f'<div class="answer"><b>Latest evaluation: {last["score"]}/100</b><br>{"; ".join(last["weaknesses"])}</div>',unsafe_allow_html=True)

# RESULTS
elif st.session_state.screen=="results":
    a=st.session_state.analysis
    r=st.session_state.report
    st.subheader("Interview Performance Report")
    c1,c2,c3=st.columns(3)
    c1.metric("Overall Score",f"{r['overall']}/100")
    c2.metric("Job Fit",f"{a['fit']}%")
    c3.metric("Readiness",r["readiness"])
    st.progress(r["overall"]/100)
    st.markdown("### Competency Scores")
    cols=st.columns(4)
    for i,(k,v) in enumerate(r["competencies"].items()):
        cols[i%4].metric(k,f"{v}/100")
    l,rr=st.columns(2)
    with l:
        st.markdown("### Strengths")
        for x in r["strengths"]: st.write("✅",x)
    with rr:
        st.markdown("### Weaknesses")
        for x in r["weaknesses"]: st.write("⚠️",x)
    st.markdown("### Preparation Gaps")
    for i,x in enumerate(r["gaps"],1): st.write(f"**Priority {i}:** {x}")
    st.markdown("### Question-level Feedback")
    for i,e in enumerate(r["evaluations"],1):
        with st.expander(f"Q{i} · {e['level']} · Score {e['score']}/100"):
            st.write("**Question**",e["question"])
            st.write("**Candidate Answer**",e["answer"])
            st.write("**What was good**")
            for x in e["strengths"]: st.write("•",x)
            st.write("**What could be better**")
            for x in e["weaknesses"]: st.write("•",x)
            st.write("**Ideal direction**")
            st.info("A stronger answer should be specific, technically justified, evidence-based, and connected to the role requirements.")
    report_json=json.dumps({"analysis":a,"report":r},indent=2)
    st.download_button("⬇️ Download JSON Report",report_json,"interview_report.json","application/json")
    if st.button("🔄 Start another interview"):
        st.session_state.screen="setup"; st.session_state.interview=None; st.session_state.report=None; st.rerun()
