from flask import Flask, render_template_string, request, redirect, session, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json, os, math, random, webbrowser, threading, time, html as html_module

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
app.secret_key = "neuralretain_v5_telco_2025_ultra"

def chk():
    if not session.get("logged_in"):
        return redirect("/")
    return None

CSV_PATH = os.path.join(os.path.dirname(__file__), "TelcoCustomerChurn.csv")
df_raw = pd.read_csv(CSV_PATH)

for col in ["ChurnLabel","CustomerStatus","Contract","InternetType","PaymentMethod","Gender"]:
    df_raw[col] = df_raw[col].astype(str).str.strip()
df_raw["ChurnCategory"]  = df_raw["ChurnCategory"].fillna("None").astype(str).str.strip()
df_raw["ChurnReason"]    = df_raw["ChurnReason"].fillna("N/A").astype(str).str.strip()
df_raw["Offer"]          = df_raw["Offer"].fillna("None").astype(str).str.strip()
for col in ["MonthlyCharge","TotalCharges","TotalRevenue","ChurnScore","CLTV","Age","SatisfactionScore","TenureinMonths"]:
    df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce").fillna(0)

TEAM_DATA = {
    "senior_manager": {"id":"SM-001","name":"Dev","role":"Senior Manager","avatar":"DV"},
    "team_leads":[
        {"id":"TL-001","name":"Priya Menon",  "role":"Team Lead","avatar":"PM","team":"Alpha","color":"#a78bfa"},
        {"id":"TL-002","name":"Rohit Verma",  "role":"Team Lead","avatar":"RV","team":"Beta", "color":"#f472b6"},
        {"id":"TL-003","name":"Sneha Kapoor", "role":"Team Lead","avatar":"SK","team":"Gamma","color":"#34d399"},
        {"id":"TL-004","name":"Arjun Nair",   "role":"Team Lead","avatar":"AN","team":"Delta","color":"#60a5fa"},
    ],
    "agents":[
        {"id":"AG-001","name":"Kavya Reddy",  "tl":"TL-001","avatar":"KR","status":"active","email":"kavya.r@telecom.in","phone":"+91-98100-00020"},
        {"id":"AG-002","name":"Manish Joshi", "tl":"TL-001","avatar":"MJ","status":"active","email":"manish.j@telecom.in","phone":"+91-98100-00021"},
        {"id":"AG-003","name":"Divya Singh",  "tl":"TL-001","avatar":"DS","status":"busy",  "email":"divya.s@telecom.in","phone":"+91-98100-00022"},
        {"id":"AG-004","name":"Rahul Gupta",  "tl":"TL-002","avatar":"RG","status":"active","email":"rahul.g@telecom.in","phone":"+91-98100-00023"},
        {"id":"AG-005","name":"Pooja Iyer",   "tl":"TL-002","avatar":"PI","status":"active","email":"pooja.i@telecom.in","phone":"+91-98100-00024"},
        {"id":"AG-006","name":"Anil Kumar",   "tl":"TL-002","avatar":"AK","status":"offline","email":"anil.k@telecom.in","phone":"+91-98100-00025"},
        {"id":"AG-007","name":"Neha Patel",   "tl":"TL-003","avatar":"NP","status":"active","email":"neha.p@telecom.in","phone":"+91-98100-00026"},
        {"id":"AG-008","name":"Suresh Rao",   "tl":"TL-003","avatar":"SR","status":"busy",  "email":"suresh.r@telecom.in","phone":"+91-98100-00027"},
        {"id":"AG-009","name":"Anjali Das",   "tl":"TL-003","avatar":"AD","status":"active","email":"anjali.d@telecom.in","phone":"+91-98100-00028"},
        {"id":"AG-010","name":"Vikram Shah",  "tl":"TL-004","avatar":"VS","status":"active","email":"vikram.s@telecom.in","phone":"+91-98100-00029"},
        {"id":"AG-011","name":"Meera Nair",   "tl":"TL-004","avatar":"MN","status":"active","email":"meera.n@telecom.in","phone":"+91-98100-00030"},
        {"id":"AG-012","name":"Deepak Roy",   "tl":"TL-004","avatar":"DR","status":"busy",  "email":"deepak.r@telecom.in","phone":"+91-98100-00031"},
    ]
}
AGENT_MAP = {a["id"]: a for a in TEAM_DATA["agents"]}
TL_MAP    = {t["id"]: t for t in TEAM_DATA["team_leads"]}

n = len(df_raw)
agent_ids = [TEAM_DATA["agents"][i % 12]["id"] for i in range(n)]
df_raw["AssignedAgent"] = agent_ids

def map_status(row):
    cs = str(row["CustomerStatus"]); cl = str(row["ChurnLabel"]); sc = float(row["ChurnScore"])
    if cs == "Churned": return "escalated"
    if cl == "Yes": return "at_risk"
    if sc >= 70: return "at_risk"
    if sc >= 50: return "flagged"
    return "active"
df_raw["CustStatus"] = df_raw.apply(map_status, axis=1)

action_log   = []
task_store   = []
alert_store  = []

def generate_alerts(df):
    alerts = []
    high_risk = df[df["ChurnScore"] >= 85]
    if len(high_risk) > 0:
        alerts.append({"id":"AL-001","type":"critical","icon":"🚨","title":f"{len(high_risk)} accounts at extreme churn risk (score >=85)","sub":"Immediate intervention recommended","time":"Just now","read":False})
    competitor = df[(df["ChurnLabel"]=="Yes") & (df["ChurnCategory"]=="Competitor")]
    if len(competitor) > 50:
        alerts.append({"id":"AL-002","type":"warning","icon":"⚡","title":f"Competitor threat spike: {len(competitor)} customers lost","sub":"Competitive pricing review advised","time":"2m ago","read":False})
    low_sat = df[df["SatisfactionScore"] <= 2]
    if len(low_sat) > 20:
        alerts.append({"id":"AL-003","type":"warning","icon":"📉","title":f"{len(low_sat)} customers with satisfaction score <=2","sub":"Proactive outreach queue ready","time":"5m ago","read":False})
    alerts.append({"id":"AL-004","type":"info","icon":"📊","title":"Weekly churn analysis report ready","sub":"Insights tab updated with latest segmentation","time":"1h ago","read":True})
    alerts.append({"id":"AL-005","type":"success","icon":"✅","title":"Team Gamma improved churn rate by 3.2%","sub":"Sneha Kapoor's retention campaign performing","time":"3h ago","read":True})
    return alerts

alert_store = generate_alerts(df_raw)

def fmt_money(v):
    v = float(v)
    if v >= 1_000_000: return f"₹{v/1_000_000:.2f}M"
    if v >= 1_000:     return f"₹{v/1_000:.1f}K"
    return f"₹{v:,.0f}"

def compute_kpis(df):
    total = len(df)
    if total == 0:
        return dict(total=0,churned=0,retained=0,rate=0.0,rev_loss=0.0,avg_sat=0.0,avg_cltv=0.0,avg_score=0.0,total_revenue=0.0)
    churned  = int((df["ChurnLabel"]=="Yes").sum())
    retained = total - churned
    rate     = round(churned/total*100,1)
    rev_loss = float(df[df["ChurnLabel"]=="Yes"]["MonthlyCharge"].sum())
    avg_sat  = round(float(df["SatisfactionScore"].mean()),2)
    avg_cltv = round(float(df["CLTV"].mean()),0)
    avg_score= round(float(df["ChurnScore"].mean()),1)
    total_revenue = float(df["TotalRevenue"].sum())
    return dict(total=total,churned=churned,retained=retained,rate=rate,
                rev_loss=rev_loss,avg_sat=avg_sat,avg_cltv=avg_cltv,
                avg_score=avg_score,total_revenue=total_revenue)

def get_agent_stats(df):
    stats = {}
    for ag in TEAM_DATA["agents"]:
        sub = df[df["AssignedAgent"]==ag["id"]]
        total   = len(sub)
        churned = int((sub["ChurnLabel"]=="Yes").sum())
        at_risk = int(sub["CustStatus"].isin(["at_risk","escalated","flagged"]).sum())
        resolved= int((sub["CustStatus"]=="active").sum())
        rate    = round(churned/total*100,1) if total>0 else 0
        rev     = float(sub[sub["ChurnLabel"]=="Yes"]["MonthlyCharge"].sum())
        avg_sat = round(float(sub["SatisfactionScore"].mean()),2) if total>0 else 0
        stats[ag["id"]] = dict(total=total,churned=churned,at_risk=at_risk,resolved=resolved,rate=rate,rev=rev,avg_sat=avg_sat)
    return stats

def get_tl_stats(df, agent_stats):
    stats = {}
    for tl in TEAM_DATA["team_leads"]:
        aids = [a["id"] for a in TEAM_DATA["agents"] if a["tl"]==tl["id"]]
        total   = sum(agent_stats.get(a,{}).get("total",0)   for a in aids)
        churned = sum(agent_stats.get(a,{}).get("churned",0) for a in aids)
        at_risk = sum(agent_stats.get(a,{}).get("at_risk",0) for a in aids)
        resolved= sum(agent_stats.get(a,{}).get("resolved",0)for a in aids)
        rate    = round(churned/total*100,1) if total>0 else 0
        rev     = sum(agent_stats.get(a,{}).get("rev",0)     for a in aids)
        stats[tl["id"]] = dict(total=total,churned=churned,at_risk=at_risk,resolved=resolved,rate=rate,rev=rev,agents=aids)
    return stats

def av_color(i): return ["av-purple","av-pink","av-cyan","av-green","av-amber"][i%5]

def score_pill(sc):
    sc=float(sc)
    cls="sp-hi" if sc>=70 else "sp-med" if sc>=40 else "sp-lo"
    return f'<span class="score-pill {cls}">{sc:.0f}</span>'

def status_badge(st):
    cls_map={"active":"csb-active","at_risk":"csb-at_risk","escalated":"csb-escalated","resolved":"csb-resolved","flagged":"csb-flagged"}
    label_map={"active":"Active","at_risk":"At Risk","escalated":"Escalated","resolved":"Resolved","flagged":"Flagged"}
    return f'<span class="cst-badge {cls_map.get(st,"csb-active")}">{label_map.get(st,st)}</span>'

def make_gauge(rate, size=220):
    cx, cy = size/2, size*0.58; R = size*0.40; stroke_w = size*0.085; span_deg = 220
    if rate < 30: arc_color="#10b981"; status_text="STABLE"; status_color="#34d399"
    elif rate < 60: arc_color="#f59e0b"; status_text="ELEVATED"; status_color="#fbbf24"
    else: arc_color="#ef4444"; status_text="CRITICAL"; status_color="#f87171"
    def arc_path(start_a, span_a, radius):
        steps=60; pts=[]
        for i in range(steps+1):
            angle=start_a-(span_a*i/steps); x=cx+radius*math.cos(angle); y=cy-radius*math.sin(angle)
            pts.append(f"{'M' if i==0 else 'L'}{x:.2f},{y:.2f}")
        return " ".join(pts)
    track_d=arc_path(math.radians(200),math.radians(220),R)
    fill_d=arc_path(math.radians(200),math.radians(220*rate/100),R)
    needle_angle_rad=math.radians(200-220*rate/100)
    nx=cx+(R-stroke_w*0.5)*math.cos(needle_angle_rad)
    ny=cy-(R-stroke_w*0.5)*math.sin(needle_angle_rad)
    return (f'<svg width="{size}" height="{int(size*0.75)}" viewBox="0 0 {size} {int(size*0.75)}" style="overflow:visible;display:block;margin:0 auto;">'
            f'<path d="{track_d}" fill="none" stroke="rgba(139,92,246,0.08)" stroke-width="{stroke_w:.1f}" stroke-linecap="round"/>'
            f'<path d="{fill_d}" fill="none" stroke="{arc_color}" stroke-width="{stroke_w:.1f}" stroke-linecap="round"/>'
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="rgba(255,255,255,0.9)" stroke-width="2.5" stroke-linecap="round"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{size*0.04:.1f}" fill="{arc_color}"/>'
            f'<text x="{cx:.1f}" y="{cy-size*0.06:.1f}" text-anchor="middle" dominant-baseline="middle" font-family="Space Grotesk,sans-serif" font-size="{size*0.14:.0f}" font-weight="800" fill="{status_color}">{rate:.1f}%</text>'
            f'<text x="{cx:.1f}" y="{cy+size*0.055:.1f}" text-anchor="middle" dominant-baseline="middle" font-family="DM Sans,sans-serif" font-size="{size*0.055:.0f}" font-weight="700" fill="{status_color}" letter-spacing="2">{status_text}</text>'
            f'</svg>')

def make_donut(data_dict, size=160):
    if not data_dict: return "", ""
    total=sum(data_dict.values()) or 1
    colors=["#8b5cf6","#f472b6","#22d3ee","#10b981","#f59e0b","#f87171","#a78bfa","#60a5fa"]
    R,r=size*0.38,size*0.24; cx,cy=size/2,size/2; mid_R=(R+r)/2; circ_mid=2*math.pi*mid_R; stroke=R-r
    slices=""; offset=0; legend_items=[]
    for i,(lbl,val) in enumerate(data_dict.items()):
        pct=val/total; arc=circ_mid*pct; c=colors[i%len(colors)]
        slices+=(f'<circle cx="{cx}" cy="{cy}" r="{mid_R:.1f}" fill="none" stroke="{c}" stroke-width="{stroke:.1f}"'
                 f' stroke-dasharray="{arc:.2f} {(circ_mid-arc):.2f}" stroke-dashoffset="{(-offset):.2f}"'
                 f' transform="rotate(-90 {cx} {cy})" stroke-linecap="butt" opacity="0.9"/>')
        offset+=arc
        legend_items.append(f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px;"><div style="width:8px;height:8px;border-radius:3px;background:{c};flex-shrink:0;"></div><span style="font-size:10px;color:var(--text3);">{lbl}</span><span style="margin-left:auto;font-family:JetBrains Mono,monospace;font-size:10px;font-weight:700;color:rgba(228,210,255,0.7);">{pct*100:.1f}%</span></div>')
    svg=(f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}"><circle cx="{cx}" cy="{cy}" r="{mid_R:.1f}" fill="none" stroke="rgba(139,92,246,0.07)" stroke-width="{stroke:.1f}"/>{slices}<circle cx="{cx}" cy="{cy}" r="{r*0.85:.1f}" fill="rgba(10,10,15,0.95)"/><text x="{cx}" y="{cy-7}" text-anchor="middle" font-family="Space Grotesk,sans-serif" font-size="14" font-weight="700" fill="#fff">{total}</text><text x="{cx}" y="{cy+9}" text-anchor="middle" font-family="DM Sans,sans-serif" font-size="9" fill="rgba(170,150,230,0.4)">TOTAL</text></svg>')
    return svg, "".join(legend_items)

def make_sparkline(values, width=120, height=32, color="#8b5cf6"):
    if len(values) < 2: return ""
    mn,mx=min(values),max(values); rng=mx-mn or 1
    pts=[]
    for i,v in enumerate(values):
        x=i*(width/(len(values)-1)); y=height-(v-mn)/rng*height
        pts.append(f"{x:.1f},{y:.1f}")
    path="M"+" L".join(pts)
    area_path="M"+" L".join(pts)+f" L{width:.1f},{height} L0,{height} Z"
    gid = color.replace("#","")
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="overflow:visible;">'
            f'<defs><linearGradient id="spk_{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{color}" stop-opacity="0.3"/><stop offset="100%" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
            f'<path d="{area_path}" fill="url(#spk_{gid})" />'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" r="2.5" fill="{color}"/>'
            f'</svg>')

# FIX: Safe JSON encoding for HTML attributes - avoids repr() bug
def safe_json_attr(data):
    """Encode data as JSON safe for use in HTML data attributes (single-quoted)."""
    return html_module.escape(json.dumps(data, ensure_ascii=True), quote=True)

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');
:root{
  --bg:#07070d;--bg2:#0d0d15;--bg3:#13131c;--bg4:#1a1a26;
  --border:rgba(139,92,246,0.09);--border2:rgba(139,92,246,0.2);--border3:rgba(139,92,246,0.38);
  --text:#e8deff;--text2:rgba(215,195,255,0.68);--text3:rgba(175,155,235,0.38);
  --purple:#8b5cf6;--purple2:#a78bfa;--purple3:#7c3aed;--purple4:#c4b5fd;
  --pink:#f472b6;--cyan:#22d3ee;--amber:#f59e0b;--red:#ef4444;--green:#10b981;
  --card-bg:rgba(139,92,246,0.025);--card-border:rgba(139,92,246,0.08);
  --nav-h:52px;--ticker-h:34px;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;transition:background 0.25s ease,color 0.25s ease;}
::-webkit-scrollbar{width:3px;height:3px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:rgba(139,92,246,0.2);border-radius:4px;}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@keyframes gradShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
@keyframes dotBlink{0%,100%{opacity:1}50%{opacity:0.2}}
@keyframes tickerScroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
@keyframes toastIn{from{transform:translateY(20px) scale(0.95);opacity:0}to{transform:translateY(0) scale(1);opacity:1}}
@keyframes toastOut{to{opacity:0;transform:translateY(8px) scale(0.96)}}
@keyframes pulseRing{0%{box-shadow:0 0 0 0 rgba(239,68,68,0.5)}70%{box-shadow:0 0 0 10px rgba(239,68,68,0)}100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}}
@keyframes slideDown{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
@keyframes liveFlash{0%,100%{opacity:1}50%{opacity:0.4}}
@keyframes scoreUp{0%{transform:scale(1)}50%{transform:scale(1.12)}100%{transform:scale(1)}}
@keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
.churn-ticker-bar{width:100%;background:linear-gradient(90deg,rgba(239,68,68,0.14),rgba(239,68,68,0.07) 50%,rgba(239,68,68,0.14));border-bottom:1px solid rgba(239,68,68,0.28);overflow:hidden;position:relative;height:var(--ticker-h);display:flex;align-items:center;flex-shrink:0;}
.ticker-badge{flex-shrink:0;background:linear-gradient(135deg,#dc2626,#ef4444);color:#fff;font-family:'Space Grotesk',sans-serif;font-size:9px;font-weight:800;letter-spacing:0.16em;padding:0 14px;height:100%;display:flex;align-items:center;gap:6px;z-index:2;}
.ticker-live-dot{width:6px;height:6px;border-radius:50%;background:#fff;animation:dotBlink 1.2s ease infinite;}
.ticker-track{flex:1;overflow:hidden;height:100%;}
.ticker-inner{display:flex;align-items:center;height:100%;white-space:nowrap;animation:tickerScroll 30s linear infinite;}
.ticker-item{display:inline-flex;align-items:center;gap:6px;padding:0 28px;font-size:10.5px;font-weight:600;color:rgba(255,255,255,0.7);border-right:1px solid rgba(239,68,68,0.18);}
.ticker-item .ti-val{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;}
.ti-val.danger{color:#f87171;animation:liveFlash 2s ease infinite;}
.ti-val.warn{color:#fbbf24;}
.ti-val.good{color:#34d399;}
.topnav{display:flex;align-items:center;justify-content:space-between;padding:0 22px;height:var(--nav-h);background:rgba(7,7,13,0.98);border-bottom:1px solid var(--border);backdrop-filter:blur(32px);position:sticky;top:var(--ticker-h);z-index:200;}
.brand{font-family:'Space Grotesk',sans-serif;font-size:13.5px;font-weight:800;color:#fff;letter-spacing:0.05em;display:flex;align-items:center;gap:9px;text-decoration:none;}
.brand-orb{width:28px;height:28px;border-radius:7px;background:linear-gradient(135deg,#7c3aed,#a78bfa,#f472b6);animation:gradShift 4s ease infinite;background-size:200% 200%;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800;color:#fff;box-shadow:0 4px 12px rgba(124,58,237,0.4);}
.ntabs{display:flex;gap:1px;}
.ntab{padding:6px 13px;border-radius:7px;background:transparent;color:var(--text3);font-family:'DM Sans',sans-serif;font-size:12px;font-weight:500;cursor:pointer;text-decoration:none;transition:all 0.18s;border:1px solid transparent;display:flex;align-items:center;gap:5px;}
.ntab:hover{color:var(--text2);background:rgba(139,92,246,0.07);}
.ntab.active{color:var(--purple2);background:rgba(139,92,246,0.12);border-color:var(--border2);}
.nav-right{display:flex;align-items:center;gap:8px;}
.nav-user{display:flex;align-items:center;gap:7px;padding:5px 11px 5px 6px;border-radius:8px;background:rgba(139,92,246,0.07);border:1px solid var(--border2);}
.nav-avatar{width:26px;height:26px;border-radius:6px;background:linear-gradient(135deg,#7c3aed,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800;color:#fff;flex-shrink:0;}
.nav-uname{font-size:11.5px;font-weight:600;color:var(--text2);}
.nav-role{font-size:9px;color:var(--text3);}
.nav-bell{position:relative;width:30px;height:30px;border-radius:7px;border:1px solid var(--border);background:transparent;color:var(--text3);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;transition:all 0.18s;}
.nav-bell:hover{background:rgba(139,92,246,0.1);color:var(--purple2);}
.nav-bell-badge{position:absolute;top:-4px;right:-4px;width:14px;height:14px;border-radius:50%;background:#ef4444;color:#fff;font-size:7px;font-weight:800;display:flex;align-items:center;justify-content:center;border:1px solid var(--bg);animation:pulseRing 2s infinite;}
.nlogout{padding:5px 11px;border-radius:7px;border:1px solid rgba(239,68,68,0.18);background:transparent;color:rgba(239,68,68,0.5);font-size:11px;font-weight:500;cursor:pointer;text-decoration:none;transition:all 0.18s;}
.nlogout:hover{background:rgba(239,68,68,0.1);color:#ef4444;}
.nav-wrapper{position:sticky;top:0;z-index:200;}
.content{padding:20px 24px 60px;}
#toastStack{position:fixed;bottom:24px;right:24px;z-index:99999;display:flex;flex-direction:column;gap:8px;pointer-events:none;}
.toast-item{background:rgba(13,13,21,0.98);border:1px solid var(--border2);border-radius:11px;padding:11px 15px;font-size:12px;font-weight:500;color:var(--purple2);box-shadow:0 8px 40px rgba(0,0,0,0.8);animation:toastIn 0.28s cubic-bezier(0.34,1.56,0.64,1) both;display:flex;align-items:flex-start;gap:10px;min-width:260px;pointer-events:auto;}
.toast-item.t-red{color:#f87171;border-color:rgba(239,68,68,0.3);}
.toast-item.t-green{color:#34d399;border-color:rgba(16,185,129,0.28);}
.toast-item.t-amber{color:#fbbf24;border-color:rgba(245,158,11,0.28);}
.toast-item.t-out{animation:toastOut 0.22s ease both;}
.toast-icon{font-size:16px;flex-shrink:0;}
.toast-body .toast-title{font-weight:700;margin-bottom:2px;font-size:12px;}
.toast-body .toast-sub{font-size:10px;opacity:0.5;line-height:1.4;}
.kpi-strip{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:20px;}
.kpi-card{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;padding:17px 18px 14px;position:relative;overflow:hidden;transition:all 0.24s;cursor:pointer;}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:14px 14px 0 0;}
.kpi-card.kc-purple::before{background:linear-gradient(90deg,var(--purple),transparent);}
.kpi-card.kc-pink::before{background:linear-gradient(90deg,var(--pink),transparent);}
.kpi-card.kc-cyan::before{background:linear-gradient(90deg,var(--cyan),transparent);}
.kpi-card.kc-amber::before{background:linear-gradient(90deg,var(--amber),transparent);}
.kpi-card.kc-green::before{background:linear-gradient(90deg,var(--green),transparent);}
.kpi-card.kc-red::before{background:linear-gradient(90deg,var(--red),transparent);}
.kpi-card:hover{transform:translateY(-3px);border-color:var(--border2);box-shadow:0 8px 32px rgba(0,0,0,0.5);}
.kpi-label{font-size:9px;font-weight:700;letter-spacing:0.12em;color:var(--text3);text-transform:uppercase;margin-bottom:9px;}
.kpi-val{font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:800;color:#fff;line-height:1;}
.kpi-sub{font-size:10px;color:var(--text3);margin-top:5px;}
.kpi-delta{font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;}
.kpi-delta.up{background:rgba(239,68,68,0.12);color:#f87171;}
.kpi-delta.down{background:rgba(16,185,129,0.12);color:#34d399;}
.kpi-sparkline{margin-top:8px;}
.slabel{font-size:9px;font-weight:700;letter-spacing:0.16em;color:var(--text3);text-transform:uppercase;margin-bottom:13px;display:flex;align-items:center;gap:12px;}
.slabel::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--border),transparent);}
.card-panel{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;overflow:hidden;margin-bottom:18px;}
.card-panel-hdr{display:flex;align-items:center;justify-content:space-between;padding:13px 17px;border-bottom:1px solid rgba(139,92,246,0.05);background:rgba(139,92,246,0.02);}
.cph-title{font-family:'Space Grotesk',sans-serif;font-size:13px;font-weight:700;color:#fff;display:flex;align-items:center;gap:8px;}
.cph-meta{font-size:11px;color:var(--text3);}
.tab-bar{display:flex;gap:2px;background:rgba(139,92,246,0.04);border:1px solid var(--border);border-radius:10px;padding:3px;margin-bottom:20px;}
.tab-btn{flex:1;padding:8px 14px;border-radius:7px;border:none;background:transparent;color:var(--text3);font-family:'DM Sans',sans-serif;font-size:12px;font-weight:600;cursor:pointer;transition:all 0.2s;display:flex;align-items:center;justify-content:center;gap:6px;}
.tab-btn:hover{color:var(--text2);background:rgba(139,92,246,0.07);}
.tab-btn.active{color:#fff;background:rgba(139,92,246,0.14);border:1px solid var(--border2);box-shadow:0 2px 12px rgba(139,92,246,0.15);}
.tab-content{display:none;animation:fadeUp 0.3s ease both;}
.tab-content.active{display:block;}
.score-pill{display:inline-flex;align-items:center;justify-content:center;padding:2px 8px;border-radius:5px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;}
.sp-hi{background:rgba(239,68,68,0.12);color:#f87171;border:1px solid rgba(239,68,68,0.22);}
.sp-med{background:rgba(245,158,11,0.1);color:#fbbf24;border:1px solid rgba(245,158,11,0.22);}
.sp-lo{background:rgba(16,185,129,0.1);color:#34d399;border:1px solid rgba(16,185,129,0.22);}
.cst-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:600;letter-spacing:0.04em;}
.csb-active{background:rgba(16,185,129,0.1);color:#34d399;border:1px solid rgba(16,185,129,0.2);}
.csb-at_risk{background:rgba(245,158,11,0.1);color:#fbbf24;border:1px solid rgba(245,158,11,0.2);}
.csb-escalated{background:rgba(239,68,68,0.1);color:#f87171;border:1px solid rgba(239,68,68,0.2);}
.csb-resolved{background:rgba(139,92,246,0.1);color:#c4b5fd;border:1px solid rgba(139,92,246,0.2);}
.csb-flagged{background:rgba(244,114,182,0.1);color:#f9a8d4;border:1px solid rgba(244,114,182,0.2);}
.avatar{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;flex-shrink:0;}
.avatar-sm{width:26px;height:26px;border-radius:6px;font-size:9px;font-weight:700;color:#fff;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.av-purple{background:linear-gradient(135deg,#7c3aed,#a78bfa);box-shadow:0 2px 8px rgba(124,58,237,0.4);}
.av-pink{background:linear-gradient(135deg,#be185d,#f472b6);box-shadow:0 2px 8px rgba(190,24,93,0.4);}
.av-cyan{background:linear-gradient(135deg,#0891b2,#22d3ee);box-shadow:0 2px 8px rgba(8,145,178,0.4);}
.av-green{background:linear-gradient(135deg,#059669,#34d399);box-shadow:0 2px 8px rgba(5,150,105,0.4);}
.av-amber{background:linear-gradient(135deg,#b45309,#fbbf24);box-shadow:0 2px 8px rgba(180,83,9,0.4);}
.status-dot{width:7px;height:7px;border-radius:50%;display:inline-block;flex-shrink:0;}
.sd-active{background:#10b981;box-shadow:0 0 6px rgba(16,185,129,0.6);}
.sd-busy{background:#f59e0b;box-shadow:0 0 6px rgba(245,158,11,0.6);}
.sd-offline{background:#374151;}
.btn{padding:7px 14px;border:1px solid var(--border2);border-radius:7px;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:12px;font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:5px;transition:all 0.18s;background:rgba(139,92,246,0.07);color:var(--text2);}
.btn:hover{background:rgba(139,92,246,0.14);color:#fff;border-color:var(--purple);}
.btn-sm{padding:6px 12px;font-size:11px;}
.btn-xs{padding:3px 8px;font-size:10px;border-radius:5px;}
.btn-purple{background:rgba(139,92,246,0.14);border-color:var(--border2);color:var(--purple2);}
.btn-purple:hover{background:rgba(139,92,246,0.24);}
.btn-danger{background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.22);color:#f87171;}
.btn-green{background:rgba(16,185,129,0.08);border-color:rgba(16,185,129,0.22);color:#34d399;}
.btn-green:hover{background:rgba(16,185,129,0.16);}
.btn-reset{background:rgba(239,68,68,0.06);border-color:rgba(239,68,68,0.18);color:rgba(239,68,68,0.65);}
.btn-reset:hover{background:rgba(239,68,68,0.12);color:#ef4444;}
.act-btn{padding:4px 9px;border-radius:5px;border:1px solid;font-family:'DM Sans',sans-serif;font-size:10px;font-weight:600;cursor:pointer;transition:all 0.15s;white-space:nowrap;}
.ab-call{background:rgba(139,92,246,0.08);border-color:rgba(139,92,246,0.25);color:#a78bfa;}
.ab-call:hover{background:rgba(139,92,246,0.18);}
.ab-offer{background:rgba(16,185,129,0.08);border-color:rgba(16,185,129,0.25);color:#34d399;}
.ab-offer:hover{background:rgba(16,185,129,0.18);}
.ab-esc{background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.25);color:#f87171;}
.ab-esc:hover{background:rgba(239,68,68,0.18);}
.ab-res{background:rgba(34,211,238,0.08);border-color:rgba(34,211,238,0.25);color:#67e8f9;}
.ab-res:hover{background:rgba(34,211,238,0.18);}
.ab-done{opacity:0.35;pointer-events:none;}
.live-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#10b981;animation:dotBlink 1.8s ease infinite;flex-shrink:0;box-shadow:0 0 8px rgba(16,185,129,0.6);}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;}
.three-col{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;}
.chart-container{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;padding:18px;}
.chart-title{font-family:'Space Grotesk',sans-serif;font-size:13px;font-weight:700;color:#fff;margin-bottom:14px;display:flex;align-items:center;justify-content:space-between;}
.gauge-panel{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;padding:20px;text-align:center;}
.dd-table{width:100%;border-collapse:collapse;}
.dd-table th{font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--text3);padding:10px 15px;text-align:left;border-bottom:1px solid var(--border);background:rgba(139,92,246,0.02);}
.dd-table td{font-size:12px;color:var(--text2);padding:11px 15px;border-bottom:1px solid rgba(139,92,246,0.04);vertical-align:middle;}
.dd-table tr:hover td{background:rgba(139,92,246,0.04);}
.tag{display:inline-block;padding:2px 7px;border-radius:4px;font-size:9px;font-weight:700;letter-spacing:0.04em;}
.tag-red{background:rgba(239,68,68,0.12);color:#f87171;border:1px solid rgba(239,68,68,0.2);}
.tag-amber{background:rgba(245,158,11,0.1);color:#fbbf24;border:1px solid rgba(245,158,11,0.2);}
.tag-green{background:rgba(16,185,129,0.1);color:#34d399;border:1px solid rgba(16,185,129,0.2);}
.tag-purple{background:rgba(139,92,246,0.1);color:#c4b5fd;border:1px solid rgba(139,92,246,0.2);}
.chart-tooltip{position:fixed;background:rgba(13,13,21,0.98);border:1px solid var(--border2);border-radius:8px;padding:9px 13px;font-size:11px;pointer-events:none;opacity:0;transition:opacity 0.15s;z-index:9999;white-space:nowrap;color:#fff;}
.chart-tooltip.visible{opacity:1;}
.stat-bar-row{display:flex;align-items:center;gap:12px;margin-bottom:9px;}
.stat-bar-label{font-size:11px;color:var(--text2);min-width:160px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.stat-bar-track{flex:1;height:5px;background:rgba(139,92,246,0.07);border-radius:6px;overflow:hidden;}
.stat-bar-fill{height:5px;border-radius:6px;transition:width 0.9s cubic-bezier(0.4,0,0.2,1);}
.stat-bar-val{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;min-width:46px;text-align:right;}
.mini-bar-wrap{width:56px;height:3px;background:rgba(139,92,246,0.1);border-radius:4px;overflow:hidden;display:inline-block;vertical-align:middle;}
.mini-bar-fill{height:3px;border-radius:4px;}
.fbar{display:flex;gap:7px;align-items:flex-end;flex-wrap:wrap;background:var(--card-bg);border:1px solid var(--card-border);border-radius:10px;padding:13px 15px;margin-bottom:16px;}
.fbar label{font-size:9px;font-weight:700;letter-spacing:0.08em;color:var(--text3);display:block;margin-bottom:3px;text-transform:uppercase;}
select,input[type=text]{padding:7px 10px;background:rgba(139,92,246,0.05);border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:'DM Sans',sans-serif;font-size:12px;transition:all 0.18s;}
select:focus,input:focus{outline:none;border-color:var(--purple);background:rgba(139,92,246,0.1);}
select option{background:#111118;}
.alert-panel{position:fixed;top:calc(var(--ticker-h) + var(--nav-h));right:0;width:360px;background:rgba(9,9,16,0.99);border-left:1px solid var(--border2);height:calc(100vh - var(--ticker-h) - var(--nav-h));z-index:300;display:flex;flex-direction:column;transform:translateX(100%);transition:transform 0.3s cubic-bezier(0.32,0.72,0,1);}
.alert-panel.open{transform:translateX(0);box-shadow:-16px 0 60px rgba(0,0,0,0.7);}
.alert-hdr{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
.alert-list{flex:1;overflow-y:auto;padding:10px;}
.alert-item{padding:11px 13px;border-radius:10px;margin-bottom:7px;border:1px solid;cursor:pointer;transition:all 0.18s;}
.alert-item.critical{background:rgba(239,68,68,0.06);border-color:rgba(239,68,68,0.18);}
.alert-item.warning{background:rgba(245,158,11,0.06);border-color:rgba(245,158,11,0.18);}
.alert-item.info{background:rgba(34,211,238,0.05);border-color:rgba(34,211,238,0.15);}
.alert-item.success{background:rgba(16,185,129,0.06);border-color:rgba(16,185,129,0.18);}
.alert-item:hover{transform:translateX(-3px);}
.alert-title{font-size:12px;font-weight:600;color:#fff;margin-bottom:3px;}
.alert-sub{font-size:10px;color:var(--text3);}
.alert-time{font-size:9px;color:var(--text3);margin-top:5px;font-family:'JetBrains Mono',monospace;}
.alert-unread{width:6px;height:6px;border-radius:50%;background:#ef4444;flex-shrink:0;display:inline-block;margin-left:5px;box-shadow:0 0 6px rgba(239,68,68,0.6);}
.side-panel{position:fixed;top:0;right:0;width:440px;height:100vh;background:rgba(9,9,16,0.99);border-left:1px solid var(--border2);z-index:500;display:flex;flex-direction:column;transform:translateX(100%);transition:transform 0.32s cubic-bezier(0.32,0.72,0,1);backdrop-filter:blur(40px);}
.side-panel.open{transform:translateX(0);box-shadow:-24px 0 80px rgba(0,0,0,0.8);}
.side-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:499;display:none;opacity:0;transition:opacity 0.28s;}
.side-overlay.open{display:block;opacity:1;}
.sp-header{padding:16px 19px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
.sp-close{width:28px;height:28px;border-radius:6px;border:1px solid var(--border);background:transparent;color:var(--text3);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:13px;transition:all 0.15s;}
.sp-close:hover{background:rgba(239,68,68,0.1);color:#f87171;}
.sp-body{flex:1;overflow-y:auto;padding:17px 19px;}
.sp-kpi-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:14px;}
.sp-kpi{background:rgba(139,92,246,0.05);border:1px solid var(--border);border-radius:8px;padding:11px;text-align:center;}
.sp-kpi-label{font-size:9px;text-transform:uppercase;letter-spacing:0.08em;color:var(--text3);margin-bottom:3px;font-weight:600;}
.sp-kpi-val{font-family:'Space Grotesk',sans-serif;font-size:19px;font-weight:800;}
.action-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;}
.sp-action-btn{padding:10px 12px;border-radius:9px;border:1px solid;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;cursor:pointer;transition:all 0.2s;display:flex;align-items:center;gap:7px;}
.sp-action-btn:hover{transform:translateY(-1px);box-shadow:0 4px 16px rgba(0,0,0,0.3);}
.sab-purple{background:rgba(139,92,246,0.08);border-color:rgba(139,92,246,0.28);color:#c4b5fd;}
.sab-purple:hover{background:rgba(139,92,246,0.18);}
.sab-green{background:rgba(16,185,129,0.08);border-color:rgba(16,185,129,0.28);color:#34d399;}
.sab-green:hover{background:rgba(16,185,129,0.18);}
.sab-red{background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.28);color:#f87171;}
.sab-red:hover{background:rgba(239,68,68,0.18);}
.sab-pink{background:rgba(244,114,182,0.08);border-color:rgba(244,114,182,0.28);color:#f9a8d4;}
.sab-cyan{background:rgba(34,211,238,0.08);border-color:rgba(34,211,238,0.28);color:#67e8f9;}
.sab-amber{background:rgba(245,158,11,0.08);border-color:rgba(245,158,11,0.28);color:#fbbf24;}
.sab-done{opacity:0.35;pointer-events:none;}
.sp-sec-title{font-size:9px;text-transform:uppercase;letter-spacing:0.12em;color:var(--text3);font-weight:700;margin-bottom:10px;}
.pred-badge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700;}
.pred-high{background:rgba(239,68,68,0.12);color:#f87171;border:1px solid rgba(239,68,68,0.22);}
.pred-med{background:rgba(245,158,11,0.1);color:#fbbf24;border:1px solid rgba(245,158,11,0.22);}
.pred-low{background:rgba(16,185,129,0.1);color:#34d399;border:1px solid rgba(16,185,129,0.22);}
.bulk-bar{display:none;align-items:center;gap:10px;padding:11px 15px;background:rgba(139,92,246,0.12);border:1px solid var(--border2);border-radius:10px;margin-bottom:12px;}
.bulk-bar.visible{display:flex;}
.bulk-count{font-family:'Space Grotesk',sans-serif;font-size:13px;font-weight:700;color:#fff;}
.bulk-actions{display:flex;gap:5px;margin-left:auto;}
input[type=checkbox]{width:14px;height:14px;accent-color:var(--purple);cursor:pointer;border-radius:3px;}
tr.row-selected td{background:rgba(139,92,246,0.07) !important;}
.editable-field{cursor:pointer;border-radius:4px;padding:2px 5px;transition:background 0.15s;position:relative;}
.editable-field:hover{background:rgba(139,92,246,0.1);outline:1px dashed var(--border2);}
.inline-edit-input{padding:4px 8px;background:rgba(139,92,246,0.15);border:1px solid var(--purple);border-radius:5px;color:#fff;font-family:'DM Sans',sans-serif;font-size:12px;outline:none;width:100%;max-width:180px;}
.kanban-board{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;align-items:start;}
.kanban-col{background:rgba(139,92,246,0.02);border:1px solid var(--border);border-radius:12px;overflow:hidden;transition:border-color 0.2s;}
.kanban-col.drag-over{border-color:var(--purple);background:rgba(139,92,246,0.06);box-shadow:0 0 20px rgba(139,92,246,0.15);}
.kc-header{padding:12px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.kc-title{font-size:12px;font-weight:700;color:#fff;display:flex;align-items:center;gap:7px;}
.kc-count{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;padding:2px 7px;background:rgba(139,92,246,0.14);border-radius:4px;color:var(--purple2);}
.kc-body{padding:8px;display:flex;flex-direction:column;gap:6px;min-height:120px;max-height:600px;overflow-y:auto;}
.kanban-card{background:rgba(19,19,28,0.95);border:1px solid rgba(139,92,246,0.07);border-radius:9px;padding:11px 12px;cursor:grab;transition:all 0.22s;user-select:none;}
.kanban-card:active{cursor:grabbing;}
.kanban-card:hover{border-color:var(--border2);transform:translateY(-2px);box-shadow:0 6px 24px rgba(0,0,0,0.4);}
.kanban-card.dragging{opacity:0.4;transform:rotate(2deg) scale(0.98);}
.kcard-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}
.kcard-id{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;color:#fff;}
.kcard-body{font-size:10px;color:var(--text3);line-height:1.7;}
.kcard-actions{display:flex;gap:3px;margin-top:8px;flex-wrap:wrap;}
.kc-hi{border-left:2px solid #ef4444;}
.kc-med{border-left:2px solid #f59e0b;}
.kc-lo{border-left:2px solid #10b981;}
.drag-handle{cursor:grab;color:var(--text3);font-size:11px;padding:2px 4px;border-radius:3px;}
.task-card{background:rgba(139,92,246,0.03);border:1px solid var(--card-border);border-radius:11px;padding:14px 16px;margin-bottom:10px;transition:all 0.22s;position:relative;overflow:hidden;}
.task-card::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;border-radius:3px 0 0 3px;}
.task-card.tc-open::before{background:#f59e0b;}
.task-card.tc-inprogress::before{background:#a78bfa;}
.task-card.tc-done::before{background:#10b981;}
.task-card.tc-overdue::before{background:#ef4444;}
.task-card:hover{border-color:var(--border2);}
.task-header{display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;}
.task-title{font-size:13px;font-weight:700;color:#fff;flex:1;}
.task-title.done-title{text-decoration:line-through;color:var(--text3);}
.task-meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;}
.task-meta-item{font-size:10px;color:var(--text3);display:flex;align-items:center;gap:4px;}
.task-priority{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;}
.tp-critical{background:rgba(239,68,68,0.12);color:#f87171;border:1px solid rgba(239,68,68,0.22);}
.tp-high{background:rgba(245,158,11,0.1);color:#fbbf24;border:1px solid rgba(245,158,11,0.22);}
.tp-normal{background:rgba(139,92,246,0.1);color:#c4b5fd;border:1px solid rgba(139,92,246,0.2);}
.task-progress-bar{height:4px;background:rgba(139,92,246,0.08);border-radius:4px;overflow:hidden;margin-top:8px;}
.task-progress-fill{height:4px;border-radius:4px;transition:width 0.6s ease;}
.task-actions{display:flex;gap:6px;margin-top:10px;border-top:1px solid rgba(139,92,246,0.06);padding-top:10px;}
.task-notes{font-size:11px;color:var(--text3);background:rgba(139,92,246,0.04);border:1px solid var(--border);border-radius:6px;padding:8px 10px;margin-top:8px;line-height:1.6;}
.task-status-badge{padding:3px 9px;border-radius:5px;font-size:9px;font-weight:700;letter-spacing:0.06em;}
.tsb-open{background:rgba(245,158,11,0.1);color:#fbbf24;border:1px solid rgba(245,158,11,0.2);}
.tsb-inprogress{background:rgba(139,92,246,0.1);color:#c4b5fd;border:1px solid rgba(139,92,246,0.2);}
.tsb-done{background:rgba(16,185,129,0.1);color:#34d399;border:1px solid rgba(16,185,129,0.2);}
.tsb-overdue{background:rgba(239,68,68,0.1);color:#f87171;border:1px solid rgba(239,68,68,0.2);}
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:600;display:none;align-items:center;justify-content:center;}
.modal-overlay.open{display:flex;}
.modal-box{background:rgba(13,13,21,0.99);border:1px solid var(--border2);border-radius:16px;padding:24px;width:480px;max-width:95vw;box-shadow:0 32px 80px rgba(0,0,0,0.8);animation:slideDown 0.28s ease;}
.modal-title{font-family:'Space Grotesk',sans-serif;font-size:15px;font-weight:700;color:#fff;margin-bottom:18px;display:flex;align-items:center;gap:9px;}
.modal-field{margin-bottom:14px;}
.modal-label{font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--text3);margin-bottom:5px;display:block;}
.modal-input{width:100%;padding:10px 12px;background:rgba(139,92,246,0.07);border:1px solid var(--border);border-radius:8px;color:#fff;font-family:'DM Sans',sans-serif;font-size:13px;transition:border-color 0.18s;outline:none;}
.modal-input:focus{border-color:var(--purple);background:rgba(139,92,246,0.12);}
textarea.modal-input{resize:vertical;min-height:72px;}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:20px;}
.alog-item{display:flex;align-items:flex-start;gap:10px;padding:10px 15px;border-bottom:1px solid rgba(139,92,246,0.04);}
.alog-icon{width:28px;height:28px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0;}
.alog-body{flex:1;}
.alog-title{font-size:12px;font-weight:600;color:var(--text2);}
.alog-sub{font-size:10px;color:var(--text3);margin-top:2px;}
.alog-ts{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text3);flex-shrink:0;}
.lb-row{display:flex;align-items:center;gap:11px;padding:11px 15px;border-bottom:1px solid rgba(139,92,246,0.04);cursor:pointer;transition:background 0.15s;}
.lb-row:hover{background:rgba(139,92,246,0.05);}
.lb-rank{font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:800;min-width:32px;text-align:center;}
.lb-bar{flex:1;height:5px;background:rgba(139,92,246,0.07);border-radius:4px;overflow:hidden;}
.lb-bar-fill{height:5px;border-radius:4px;transition:width 1s ease;}
.tl-row-inner{display:grid;grid-template-columns:230px 90px 140px 80px 80px 100px 80px 40px;align-items:center;padding:11px 15px;border-bottom:1px solid rgba(139,92,246,0.05);cursor:pointer;transition:background 0.15s;}
.tl-row-inner:hover{background:rgba(139,92,246,0.04);}
.agent-rows-wrap{display:none;background:rgba(139,92,246,0.02);border-bottom:1px solid rgba(139,92,246,0.06);}
.agent-rows-wrap.open{display:block;}
.agent-row-inner{display:grid;grid-template-columns:230px 90px 140px 80px 80px 100px 80px 40px;align-items:center;padding:8px 15px 8px 38px;border-bottom:1px solid rgba(139,92,246,0.03);cursor:pointer;transition:background 0.15s;}
.agent-row-inner:hover{background:rgba(139,92,246,0.05);}
.expand-chevron{width:17px;height:17px;border-radius:4px;display:inline-flex;align-items:center;justify-content:center;font-size:9px;color:var(--text3);background:rgba(139,92,246,0.08);transition:transform 0.22s,background 0.15s;flex-shrink:0;margin-right:5px;}
.tl-row.open .expand-chevron{transform:rotate(90deg);background:rgba(139,92,246,0.18);color:var(--purple2);}
.indent-line{display:inline-flex;align-items:center;gap:8px;}
.indent-line::before{content:'';display:inline-block;width:1px;height:22px;background:rgba(139,92,246,0.22);flex-shrink:0;}
.ai-chat-fab{position:fixed;bottom:28px;right:28px;z-index:400;width:52px;height:52px;border-radius:14px;background:linear-gradient(135deg,#7c3aed,#a78bfa,#f472b6);background-size:200% 200%;animation:gradShift 4s ease infinite;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 8px 32px rgba(124,58,237,0.5);transition:all 0.22s;}
.ai-chat-fab:hover{transform:scale(1.08);}
.ai-chat-panel{position:fixed;bottom:92px;right:28px;width:380px;z-index:400;background:rgba(9,9,16,0.99);border:1px solid var(--border2);border-radius:16px;box-shadow:0 24px 80px rgba(0,0,0,0.8);display:none;flex-direction:column;overflow:hidden;}
.ai-chat-panel.open{display:flex;}
.ai-chat-hdr{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;flex-shrink:0;}
.ai-chat-msgs{flex:1;max-height:320px;overflow-y:auto;padding:12px;}
.ai-msg{padding:9px 12px;border-radius:10px;margin-bottom:8px;font-size:12px;line-height:1.6;max-width:86%;}
.ai-msg.bot{background:rgba(139,92,246,0.1);border:1px solid rgba(139,92,246,0.16);color:var(--text2);margin-right:auto;border-radius:10px 10px 10px 2px;}
.ai-msg.user{background:rgba(139,92,246,0.2);border:1px solid rgba(139,92,246,0.3);color:#fff;margin-left:auto;border-radius:10px 10px 2px 10px;}
.ai-typing span{width:6px;height:6px;border-radius:50%;background:var(--purple2);animation:dotBlink 1.2s ease infinite;display:inline-block;margin:0 2px;}
.ai-typing span:nth-child(2){animation-delay:0.2s;}
.ai-typing span:nth-child(3){animation-delay:0.4s;}
.ai-chat-footer{padding:10px 12px;border-top:1px solid var(--border);display:flex;gap:8px;flex-shrink:0;}
.ai-chat-input{flex:1;padding:8px 12px;background:rgba(139,92,246,0.07);border:1px solid var(--border);border-radius:8px;color:var(--text);font-family:'DM Sans',sans-serif;font-size:12px;resize:none;outline:none;}
.ai-chat-input:focus{border-color:var(--purple);}
.ai-chat-send{padding:8px 14px;background:rgba(139,92,246,0.2);border:1px solid var(--border2);border-radius:8px;color:var(--purple2);font-size:12px;font-weight:700;cursor:pointer;}
.ai-quick-btns{padding:0 12px 10px;display:flex;gap:5px;flex-wrap:wrap;}
.ai-quick-btn{padding:3px 9px;border-radius:5px;background:rgba(139,92,246,0.08);border:1px solid var(--border);color:var(--text3);font-size:10px;cursor:pointer;transition:all 0.15s;}
.ai-quick-btn:hover{background:rgba(139,92,246,0.16);color:var(--purple2);}
.reveal{opacity:0;transform:translateY(14px);transition:opacity 0.48s ease,transform 0.48s ease;}
.reveal.visible{opacity:1;transform:none;}
.live-badge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-size:9px;font-weight:700;background:rgba(16,185,129,0.1);color:#34d399;border:1px solid rgba(16,185,129,0.2);}
.wl-cell{border-radius:5px;height:36px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;cursor:pointer;transition:all 0.18s;}
.wl-cell:hover{transform:scale(1.1);}

/* ================= LIGHT THEME (dashboard page only) ================= */
body.light-theme{
  --bg:#f3f1fa;--bg2:#ffffff;--bg3:#efecf9;--bg4:#e7e1f5;
  --border:rgba(124,58,237,0.14);--border2:rgba(124,58,237,0.28);--border3:rgba(124,58,237,0.45);
  --text:#241f38;--text2:rgba(38,28,68,0.72);--text3:rgba(58,42,98,0.48);
  --card-bg:rgba(124,58,237,0.045);--card-border:rgba(124,58,237,0.16);
}
body.light-theme{background:var(--bg);color:var(--text);}
body.light-theme .topnav{background:rgba(255,255,255,0.97);border-bottom-color:var(--border);}
body.light-theme .churn-ticker-bar{background:linear-gradient(90deg,rgba(239,68,68,0.10),rgba(239,68,68,0.05) 50%,rgba(239,68,68,0.10));border-bottom-color:rgba(239,68,68,0.22);}
body.light-theme .ticker-item{color:rgba(38,28,68,0.62);border-right-color:rgba(239,68,68,0.16);}
body.light-theme .nav-user{background:rgba(124,58,237,0.07);}
body.light-theme .nav-bell{border-color:var(--border);color:var(--text3);}
body.light-theme .nav-bell:hover{background:rgba(124,58,237,0.1);}
body.light-theme .kpi-card,body.light-theme .card-panel,body.light-theme .chart-container,body.light-theme .gauge-panel{background:var(--card-bg);border-color:var(--card-border);}
body.light-theme .card-panel-hdr{background:rgba(124,58,237,0.035);border-bottom-color:rgba(124,58,237,0.09);}
body.light-theme .dd-table th{background:rgba(124,58,237,0.045);color:var(--text3);border-bottom-color:var(--border);}
body.light-theme .dd-table td{color:var(--text2);border-bottom-color:rgba(124,58,237,0.08);}
body.light-theme .dd-table tr:hover td{background:rgba(124,58,237,0.07);}
body.light-theme .tab-bar{background:rgba(124,58,237,0.05);border-color:var(--border);}
body.light-theme .tab-btn{color:var(--text3);}
body.light-theme .tab-btn.active{color:#2c1a5c;background:rgba(124,58,237,0.16);}
body.light-theme select,body.light-theme input[type=text]{background:rgba(124,58,237,0.05);border-color:var(--border);color:var(--text);}
body.light-theme select option{background:#ffffff;color:#241f38;}
body.light-theme .alert-panel{background:rgba(255,255,255,0.98);border-left-color:var(--border2);}
body.light-theme .side-panel{background:rgba(255,255,255,0.99);border-left-color:var(--border2);}
body.light-theme .modal-box{background:#ffffff;border-color:var(--border2);}
body.light-theme .ai-chat-panel{background:#ffffff;border-color:var(--border2);}
body.light-theme .toast-item{background:#ffffff;border-color:var(--border2);box-shadow:0 8px 30px rgba(80,60,140,0.18);}
body.light-theme .kanban-card{background:#ffffff;border-color:rgba(124,58,237,0.12);}
body.light-theme .kanban-col{background:rgba(124,58,237,0.025);border-color:var(--border);}
body.light-theme .task-card{background:#ffffff;border-color:var(--card-border);}
body.light-theme .task-notes{background:rgba(124,58,237,0.05);border-color:var(--border);color:var(--text3);}
body.light-theme .chart-tooltip{background:#ffffff;border-color:var(--border2);color:#241f38;box-shadow:0 8px 24px rgba(80,60,140,0.2);}
body.light-theme .sp-kpi{background:rgba(124,58,237,0.05);border-color:var(--border);}
body.light-theme .brand{color:#241f38;}
body.light-theme .nlogout{color:rgba(220,38,38,0.65);}
body.light-theme .stat-bar-track,body.light-theme .lb-bar,body.light-theme .task-progress-bar,body.light-theme .mini-bar-wrap{background:rgba(124,58,237,0.09);}
body.light-theme .agent-rows-wrap{background:rgba(124,58,237,0.025);}
body.light-theme .expand-chevron{background:rgba(124,58,237,0.09);color:var(--text3);}
body.light-theme .ai-msg.bot{background:rgba(124,58,237,0.08);border-color:rgba(124,58,237,0.14);color:var(--text2);}
body.light-theme .ai-chat-input{background:rgba(124,58,237,0.05);border-color:var(--border);color:var(--text);}
body.light-theme .lb-row:hover{background:rgba(124,58,237,0.06);}
body.light-theme ::-webkit-scrollbar-thumb{background:rgba(124,58,237,0.28);}
body.light-theme .kpi-val,body.light-theme .cph-title,body.light-theme .alert-title,body.light-theme .chart-title,
body.light-theme .modal-title,body.light-theme .task-title,body.light-theme .kcard-id,body.light-theme .kc-title{color:#241f38;}
body.light-theme [style*="color:#fff"]{color:#241f38 !important;}
body.light-theme [style*="color: #fff"]{color:#241f38 !important;}
</style>
"""

LOGIN_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>NeuralRetain v5 - Login</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;800&family=DM+Sans:wght@400;500;600&display=swap');
:root{--bg:#07070d;--purple:#8b5cf6;}
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--bg);font-family:'DM Sans',sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;color:#e8deff;overflow:hidden;}
canvas{position:fixed;inset:0;pointer-events:none;z-index:0;}
.wrap{width:420px;position:relative;z-index:2;}
.card{background:rgba(139,92,246,0.04);border:1px solid rgba(139,92,246,0.14);border-radius:20px;overflow:hidden;box-shadow:0 0 120px rgba(139,92,246,0.07),0 32px 80px rgba(0,0,0,0.8);}
.card-top{padding:32px 32px 26px;border-bottom:1px solid rgba(139,92,246,0.09);}
.card-bot{padding:26px 32px 32px;}
.brand{font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:800;color:#fff;margin-bottom:4px;display:flex;align-items:center;gap:10px;}
.brand-orb{width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,#7c3aed,#a78bfa,#f472b6);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:#fff;background-size:200% 200%;animation:grad 4s ease infinite;}
@keyframes grad{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.sub{font-size:11px;color:rgba(170,150,230,0.3);margin-top:3px;}
.features{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:16px;}
.feature-chip{padding:7px 10px;background:rgba(139,92,246,0.04);border:1px solid rgba(139,92,246,0.09);border-radius:7px;font-size:10px;color:rgba(170,150,230,0.35);display:flex;align-items:center;gap:5px;}
.feature-chip.new{border-color:rgba(34,211,238,0.2);color:rgba(103,232,249,0.6);}
.flabel{font-size:9px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(170,150,230,0.3);margin-bottom:6px;margin-top:16px;display:block;}
.linput{width:100%;padding:11px 14px;background:rgba(139,92,246,0.05);border:1px solid rgba(139,92,246,0.13);border-radius:8px;color:#e8deff;font-family:'DM Sans',sans-serif;font-size:13px;transition:all 0.2s;}
.linput:focus{outline:none;border-color:rgba(139,92,246,0.42);background:rgba(139,92,246,0.09);}
.linput::placeholder{color:rgba(170,150,230,0.18);}
.lbtn{width:100%;padding:12px;margin-top:20px;background:rgba(139,92,246,0.14);border:1px solid rgba(139,92,246,0.3);border-radius:9px;color:rgba(228,210,255,0.9);font-family:'DM Sans',sans-serif;font-size:13px;font-weight:700;cursor:pointer;transition:all 0.24s;}
.lbtn:hover{background:rgba(139,92,246,0.26);color:#fff;transform:translateY(-1px);}
.lerr{background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.2);border-radius:7px;padding:9px 12px;font-size:12px;color:#f87171;margin-bottom:12px;}
.demo-hint{margin-top:14px;font-size:10px;color:rgba(170,150,230,0.16);text-align:center;}
.demo-hint b{color:rgba(170,150,230,0.38);}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div class="wrap">
  <div class="card">
    <div class="card-top">
      <div class="brand"><div class="brand-orb">NR</div>NeuralRetain <span style="font-size:11px;font-weight:400;color:rgba(170,150,230,0.3);margin-left:2px;">v5</span></div>
      <div class="sub">Telco Churn Intelligence Platform</div>
      <div class="features">
        <div class="feature-chip new">Drag-and-Drop Kanban</div>
        <div class="feature-chip new">Bulk Select + Mass Actions</div>
        <div class="feature-chip new">Inline Field Editing</div>
        <div class="feature-chip new">Live Score Simulation</div>
        <div class="feature-chip new">Task Assignment Tracker</div>
        <div class="feature-chip">AI Chat Assistant</div>
        <div class="feature-chip">Smart Alerts</div>
        <div class="feature-chip">Team Hierarchy View</div>
      </div>
    </div>
    <div class="card-bot">
      __ERR__
      <form method="POST" action="/login">
        <span class="flabel">Username</span>
        <input class="linput" type="text" name="username" placeholder="dev" autocomplete="off" required>
        <span class="flabel">Password</span>
        <input class="linput" type="password" name="password" placeholder="password" required>
        <button class="lbtn" type="submit">Access Platform</button>
      </form>
      <div class="demo-hint">credentials: <b>dev</b> / <b>devi2005</b></div>
    </div>
  </div>
</div>
<script>
(function(){
  var c=document.getElementById('c'),ctx=c.getContext('2d'),W,H,bubbles=[];
  function sz(){W=c.width=innerWidth;H=c.height=innerHeight;}
  addEventListener('resize',sz);sz();
  var colorPairs=[[139,92,246],[167,139,250],[244,114,182],[196,181,253]];
  function makeBubble(){
    var col=colorPairs[Math.floor(Math.random()*colorPairs.length)];
    return {
      x:Math.random()*W,
      y:H+Math.random()*H*0.5+20,
      r:Math.random()*46+14,
      speed:Math.random()*0.55+0.15,
      drift:(Math.random()-0.5)*0.4,
      a:Math.random()*0.22+0.06,
      col:col,
      wobble:Math.random()*Math.PI*2,
      wobbleSpeed:Math.random()*0.02+0.005
    };
  }
  var count=32;
  for(var i=0;i<count;i++){
    var b=makeBubble();
    b.y=Math.random()*H;
    bubbles.push(b);
  }
  function draw(){
    ctx.clearRect(0,0,W,H);
    bubbles.forEach(function(b){
      b.y-=b.speed;
      b.wobble+=b.wobbleSpeed;
      b.x+=Math.sin(b.wobble)*b.drift;
      if(b.y<-b.r-20){
        var nb=makeBubble();
        b.x=nb.x;b.y=H+b.r+20;b.r=nb.r;b.speed=nb.speed;b.drift=nb.drift;b.a=nb.a;b.col=nb.col;b.wobble=nb.wobble;b.wobbleSpeed=nb.wobbleSpeed;
      }
      var grad=ctx.createRadialGradient(b.x,b.y,0,b.x,b.y,b.r);
      grad.addColorStop(0,'rgba('+b.col[0]+','+b.col[1]+','+b.col[2]+','+(b.a*1.4).toFixed(3)+')');
      grad.addColorStop(0.6,'rgba('+b.col[0]+','+b.col[1]+','+b.col[2]+','+(b.a*0.5).toFixed(3)+')');
      grad.addColorStop(1,'rgba('+b.col[0]+','+b.col[1]+','+b.col[2]+',0)');
      ctx.beginPath();
      ctx.arc(b.x,b.y,b.r,0,Math.PI*2);
      ctx.fillStyle=grad;
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }
  draw();
})();
</script>
</body>
</html>"""

@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect("/dashboard")
    return render_template_string(LOGIN_PAGE.replace("__ERR__", ""))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    if username == "dev" and password == "devi2005":
        session["logged_in"] = True
        session["user"] = "Dev"
        return redirect("/dashboard")
    err_html = '<div class="lerr">Invalid username or password.</div>'
    return render_template_string(LOGIN_PAGE.replace("__ERR__", err_html))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

def build_live_ticker(kp, df):
    high_risk = int((df["ChurnScore"]>=70).sum())
    escalated = int((df["CustStatus"]=="escalated").sum())
    top_cat_s = df[df["ChurnLabel"]=="Yes"]["ChurnCategory"].value_counts()
    top_cat   = top_cat_s.idxmax() if len(top_cat_s)>0 else "N/A"
    sat_color = "good" if kp["avg_sat"]>=3.5 else "warn" if kp["avg_sat"]>=2.5 else "danger"
    items = [
        '<span class="ticker-item"><span style="width:5px;height:5px;border-radius:50%;background:#ef4444;display:inline-block;"></span>CHURN RATE <span class="ti-val danger">' + str(kp["rate"]) + '%</span></span>',
        '<span class="ticker-item">CHURNED <span class="ti-val danger">' + str(kp["churned"]) + '</span> / ' + str(kp["total"]) + '</span>',
        '<span class="ticker-item">REVENUE AT RISK <span class="ti-val warn">' + fmt_money(kp["rev_loss"]) + '/mo</span></span>',
        '<span class="ticker-item">HIGH-RISK <span class="ti-val danger">' + str(high_risk) + '</span></span>',
        '<span class="ticker-item">ESCALATED <span class="ti-val danger">' + str(escalated) + '</span></span>',
        '<span class="ticker-item">TOP CAUSE <span class="ti-val warn">' + str(top_cat) + '</span></span>',
        '<span class="ticker-item">AVG SAT <span class="ti-val ' + sat_color + '">' + str(kp["avg_sat"]) + '/5</span></span>',
        '<span class="ticker-item">AVG SCORE <span class="ti-val danger">' + str(kp["avg_score"]) + '</span>/100</span>',
        '<span class="ticker-item">RETAINED <span class="ti-val good">' + str(kp["retained"]) + '</span></span>',
        '<span class="ticker-item">AVG CLTV <span class="ti-val warn">' + fmt_money(kp["avg_cltv"]) + '</span></span>',
    ]
    return ('<div class="churn-ticker-bar"><div class="ticker-badge"><div class="ticker-live-dot"></div>LIVE</div>'
            '<div class="ticker-track"><div class="ticker-inner">' + "".join(items)*2 + '</div></div></div>')

def nav(active):
    unread = sum(1 for a in alert_store if not a["read"])
    pages=[("d","/dashboard","Dashboard"),("t","/team","Team View"),("c","/customers","Customers"),("a","/actions","Action Log"),("i","/insights","Insights")]
    tabs="".join('<a href="{}" class="ntab {}">{}</a>'.format(u, "active" if k==active else "", lb) for k,u,lb in pages)
    bell_badge = '<span class="nav-bell-badge">{}</span>'.format(unread) if unread>0 else ''
    theme_btn = '<button class="nav-bell" id="themeToggleBtn" onclick="toggleTheme()" title="Toggle light / dark theme">&#9728;</button>' if active=="d" else ''
    return (
        '<nav class="topnav">'
        '<a href="/dashboard" class="brand"><div class="brand-orb">NR</div>NeuralRetain <span style="font-size:10px;font-weight:400;color:var(--text3);margin-left:3px;">v5</span></a>'
        '<div class="ntabs">' + tabs + '</div>'
        '<div class="nav-right">'
        + theme_btn +
        '<button class="nav-bell" onclick="toggleAlerts()" title="Alerts">&#128276;' + bell_badge + '</button>'
        '<div class="nav-user"><div class="nav-avatar">DV</div><div><div class="nav-uname">Dev</div><div class="nav-role">Senior Manager</div></div></div>'
        '<a href="/logout" class="nlogout">Logout</a>'
        '</div></nav>'
    )

def build_alert_panel():
    items_html=""
    for al in alert_store:
        dot = '<span class="alert-unread"></span>' if not al["read"] else ''
        items_html += (
            '<div class="alert-item {}" onclick="markAlertRead(\'{}\')">'.format(al["type"], al["id"])
            + '<div class="alert-title">{} {} {}</div>'.format(al["icon"], al["title"], dot)
            + '<div class="alert-sub">{}</div>'.format(al["sub"])
            + '<div class="alert-time">{}</div></div>'.format(al["time"])
        )
    unread = sum(1 for a in alert_store if not a["read"])
    return (
        '<div class="alert-panel" id="alertPanel">'
        '<div class="alert-hdr"><span style="font-family:Space Grotesk,sans-serif;font-size:13px;font-weight:700;color:#fff;">Alerts '
        '<span class="tag tag-red" style="margin-left:6px;">{} new</span></span>'.format(unread)
        + '<button style="background:transparent;border:none;color:var(--text3);cursor:pointer;font-size:13px;" onclick="toggleAlerts()">&#x2715;</button></div>'
        '<div class="alert-list" id="alertList">' + items_html + '</div></div>'
    )

def build_ai_chat():
    return """
<button class="ai-chat-fab" onclick="toggleAiChat()" title="AI Assistant">&#129302;</button>
<div class="ai-chat-panel" id="aiChatPanel">
  <div class="ai-chat-hdr">
    <div style="width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,#7c3aed,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:12px;">&#129302;</div>
    <div><div style="font-family:Space Grotesk,sans-serif;font-size:12px;font-weight:700;color:#fff;">NeuralRetain AI</div>
    <div style="font-size:10px;color:var(--text3);">Churn Intelligence &middot; Always On</div></div>
    <div style="margin-left:auto;display:flex;align-items:center;gap:4px;font-size:10px;color:#34d399;"><div class="live-dot"></div>Online</div>
  </div>
  <div class="ai-chat-msgs" id="aiMsgs">
    <div class="ai-msg bot">Hello Dev! I am your Churn AI. I can analyse patterns, assign tasks, explain risk scores, and suggest actions. What do you need?</div>
  </div>
  <div class="ai-quick-btns">
    <button class="ai-quick-btn" onclick="askAI('What is the main churn driver?')">Main driver?</button>
    <button class="ai-quick-btn" onclick="askAI('Which team needs attention?')">Team alerts?</button>
    <button class="ai-quick-btn" onclick="askAI('Best retention strategy?')">Retention tips</button>
    <button class="ai-quick-btn" onclick="askAI('Assign tasks to agents')">Assign tasks</button>
  </div>
  <div class="ai-chat-footer">
    <input type="text" class="ai-chat-input" id="aiInput" placeholder="Ask anything about churn..." onkeydown="if(event.key==='Enter'){event.preventDefault();sendAI();}">
    <button class="ai-chat-send" onclick="sendAI()">Send</button>
  </div>
</div>
"""

def build_task_modal():
    agent_opts = "".join(
        '<option value="{}">{} ({} Team)</option>'.format(a["id"], a["name"], TL_MAP.get(a["tl"],{}).get("team","?"))
        for a in TEAM_DATA["agents"]
    )
    return """
<div class="modal-overlay" id="taskModal">
  <div class="modal-box">
    <div class="modal-title">&#128203; Assign New Task</div>
    <div class="modal-field">
      <label class="modal-label">Task Title</label>
      <input type="text" class="modal-input" id="taskTitle" placeholder="e.g. Call high-risk customers">
    </div>
    <div class="modal-field">
      <label class="modal-label">Assign To</label>
      <select class="modal-input" id="taskAgent">""" + agent_opts + """</select>
    </div>
    <div class="modal-field">
      <label class="modal-label">Priority</label>
      <select class="modal-input" id="taskPriority">
        <option value="critical">Critical</option>
        <option value="high" selected>High</option>
        <option value="normal">Normal</option>
      </select>
    </div>
    <div class="modal-field">
      <label class="modal-label">Due Date</label>
      <input type="date" class="modal-input" id="taskDue">
    </div>
    <div class="modal-field">
      <label class="modal-label">Customer IDs (comma-separated, optional)</label>
      <input type="text" class="modal-input" id="taskCustomers" placeholder="CX-1001, CX-1002...">
    </div>
    <div class="modal-field">
      <label class="modal-label">Notes</label>
      <textarea class="modal-input" id="taskNotes" placeholder="Add context or instructions..."></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn" onclick="closeTaskModal()">Cancel</button>
      <button class="btn btn-purple" onclick="submitTask()">Assign Task</button>
    </div>
  </div>
</div>"""

# ── GLOBAL JS — FIX: use data attributes for JSON, no repr() in onclick ──
GLOBAL_JS = """
<script>
// ── TOAST ──────────────────────────────────────────────────────────────
var _tc = 0;
function showToast(title, sub, type) {
  var stack = document.getElementById('toastStack');
  if (!stack) return;
  var cls = type ? 't-' + type : '';
  var id = 't' + (++_tc);
  var el = document.createElement('div');
  el.className = 'toast-item ' + cls;
  el.id = id;
  el.innerHTML = '<span class="toast-icon">&#9670;</span><div class="toast-body"><div class="toast-title">' + title + '</div>' + (sub ? '<div class="toast-sub">' + sub + '</div>' : '') + '</div>';
  stack.appendChild(el);
  setTimeout(function() {
    var t = document.getElementById(id);
    if (t) { t.classList.add('t-out'); setTimeout(function() { if (t.parentNode) t.parentNode.removeChild(t); }, 240); }
  }, 3600);
}

// ── CHART TOOLTIP ──────────────────────────────────────────────────────
function showChartTip(evt, msg) {
  var t = document.getElementById('chartTip');
  if (!t) { t = document.createElement('div'); t.id = 'chartTip'; t.className = 'chart-tooltip'; document.body.appendChild(t); }
  t.textContent = msg; t.classList.add('visible');
  t.style.left = (evt.clientX + 14) + 'px'; t.style.top = (evt.clientY - 38) + 'px';
}
function hideChartTip() { var t = document.getElementById('chartTip'); if (t) t.classList.remove('visible'); }

// ── CUSTOMER ACTION ────────────────────────────────────────────────────
function doCustomerAction(cid, action, btnEl) {
  if (btnEl) { btnEl.disabled = true; btnEl.style.opacity = '0.5'; btnEl.textContent = '...'; }
  fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({customer_id:cid, action:action})})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        showToast(action.split(' ').slice(0,3).join(' '), 'Applied to ' + cid, 'green');
        if (btnEl) { btnEl.textContent = 'Done'; btnEl.classList.add('ab-done'); }
      }
    }).catch(function(e) { console.error(e); });
}

// ── ALERTS ─────────────────────────────────────────────────────────────
function toggleAlerts() { document.getElementById('alertPanel').classList.toggle('open'); }
function markAlertRead(id) { fetch('/api/alert_read/' + id).catch(function(){}); }

// ── SIDE PANEL ─────────────────────────────────────────────────────────
// FIX: Read JSON from data attribute to avoid quote-escaping bugs
function openSidePanelFromEl(el, type) {
  var raw = el.getAttribute('data-json');
  if (!raw) return;
  var data;
  try { data = JSON.parse(raw); } catch(e) { console.error('JSON parse error:', e, raw); return; }
  var panel = document.getElementById('sidePanel');
  var overlay = document.getElementById('sideOverlay');
  buildSidePanelContent(data, type, document.getElementById('spTitle'), document.getElementById('spBody'));
  panel.classList.add('open'); overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeSidePanel() {
  var p = document.getElementById('sidePanel'), o = document.getElementById('sideOverlay');
  if (p) p.classList.remove('open'); if (o) o.classList.remove('open');
  document.body.style.overflow = '';
}

// FIX: spAction uses data-cid attribute from button, not inline JSON
function spAction(btn, cid, action) {
  btn.disabled = true; btn.style.opacity = '0.5'; btn.textContent = '...';
  fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({customer_id:cid, action:action})})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        btn.textContent = 'Done'; btn.classList.add('sab-done');
        var log = document.getElementById('spActionLog');
        if (log) {
          if (log.textContent === 'No actions yet.') log.innerHTML = '';
          var item = document.createElement('div');
          item.style.cssText = 'font-size:11px;color:#34d399;padding:4px 0;border-bottom:1px solid rgba(139,92,246,0.06);display:flex;gap:8px;';
          item.innerHTML = '<span>&#10003;</span><span>' + action + '</span><span style="margin-left:auto;color:var(--text3);">' + new Date().toLocaleTimeString() + '</span>';
          log.insertBefore(item, log.firstChild);
        }
        showToast(action, 'Applied to ' + cid, 'green');
      }
    }).catch(function(e){ console.error(e); });
}

function buildSidePanelContent(data, type, titleEl, bodyEl) {
  if (type === 'customer') {
    var sc = parseFloat(data.score) || 0;
    var scClr = sc >= 70 ? '#ef4444' : sc >= 40 ? '#fbbf24' : '#34d399';
    var statusMap = {active:'csb-active', at_risk:'csb-at_risk', escalated:'csb-escalated', resolved:'csb-resolved', flagged:'csb-flagged'};
    var stClass = statusMap[data.status] || 'csb-active';
    var R = 28, circ = 2 * Math.PI * R, offset = circ * (1 - sc / 100);
    var predCls = sc >= 70 ? 'pred-high' : sc >= 40 ? 'pred-med' : 'pred-low';
    var predLbl = sc >= 70 ? 'HIGH RISK' : sc >= 40 ? 'MEDIUM RISK' : 'LOW RISK';
    var statusLabel = (data.status || '').replace(/_/g, ' ').toUpperCase();
    var cid = data.id;
    titleEl.innerHTML = '<span style="font-family:JetBrains Mono,monospace;font-size:13px;font-weight:700;color:#fff;">' + cid + '</span>';
    bodyEl.innerHTML =
      '<div style="display:flex;align-items:center;gap:13px;padding:14px;background:rgba(139,92,246,0.05);border:1px solid var(--border);border-radius:11px;margin-bottom:14px;">'
      + '<svg width="68" height="68" viewBox="0 0 68 68"><circle cx="34" cy="34" r="' + R + '" fill="none" stroke="rgba(139,92,246,0.12)" stroke-width="5.5"/>'
      + '<circle cx="34" cy="34" r="' + R + '" fill="none" stroke="' + scClr + '" stroke-width="5.5" stroke-linecap="round" stroke-dasharray="' + circ.toFixed(1) + '" stroke-dashoffset="' + offset.toFixed(1) + '" transform="rotate(-90 34 34)"/>'
      + '<text x="34" y="34" text-anchor="middle" dominant-baseline="middle" font-family="Space Grotesk,sans-serif" font-size="14" font-weight="800" fill="' + scClr + '">' + sc.toFixed(0) + '</text></svg>'
      + '<div><div style="font-size:15px;font-weight:800;color:#fff;font-family:Space Grotesk,sans-serif;margin-bottom:5px;">' + cid + '</div>'
      + '<span class="cst-badge ' + stClass + '">' + statusLabel + '</span>'
      + ' <span class="pred-badge ' + predCls + '">' + predLbl + '</span>'
      + '<div style="font-size:10px;color:var(--text3);margin-top:5px;">' + (data.contract||'') + ' &middot; ' + (data.internet||'') + '</div>'
      + '<div style="font-size:10px;color:var(--text3);">' + (data.city||'') + ' &middot; ' + (data.gender||'') + ' &middot; Age ' + (data.age||'') + '</div></div></div>'
      + '<div class="sp-kpi-grid">'
      + '<div class="sp-kpi"><div class="sp-kpi-label">Monthly Charge</div><div class="sp-kpi-val" style="color:#c4b5fd;">&#8377;' + parseFloat(data.charge||0).toFixed(2) + '</div></div>'
      + '<div class="sp-kpi"><div class="sp-kpi-label">Satisfaction</div><div class="sp-kpi-val" style="color:' + (parseInt(data.sat) <= 2 ? '#f87171' : parseInt(data.sat) <= 3 ? '#fbbf24' : '#34d399') + ';">' + (data.sat||0) + '/5</div></div>'
      + '<div class="sp-kpi"><div class="sp-kpi-label">Tenure</div><div class="sp-kpi-val" style="color:#e8deff;">' + (data.tenure||0) + 'mo</div></div>'
      + '<div class="sp-kpi"><div class="sp-kpi-label">CLTV</div><div class="sp-kpi-val" style="color:#a78bfa;">&#8377;' + parseInt(data.cltv||0).toLocaleString() + '</div></div>'
      + '</div>'
      + '<div class="sp-sec-title" style="margin-bottom:10px;">Churn Risk</div>'
      + '<div style="padding:10px 14px;background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.14);border-radius:8px;font-size:12px;font-weight:700;color:#f87171;margin-bottom:6px;">' + (data.category||'Unknown') + '</div>'
      + '<div style="padding:8px 12px;background:rgba(139,92,246,0.04);border:1px solid var(--border);border-radius:8px;font-size:11px;color:var(--text3);margin-bottom:14px;">' + (data.reason||'N/A') + '</div>'
      + '<div class="sp-sec-title">Quick Actions</div>'
      + '<div class="action-grid">'
      + '<button class="sp-action-btn sab-purple" onclick="spAction(this,' + JSON.stringify(cid) + ',' + JSON.stringify('Schedule callback') + ')">Schedule Call</button>'
      + '<button class="sp-action-btn sab-green" onclick="spAction(this,' + JSON.stringify(cid) + ',' + JSON.stringify('Send retention offer') + ')">Send Offer</button>'
      + '<button class="sp-action-btn sab-red" onclick="spAction(this,' + JSON.stringify(cid) + ',' + JSON.stringify('Escalate to senior') + ')">Escalate</button>'
      + '<button class="sp-action-btn sab-pink" onclick="spAction(this,' + JSON.stringify(cid) + ',' + JSON.stringify('Flag for review') + ')">Flag</button>'
      + '<button class="sp-action-btn sab-cyan" onclick="spAction(this,' + JSON.stringify(cid) + ',' + JSON.stringify('Mark as resolved') + ')">Resolve</button>'
      + '<button class="sp-action-btn sab-amber" onclick="openTaskModal(' + JSON.stringify(cid) + ')">Assign Task</button>'
      + '</div>'
      + '<div class="sp-sec-title" style="margin-top:14px;">Action Log</div>'
      + '<div id="spActionLog" style="font-size:11px;color:var(--text3);">No actions yet.</div>';
  } else if (type === 'agent') {
    var aid = data.id;
    titleEl.innerHTML = '<div style="display:flex;align-items:center;gap:10px;"><div class="avatar av-purple">' + (data.avatar||'??') + '</div><div><div style="font-size:14px;font-weight:700;color:#fff;font-family:Space Grotesk,sans-serif;">' + (data.name||'') + '</div><div style="font-size:10px;color:var(--text3);">' + (data.role||'') + '</div></div></div>';
    bodyEl.innerHTML =
      '<div class="sp-kpi-grid">'
      + '<div class="sp-kpi"><div class="sp-kpi-label">Accounts</div><div class="sp-kpi-val" style="color:#fff;">' + (data.total||0) + '</div></div>'
      + '<div class="sp-kpi"><div class="sp-kpi-label">Churn Rate</div><div class="sp-kpi-val" style="color:' + (parseFloat(data.rate||0) > 40 ? '#f87171' : '#34d399') + ';">' + (data.rate||0) + '%</div></div>'
      + '<div class="sp-kpi"><div class="sp-kpi-label">At Risk</div><div class="sp-kpi-val" style="color:#fbbf24;">' + (data.at_risk||0) + '</div></div>'
      + '<div class="sp-kpi"><div class="sp-kpi-label">Active</div><div class="sp-kpi-val" style="color:#34d399;">' + (data.resolved||0) + '</div></div>'
      + '</div>'
      + '<div class="sp-sec-title">Contact</div>'
      + '<div style="background:rgba(139,92,246,0.04);border:1px solid var(--border);border-radius:8px;padding:12px;font-size:11px;color:var(--text3);line-height:2.2;margin-bottom:14px;">'
      + (data.email||'') + '<br>' + (data.phone||'')
      + '</div>'
      + '<div class="sp-sec-title">Manager Actions</div>'
      + '<div class="action-grid">'
      + '<button class="sp-action-btn sab-amber" onclick="openTaskModal(null,' + JSON.stringify(aid) + ')">Assign Task</button>'
      + '<button class="sp-action-btn sab-green" onclick="spAction(this,' + JSON.stringify(aid) + ',' + JSON.stringify('Send performance brief') + ')">Send Brief</button>'
      + '<button class="sp-action-btn sab-purple" onclick="spAction(this,' + JSON.stringify(aid) + ',' + JSON.stringify('Schedule 1:1 review') + ')">Schedule 1:1</button>'
      + '<button class="sp-action-btn sab-cyan" onclick="spAction(this,' + JSON.stringify(aid) + ',' + JSON.stringify('Acknowledge good work') + ')">Acknowledge</button>'
      + '</div>'
      + '<div class="sp-sec-title" style="margin-top:14px;">Action Log</div>'
      + '<div id="spActionLog" style="font-size:11px;color:var(--text3);">No actions yet.</div>';
  }
}

// ── TASK MODAL ─────────────────────────────────────────────────────────
function openTaskModal(cid, agentId) {
  if (cid) document.getElementById('taskCustomers').value = cid;
  if (agentId) {
    var sel = document.getElementById('taskAgent');
    for (var i = 0; i < sel.options.length; i++) { if (sel.options[i].value === agentId) { sel.selectedIndex = i; break; } }
  }
  var d = new Date(); d.setDate(d.getDate() + 1);
  document.getElementById('taskDue').value = d.toISOString().split('T')[0];
  document.getElementById('taskModal').classList.add('open');
}
function closeTaskModal() { document.getElementById('taskModal').classList.remove('open'); }
function submitTask() {
  var title = document.getElementById('taskTitle').value.trim();
  if (!title) { showToast('Task title required', '', 'red'); return; }
  var payload = {
    title: title,
    agent_id: document.getElementById('taskAgent').value,
    priority: document.getElementById('taskPriority').value,
    due_date: document.getElementById('taskDue').value,
    customer_ids: document.getElementById('taskCustomers').value,
    notes: document.getElementById('taskNotes').value.trim()
  };
  fetch('/api/task/create', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        showToast('Task assigned', 'To ' + d.agent_name, 'green');
        closeTaskModal();
        document.getElementById('taskTitle').value = '';
        document.getElementById('taskCustomers').value = '';
        document.getElementById('taskNotes').value = '';
        if (window.location.pathname === '/actions') setTimeout(function(){ location.reload(); }, 800);
      }
    }).catch(function(e){ console.error(e); });
}
document.addEventListener('keydown', function(e) { if (e.key === 'Escape') { closeTaskModal(); closeSidePanel(); } });

// ── BULK SELECT ────────────────────────────────────────────────────────
var _selectedRows = new Set();
function toggleSelectAll(cb) {
  var checkboxes = document.querySelectorAll('.row-checkbox');
  checkboxes.forEach(function(c) {
    c.checked = cb.checked;
    var rowId = c.dataset.id;
    if (cb.checked) _selectedRows.add(rowId); else _selectedRows.delete(rowId);
    var tr = c.closest('tr');
    if (tr) tr.classList.toggle('row-selected', cb.checked);
  });
  updateBulkBar();
}
function toggleRowSelect(cb) {
  var rowId = cb.dataset.id;
  if (cb.checked) _selectedRows.add(rowId); else _selectedRows.delete(rowId);
  var tr = cb.closest('tr');
  if (tr) tr.classList.toggle('row-selected', cb.checked);
  updateBulkBar();
}
function updateBulkBar() {
  var bar = document.getElementById('bulkBar');
  if (!bar) return;
  var cnt = _selectedRows.size;
  if (cnt > 0) { bar.classList.add('visible'); document.getElementById('bulkCount').textContent = cnt + ' selected'; }
  else { bar.classList.remove('visible'); }
}
function bulkAction(action) {
  if (_selectedRows.size === 0) return;
  var ids = Array.from(_selectedRows);
  fetch('/api/bulk_action', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({customer_ids:ids, action:action})})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        showToast(action + ' sent', 'Applied to ' + ids.length + ' customers', 'green');
        _selectedRows.clear();
        document.querySelectorAll('.row-checkbox').forEach(function(c) { c.checked = false; var tr = c.closest('tr'); if (tr) tr.classList.remove('row-selected'); });
        document.querySelectorAll('.select-all-cb').forEach(function(c) { c.checked = false; });
        updateBulkBar();
      }
    }).catch(function(e){ console.error(e); });
}

// ── INLINE EDIT ────────────────────────────────────────────────────────
function makeEditable(el, custId, field, currentVal, options) {
  if (el.dataset.editing) return;
  el.dataset.editing = 'true';
  var orig = el.innerHTML;
  var input;
  if (options && options.length) {
    input = document.createElement('select');
    input.className = 'inline-edit-input';
    options.forEach(function(o) {
      var opt = document.createElement('option');
      opt.value = o.value || o; opt.textContent = o.label || o;
      if ((o.value || o) === currentVal) opt.selected = true;
      input.appendChild(opt);
    });
  } else {
    input = document.createElement('input');
    input.type = 'text'; input.className = 'inline-edit-input'; input.value = currentVal;
  }
  el.innerHTML = ''; el.appendChild(input); input.focus();
  function save() {
    var newVal = input.value;
    fetch('/api/update_field', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({customer_id:custId, field:field, value:newVal})})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) { el.innerHTML = d.display || newVal; showToast('Updated', 'Field saved', 'green'); delete el.dataset.editing; }
        else { el.innerHTML = orig; delete el.dataset.editing; }
      }).catch(function(){ el.innerHTML = orig; delete el.dataset.editing; });
  }
  input.addEventListener('blur', save);
  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { e.preventDefault(); save(); }
    if (e.key === 'Escape') { e.preventDefault(); el.innerHTML = orig; delete el.dataset.editing; }
  });
}

// ── TEAM HIERARCHY EXPAND/COLLAPSE ────────────────────────────────────
function toggleHierRow(tlId) {
  var wrap = document.getElementById('agents-' + tlId);
  var row = document.getElementById('tl-row-' + tlId);
  if (!wrap || !row) return;
  var isOpen = wrap.classList.contains('open');
  wrap.classList.toggle('open', !isOpen);
  row.classList.toggle('open', !isOpen);
}

// ── TAB SWITCHING — FIXED: no ALL_TABS string injection, use data-tabs attr ──
function switchTab(name) {
  // Find the tab bar that contains the clicked button
  var clickedBtn = document.querySelector('.tab-btn[data-tab="' + name + '"]');
  if (!clickedBtn) return;
  var tabBar = clickedBtn.closest('.tab-bar');
  if (!tabBar) return;

  // Get all tab names from sibling buttons in the same tab-bar
  var allBtns = tabBar.querySelectorAll('.tab-btn');
  var allTabNames = [];
  allBtns.forEach(function(b) { if (b.dataset.tab) allTabNames.push(b.dataset.tab); });

  // Update button active states
  allBtns.forEach(function(b) { b.classList.toggle('active', b.dataset.tab === name); });

  // Update tab content panels
  allTabNames.forEach(function(t) {
    var el = document.getElementById('tab-' + t);
    if (el) el.classList.toggle('active', t === name);
  });

  if (name === 'kanban') { setTimeout(initKanban, 50); }
  setTimeout(function() {
    document.querySelectorAll('.reveal').forEach(function(el) { el.classList.add('visible'); });
  }, 80);
}

// ── DRAG AND DROP KANBAN ───────────────────────────────────────────────
var _dragCard = null;
function initKanban() {
  document.querySelectorAll('.kanban-card').forEach(function(card) {
    if (card._kanbanInit) return;
    card._kanbanInit = true;
    card.setAttribute('draggable', 'true');
    card.addEventListener('dragstart', function(e) {
      _dragCard = card; card.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    });
    card.addEventListener('dragend', function() {
      card.classList.remove('dragging');
      document.querySelectorAll('.kanban-col').forEach(function(c) { c.classList.remove('drag-over'); });
      _dragCard = null;
    });
  });
  document.querySelectorAll('.kc-body').forEach(function(col) {
    if (col._kanbanColInit) return;
    col._kanbanColInit = true;
    col.addEventListener('dragover', function(e) {
      e.preventDefault();
      col.closest('.kanban-col').classList.add('drag-over');
    });
    col.addEventListener('dragleave', function(e) {
      if (!col.contains(e.relatedTarget)) col.closest('.kanban-col').classList.remove('drag-over');
    });
    col.addEventListener('drop', function(e) {
      e.preventDefault();
      var targetCol = col.closest('.kanban-col');
      targetCol.classList.remove('drag-over');
      if (!_dragCard) return;
      var newStatus = targetCol.dataset.status;
      var oldStatus = _dragCard.dataset.status;
      col.appendChild(_dragCard);
      if (newStatus !== oldStatus) {
        _dragCard.dataset.status = newStatus;
        var badge = _dragCard.querySelector('.cst-badge');
        if (badge) {
          var statusMap = {active:'csb-active', at_risk:'csb-at_risk', escalated:'csb-escalated', resolved:'csb-resolved', flagged:'csb-flagged'};
          var labelMap = {active:'Active', at_risk:'At Risk', escalated:'Escalated', resolved:'Resolved', flagged:'Flagged'};
          badge.className = 'cst-badge ' + (statusMap[newStatus] || 'csb-active');
          badge.textContent = labelMap[newStatus] || newStatus;
        }
        _dragCard.classList.remove('kc-hi','kc-med','kc-lo');
        if (newStatus === 'escalated') _dragCard.classList.add('kc-hi');
        else if (newStatus === 'at_risk' || newStatus === 'flagged') _dragCard.classList.add('kc-med');
        else _dragCard.classList.add('kc-lo');
        document.querySelectorAll('.kanban-col').forEach(function(kc) {
          var cnt = kc.querySelectorAll('.kanban-card').length;
          var countEl = kc.querySelector('.kc-count');
          if (countEl) countEl.textContent = cnt;
        });
        fetch('/api/update_field', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({customer_id:_dragCard.dataset.custid, field:'status', value:newStatus})});
        showToast('Status updated', 'Moved to ' + newStatus.replace(/_/g,' '), 'green');
      }
    });
  });
}

// ── LIVE SCORE SIMULATION ──────────────────────────────────────────────
var _liveSimActive = false, _liveSimInterval = null;
function toggleLiveSim() {
  _liveSimActive = !_liveSimActive;
  var btn = document.getElementById('liveSimBtn');
  if (_liveSimActive) {
    if (btn) btn.textContent = 'Stop Simulation';
    _liveSimInterval = setInterval(runSimTick, 2200);
    showToast('Live simulation started', 'Scores updating every 2s', 'amber');
  } else {
    if (btn) btn.textContent = 'Start Live Simulation';
    clearInterval(_liveSimInterval);
    showToast('Simulation stopped', '', '');
  }
}
function runSimTick() {
  fetch('/api/sim_tick', {method:'POST', headers:{'Content-Type':'application/json'}})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.ok) return;
      d.updates.forEach(function(u) {
        document.querySelectorAll('[data-custid="' + u.id + '"]').forEach(function(el) {
          var pill = el.querySelector('.score-pill');
          if (pill) {
            var cls = u.score >= 70 ? 'sp-hi' : u.score >= 40 ? 'sp-med' : 'sp-lo';
            pill.textContent = u.score;
            pill.className = 'score-pill ' + cls;
          }
        });
      });
      if (d.new_alert) {
        showToast(d.new_alert.title, d.new_alert.sub, 'red');
        var list = document.getElementById('alertList');
        if (list) {
          var el = document.createElement('div');
          el.className = 'alert-item critical';
          el.innerHTML = '<div class="alert-title">' + d.new_alert.title + ' <span class="alert-unread"></span></div><div class="alert-sub">' + d.new_alert.sub + '</div><div class="alert-time">Just now</div>';
          list.insertBefore(el, list.firstChild);
        }
        var badge = document.querySelector('.nav-bell-badge');
        if (badge) { var n = parseInt(badge.textContent || 0) + 1; badge.textContent = n; }
      }
    }).catch(function(e){ console.error(e); });
}

// ── AI CHAT ────────────────────────────────────────────────────────────
var aiOpen = false;
function toggleAiChat() {
  var p = document.getElementById('aiChatPanel');
  aiOpen = !aiOpen;
  p.classList.toggle('open', aiOpen);
  if (aiOpen) document.getElementById('aiInput').focus();
}
var AI_RESPONSES = {
  "main churn driver": "Based on your dataset, the primary driver is Competitor (about 45% of churned). Customers see better pricing or more data at rivals. Recommend: targeted counter-offers for Competitor-flagged at-risk accounts.",
  "team alerts": "All 4 teams show high churn rates. Team Alpha (Priya Menon) has the highest at-risk count. Suggest: assign bulk escalation tasks via Action Log.",
  "retention strategy": "Top 3 plays: 1. Counter competitor offers - match on data packages. 2. Satisfaction blitz - 1:1 calls for Sat 2 or lower customers. 3. Contract lock-ins - incentivise 1yr upgrades.",
  "assign tasks": "You can assign tasks: go to Action Log, click Assign Task, pick an agent, add customer IDs, set priority and due date.",
  "default": "I can see your telco dataset has high churn risk. The biggest levers are competitor response and satisfaction improvement. What should we tackle first?"
};
function askAI(q) {
  addAiMsg(q, 'user'); document.getElementById('aiInput').value = '';
  showAiTyping();
  setTimeout(function() {
    removeAiTyping();
    var lower = q.toLowerCase();
    var response = AI_RESPONSES['default'];
    for (var key in AI_RESPONSES) { if (lower.indexOf(key) >= 0) { response = AI_RESPONSES[key]; break; } }
    addAiMsg(response, 'bot');
  }, 900 + Math.random() * 600);
}
function sendAI() { var inp = document.getElementById('aiInput'); var q = inp.value.trim(); if (!q) return; askAI(q); }
function addAiMsg(text, role) {
  var msgs = document.getElementById('aiMsgs');
  var d = document.createElement('div'); d.className = 'ai-msg ' + role;
  d.textContent = text;
  msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight;
}
var typingEl = null;
function showAiTyping() {
  var msgs = document.getElementById('aiMsgs');
  typingEl = document.createElement('div'); typingEl.className = 'ai-msg bot';
  typingEl.innerHTML = '<div class="ai-typing"><span></span><span></span><span></span></div>';
  msgs.appendChild(typingEl); msgs.scrollTop = msgs.scrollHeight;
}
function removeAiTyping() { if (typingEl && typingEl.parentNode) { typingEl.parentNode.removeChild(typingEl); typingEl = null; } }

// ── REVEAL ANIMATION ───────────────────────────────────────────────────
(function() {
  var obs = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, {threshold: 0.06});
  document.querySelectorAll('.reveal').forEach(function(el) { obs.observe(el); });
})();

// ── DATA ATTRIBUTE EVENT DELEGATION for side panel clicks ───────────────
document.addEventListener('click', function(e) {
  var el = e.target.closest('[data-panel-type]');
  if (el) {
    e.stopPropagation();
    openSidePanelFromEl(el, el.getAttribute('data-panel-type'));
  }
});

// ── LIGHT / DARK THEME TOGGLE (dashboard page only) ──────────────────────
function applyTheme(theme) {
  document.body.classList.toggle('light-theme', theme === 'light');
  var btn = document.getElementById('themeToggleBtn');
  if (btn) btn.innerHTML = theme === 'light' ? '&#127769;' : '&#9728;';
}
function toggleTheme() {
  var isLight = document.body.classList.contains('light-theme');
  var next = isLight ? 'dark' : 'light';
  applyTheme(next);
  try { localStorage.setItem('nr_dashboard_theme', next); } catch (e) {}
}
(function initTheme() {
  if (document.body.getAttribute('data-page') !== 'dashboard') return;
  var saved = 'dark';
  try { saved = localStorage.getItem('nr_dashboard_theme') || 'dark'; } catch (e) {}
  applyTheme(saved);
})();
</script>
"""

def page_shell(active, title_tag, body_html, ticker_html="", extra_js="", page_id=""):
    return (
        "<!DOCTYPE html><html><head>"
        "<meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>NeuralRetain v5 - " + title_tag + "</title>"
        + BASE_CSS
        + "</head><body data-page='" + page_id + "'>"
        + '<div class="nav-wrapper">'
        + (ticker_html if ticker_html else "")
        + nav(active)
        + '</div>'
        + build_alert_panel()
        + build_task_modal()
        + '<div class="content">' + body_html + '</div>'
        + '<div id="toastStack"></div>'
        + '<div class="side-overlay" id="sideOverlay" onclick="closeSidePanel()"></div>'
        + '<div class="side-panel" id="sidePanel">'
        + '<div class="sp-header"><div id="spTitle" style="font-family:Space Grotesk,sans-serif;font-size:13px;font-weight:700;color:#fff;">Details</div>'
        + '<button class="sp-close" onclick="closeSidePanel()">&#x2715;</button></div>'
        + '<div class="sp-body" id="spBody"></div></div>'
        + build_ai_chat()
        + GLOBAL_JS + extra_js
        + "</body></html>"
    )

# ── Helper: build customer JSON dict for data attributes ──────────────────────
def cust_data_dict(row):
    return {
        "id": str(row["CustomerID"]),
        "score": float(row["ChurnScore"]),
        "status": str(row["CustStatus"]),
        "contract": str(row["Contract"]),
        "internet": str(row["InternetType"]),
        "charge": float(row["MonthlyCharge"]),
        "sat": int(row["SatisfactionScore"]),
        "tenure": int(row["TenureinMonths"]),
        "cltv": int(row["CLTV"]),
        "totalrev": float(row["TotalRevenue"]),
        "city": str(row["City"]),
        "gender": str(row["Gender"]),
        "age": int(row["Age"]),
        "category": str(row["ChurnCategory"]),
        "reason": str(row["ChurnReason"])
    }

def agent_data_dict(ag, st):
    return {
        "id": ag["id"], "name": ag["name"], "role": ag.get("role","Agent"),
        "email": ag.get("email",""), "phone": ag.get("phone",""),
        "avatar": ag["avatar"], "status": ag.get("status","active"),
        "total": st.get("total",0), "rate": st.get("rate",0),
        "at_risk": st.get("at_risk",0), "resolved": st.get("resolved",0),
        "rev": st.get("rev",0)
    }

# ── APIs ──────────────────────────────────────────────────────────────────────
@app.route("/api/alert_read/<aid>")
def api_alert_read(aid):
    for a in alert_store:
        if a["id"] == aid: a["read"] = True
    return jsonify({"ok": True})

@app.route("/api/action", methods=["POST"])
def api_action():
    if not session.get("logged_in"): return jsonify({"ok":False}),403
    data = request.get_json(force=True)
    action_log.append({
        "ts": datetime.now().strftime("%H:%M:%S"),
        "customer_id": data.get("customer_id","?"),
        "action": data.get("action","?"),
        "agent": session.get("user","Dev")
    })
    return jsonify({"ok": True})

@app.route("/api/bulk_action", methods=["POST"])
def api_bulk_action():
    if not session.get("logged_in"): return jsonify({"ok":False}),403
    data = request.get_json(force=True)
    cids = data.get("customer_ids",[])
    action = data.get("action","Bulk action")
    for cid in cids:
        action_log.append({
            "ts": datetime.now().strftime("%H:%M:%S"),
            "customer_id": cid,
            "action": "[BULK] " + action,
            "agent": session.get("user","Dev")
        })
    return jsonify({"ok": True, "count": len(cids)})

@app.route("/api/task/create", methods=["POST"])
def api_task_create():
    if not session.get("logged_in"): return jsonify({"ok":False}),403
    data = request.get_json(force=True)
    ag = AGENT_MAP.get(data.get("agent_id",""),{})
    task = {
        "id": "TASK-{:03d}".format(len(task_store)+1),
        "title": data.get("title",""),
        "agent_id": data.get("agent_id",""),
        "agent_name": ag.get("name","Unknown"),
        "priority": data.get("priority","normal"),
        "due_date": data.get("due_date",""),
        "customer_ids": data.get("customer_ids",""),
        "notes": data.get("notes",""),
        "status": "open",
        "progress": 0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "created_by": session.get("user","Dev")
    }
    task_store.append(task)
    action_log.append({
        "ts": datetime.now().strftime("%H:%M:%S"),
        "customer_id": task["customer_ids"] or "-",
        "action": "Task assigned: " + task["title"],
        "agent": ag.get("name","Dev")
    })
    return jsonify({"ok": True, "task_id": task["id"], "agent_name": task["agent_name"]})

@app.route("/api/task/update", methods=["POST"])
def api_task_update():
    if not session.get("logged_in"): return jsonify({"ok":False}),403
    data = request.get_json(force=True)
    tid = data.get("task_id")
    for t in task_store:
        if t["id"] == tid:
            if "status" in data: t["status"] = data["status"]
            if "progress" in data: t["progress"] = int(data["progress"])
            if "notes" in data: t["notes"] = data["notes"]
    return jsonify({"ok": True})

@app.route("/api/update_field", methods=["POST"])
def api_update_field():
    if not session.get("logged_in"): return jsonify({"ok":False}),403
    data = request.get_json(force=True)
    cid   = data.get("customer_id")
    field = data.get("field")
    value = data.get("value")
    if field == "status":
        mask = df_raw["CustomerID"] == cid
        if mask.any(): df_raw.loc[mask, "CustStatus"] = value
    action_log.append({
        "ts": datetime.now().strftime("%H:%M:%S"),
        "customer_id": cid,
        "action": "Field '{}' updated to {}".format(field, value),
        "agent": session.get("user","Dev")
    })
    label_map={"active":"Active","at_risk":"At Risk","escalated":"Escalated","resolved":"Resolved","flagged":"Flagged"}
    cls_map={"active":"csb-active","at_risk":"csb-at_risk","escalated":"csb-escalated","resolved":"csb-resolved","flagged":"csb-flagged"}
    if field == "status":
        display = '<span class="cst-badge {}">{}</span>'.format(cls_map.get(value,"csb-active"), label_map.get(value,value))
        return jsonify({"ok": True, "display": display})
    return jsonify({"ok": True, "display": value})

@app.route("/api/sim_tick", methods=["POST"])
def api_sim_tick():
    if not session.get("logged_in"): return jsonify({"ok":False}),403
    sample = df_raw.sample(n=min(4, len(df_raw)))
    updates = []
    new_alert = None
    for _, row in sample.iterrows():
        cid = str(row["CustomerID"])
        current = float(row["ChurnScore"])
        delta = random.uniform(-3, 4)
        new_score = max(0, min(100, current + delta))
        df_raw.loc[df_raw["CustomerID"]==cid, "ChurnScore"] = new_score
        updates.append({"id": cid, "score": round(new_score, 0)})
        if new_score >= 90 and random.random() < 0.3:
            new_alert = {"title": "{} churn score reached {:.0f}".format(cid, new_score), "sub": "Immediate action recommended"}
    return jsonify({"ok": True, "updates": updates, "new_alert": new_alert})

@app.route("/api/tasks")
def api_tasks():
    if not session.get("logged_in"): return jsonify({"ok":False}),403
    return jsonify({"ok": True, "tasks": task_store})

# ── HIERARCHICAL TEAM TABLE ───────────────────────────────────────────────────
# FIX: Use data-json + data-panel-type attributes instead of onclick with repr()
def build_hierarchical_team_table(tl_stats, agent_stats, df):
    hdr = (
        '<div style="display:grid;grid-template-columns:230px 90px 140px 80px 80px 100px 80px 40px;'
        'padding:10px 15px;border-bottom:1px solid var(--border);background:rgba(139,92,246,0.02);">'
        + "".join('<div style="font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--text3);">' + h + '</div>'
                  for h in ["Team / Agent","Accounts","Churn Rate","At Risk","Active","Rev Risk","Status",""])
        + '</div>'
    )
    rows_html = ""
    for i, tl in enumerate(TEAM_DATA["team_leads"]):
        ts = tl_stats[tl["id"]]
        clr = "#ef4444" if ts["rate"]>60 else "#fbbf24" if ts["rate"]>30 else "#34d399"
        tag = ('<span class="tag tag-red">Critical</span>' if ts["rate"]>60
               else '<span class="tag tag-amber">Elevated</span>' if ts["rate"]>30
               else '<span class="tag tag-green">Stable</span>')
        av_cls = av_color(i)
        # FIX: Use data-json attribute instead of repr() in onclick
        tl_data = {
            "id":tl["id"],"name":tl["name"],"role":tl["role"],"email":"tl@telecom.in",
            "phone":"+91-98100-00000","avatar":tl["avatar"],"status":"active",
            "total":ts["total"],"rate":ts["rate"],"at_risk":ts["at_risk"],
            "resolved":ts["resolved"],"rev":ts["rev"]
        }
        tl_json_attr = html_module.escape(json.dumps(tl_data, ensure_ascii=True), quote=True)
        bar_w = min(100,ts["rate"])

        agent_sub = ""
        for j, ag in enumerate(TEAM_DATA["agents"]):
            if ag["tl"] != tl["id"]: continue
            st = agent_stats.get(ag["id"],{})
            aclr = "#ef4444" if st.get("rate",0)>60 else "#fbbf24" if st.get("rate",0)>30 else "#34d399"
            sd_cls = "sd-active" if ag["status"]=="active" else "sd-busy" if ag["status"]=="busy" else "sd-offline"
            ag_data = agent_data_dict(ag, st)
            ag_json_attr = html_module.escape(json.dumps(ag_data, ensure_ascii=True), quote=True)
            abw = min(100,st.get("rate",0))
            agent_sub += (
                '<div class="agent-row-inner" data-panel-type="agent" data-json="' + ag_json_attr + '">'
                + '<div class="indent-line"><div class="avatar-sm ' + av_color(j) + '">' + ag["avatar"] + '</div>'
                + '<div><div style="font-size:12px;font-weight:500;color:var(--text2);">' + ag["name"] + '</div>'
                + '<div style="font-size:10px;color:var(--text3);display:flex;align-items:center;gap:4px;">'
                + '<span class="status-dot ' + sd_cls + '"></span>' + ag["status"].capitalize() + '</div></div></div>'
                + '<div style="font-size:12px;color:var(--text2);">' + str(st.get("total",0)) + '</div>'
                + '<div style="display:flex;align-items:center;gap:6px;">'
                + '<div class="mini-bar-wrap"><div class="mini-bar-fill" style="width:' + str(int(abw)) + '%;background:' + aclr + ';"></div></div>'
                + '<span style="color:' + aclr + ';font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;">' + str(st.get("rate",0)) + '%</span></div>'
                + '<div style="color:#f87171;font-size:12px;">' + str(st.get("at_risk",0)) + '</div>'
                + '<div style="color:#34d399;font-size:12px;">' + str(st.get("resolved",0)) + '</div>'
                + '<div style="color:#fbbf24;font-size:12px;">' + fmt_money(st.get("rev",0)) + '</div>'
                + '<div></div>'
                + '<div><button class="btn btn-xs" style="color:#f9a8d4;" onclick="event.stopPropagation();openTaskModal(null,\'' + ag["id"] + '\')">Task</button></div>'
                + '</div>'
            )

        rows_html += (
            '<div class="tl-row" id="tl-row-' + tl["id"] + '">'
            + '<div class="tl-row-inner" onclick="toggleHierRow(\'' + tl["id"] + '\')">'
            + '<div style="display:flex;align-items:center;gap:8px;">'
            + '<span class="expand-chevron">&#9658;</span>'
            + '<div class="avatar ' + av_cls + '">' + tl["avatar"] + '</div>'
            + '<div><div style="font-weight:700;color:#fff;font-size:13px;font-family:Space Grotesk,sans-serif;">' + tl["name"] + '</div>'
            + '<div style="font-size:10px;color:var(--text3);">Team ' + tl["team"] + '</div></div></div>'
            + '<div style="font-size:12px;color:var(--text2);">' + str(ts["total"]) + '</div>'
            + '<div style="display:flex;align-items:center;gap:7px;">'
            + '<div class="mini-bar-wrap"><div class="mini-bar-fill" style="width:' + str(int(bar_w)) + '%;background:' + clr + ';"></div></div>'
            + '<span style="color:' + clr + ';font-family:JetBrains Mono,monospace;font-size:13px;font-weight:800;">' + str(ts["rate"]) + '%</span></div>'
            + '<div style="color:#f87171;font-size:13px;font-weight:600;">' + str(ts["at_risk"]) + '</div>'
            + '<div style="color:#34d399;font-size:13px;font-weight:600;">' + str(ts["resolved"]) + '</div>'
            + '<div style="color:#fbbf24;font-size:12px;">' + fmt_money(ts["rev"]) + '</div>'
            + '<div>' + tag + '</div>'
            + '<div><button class="btn btn-xs btn-purple" data-panel-type="agent" data-json="' + tl_json_attr + '" onclick="event.stopPropagation();" title="View details">View</button></div>'
            + '</div></div>'
            + '<div class="agent-rows-wrap" id="agents-' + tl["id"] + '">' + agent_sub + '</div>'
        )

    return (
        '<div class="card-panel reveal">'
        + '<div class="card-panel-hdr"><span class="cph-title">Team Hierarchy — click View for details, Task to assign tasks</span></div>'
        + hdr + rows_html + '</div>'
    )

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    r = chk()
    if r: return r
    df = df_raw
    kp = compute_kpis(df)
    agent_stats = get_agent_stats(df)
    tl_stats = get_tl_stats(df, agent_stats)
    ticker = build_live_ticker(kp, df)

    random.seed(42)
    churn_trend = [random.uniform(88, 98) for _ in range(8)]
    rev_trend   = [random.uniform(34000, 42000) for _ in range(8)]
    sat_trend   = [random.uniform(1.6, 2.2) for _ in range(8)]
    score_trend = [random.uniform(78, 88) for _ in range(8)]

    kpi_html = (
        '<div class="kpi-strip">'
        + '<div class="kpi-card kc-purple"><div class="kpi-label">Total Customers</div>'
        + '<div class="kpi-val">' + str(kp["total"]) + '</div><div class="kpi-sub">All active accounts</div></div>'
        + '<div class="kpi-card kc-red"><div class="kpi-label">Churned</div>'
        + '<div class="kpi-val" style="color:#f87171;" id="kpiChurned">' + str(kp["churned"]) + '</div>'
        + '<div style="display:flex;align-items:center;gap:6px;margin-top:4px;"><span class="kpi-delta up">Critical</span>'
        + '<span class="live-badge"><div class="live-dot"></div>Live</span></div>'
        + '<div class="kpi-sparkline">' + make_sparkline([round(v,1) for v in churn_trend], color="#f87171") + '</div></div>'
        + '<div class="kpi-card kc-amber"><div class="kpi-label">Revenue at Risk</div>'
        + '<div class="kpi-val" style="color:#fbbf24;">' + fmt_money(kp["rev_loss"]) + '</div>'
        + '<div class="kpi-sparkline">' + make_sparkline([round(v) for v in rev_trend], color="#fbbf24") + '</div></div>'
        + '<div class="kpi-card kc-pink"><div class="kpi-label">Avg Churn Score</div>'
        + '<div class="kpi-val" style="color:#f9a8d4;" id="kpiAvgScore">' + str(kp["avg_score"]) + '</div>'
        + '<div class="kpi-sparkline">' + make_sparkline([round(v,1) for v in score_trend], color="#f9a8d4") + '</div></div>'
        + '<div class="kpi-card kc-green"><div class="kpi-label">Avg Satisfaction</div>'
        + '<div class="kpi-val" style="color:#34d399;">' + str(kp["avg_sat"]) + '/5</div>'
        + '<div class="kpi-sparkline">' + make_sparkline([round(v,1) for v in sat_trend], color="#34d399") + '</div></div>'
        + '</div>'
    )

    sim_bar = (
        '<div style="display:flex;align-items:center;gap:10px;padding:12px 16px;background:rgba(16,185,129,0.04);border:1px solid rgba(16,185,129,0.14);border-radius:10px;margin-bottom:20px;">'
        + '<div class="live-dot"></div>'
        + '<span style="font-size:12px;font-weight:600;color:#34d399;">Live Score Simulation</span>'
        + '<span style="font-size:11px;color:var(--text3);flex:1;">Watch churn scores update in real-time</span>'
        + '<button id="liveSimBtn" onclick="toggleLiveSim()" class="btn btn-green btn-sm">Start Live Simulation</button>'
        + '</div>'
    )

    # Top risk table with bulk select
    top8 = df.sort_values("ChurnScore", ascending=False).head(8)
    bulk_bar_html = (
        '<div class="bulk-bar" id="bulkBar">'
        + '<span class="bulk-count" id="bulkCount">0 selected</span>'
        + '<div class="bulk-actions">'
        + '<button class="btn btn-xs btn-green" onclick="bulkAction(\'Send retention offer\')">Bulk Offer</button>'
        + '<button class="btn btn-xs" style="color:#a78bfa;" onclick="bulkAction(\'Schedule callback\')">Bulk Call</button>'
        + '<button class="btn btn-xs btn-danger" onclick="bulkAction(\'Escalate to senior\')">Escalate All</button>'
        + '<button class="btn btn-xs btn-purple" onclick="openTaskModal()">Assign Task</button>'
        + '</div></div>'
    )
    risk_html = (
        '<div class="card-panel reveal">'
        + '<div class="card-panel-hdr"><span class="cph-title">Top Risk Accounts</span>'
        + '<div style="display:flex;gap:7px;">'
        + '<a href="/customers?score=High" class="btn btn-xs btn-purple">View all</a></div></div>'
        + bulk_bar_html
        + '<div style="overflow-x:auto;"><table class="dd-table">'
        + '<tr><th><input type="checkbox" class="select-all-cb" onchange="toggleSelectAll(this)"></th>'
        + '<th>Customer</th><th>Score</th><th>Status</th><th>Contract</th><th>Reason</th><th>Actions</th></tr>'
    )
    for _, row in top8.iterrows():
        sc=float(row["ChurnScore"]); cid=str(row["CustomerID"])
        # FIX: Use data-json attribute, not repr() in onclick
        cdata_attr = html_module.escape(json.dumps(cust_data_dict(row), ensure_ascii=True), quote=True)
        risk_html += (
            '<tr data-custid="' + cid + '">'
            + '<td><input type="checkbox" class="row-checkbox" data-id="' + cid + '" onchange="toggleRowSelect(this)"></td>'
            + '<td class="clickable-cust" data-panel-type="customer" data-json="' + cdata_attr + '" style="cursor:pointer;font-family:JetBrains Mono,monospace;font-weight:700;color:#fff;">' + cid + '</td>'
            + '<td class="score-live" data-custid="' + cid + '">' + score_pill(sc) + '</td>'
            + '<td class="editable-field" onclick="makeEditable(this,\'' + cid + '\',\'status\',\'' + str(row["CustStatus"]) + '\','
            + '[{value:\'active\',label:\'Active\'},{value:\'at_risk\',label:\'At Risk\'},'
            + '{value:\'flagged\',label:\'Flagged\'},{value:\'escalated\',label:\'Escalated\'},'
            + '{value:\'resolved\',label:\'Resolved\'}])">'
            + status_badge(str(row["CustStatus"])) + '</td>'
            + '<td style="color:var(--text2);">' + str(row["Contract"]) + '</td>'
            + '<td style="color:var(--text3);max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + str(row["ChurnReason"])[:35] + '</td>'
            + '<td><div style="display:flex;gap:3px;">'
            + '<button class="act-btn ab-offer" onclick="doCustomerAction(\'' + cid + '\',\'Send retention offer\',this)">Offer</button>'
            + '<button class="act-btn ab-esc" onclick="doCustomerAction(\'' + cid + '\',\'Escalate\',this)">Esc</button>'
            + '<button class="act-btn ab-res" onclick="doCustomerAction(\'' + cid + '\',\'Mark as resolved\',this)">Res</button>'
            + '<button class="act-btn ab-call" onclick="openTaskModal(\'' + cid + '\')" title="Assign task">Task</button>'
            + '</div></td></tr>'
        )
    risk_html += '</table></div></div>'

    team_table = build_hierarchical_team_table(tl_stats, agent_stats, df)

    cat_counts = df[df["ChurnLabel"]=="Yes"]["ChurnCategory"].value_counts().to_dict()
    donut_svg, donut_legend = make_donut(cat_counts, size=160)
    gauge_section = (
        '<div class="two-col">'
        + '<div class="gauge-panel"><div style="font-family:Space Grotesk,sans-serif;font-size:13px;font-weight:700;color:#fff;margin-bottom:16px;display:flex;align-items:center;gap:8px;"><span class="live-dot"></span>Live Churn Rate</div>'
        + make_gauge(kp["rate"],size=220)
        + '<div style="display:flex;justify-content:center;gap:24px;margin-top:12px;">'
        + '<div style="text-align:center;"><div style="font-size:9px;color:var(--text3);">CHURNED</div><div style="font-family:Space Grotesk,sans-serif;font-size:18px;font-weight:800;color:#f87171;">' + str(kp["churned"]) + '</div></div>'
        + '<div style="text-align:center;"><div style="font-size:9px;color:var(--text3);">RETAINED</div><div style="font-family:Space Grotesk,sans-serif;font-size:18px;font-weight:800;color:#34d399;">' + str(kp["retained"]) + '</div></div>'
        + '<div style="text-align:center;"><div style="font-size:9px;color:var(--text3);">AVG SCORE</div><div style="font-family:Space Grotesk,sans-serif;font-size:18px;font-weight:800;color:#c4b5fd;">' + str(kp["avg_score"]) + '</div></div>'
        + '</div></div>'
        + '<div class="chart-container"><div class="chart-title">Churn by Category</div>'
        + '<div style="display:flex;align-items:center;gap:18px;">' + donut_svg + '<div style="flex:1;">' + donut_legend + '</div></div></div>'
        + '</div>'
    )

    body = kpi_html + sim_bar + gauge_section + '<div class="slabel">Team Performance</div>' + team_table + '<div class="slabel">Top Risk — Click status to edit inline</div>' + risk_html
    extra_js = '<script>setTimeout(function(){document.querySelectorAll(".reveal").forEach(function(el){el.classList.add("visible");});},80);</script>'
    return page_shell("d","Dashboard",body,ticker,extra_js,page_id="dashboard")

# ── TEAM VIEW ─────────────────────────────────────────────────────────────────
@app.route("/team")
def team_view():
    r = chk()
    if r: return r
    df = df_raw
    agent_stats = get_agent_stats(df)
    tl_stats    = get_tl_stats(df, agent_stats)
    kp          = compute_kpis(df)
    ticker      = build_live_ticker(kp, df)
    active_tab  = request.args.get("tab","leaderboard")

    # FIX: Tab buttons just use data-tab, no ALL_TABS injection needed
    def tbtn(tab_id, label):
        active_cls = "active" if active_tab == tab_id else ""
        return ('<button class="tab-btn ' + active_cls + '" data-tab="' + tab_id + '" '
                + 'onclick="switchTab(\'' + tab_id + '\')">' + label + '</button>')

    tab_bar = (
        '<div class="tab-bar">'
        + tbtn("leaderboard", "&#127942; Leaderboard")
        + tbtn("heatmap", "&#128293; Workload Heatmap")
        + tbtn("kanban", "&#128203; Kanban Board")
        + tbtn("drilldown", "&#128269; Drill-Down")
        + '</div>'
    )

    # LEADERBOARD
    sorted_agents = sorted(TEAM_DATA["agents"], key=lambda a: agent_stats.get(a["id"],{}).get("rate",0), reverse=True)
    max_rate = max((agent_stats.get(a["id"],{}).get("rate",0) for a in sorted_agents), default=1) or 1
    lb_rows = ""
    medal_colors = {1:"#f59e0b",2:"#9ca3af",3:"#b45309"}
    for rank, ag in enumerate(sorted_agents, 1):
        st = agent_stats.get(ag["id"],{})
        rate = st.get("rate",0)
        clr = "#ef4444" if rate>60 else "#fbbf24" if rate>30 else "#34d399"
        mc = medal_colors.get(rank,"var(--text3)")
        bar_w = rate/max_rate*100
        # FIX: data-json attribute
        ag_json_attr = html_module.escape(json.dumps(agent_data_dict(ag, st), ensure_ascii=True), quote=True)
        medal = "#" + str(rank) if rank > 3 else ("1st" if rank==1 else "2nd" if rank==2 else "3rd")
        sd_cls = "sd-active" if ag["status"]=="active" else "sd-busy" if ag["status"]=="busy" else "sd-offline"
        tl = TL_MAP.get(ag["tl"],{})
        lb_rows += (
            '<div class="lb-row reveal" data-panel-type="agent" data-json="' + ag_json_attr + '">'
            + '<div class="lb-rank" style="color:' + mc + ';">' + medal + '</div>'
            + '<div class="avatar ' + av_color(rank%5) + '">' + ag["avatar"] + '</div>'
            + '<div style="flex:1;min-width:0;">'
            + '<div style="font-size:13px;font-weight:700;color:#fff;display:flex;align-items:center;gap:7px;">'
            + ag["name"] + ' <span class="status-dot ' + sd_cls + '"></span>'
            + '<span style="font-size:10px;color:var(--text3);">Team ' + tl.get("team","?") + '</span></div>'
            + '<div style="display:flex;align-items:center;gap:8px;margin-top:4px;">'
            + '<div class="lb-bar"><div class="lb-bar-fill" style="width:' + str(int(bar_w)) + '%;background:' + clr + ';"></div></div>'
            + '<span style="font-family:JetBrains Mono,monospace;font-size:12px;font-weight:700;color:' + clr + ';">' + str(rate) + '%</span></div></div>'
            + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;text-align:center;">'
            + '<div><div style="font-size:9px;color:var(--text3);">Accounts</div><div style="font-family:Space Grotesk,sans-serif;font-size:15px;font-weight:700;color:#fff;">' + str(st.get("total",0)) + '</div></div>'
            + '<div><div style="font-size:9px;color:var(--text3);">At Risk</div><div style="font-family:Space Grotesk,sans-serif;font-size:15px;font-weight:700;color:#f87171;">' + str(st.get("at_risk",0)) + '</div></div>'
            + '<div><div style="font-size:9px;color:var(--text3);">Active</div><div style="font-family:Space Grotesk,sans-serif;font-size:15px;font-weight:700;color:#34d399;">' + str(st.get("resolved",0)) + '</div></div>'
            + '</div>'
            + '<button class="btn btn-xs btn-purple" onclick="event.stopPropagation();openTaskModal(null,\'' + ag["id"] + '\')">Task</button>'
            + '</div>'
        )
    leaderboard_tab = (
        '<div id="tab-leaderboard" class="tab-content ' + ("active" if active_tab=="leaderboard" else "") + '">'
        + '<div class="card-panel"><div class="card-panel-hdr"><span class="cph-title">Agent Leaderboard — click row for details</span>'
        + '<button class="btn btn-sm btn-purple" onclick="openTaskModal()">Assign Task</button></div>'
        + lb_rows + '</div></div>'
    )

    # HEATMAP
    hours = ["9AM","10AM","11AM","12PM","1PM","2PM","3PM","4PM","5PM","6PM","7PM"]
    days  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    random.seed(123)
    hm_hdr = (
        '<div style="display:grid;grid-template-columns:50px repeat(11,1fr);gap:3px;margin-bottom:6px;padding:0 15px;">'
        + '<div></div>'
        + "".join('<div style="font-size:9px;color:var(--text3);text-align:center;">' + h + '</div>' for h in hours)
        + '</div>'
    )
    hm_body = ""
    for day in days:
        hm_body += '<div style="display:grid;grid-template-columns:50px repeat(11,1fr);gap:3px;margin-bottom:3px;padding:0 15px;">'
        hm_body += '<div style="font-size:10px;color:var(--text3);display:flex;align-items:center;">' + day + '</div>'
        for h in hours:
            load = random.randint(10,100)
            alpha = load/100*0.85+0.12
            if load > 70: bg = "rgba(239,68,68,{:.2f})".format(alpha)
            elif load > 40: bg = "rgba(245,158,11,{:.2f})".format(alpha)
            else: bg = "rgba(16,185,129,{:.2f})".format(alpha)
            tip = html_module.escape(day + ' ' + h + ': ' + str(load) + '% load', quote=True)
            hm_body += '<div class="wl-cell" style="background:' + bg + ';color:#fff;" onmouseover="showChartTip(event,\'' + tip + '\')" onmouseout="hideChartTip()">' + str(load) + '</div>'
        hm_body += '</div>'

    agent_wl_html = ""
    for i, ag in enumerate(TEAM_DATA["agents"]):
        st = agent_stats.get(ag["id"],{})
        pct = min(100, (st.get("at_risk",0)+st.get("churned",0))/150*100)
        clr = "#ef4444" if pct>70 else "#f59e0b" if pct>40 else "#10b981"
        agent_wl_html += (
            '<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(139,92,246,0.04);">'
            + '<div class="avatar-sm ' + av_color(i) + '">' + ag["avatar"] + '</div>'
            + '<div style="width:100px;font-size:11px;color:var(--text2);">' + ag["name"] + '</div>'
            + '<div style="flex:1;height:6px;background:rgba(139,92,246,0.07);border-radius:4px;overflow:hidden;">'
            + '<div style="width:' + str(int(pct)) + '%;height:6px;background:' + clr + ';border-radius:4px;"></div></div>'
            + '<span style="font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;color:' + clr + ';min-width:38px;">' + str(int(pct)) + '%</span>'
            + '<button class="btn btn-xs" style="color:#f9a8d4;" onclick="openTaskModal(null,\'' + ag["id"] + '\')">Task</button>'
            + '</div>'
        )
    heatmap_tab = (
        '<div id="tab-heatmap" class="tab-content ' + ("active" if active_tab=="heatmap" else "") + '">'
        + '<div class="two-col">'
        + '<div class="card-panel"><div class="card-panel-hdr"><span class="cph-title">Call Volume Heatmap</span></div>'
        + '<div style="padding:14px 0;">' + hm_hdr + hm_body + '</div></div>'
        + '<div class="card-panel"><div class="card-panel-hdr"><span class="cph-title">Agent Workload</span>'
        + '<button class="btn btn-xs btn-purple" onclick="openTaskModal()">Assign Task</button></div>'
        + '<div style="padding:10px 15px;">' + agent_wl_html + '</div></div>'
        + '</div></div>'
    )

    # KANBAN
    status_cols = [
        ("at_risk",  "At Risk",   "#f59e0b", "kc-med"),
        ("flagged",  "Flagged",   "#f472b6", "kc-med"),
        ("escalated","Escalated", "#ef4444", "kc-hi"),
        ("active",   "Active",    "#10b981", "kc-lo"),
    ]
    kanban_cols = ""
    for status, label, color, risk_cls in status_cols:
        status_df = df[df["CustStatus"]==status].sort_values("ChurnScore",ascending=False).head(12)
        cards_html = ""
        for _, row in status_df.iterrows():
            sc=float(row["ChurnScore"]); cid=str(row["CustomerID"])
            ag=AGENT_MAP.get(str(row["AssignedAgent"]),{})
            reason_short = str(row["ChurnReason"])[:26]
            cards_html += (
                '<div class="kanban-card ' + risk_cls + '" draggable="true" data-custid="' + cid + '" data-status="' + status + '">'
                + '<div class="kcard-top"><span class="kcard-id">' + cid + '</span>'
                + '<span class="drag-handle" title="Drag">&#8942;</span></div>'
                + '<div style="margin-bottom:5px;">' + score_pill(sc) + '</div>'
                + '<div class="kcard-body">' + str(row["Contract"]) + '<br>'
                + '&#8377;' + str(int(float(row["MonthlyCharge"]))) + '/mo &middot; Sat ' + str(int(row["SatisfactionScore"])) + '/5<br>'
                + '<span style="color:rgba(255,255,255,0.4);">' + ag.get("name","?")[:14] + '</span><br>'
                + '<span style="color:#f87171;font-size:9px;">' + reason_short + '</span></div>'
                + '<div class="kcard-actions">'
                + '<button class="act-btn ab-offer" onclick="event.stopPropagation();doCustomerAction(\'' + cid + '\',\'Send offer\',this)">Offer</button>'
                + '<button class="act-btn ab-call" onclick="event.stopPropagation();openTaskModal(\'' + cid + '\')">Task</button>'
                + '<button class="act-btn ab-res" onclick="event.stopPropagation();doCustomerAction(\'' + cid + '\',\'Resolve\',this)">Res</button>'
                + '</div></div>'
            )
        kanban_cols += (
            '<div class="kanban-col" data-status="' + status + '">'
            + '<div class="kc-header"><div class="kc-title" style="color:' + color + ';">' + label + '</div>'
            + '<span class="kc-count">' + str(len(status_df)) + '</span></div>'
            + '<div class="kc-body" id="kc-' + status + '">' + (cards_html if cards_html else '<div style="padding:20px;text-align:center;color:var(--text3);font-size:11px;">No cards</div>') + '</div>'
            + '</div>'
        )
    kanban_tab = (
        '<div id="tab-kanban" class="tab-content ' + ("active" if active_tab=="kanban" else "") + '">'
        + '<div style="margin-bottom:12px;padding:10px 14px;background:rgba(34,211,238,0.05);border:1px solid rgba(34,211,238,0.15);border-radius:9px;font-size:11px;color:rgba(103,232,249,0.7);">'
        + 'Drag cards between columns to update customer status. Click Task on any card to assign.</div>'
        + '<div class="kanban-board">' + kanban_cols + '</div></div>'
    )

    drilldown_tab = (
        '<div id="tab-drilldown" class="tab-content ' + ("active" if active_tab=="drilldown" else "") + '">'
        + build_hierarchical_team_table(tl_stats, agent_stats, df) + '</div>'
    )

    tab_js = '<script>setTimeout(function(){document.querySelectorAll(".reveal").forEach(function(el){el.classList.add("visible");});},100);if(document.getElementById("tab-kanban").classList.contains("active"))initKanban();</script>'
    return page_shell("t","Team View",tab_bar+leaderboard_tab+heatmap_tab+kanban_tab+drilldown_tab,ticker,tab_js)

# ── CUSTOMERS ─────────────────────────────────────────────────────────────────
@app.route("/customers")
def customers():
    r = chk()
    if r: return r
    df = df_raw.copy()
    kp = compute_kpis(df_raw)
    ticker = build_live_ticker(kp, df_raw)

    f_search   = request.args.get("search","").strip()
    f_status   = request.args.get("status","All")
    f_churn    = request.args.get("churn","All")
    f_contract = request.args.get("contract","All")
    f_score    = request.args.get("score","All")
    f_internet = request.args.get("internet","All")
    page_num   = int(request.args.get("page","1"))
    per_page   = 25

    if f_search:       df = df[df["CustomerID"].str.upper().str.contains(f_search.upper(),na=False)]
    if f_status != "All": df = df[df["CustStatus"]==f_status]
    if f_churn  != "All": df = df[df["ChurnLabel"]==f_churn]
    if f_contract!= "All": df = df[df["Contract"]==f_contract]
    if f_internet!= "All": df = df[df["InternetType"]==f_internet]
    if f_score=="High":     df = df[df["ChurnScore"]>=70]
    elif f_score=="Medium": df = df[(df["ChurnScore"]>=40)&(df["ChurnScore"]<70)]
    elif f_score=="Low":    df = df[df["ChurnScore"]<40]
    df = df.sort_values("ChurnScore",ascending=False)

    total_filtered = len(df)
    total_pages    = max(1,(total_filtered+per_page-1)//per_page)
    page_num       = max(1,min(page_num,total_pages))
    page_df        = df.iloc[(page_num-1)*per_page:page_num*per_page]

    def qstr(**kwargs):
        p={"search":f_search,"status":f_status,"churn":f_churn,"contract":f_contract,"score":f_score,"internet":f_internet}
        p.update(kwargs)
        return "&".join("{}={}".format(k,v) for k,v in p.items() if v and v!="All")

    def sel(name, val, options):
        opts = '<option value="All">All</option>'
        for o in options:
            opts += '<option {}value="{}">{}</option>'.format("selected " if val==o else "", o, o)
        return '<select name="{}">{}</select>'.format(name, opts)

    filter_bar = (
        '<form class="fbar" method="GET" action="/customers">'
        + '<div><label>Search</label><input type="text" name="search" value="' + html_module.escape(f_search) + '" placeholder="Customer ID..." style="width:120px;"></div>'
        + '<div><label>Status</label>' + sel("status", f_status, ["active","at_risk","escalated","flagged"]) + '</div>'
        + '<div><label>Churn</label>' + sel("churn", f_churn, ["Yes","No"]) + '</div>'
        + '<div><label>Risk</label>' + sel("score", f_score, ["High","Medium","Low"]) + '</div>'
        + '<div><label>Contract</label>' + sel("contract", f_contract, ["Month-to-Month","One Year","Two Year"]) + '</div>'
        + '<button class="btn btn-sm btn-purple" type="submit">Filter</button>'
        + '<a href="/customers" class="btn btn-sm btn-reset">Reset</a>'
        + '</form>'
    )

    bulk_bar_html = (
        '<div class="bulk-bar" id="bulkBar">'
        + '<span class="bulk-count" id="bulkCount">0 selected</span>'
        + '<div class="bulk-actions">'
        + '<button class="btn btn-xs btn-green" onclick="bulkAction(\'Send retention offer\')">Bulk Offer</button>'
        + '<button class="btn btn-xs" style="color:#a78bfa;" onclick="bulkAction(\'Schedule callback\')">Bulk Call</button>'
        + '<button class="btn btn-xs btn-danger" onclick="bulkAction(\'Escalate to senior\')">Escalate All</button>'
        + '<button class="btn btn-xs btn-purple" onclick="openTaskModal()">Assign Task</button>'
        + '<button class="btn btn-xs" style="color:#34d399;" onclick="bulkAction(\'Mark as resolved\')">Resolve All</button>'
        + '</div></div>'
    )

    summary_strip = (
        '<div style="display:flex;gap:10px;margin-bottom:16px;">'
        + '<div style="flex:1;background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.18);border-radius:10px;padding:11px 14px;display:flex;align-items:center;gap:10px;">'
        + '<div style="font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:rgba(248,113,113,0.7);">High Risk</div>'
        + '<div style="font-family:Space Grotesk,sans-serif;font-size:20px;font-weight:800;color:#f87171;margin-left:auto;">' + str(len(df[df["ChurnScore"]>=70])) + '</div></div>'
        + '<div style="flex:1;background:rgba(139,92,246,0.06);border:1px solid rgba(139,92,246,0.16);border-radius:10px;padding:11px 14px;display:flex;align-items:center;gap:10px;">'
        + '<div style="font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:rgba(167,139,250,0.7);">Filtered</div>'
        + '<div style="font-family:Space Grotesk,sans-serif;font-size:20px;font-weight:800;color:#c4b5fd;margin-left:auto;">' + str(total_filtered) + '</div></div>'
        + '</div>'
    )

    table_rows = ""
    for _, row in page_df.iterrows():
        sc=float(row["ChurnScore"]); cid=str(row["CustomerID"])
        ag=AGENT_MAP.get(str(row["AssignedAgent"]),{})
        # FIX: data-json attribute
        cdata_attr = html_module.escape(json.dumps(cust_data_dict(row), ensure_ascii=True), quote=True)
        sat_val = int(row["SatisfactionScore"])
        sat_clr = "#f87171" if sat_val<=2 else "#fbbf24" if sat_val<=3 else "#34d399"
        table_rows += (
            '<tr data-custid="' + cid + '">'
            + '<td><input type="checkbox" class="row-checkbox" data-id="' + cid + '" onchange="toggleRowSelect(this)"></td>'
            + '<td class="clickable-cust" data-panel-type="customer" data-json="' + cdata_attr + '" style="cursor:pointer;font-family:JetBrains Mono,monospace;font-weight:700;color:#fff;">' + cid + '</td>'
            + '<td class="score-live" data-custid="' + cid + '">' + score_pill(sc) + '</td>'
            + '<td class="editable-field" onclick="makeEditable(this,\'' + cid + '\',\'status\',\'' + str(row["CustStatus"]) + '\','
            + '[{value:\'active\',label:\'Active\'},{value:\'at_risk\',label:\'At Risk\'},'
            + '{value:\'flagged\',label:\'Flagged\'},{value:\'escalated\',label:\'Escalated\'},'
            + '{value:\'resolved\',label:\'Resolved\'}])">'
            + status_badge(str(row["CustStatus"])) + '</td>'
            + '<td style="color:var(--text2);">' + str(row["Contract"]) + '</td>'
            + '<td style="color:var(--text3);">' + str(row["InternetType"]) + '</td>'
            + '<td style="font-family:JetBrains Mono,monospace;color:#c4b5fd;">&#8377;' + "{:.2f}".format(float(row["MonthlyCharge"])) + '</td>'
            + '<td style="color:' + sat_clr + ';">' + str(sat_val) + '/5</td>'
            + '<td style="color:var(--text3);">' + ag.get("name","?") + '</td>'
            + '<td><div style="display:flex;gap:3px;" onclick="event.stopPropagation();">'
            + '<button class="act-btn ab-call" onclick="doCustomerAction(\'' + cid + '\',\'Call\',this)">Call</button>'
            + '<button class="act-btn ab-offer" onclick="doCustomerAction(\'' + cid + '\',\'Send offer\',this)">Offer</button>'
            + '<button class="act-btn ab-esc" onclick="doCustomerAction(\'' + cid + '\',\'Escalate\',this)">Esc</button>'
            + '<button class="act-btn ab-res" onclick="doCustomerAction(\'' + cid + '\',\'Resolve\',this)">Res</button>'
            + '<button class="act-btn ab-call" onclick="openTaskModal(\'' + cid + '\')" title="Assign task">Task</button>'
            + '</div></td></tr>'
        )

    if not table_rows:
        table_rows = '<tr><td colspan="10" style="text-align:center;padding:32px;color:var(--text3);">No records match filters</td></tr>'

    prev_btn = '<a href="/customers?' + qstr(page=page_num-1) + '" class="btn btn-xs">Prev</a>' if page_num>1 else '<span class="btn btn-xs" style="opacity:0.3;">Prev</span>'
    next_btn = '<a href="/customers?' + qstr(page=page_num+1) + '" class="btn btn-xs">Next</a>' if page_num<total_pages else '<span class="btn btn-xs" style="opacity:0.3;">Next</span>'

    body = (
        '<div class="slabel">Customer Intelligence — Click status to edit inline &middot; Select rows for bulk actions</div>'
        + filter_bar + summary_strip + bulk_bar_html
        + '<div class="card-panel"><div style="overflow-x:auto;"><table class="dd-table">'
        + '<tr><th><input type="checkbox" class="select-all-cb" onchange="toggleSelectAll(this)"></th>'
        + '<th>Customer ID</th><th>Risk Score</th><th>Status (click to edit)</th><th>Contract</th><th>Internet</th><th>Charge/mo</th><th>Sat</th><th>Agent</th><th>Actions</th></tr>'
        + table_rows
        + '</table></div>'
        + '<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 15px;border-top:1px solid var(--border);">'
        + '<span style="font-size:11px;color:var(--text3);">Page <b style="color:#fff;">' + str(page_num) + '</b> of ' + str(total_pages) + ' &middot; ' + str(total_filtered) + ' records</span>'
        + '<div style="display:flex;gap:5px;">' + prev_btn + next_btn + '</div></div></div>'
    )
    return page_shell("c","Customers",body,ticker)

# ── ACTION LOG ────────────────────────────────────────────────────────────────
@app.route("/actions")
def action_log_page():
    r = chk()
    if r: return r
    kp = compute_kpis(df_raw)
    ticker = build_live_ticker(kp, df_raw)
    active_tab = request.args.get("tab","tasks")

    total_tasks  = len(task_store)
    open_tasks   = sum(1 for t in task_store if t["status"]=="open")
    done_tasks   = sum(1 for t in task_store if t["status"]=="done")
    overdue_tasks= sum(1 for t in task_store if t["status"]=="overdue")
    inprog_tasks = sum(1 for t in task_store if t["status"]=="inprogress")

    resolved  = sum(1 for e in action_log if "resolv"  in e["action"].lower())
    escalated = sum(1 for e in action_log if "escal"   in e["action"].lower())
    offers    = sum(1 for e in action_log if "offer"   in e["action"].lower())
    calls     = sum(1 for e in action_log if "call"    in e["action"].lower())

    kpi_html = (
        '<div class="kpi-strip">'
        + '<div class="kpi-card kc-purple"><div class="kpi-label">Total Tasks</div><div class="kpi-val">' + str(total_tasks) + '</div></div>'
        + '<div class="kpi-card kc-amber"><div class="kpi-label">Open</div><div class="kpi-val" style="color:#fbbf24;">' + str(open_tasks) + '</div></div>'
        + '<div class="kpi-card kc-pink"><div class="kpi-label">In Progress</div><div class="kpi-val" style="color:#f9a8d4;">' + str(inprog_tasks) + '</div></div>'
        + '<div class="kpi-card kc-green"><div class="kpi-label">Completed</div><div class="kpi-val" style="color:#34d399;">' + str(done_tasks) + '</div></div>'
        + '<div class="kpi-card kc-red"><div class="kpi-label">Overdue</div><div class="kpi-val" style="color:#f87171;">' + str(overdue_tasks) + '</div></div>'
        + '</div>'
    )

    # FIX: No ALL_TABS injection — switchTab reads siblings from DOM
    def tbtn(tab_id, label):
        active_cls = "active" if active_tab == tab_id else ""
        return ('<button class="tab-btn ' + active_cls + '" data-tab="' + tab_id + '" '
                + 'onclick="switchTab(\'' + tab_id + '\')">' + label + '</button>')

    tab_bar = (
        '<div class="tab-bar">'
        + tbtn("tasks", "&#128203; Task Board")
        + tbtn("log", "&#128336; Activity Log")
        + tbtn("breakdown", "&#128202; Breakdown")
        + '</div>'
    )

    # TASK BOARD
    priority_order = {"critical": 0, "high": 1, "normal": 2}
    sorted_tasks = sorted(task_store, key=lambda t: (priority_order.get(t["priority"],2), t.get("created_at","")))

    def task_card_html(t):
        status_cls = "tc-" + t["status"]
        badge_cls  = "tsb-" + t["status"]
        title_cls  = "done-title" if t["status"]=="done" else ""
        prio_cls   = "tp-critical" if t["priority"]=="critical" else "tp-high" if t["priority"]=="high" else "tp-normal"
        ag = AGENT_MAP.get(t.get("agent_id",""),{})
        av_i = list(AGENT_MAP.keys()).index(t.get("agent_id","AG-001")) if t.get("agent_id") in AGENT_MAP else 0
        prog = int(t.get("progress",0))
        prog_clr = "#10b981" if prog>=80 else "#a78bfa" if prog>=40 else "#f59e0b"
        tid = t["id"]
        customers_disp = t.get("customer_ids","") or "-"
        hide_start   = ' style="display:none;"' if t["status"] in ["done","inprogress"] else ""
        hide_done    = ' style="display:none;"' if t["status"] == "done" else ""
        hide_overdue = ' style="display:none;"' if t["status"] in ["done"] else ""
        return (
            '<div class="task-card ' + status_cls + '" id="taskcard-' + tid + '">'
            + '<div class="task-header">'
            + '<div class="avatar-sm ' + av_color(av_i) + '">' + ag.get("avatar","??") + '</div>'
            + '<div style="flex:1;">'
            + '<div class="task-title ' + title_cls + '">' + html_module.escape(t["title"]) + '</div>'
            + '<div style="font-size:10px;color:var(--text3);">Assigned to <strong style="color:var(--text2);">' + ag.get("name","?") + '</strong></div>'
            + '</div>'
            + '<span class="task-status-badge ' + badge_cls + '">' + t["status"].upper() + '</span>'
            + '</div>'
            + '<div class="task-meta">'
            + '<span class="task-priority ' + prio_cls + '">' + t["priority"].upper() + '</span>'
            + ('<span class="task-meta-item">Due: ' + t.get("due_date","?") + '</span>' if t.get("due_date") else '')
            + ('<span class="task-meta-item">Customer: ' + html_module.escape(customers_disp[:24]) + '</span>' if customers_disp != "-" else '')
            + '<span class="task-meta-item" style="margin-left:auto;font-family:JetBrains Mono,monospace;">' + tid + '</span>'
            + '</div>'
            + ('<div class="task-notes">' + html_module.escape(t["notes"]) + '</div>' if t.get("notes") else '')
            + '<div><div style="display:flex;justify-content:space-between;font-size:9px;color:var(--text3);margin-bottom:3px;margin-top:8px;"><span>Progress</span><span style="color:' + prog_clr + ';">' + str(prog) + '%</span></div>'
            + '<div class="task-progress-bar"><div class="task-progress-fill" style="width:' + str(prog) + '%;background:' + prog_clr + ';"></div></div></div>'
            + '<div class="task-actions">'
            + ('<button class="btn btn-xs btn-green" onclick="updateTask(\'' + tid + '\',\'done\',100)"' + hide_done + '>Complete</button>')
            + ('<button class="btn btn-xs btn-purple" onclick="updateTask(\'' + tid + '\',\'inprogress\')"' + hide_start + '>Start</button>')
            + '<button class="btn btn-xs" onclick="setProgress(\'' + tid + '\')" style="color:var(--text3);">Set Progress</button>'
            + ('<button class="btn btn-xs btn-danger" onclick="updateTask(\'' + tid + '\',\'overdue\')"' + hide_overdue + '>Mark Overdue</button>')
            + '<span style="font-size:10px;color:var(--text3);margin-left:auto;">' + t.get("created_at","?") + '</span>'
            + '</div></div>'
        )

    tasks_by_status = {"open":[],"inprogress":[],"done":[],"overdue":[]}
    for t in sorted_tasks:
        tasks_by_status.setdefault(t["status"],[]).append(t)

    col_info = [
        ("open","Open","#f59e0b"),
        ("inprogress","In Progress","#a78bfa"),
        ("done","Done","#10b981"),
        ("overdue","Overdue","#ef4444"),
    ]
    task_board_html = '<div class="kanban-board" style="grid-template-columns:repeat(4,1fr);">'
    for st, label, clr in col_info:
        ts_list = tasks_by_status.get(st, [])
        body_content = "".join(task_card_html(t) for t in ts_list) if ts_list else '<div style="padding:20px;text-align:center;color:var(--text3);font-size:11px;">No tasks</div>'
        task_board_html += (
            '<div class="kanban-col">'
            + '<div class="kc-header"><div class="kc-title" style="color:' + clr + ';">' + label + '</div>'
            + '<span class="kc-count">' + str(len(ts_list)) + '</span></div>'
            + '<div class="kc-body">' + body_content + '</div>'
            + '</div>'
        )
    task_board_html += '</div>'

    if not sorted_tasks:
        task_board_html = (
            '<div style="text-align:center;padding:60px 20px;color:var(--text3);">'
            + '<div style="font-size:36px;margin-bottom:12px;opacity:0.4;">&#128203;</div>'
            + '<div style="font-family:Space Grotesk,sans-serif;font-size:14px;font-weight:600;color:rgba(170,150,230,0.3);margin-bottom:8px;">No tasks assigned yet</div>'
            + '<button class="btn btn-purple" onclick="openTaskModal()">Assign First Task</button>'
            + '</div>'
        )

    tasks_tab = (
        '<div id="tab-tasks" class="tab-content ' + ("active" if active_tab=="tasks" else "") + '">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">'
        + '<div style="font-size:11px;color:var(--text3);">Tasks assigned to agents</div>'
        + '<button class="btn btn-purple" onclick="openTaskModal()">+ Assign New Task</button>'
        + '</div>'
        + task_board_html + '</div>'
    )

    # ACTIVITY LOG
    log_items = list(reversed(action_log))
    icon_map = {"Schedule callback":"&#128222;","Send retention offer":"&#127873;","Send offer":"&#127873;","Escalate to senior":"&#11014;","Escalate":"&#11014;","Flag for review":"&#128681;","Mark as resolved":"&#10003;","Resolve":"&#10003;"}
    if log_items:
        timeline_html = ""
        for i, entry in enumerate(log_items):
            al = entry["action"].lower()
            icon = "&#128204;"
            for k,v in icon_map.items():
                if k.lower() in al: icon = v; break
            dot_clr = "#f87171" if "escal" in al else "#34d399" if ("resolv" in al or "done" in al) else "#a78bfa" if "task" in al else "#fbbf24"
            is_bulk = "[BULK]" in entry["action"]
            is_task = "task assigned" in al
            bulk_badge = '<span class="tag tag-purple" style="margin-left:6px;">BULK</span>' if is_bulk else ''
            task_badge = '<span class="tag tag-amber" style="margin-left:6px;">TASK</span>' if is_task else ''
            connector = '<div style="width:1px;flex:1;background:rgba(139,92,246,0.12);min-height:16px;"></div>' if i < len(log_items)-1 else ''
            timeline_html += (
                '<div class="alog-item">'
                + '<div style="display:flex;flex-direction:column;align-items:center;">'
                + '<div style="width:10px;height:10px;border-radius:50%;background:' + dot_clr + ';flex-shrink:0;box-shadow:0 0 8px ' + dot_clr + '66;"></div>'
                + connector + '</div>'
                + '<div class="alog-icon" style="background:rgba(139,92,246,0.1);">' + icon + '</div>'
                + '<div class="alog-body"><div class="alog-title">' + html_module.escape(entry["action"].replace("[BULK] ","")) + bulk_badge + task_badge + '</div>'
                + '<div class="alog-sub">Customer <b style="color:rgba(228,210,255,0.6);font-family:JetBrains Mono,monospace;">' + html_module.escape(str(entry["customer_id"])) + '</b> &middot; By ' + html_module.escape(str(entry["agent"])) + '</div></div>'
                + '<div class="alog-ts">' + str(entry["ts"]) + '</div></div>'
            )
    else:
        timeline_html = '<div style="text-align:center;padding:40px;color:var(--text3);">No activity yet this session. Try taking actions on customers!</div>'

    log_tab = (
        '<div id="tab-log" class="tab-content ' + ("active" if active_tab=="log" else "") + '">'
        + '<div class="card-panel">'
        + '<div class="card-panel-hdr"><span class="cph-title"><span class="live-dot"></span>Activity Timeline</span>'
        + '<span class="cph-meta">' + str(len(action_log)) + ' actions</span></div>'
        + '<div>' + timeline_html + '</div></div></div>'
    )

    # BREAKDOWN
    breakdown_items = [
        ("Calls", calls, "#a78bfa"),
        ("Offers", offers, "#34d399"),
        ("Escalations", escalated, "#f87171"),
        ("Resolved", resolved, "#67e8f9"),
        ("Tasks", total_tasks, "#fbbf24"),
    ]
    max_bd = max((v for _,v,_ in breakdown_items),default=1) or 1
    breakdown_html = "".join(
        '<div class="stat-bar-row"><span class="stat-bar-label">' + lbl + '</span>'
        + '<div class="stat-bar-track"><div class="stat-bar-fill" style="width:' + str(int(v/max_bd*100)) + '%;background:' + clr + ';"></div></div>'
        + '<span class="stat-bar-val" style="color:' + clr + ';">' + str(v) + '</span></div>'
        for lbl,v,clr in breakdown_items
    )

    agent_task_html = ""
    for ag in TEAM_DATA["agents"]:
        my_tasks = [t for t in task_store if t.get("agent_id")==ag["id"]]
        if not my_tasks: continue
        done = sum(1 for t in my_tasks if t["status"]=="done")
        pct = round(done/len(my_tasks)*100) if my_tasks else 0
        av_i = list(AGENT_MAP.keys()).index(ag["id"])
        agent_task_html += (
            '<div style="display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid rgba(139,92,246,0.04);">'
            + '<div class="avatar-sm ' + av_color(av_i) + '">' + ag["avatar"] + '</div>'
            + '<div style="width:110px;font-size:11px;color:var(--text2);">' + ag["name"] + '</div>'
            + '<span style="font-size:10px;color:var(--text3);">' + str(len(my_tasks)) + ' tasks</span>'
            + '<div style="flex:1;height:5px;background:rgba(139,92,246,0.07);border-radius:4px;overflow:hidden;">'
            + '<div style="width:' + str(pct) + '%;height:5px;background:#34d399;border-radius:4px;"></div></div>'
            + '<span style="font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;color:#34d399;">' + str(pct) + '%</span>'
            + '</div>'
        )

    breakdown_tab = (
        '<div id="tab-breakdown" class="tab-content ' + ("active" if active_tab=="breakdown" else "") + '">'
        + '<div class="two-col">'
        + '<div class="card-panel"><div class="card-panel-hdr"><span class="cph-title">Action Breakdown</span></div>'
        + '<div style="padding:14px 15px;">' + breakdown_html + '</div></div>'
        + '<div class="card-panel"><div class="card-panel-hdr"><span class="cph-title">Agent Task Completion</span></div>'
        + '<div style="padding:10px 15px;">' + (agent_task_html if agent_task_html else '<div style="padding:20px;color:var(--text3);font-size:11px;">No tasks yet. Assign tasks to agents to track completion.</div>') + '</div></div>'
        + '</div></div>'
    )

    task_js = """<script>
function updateTask(tid, status, progress) {
  var payload = {task_id: tid, status: status};
  if (progress !== undefined) payload.progress = progress;
  fetch('/api/task/update', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
    .then(function(r) { return r.json(); })
    .then(function(d) { if (d.ok) { showToast('Task updated', 'Status: ' + status, 'green'); setTimeout(function(){ location.reload(); }, 800); } })
    .catch(function(e){ console.error(e); });
}
function setProgress(tid) {
  var pct = prompt('Enter progress % (0-100):', '50');
  if (pct === null) return;
  pct = Math.max(0, Math.min(100, parseInt(pct) || 0));
  var status = pct >= 100 ? 'done' : pct > 0 ? 'inprogress' : 'open';
  fetch('/api/task/update', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({task_id:tid, status:status, progress:pct})})
    .then(function(r) { return r.json(); })
    .then(function(d) { if (d.ok) { showToast('Progress set to ' + pct + '%', '', 'green'); setTimeout(function(){ location.reload(); }, 600); } })
    .catch(function(e){ console.error(e); });
}
setTimeout(function(){document.querySelectorAll('.reveal').forEach(function(el){el.classList.add('visible');});}, 80);
</script>"""
    return page_shell("a","Action Log",kpi_html+tab_bar+tasks_tab+log_tab+breakdown_tab,ticker,task_js)

# ── INSIGHTS ──────────────────────────────────────────────────────────────────
@app.route("/insights")
def insights():
    r = chk()
    if r: return r
    df = df_raw
    kp = compute_kpis(df)
    ticker = build_live_ticker(kp, df)
    active_tab = request.args.get("tab", "overview")

    # FIX: No ALL_TABS injection — switchTab reads siblings from DOM
    def tbtn(tab_id, label):
        active_cls = "active" if active_tab == tab_id else ""
        return ('<button class="tab-btn ' + active_cls + '" data-tab="' + tab_id + '" '
                + 'onclick="switchTab(\'' + tab_id + '\')">' + label + '</button>')

    tab_bar = (
        '<div class="tab-bar">'
        + tbtn("overview", "&#128202; Overview")
        + tbtn("segments", "&#127914; Segments")
        + tbtn("drivers", "&#128269; Churn Drivers")
        + tbtn("cohorts", "&#128101; Cohorts")
        + '</div>'
    )

    # ═══ OVERVIEW TAB ═══
    cat_counts = df[df["ChurnLabel"]=="Yes"]["ChurnCategory"].value_counts().to_dict()
    donut_svg, donut_legend = make_donut(cat_counts, size=170)
    contract_counts = df["Contract"].value_counts().to_dict()
    contract_donut_svg, contract_donut_legend = make_donut(contract_counts, size=170)
    random.seed(7)
    score_dist_trend = [round(random.uniform(70,90),1) for _ in range(10)]

    overview_kpis = (
        '<div class="kpi-strip">'
        + '<div class="kpi-card kc-purple"><div class="kpi-label">Total Customers</div><div class="kpi-val">' + str(kp["total"]) + '</div></div>'
        + '<div class="kpi-card kc-red"><div class="kpi-label">Churn Rate</div><div class="kpi-val" style="color:#f87171;">' + str(kp["rate"]) + '%</div></div>'
        + '<div class="kpi-card kc-amber"><div class="kpi-label">Total Revenue</div><div class="kpi-val" style="color:#fbbf24;">' + fmt_money(kp["total_revenue"]) + '</div></div>'
        + '<div class="kpi-card kc-pink"><div class="kpi-label">Avg CLTV</div><div class="kpi-val" style="color:#f9a8d4;">' + fmt_money(kp["avg_cltv"]) + '</div></div>'
        + '<div class="kpi-card kc-green"><div class="kpi-label">Avg Satisfaction</div><div class="kpi-val" style="color:#34d399;">' + str(kp["avg_sat"]) + '/5</div></div>'
        + '</div>'
    )

    overview_charts = (
        '<div class="two-col">'
        + '<div class="chart-container"><div class="chart-title">Customer Base by Contract Type</div>'
        + '<div style="display:flex;align-items:center;gap:18px;">' + contract_donut_svg + '<div style="flex:1;">' + contract_donut_legend + '</div></div></div>'
        + '</div>'
    )

    bands = [("0-39 (Low)",0,40,"#34d399"),("40-69 (Medium)",40,70,"#fbbf24"),("70-100 (High)",70,101,"#f87171")]
    band_rows = ""
    max_band = max(int(((df["ChurnScore"]>=lo)&(df["ChurnScore"]<hi)).sum()) for _,lo,hi,_ in bands) or 1
    for lbl,lo,hi,clr in bands:
        cnt = int(((df["ChurnScore"]>=lo)&(df["ChurnScore"]<hi)).sum())
        pct_w = cnt/max_band*100
        band_rows += (
            '<div class="stat-bar-row"><span class="stat-bar-label">' + lbl + '</span>'
            + '<div class="stat-bar-track"><div class="stat-bar-fill" style="width:' + str(int(pct_w)) + '%;background:' + clr + ';"></div></div>'
            + '<span class="stat-bar-val" style="color:' + clr + ';">' + str(cnt) + '</span></div>'
        )

    overview_bottom = (
        '<div class="two-col">'
        + '<div class="chart-container"><div class="chart-title">Risk Score Distribution</div>'
        + '<div style="padding-top:6px;">' + band_rows + '</div></div>'
        + '<div class="chart-container"><div class="chart-title">Churn Score Trend <span style="font-size:10px;color:var(--text3);font-weight:400;">(sampled)</span></div>'
        + '<div style="padding:14px 0;">' + make_sparkline(score_dist_trend, width=320, height=70, color="#a78bfa") + '</div>'
        + '<div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text3);margin-top:4px;"><span>10 periods ago</span><span>Now</span></div></div>'
        + '</div>'
    )

    overview_tab = (
        '<div id="tab-overview" class="tab-content ' + ("active" if active_tab=="overview" else "") + '">'
        + overview_kpis + overview_charts + overview_bottom + '</div>'
    )

    # ═══ SEGMENTS TAB ═══
    def segment_bar_block(title, series_dict, color_key="rate"):
        rows = ""
        items = sorted(series_dict.items(), key=lambda kv: kv[1], reverse=True)
        max_v = max((v for _,v in items), default=1) or 1
        for lbl, v in items:
            clr = "#f87171" if (color_key=="rate" and v>40) else "#fbbf24" if (color_key=="rate" and v>20) else "#34d399" if color_key=="rate" else "#a78bfa"
            pct_w = v/max_v*100
            disp = (str(v)+"%") if color_key=="rate" else str(v)
            rows += (
                '<div class="stat-bar-row"><span class="stat-bar-label">' + str(lbl) + '</span>'
                + '<div class="stat-bar-track"><div class="stat-bar-fill" style="width:' + str(int(pct_w)) + '%;background:' + clr + ';"></div></div>'
                + '<span class="stat-bar-val" style="color:' + clr + ';">' + disp + '</span></div>'
            )
        return '<div class="chart-container"><div class="chart-title">' + title + '</div><div style="padding-top:6px;">' + rows + '</div></div>'

    def churn_rate_by(col):
        out = {}
        for val, sub in df.groupby(col):
            total = len(sub)
            if total == 0: continue
            churned = int((sub["ChurnLabel"]=="Yes").sum())
            out[val] = round(churned/total*100,1)
        return out

    contract_rate = churn_rate_by("Contract")
    internet_rate = churn_rate_by("InternetType")
    payment_rate  = churn_rate_by("PaymentMethod")
    gender_rate   = churn_rate_by("Gender")

    segments_grid = (
        '<div class="two-col">'
        + segment_bar_block("Churn Rate by Contract Type", contract_rate)
        + segment_bar_block("Churn Rate by Internet Type", internet_rate)
        + '</div>'
        + '<div class="two-col">'
        + segment_bar_block("Churn Rate by Payment Method", payment_rate)
        + segment_bar_block("Churn Rate by Gender", gender_rate)
        + '</div>'
    )

    offer_counts = df[df["Offer"]!="None"]["Offer"].value_counts().head(8)
    offer_rows = ""
    if len(offer_counts) > 0:
        for off, cnt in offer_counts.items():
            sub = df[df["Offer"]==off]
            churned_n = int((sub["ChurnLabel"]=="Yes").sum())
            rate = round(churned_n/len(sub)*100,1) if len(sub)>0 else 0
            clr = "#f87171" if rate>40 else "#fbbf24" if rate>20 else "#34d399"
            offer_rows += (
                '<tr><td style="color:#fff;font-weight:600;">' + str(off) + '</td>'
                + '<td>' + str(int(cnt)) + '</td>'
                + '<td style="color:' + clr + ';font-family:JetBrains Mono,monospace;font-weight:700;">' + str(rate) + '%</td></tr>'
            )
    else:
        offer_rows = '<tr><td colspan="3" style="text-align:center;color:var(--text3);padding:20px;">No offer data available</td></tr>'

    offers_table = (
        '<div class="card-panel"><div class="card-panel-hdr"><span class="cph-title">Retention Offer Performance</span></div>'
        + '<table class="dd-table"><tr><th>Offer</th><th>Customers</th><th>Churn Rate</th></tr>' + offer_rows + '</table></div>'
    )

    segments_tab = (
        '<div id="tab-segments" class="tab-content ' + ("active" if active_tab=="segments" else "") + '">'
        + segments_grid + offers_table + '</div>'
    )

    # ═══ DRIVERS TAB ═══
    churned_df = df[df["ChurnLabel"]=="Yes"]
    reason_counts = churned_df["ChurnReason"].value_counts().head(10)
    max_reason = int(reason_counts.max()) if len(reason_counts) > 0 else 1
    reason_rows = ""
    for reason, cnt in reason_counts.items():
        pct_w = cnt/max_reason*100
        reason_rows += (
            '<div class="stat-bar-row"><span class="stat-bar-label" title="' + html_module.escape(str(reason), quote=True) + '">' + html_module.escape(str(reason))[:42] + '</span>'
            + '<div class="stat-bar-track"><div class="stat-bar-fill" style="width:' + str(int(pct_w)) + '%;background:#f87171;"></div></div>'
            + '<span class="stat-bar-val" style="color:#f87171;">' + str(int(cnt)) + '</span></div>'
        )
    if not reason_rows:
        reason_rows = '<div style="text-align:center;color:var(--text3);padding:20px;">No churn reason data available</div>'

    drivers_top = (
        '<div class="chart-container"><div class="chart-title">Top Churn Reasons</div>' + reason_rows + '</div>'
    )

    rev_by_cat = churned_df.groupby("ChurnCategory")["MonthlyCharge"].sum().sort_values(ascending=False)
    rev_rows = ""
    max_rev = float(rev_by_cat.max()) if len(rev_by_cat) > 0 else 1
    for cat, rev in rev_by_cat.items():
        pct_w = rev/max_rev*100 if max_rev else 0
        rev_rows += (
            '<div class="stat-bar-row"><span class="stat-bar-label">' + str(cat) + '</span>'
            + '<div class="stat-bar-track"><div class="stat-bar-fill" style="width:' + str(int(pct_w)) + '%;background:#fbbf24;"></div></div>'
            + '<span class="stat-bar-val" style="color:#fbbf24;">' + fmt_money(rev) + '</span></div>'
        )
    if not rev_rows:
        rev_rows = '<div style="text-align:center;color:var(--text3);padding:20px;">No revenue-loss data available</div>'

    drivers_bottom = '<div class="chart-container"><div class="chart-title">Monthly Revenue Lost by Churn Category</div>' + rev_rows + '</div>'
    drivers_tab = (
        '<div id="tab-drivers" class="tab-content ' + ("active" if active_tab=="drivers" else "") + '">'
        + drivers_top + drivers_bottom + '</div>'
    )

    # ═══ COHORTS TAB ═══
    tenure_bins = [(0,12,"0-12 mo"),(12,24,"12-24 mo"),(24,48,"24-48 mo"),(48,72,"48-72 mo"),(72,999,"72+ mo")]
    tenure_rows = ""
    max_tenure_n = 1
    tenure_data = []
    for lo,hi,lbl in tenure_bins:
        sub = df[(df["TenureinMonths"]>=lo)&(df["TenureinMonths"]<hi)]
        total = len(sub)
        churned_n = int((sub["ChurnLabel"]=="Yes").sum())
        rate = round(churned_n/total*100,1) if total>0 else 0
        tenure_data.append((lbl,total,rate))
        max_tenure_n = max(max_tenure_n, total)
    for lbl,total,rate in tenure_data:
        clr = "#f87171" if rate>40 else "#fbbf24" if rate>20 else "#34d399"
        pct_w = total/max_tenure_n*100 if max_tenure_n else 0
        tenure_rows += (
            '<div class="stat-bar-row"><span class="stat-bar-label">' + lbl + '</span>'
            + '<div class="stat-bar-track"><div class="stat-bar-fill" style="width:' + str(int(pct_w)) + '%;background:' + clr + ';"></div></div>'
            + '<span class="stat-bar-val" style="color:' + clr + ';">' + str(rate) + '%</span></div>'
        )

    sat_rows = ""
    max_sat_n = 1
    sat_data = []
    for s in range(1,6):
        sub = df[df["SatisfactionScore"]==s]
        total = len(sub)
        churned_n = int((sub["ChurnLabel"]=="Yes").sum())
        rate = round(churned_n/total*100,1) if total>0 else 0
        sat_data.append((s,total,rate))
        max_sat_n = max(max_sat_n, total)
    for s,total,rate in sat_data:
        clr = "#f87171" if rate>40 else "#fbbf24" if rate>20 else "#34d399"
        pct_w = total/max_sat_n*100 if max_sat_n else 0
        sat_rows += (
            '<div class="stat-bar-row"><span class="stat-bar-label">Satisfaction ' + str(s) + '/5</span>'
            + '<div class="stat-bar-track"><div class="stat-bar-fill" style="width:' + str(int(pct_w)) + '%;background:' + clr + ';"></div></div>'
            + '<span class="stat-bar-val" style="color:' + clr + ';">' + str(rate) + '%</span></div>'
        )

    cohorts_top = (
        '<div class="two-col">'
        + '<div class="chart-container"><div class="chart-title">Churn Rate by Tenure</div>' + tenure_rows + '</div>'
        + '<div class="chart-container"><div class="chart-title">Churn Rate by Satisfaction Score</div>' + sat_rows + '</div>'
        + '</div>'
    )

    age_bins = [(0,30,"&lt;30"),(30,45,"30-45"),(45,60,"45-60"),(60,200,"60+")]
    age_rows = ""
    for lo,hi,lbl in age_bins:
        sub = df[(df["Age"]>=lo)&(df["Age"]<hi)]
        total = len(sub)
        if total == 0: continue
        churned_n = int((sub["ChurnLabel"]=="Yes").sum())
        rate = round(churned_n/total*100,1)
        clr = "#f87171" if rate>40 else "#fbbf24" if rate>20 else "#34d399"
        age_rows += (
            '<div class="stat-bar-row"><span class="stat-bar-label">Age ' + lbl + ' (' + str(total) + ' cust.)</span>'
            + '<div class="stat-bar-track"><div class="stat-bar-fill" style="width:' + str(min(100,int(rate*1.5))) + '%;background:' + clr + ';"></div></div>'
            + '<span class="stat-bar-val" style="color:' + clr + ';">' + str(rate) + '%</span></div>'
        )
    if not age_rows:
        age_rows = '<div style="text-align:center;color:var(--text3);padding:20px;">No age data available</div>'

    cohorts_bottom = '<div class="chart-container"><div class="chart-title">Churn Rate by Age Group</div>' + age_rows + '</div>'
    cohorts_tab = (
        '<div id="tab-cohorts" class="tab-content ' + ("active" if active_tab=="cohorts" else "") + '">'
        + cohorts_top + cohorts_bottom + '</div>'
    )

    body = tab_bar + overview_tab + segments_tab + drivers_tab + cohorts_tab
    extra_js = '<script>setTimeout(function(){document.querySelectorAll(".reveal").forEach(function(el){el.classList.add("visible");});},80);</script>'
    return page_shell("i", "Insights", body, ticker, extra_js)

if __name__ == "__main__":
    def _open_browser():
        time.sleep(1.2)
        webbrowser.open("http://127.0.0.1:5000")
    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(debug=True, port=5000)