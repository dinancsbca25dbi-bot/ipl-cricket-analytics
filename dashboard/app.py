"""
IPL Matches Dashboard  -  Domain C (Matches)  -  animated UI edition (single file)
Run from the project folder:   streamlit run dashboard/app.py

The page is empty until you upload data. Use the ONE upload box in the sidebar:
select your matches file and your deliveries (ball-by-ball) file together
(a teams file is optional; one merged file also works). The app works out
which file is which and finds the columns by itself, whatever they are called.
Every number on the page comes from a SQL query sent through q().

UI extras (all inside this one file, no other file needed):
  banner with bowling cricket ball, dark/light switch, count-up KPI cards,
  charts that draw themselves in (with a replay button), hover lifts, styled tabs.
"""
import hashlib
import io
import math
import re
import sqlite3
import textwrap

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="IPL Matches Dashboard", page_icon="🏏", layout="wide")

# ----------------------------------------------------------------------------
# 1. CONFIG: colours and team names
# ----------------------------------------------------------------------------
NAVY, TEAL, AMBER = "#102A43", "#0E9AA7", "#F4A300"
CORAL, PLUM, BLUE, GREEN = "#E4572E", "#6C4AB6", "#2F6FED", "#2BA84A"
INN_COL = {1: AMBER, 2: PLUM}  # innings 1 = amber, innings 2 = plum (Tab 2)
FONT = "DM Sans, system-ui, sans-serif"

TEAM_FIX = {
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Royal Challengers Bengaluru": "Royal Challengers Bangalore",
    "Rising Pune Supergiant": "Rising Pune Supergiants",
}
ABBR = {
    "Chennai Super Kings": "CSK", "Mumbai Indians": "MI", "Kolkata Knight Riders": "KKR",
    "Royal Challengers Bangalore": "RCB", "Sunrisers Hyderabad": "SRH", "Rajasthan Royals": "RR",
    "Delhi Capitals": "DC", "Punjab Kings": "PBKS", "Gujarat Titans": "GT",
    "Lucknow Super Giants": "LSG", "Deccan Chargers": "DCH", "Pune Warriors": "PWI",
    "Rising Pune Supergiants": "RPS", "Gujarat Lions": "GL", "Kochi Tuskers Kerala": "KTK",
}


def abbr(team):
    if team is None or (isinstance(team, float) and math.isnan(team)):
        return "-"
    return ABBR.get(team, "".join(w[0] for w in str(team).split()).upper())


# ----------------------------------------------------------------------------
# 1b. UI KIT: theme, CSS animations, banner, cards, self-drawing charts
# ----------------------------------------------------------------------------
def _vars(dark):
    if dark:
        return (":root{--bg:#0B1620;--fg:#E6EDF3;--card:#13222F;--line:#26394A;--muted:#9FB3C8;"
                "--shadow:rgba(0,0,0,.55);--side1:#0F1D29;--side2:#0B1620;}")
    return (":root{--bg:#F4F7FA;--fg:#102A43;--card:#FFFFFF;--line:#D9E2EC;--muted:#627D98;"
            "--shadow:rgba(16,42,67,.18);--side1:#FFFFFF;--side2:#E9F1F6;}")


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&family=DM+Sans:wght@400;500;700&display=swap');
html, body, .stApp { font-family: 'DM Sans', system-ui, sans-serif; }
.stApp { background: var(--bg); color: var(--fg); transition: background .45s ease, color .45s ease; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.4rem; max-width: 1400px; }
.stMarkdown p, label, [data-testid="stWidgetLabel"] p { color: var(--fg); }
[data-testid="stCaptionContainer"] { color: var(--muted); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: linear-gradient(#0E9AA7, #6C4AB6); border-radius: 8px; }

[data-testid="stSidebar"] { background: linear-gradient(180deg, var(--side1), var(--side2)); border-right: 1px solid var(--line); }
[data-testid="stSidebar"] .stButton > button { width: 100%; }

.ipl-banner { position: relative; overflow: hidden; border-radius: 18px; padding: 22px 28px 34px;
  background: linear-gradient(120deg, #102A43, #0E6E8C, #0E9AA7, #6C4AB6, #102A43);
  background-size: 320% 320%; animation: iplGrad 14s ease infinite;
  box-shadow: 0 14px 34px -14px var(--shadow); margin-bottom: 14px; }
.ipl-title { font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif; font-weight: 800;
  font-size: clamp(1.5rem, 3.2vw, 2.4rem); color: #fff; letter-spacing: -.01em; line-height: 1.1; }
.ipl-sub { color: rgba(255,255,255,.85); font-size: .95rem; margin-top: 6px; max-width: 60ch; }
.ipl-pitch { position: absolute; left: 0; right: 0; bottom: 12px; height: 2px;
  background: repeating-linear-gradient(90deg, rgba(255,255,255,.35) 0 10px, transparent 10px 20px); }
.ipl-ball-x { position: absolute; bottom: 0; left: -40px; animation: iplFly 3.6s linear infinite; }
.ipl-ball-y { animation: iplBounce 3.6s infinite; }
.ipl-ball { width: 22px; height: 22px; border-radius: 50%; position: relative;
  background: radial-gradient(circle at 30% 28%, #ff7a59, #C1272D 62%, #7d1519);
  box-shadow: 0 6px 10px rgba(0,0,0,.35); animation: iplSpin .7s linear infinite; }
.ipl-ball::before { content: ""; position: absolute; inset: 0; border-radius: 50%;
  border-top: 2px dashed rgba(255,255,255,.9); transform: translateY(8px) scaleX(.9); }
@keyframes iplGrad { 0% {background-position: 0% 50%} 50% {background-position: 100% 50%} 100% {background-position: 0% 50%} }
@keyframes iplFly { from {left: -40px} to {left: calc(100% + 20px)} }
@keyframes iplBounce { 0% {transform: translateY(-30px)} 52% {transform: translateY(0)} 60% {transform: translateY(-12px)} 100% {transform: translateY(-26px)} }
@keyframes iplSpin { to {transform: rotate(360deg)} }

.ipl-kpi { position: relative; overflow: hidden; border-radius: 16px; padding: 15px 20px; color: #fff;
  background: linear-gradient(135deg, var(--c), color-mix(in srgb, var(--c) 70%, #000));
  box-shadow: 0 10px 22px -12px var(--c); cursor: default;
  transition: transform .28s cubic-bezier(.2,.8,.2,1), box-shadow .28s ease;
  animation: iplPop .7s cubic-bezier(.2,.9,.25,1.2) both; }
.ipl-kpi:hover { transform: translateY(-6px) scale(1.025); box-shadow: 0 22px 34px -14px var(--c); }
.ipl-kpi::after { content: ""; position: absolute; top: 0; left: -60%; width: 40%; height: 100%;
  background: linear-gradient(100deg, transparent, rgba(255,255,255,.28), transparent);
  transform: skewX(-20deg); animation: iplSweep 5.5s ease-in-out infinite; }
.ipl-kpi .l { font-size: .74rem; font-weight: 700; letter-spacing: .05em; opacity: .95; }
.ipl-kpi .v { font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif; font-size: 1.9rem; font-weight: 800; line-height: 1.25; }
.ipl-kpi .s { font-size: .75rem; opacity: .9; }
@keyframes iplSweep { 0%, 55% {left: -60%} 100% {left: 140%} }
@keyframes iplPop { from {opacity: 0; transform: translateY(18px) scale(.94)} to {opacity: 1; transform: none} }

.ipl-mc { background: var(--card); color: var(--fg); border: 1.5px solid var(--line); border-radius: 12px;
  padding: 11px 16px; transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
  animation: iplPop .6s ease both; }
.ipl-mc:hover { transform: translateY(-4px); box-shadow: 0 14px 24px -14px var(--shadow); border-color: #0E9AA7; }
.ipl-mc.hl { border: 2.5px solid #1E88E5; animation: iplPop .6s ease both, iplGlow 2.4s ease-in-out infinite 1s; }
.ipl-mc .l { font-size: .7rem; font-weight: 800; color: var(--muted); }
.ipl-mc .v { font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 800; }
@keyframes iplGlow { 0%, 100% {box-shadow: 0 0 0 0 rgba(30,136,229,0)} 50% {box-shadow: 0 0 0 6px rgba(30,136,229,.18)} }

[data-testid="stPlotlyChart"] { animation: iplPop .75s cubic-bezier(.2,.8,.2,1) both; border-radius: 12px; }
[data-testid="stVerticalBlockBorderWrapper"] { transition: box-shadow .3s ease, border-color .3s ease; border-radius: 14px; }
[data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow: 0 16px 28px -18px var(--shadow); }

.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: 8px 18px; font-weight: 700; color: var(--muted);
  transition: background .25s ease, color .25s ease, transform .25s ease; }
.stTabs [data-baseweb="tab"]:hover { background: color-mix(in srgb, #0E9AA7 14%, transparent); color: var(--fg); transform: translateY(-2px); }
.stTabs [aria-selected="true"] { color: #0E9AA7; }
.stTabs [data-baseweb="tab-highlight"] { height: 3px; background: linear-gradient(90deg, #0E9AA7, #6C4AB6); border-radius: 3px; }

[data-baseweb="select"] > div { transition: box-shadow .25s ease, border-color .25s ease; }
[data-baseweb="select"] > div:hover { box-shadow: 0 0 0 3px color-mix(in srgb, #0E9AA7 25%, transparent); border-color: #0E9AA7; }
[data-baseweb="select"] > div:focus-within { box-shadow: 0 0 0 3px color-mix(in srgb, #6C4AB6 30%, transparent); }
.stRadio label { transition: transform .2s ease; }
.stRadio label:hover { transform: translateX(3px); }
.stButton > button { border-radius: 12px; font-weight: 700; border: 1.5px solid var(--line);
  transition: transform .2s ease, box-shadow .2s ease; }
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 10px 18px -10px var(--shadow); border-color: #0E9AA7; }
.stButton > button:active { transform: scale(.96); }

.ipl-dark [data-baseweb="select"] > div, .ipl-dark [data-baseweb="input"] > div { background: var(--card); color: var(--fg); border-color: var(--line); }
.ipl-dark [data-baseweb="select"] span, .ipl-dark [data-baseweb="select"] input { color: var(--fg); }
.ipl-dark .stButton > button { background: var(--card); color: var(--fg); }
.ipl-dark [data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--line); }
.ipl-dark [data-testid="stAlert"] { background: var(--card); }
.ipl-dark [data-testid="stMarkdownContainer"] h1, .ipl-dark [data-testid="stMarkdownContainer"] h2 { color: var(--fg); }

@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
"""

JS = """
<script>
(function () {
  const P = window.parent, D = P.document, REPLAY = %REPLAY%, DARK = %DARK%;
  const app = D.querySelector('.stApp');
  D.body.classList.toggle('ipl-dark', DARK);
  if (app) app.classList.toggle('ipl-dark', DARK);
  if (P.__iplTimer) P.clearInterval(P.__iplTimer);
  if (P.__iplReplay !== REPLAY || !P.__iplSigs) {
    P.__iplReplay = REPLAY; P.__iplSigs = new WeakMap();
    D.querySelectorAll('.ipl-kpi .v').forEach(el => delete el.dataset.done);
  }
  const NUM = /\\d[\\d,]*(\\.\\d+)?/g;
  function count(el) {
    if (el.dataset.done) return;
    el.dataset.done = '1';
    const txt = el.textContent, t0 = performance.now(), dur = 1100;
    if (!/\\d/.test(txt)) return;
    (function tick(now) {
      const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      el.textContent = txt.replace(NUM, s => {
        const dec = (s.split('.')[1] || '').length, v = parseFloat(s.replace(/,/g, '')) * e;
        return s.includes(',') ? v.toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec}) : v.toFixed(dec);
      });
      if (k < 1) P.requestAnimationFrame(tick); else el.textContent = txt;
    })(performance.now());
  }
  function autoplay(gd) {
    const t = (gd.layout && gd.layout.title && gd.layout.title.text) || '';
    const sig = t + '|' + (gd.layout && gd.layout.height);
    if (P.__iplSigs.get(gd) === sig) return;
    const btn = gd.querySelector('.updatemenu-button') || gd.querySelector('.updatemenu-header');
    if (!btn) return;
    P.__iplSigs.set(gd, sig);
    ['mousedown', 'mouseup', 'click'].forEach(n => btn.dispatchEvent(new MouseEvent(n, {bubbles: true, cancelable: true})));
  }
  P.__iplTimer = P.setInterval(function () {
    D.body.classList.toggle('ipl-dark', DARK);
    D.querySelectorAll('.ipl-kpi .v').forEach(count);
    D.querySelectorAll('.js-plotly-plot').forEach(autoplay);
  }, 450);
})();
</script>
"""


def inject(dark=False):
    st.markdown(f"<style>{_vars(dark)}{CSS}</style>", unsafe_allow_html=True)


def run_scripts(dark=False, replay=0):
    components.html(JS.replace("%REPLAY%", str(int(replay))).replace("%DARK%", "true" if dark else "false"), height=0)


def banner(sub="For the team analyst, deciding whether to bat or field first after winning the toss"):
    st.markdown(
        "<div class='ipl-banner'><div class='ipl-title'>IPL Matches Dashboard</div>"
        f"<div class='ipl-sub'>{sub}</div>"
        "<div class='ipl-pitch'><div class='ipl-ball-x'><div class='ipl-ball-y'><div class='ipl-ball'></div></div></div></div>"
        "</div>", unsafe_allow_html=True)


def kpi(bg, label, value, sub):
    st.markdown(f"<div class='ipl-kpi' style='--c:{bg}'><div class='l'>{label}</div>"
                f"<div class='v'>{value}</div><div class='s'>{sub}</div></div>", unsafe_allow_html=True)


def match_card(label, value, highlight=False):
    st.markdown(f"<div class='ipl-mc{' hl' if highlight else ''}'><div class='l'>{label}</div>"
                f"<div class='v'>{value}</div></div>", unsafe_allow_html=True)


def add_play(fig, steps=16):
    """Bar / line charts draw themselves in; small play button replays. Pies are left alone."""
    try:
        items = []
        for i, t in enumerate(fig.data):
            if t.type == "bar":
                horiz = t.orientation == "h"
                items.append((i, "bar", horiz, np.asarray(t.x if horiz else t.y, dtype=float)))
            elif t.type == "scatter":
                items.append((i, "line", False, np.asarray(t.y, dtype=float)))
            elif t.type == "pie":
                return fig
        if not items:
            return fig
        bars_v = [a for _, k, h, a in items if k == "bar" and not h]
        bars_h = [a for _, k, h, a in items if k == "bar" and h]
        stack = fig.layout.barmode == "stack"
        if bars_v and fig.layout.yaxis.range is None:
            top = np.nansum(np.vstack(bars_v), axis=0).max() if stack and len({len(a) for a in bars_v}) == 1 \
                else max(np.nanmax(a) for a in bars_v)
            fig.update_yaxes(range=[0, float(top) * 1.2 + 1e-9])
        if bars_h and fig.layout.xaxis.range is None:
            fig.update_xaxes(range=[0, float(max(np.nanmax(a) for a in bars_h)) * 1.2 + 1e-9])
        lines = [a for _, k, _, a in items if k == "line"]
        if lines and fig.layout.yaxis.range is None:
            lo, hi = min(np.nanmin(a) for a in lines), max(np.nanmax(a) for a in lines)
            pad = (hi - lo) * 0.12 or 1
            fig.update_yaxes(range=[lo - pad, hi + pad])
        if lines and fig.layout.xaxis.type == "category" and fig.layout.xaxis.range is None:
            first_line = next(i for i, k, _, _ in items if k == "line")
            fig.update_xaxes(range=[-0.5, len(fig.data[first_line].x) - 0.5])
        frames = []
        for s in range(1, steps + 1):
            f = s / steps
            e = 1 - (1 - f) ** 3
            data, idxs = [], []
            for i, kind, horiz, arr in items:
                t = fig.data[i]
                if kind == "bar":
                    data.append(go.Bar(x=arr * e) if horiz else go.Bar(y=arr * e))
                else:
                    j = max(1, int(np.ceil(len(arr) * f)))
                    kw = dict(x=list(t.x)[:j], y=list(arr)[:j])
                    if t.text is not None and len(t.text) == len(arr):
                        kw["text"] = list(t.text)[:j]
                    data.append(go.Scatter(**kw))
                idxs.append(i)
            frames.append(go.Frame(data=data, traces=idxs, name=str(s)))
        fig.frames = frames
        fig.update_layout(updatemenus=[dict(
            type="buttons", showactive=False, x=1, xanchor="right", y=1.0, yanchor="bottom",
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)", font=dict(size=13, color="#7B8794"),
            buttons=[dict(label="▶", method="animate",
                          args=[None, dict(frame=dict(duration=38, redraw=True), fromcurrent=False,
                                           transition=dict(duration=0), mode="immediate")])])])
        fig.update_layout(legend=dict(x=0.9))
    except Exception:  # an animation problem must never break a chart
        fig.frames = []
        fig.update_layout(updatemenus=[])
    return fig


def polish(fig, dark=False):
    fg = "#E6EDF3" if dark else "#334E68"
    title_c = "#F0F6FC" if dark else NAVY
    grid = "#22313F" if dark else "#EEF2F5"
    line = "#33475B" if dark else "#C9D3DC"
    add_play(fig)
    fig.update_layout(
        font=dict(family=FONT, color=fg), title_font=dict(color=title_c),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor=NAVY, bordercolor=TEAL, font=dict(color="white", family=FONT)),
        transition=dict(duration=500, easing="cubic-in-out"),
    )
    fig.update_xaxes(gridcolor=grid, linecolor=line, tickfont=dict(color=fg))
    fig.update_yaxes(gridcolor=grid, linecolor=line, tickfont=dict(color=fg))
    for a in fig.layout.annotations:
        a.update(font=dict(color=fg))
    vertical = all((t.type == "scatter") or (t.type == "bar" and t.orientation != "h") for t in fig.data)
    if fig.data and vertical:
        fig.update_layout(hovermode="x unified")
    try:
        fig.update_traces(marker_cornerradius=7, selector=dict(type="bar"))
    except Exception:
        pass
    return fig


# ---- theme switch + CSS + scripts (before anything that can st.stop()) ------
st.sidebar.header("Look & feel")
DARK = st.sidebar.toggle("Dark mode", value=False, key="dark")
if st.sidebar.button("▶ Replay animations", key="replay_btn"):
    st.session_state["replay"] = st.session_state.get("replay", 0) + 1
inject(DARK)
with st.sidebar:
    run_scripts(DARK, st.session_state.get("replay", 0))

# ----------------------------------------------------------------------------
# 2. DATA: upload -> automatic column detection -> in-memory SQLite -> q()
# ----------------------------------------------------------------------------
def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# Each field: exact names tried first (alias), then a pattern on the cleaned name.
MATCH_SPEC = {
    "id": dict(alias=["matchid", "id", "gameid", "matchno", "matchnumber"],
               inc=r"^(match|game)?(id|no|number)$", exc=r"player|venue|team|umpire|season"),
    "season": dict(alias=["season", "year", "seasonyear", "iplseason", "iplyear"], inc=r"season|year", exc=r"toss|player"),
    "date": dict(alias=["date", "matchdate", "startdate"], inc=r"date", exc=""),
    "team1": dict(alias=["team1", "teama", "hometeam", "firstteam", "team_1"], inc=r"^team(1|a|one)$|^(home|first)team", exc=""),
    "team2": dict(alias=["team2", "teamb", "awayteam", "secondteam", "team_2"], inc=r"^team(2|b|two)$|^(away|second)team", exc=""),
    "toss_winner": dict(alias=["tosswinner", "tosswonby", "tosswin", "tosswinningteam"],
                        inc=r"toss.*(win|won|by|team)", exc="decision|choice|id$"),
    "toss_decision": dict(alias=["tossdecision", "elected", "electedto", "tosschoice", "tosselected"],
                          inc=r"toss.*(decision|choice|elect|chose|opt)|^elected|^choice", exc=""),
    "winner": dict(alias=["winner", "winningteam", "matchwinner", "winnerteam", "wonbyteam"],
                   inc=r"winner|winningteam", exc=r"toss|player|man|margin|id$"),
    "venue": dict(alias=["venue", "stadium", "ground", "venuename"], inc=r"venue|stadium|ground", exc=r"id$"),
    "player_of_match": dict(alias=["playerofmatch", "manofthematch", "mom", "playerofthematch"],
                            inc=r"playerofmatch|manofthematch|^mom$", exc=r"id$"),
    "win_by_runs": dict(alias=["winbyruns", "wonbyruns", "marginruns"], inc=r"win.*runs|won.*runs", exc=""),
    "win_by_wickets": dict(alias=["winbywickets", "wonbywickets", "marginwickets"], inc=r"win.*wickets|won.*wickets", exc=""),
}
DELIV_SPEC = {
    "match_id": dict(alias=["matchid", "id", "gameid"], inc=r"^(match|game)?id$|matchid", exc=r"player|bat|bowl|team"),
    "inning": dict(alias=["inning", "innings", "inningsno", "inningnumber"], inc=r"inning", exc=""),
    "batting_team": dict(alias=["battingteam", "battingside", "teambatting", "team"], inc=r"battingteam|battingside|^batteam", exc=""),
    "over": dict(alias=["over", "overs", "overnumber", "overno"], inc=r"^overs?(number|no)?$", exc=""),
    "batsman_runs": dict(alias=["batsmanruns", "batterruns", "runsbatter", "runsoffbat", "runsbatsman", "runsscored"],
                         inc=r"(batsman|batter|bat).*runs|runs.*(batsman|batter|offbat)|offbat", exc=r"total|extra|team"),
    "total_runs": dict(alias=["totalruns", "runstotal", "total", "runs"], inc=r"^total(runs)?$|runstotal|totalruns", exc=""),
    "extra_runs": dict(alias=["extraruns", "extras", "runsextras"], inc=r"extra", exc=r"type|kind"),
    "is_wicket": dict(alias=["iswicket", "wicket", "wickettaken", "isout"], inc=r"^(is)?wickets?(taken)?$|^isout$", exc=r"type|kind|player"),
    "player_dismissed": dict(alias=["playerdismissed", "dismissedplayer", "playerout", "batterout", "dismissed"],
                             inc=r"dismissed|playerout", exc=r"kind|type|non"),
}
TEAM_SPEC = {
    "id": dict(alias=["id", "teamid"], inc=r"^(team)?id$", exc=""),
    "name": dict(alias=["name", "teamname", "fullname", "team"], inc=r"name|team", exc=r"id|short|code"),
}


def find_col(columns, spec):
    lookup = {norm(c): c for c in columns}
    for a in spec["alias"]:
        if a in lookup:
            return lookup[a]
    inc = re.compile(spec["inc"]) if spec["inc"] else None
    exc = re.compile(spec["exc"]) if spec["exc"] else None
    for c in columns:
        n = norm(c)
        if inc and inc.search(n) and not (exc and exc.search(n)):
            return c
    return None


def auto_map(df, spec):
    return {f: find_col(df.columns, s) for f, s in spec.items()}


def missing_required(mm, dm, full):
    miss = []
    need_m = [("id", "match id"), ("toss_winner", "toss winner"), ("toss_decision", "toss decision")]
    if not full:
        need_m += [("team1", "team 1"), ("team2", "team 2"), ("winner", "match winner")]
    for f, label in need_m:
        if not mm.get(f):
            miss.append(f"matches file: {label}")
    if full:
        for f, label in [("match_id", "match id"), ("inning", "innings number"),
                         ("batting_team", "batting team"), ("over", "over number")]:
            if not dm.get(f):
                miss.append(f"deliveries file: {label}")
        if not dm.get("batsman_runs") and not dm.get("total_runs"):
            miss.append("deliveries file: runs per ball")
    return miss


@st.cache_data(show_spinner=False)
def read_df(b):
    try:
        return pd.read_csv(io.BytesIO(b), low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(b), low_memory=False, encoding="latin-1")


def digest(b):
    return hashlib.md5(b).hexdigest() if b else ""


def season_yy(s):
    try:
        s = str(int(float(s)))
    except (TypeError, ValueError):
        s = str(s)
    if "/" in s:               # "2007/08" -> "08"
        s = s.split("/")[1]
    return s[-2:]              # "2009" -> "09"


def id_str(s):
    n = pd.to_numeric(s, errors="coerce")
    if n.notna().all():
        return n.astype("int64").astype(str)
    return s.astype(str).str.strip()


def pick(raw, mapping):
    return pd.DataFrame({k: raw[v] for k, v in mapping.items() if v})


def clean_team(s):
    return s.map(lambda v: v.strip() if isinstance(v, str) else v).replace(TEAM_FIX)


@st.cache_resource(show_spinner="Reading your data...")
def build_db(key, _mb, _db, _tb, mm_items, dm_items, tm_items):
    mm, dm, tm = dict(mm_items), dict(dm_items), dict(tm_items)
    m = pick(read_df(_mb), mm)
    m = m.drop_duplicates(subset="id")          # merged file: one row per match
    d = pick(read_df(_db), dm) if _db else None   # None = matches-only view

    # optional team-id -> team-name lookup
    team_cols_m = [c for c in ["team1", "team2", "toss_winner", "winner"] if c in m]
    if _tb and tm.get("id") and tm.get("name"):
        t = read_df(_tb)

        def k(v):
            if pd.isna(v):
                return v
            try:
                return str(int(float(v)))
            except (TypeError, ValueError):
                return str(v)
        lookup = {k(a): b for a, b in zip(t[tm["id"]], t[tm["name"]])}
        for c in team_cols_m:
            m[c] = m[c].map(lambda v: lookup.get(k(v), v))
        if d is not None:
            d["batting_team"] = d["batting_team"].map(lambda v: lookup.get(k(v), v))

    for c in team_cols_m:
        m[c] = clean_team(m[c])
    if d is not None:
        d["batting_team"] = clean_team(d["batting_team"])

    m["id"] = id_str(m["id"])
    if "season" in m:
        m["season_yy"] = m["season"].map(season_yy)
    elif "date" in m:
        m["season_yy"] = pd.to_datetime(m["date"], errors="coerce").dt.year.map(season_yy)
    else:
        m["season_yy"] = "--"
    m["season_yy"] = m["season_yy"].fillna("--").astype(str)
    m["date"] = m["date"].astype(str) if "date" in m else m["season_yy"]

    td = m["toss_decision"].astype(str).str.strip().str.lower()
    m["toss_decision"] = np.where(td.str.startswith(("bowl", "field")), "field",
                                  np.where(td.str.startswith("bat"), "bat", td))
    if "winner" in m:
        bad = m["winner"].astype(str).str.strip().str.lower().isin(
            ["", "nan", "none", "na", "no result", "tie", "abandoned"])
        m.loc[bad, "winner"] = np.nan

    con = sqlite3.connect(":memory:", check_same_thread=False)

    # ------------------------------------------------------------------ matches-only
    if d is None:
        mx = m.copy()
        tw = mx["toss_winner"]
        other = np.where(mx["team1"] == tw, mx["team2"], mx["team1"])
        field = mx["toss_decision"] == "field"
        mx["chase_team"] = np.where(field, tw, other)
        mx["first_team"] = np.where(field, other, tw)
        w = mx["winner"]
        mx["decided"] = (w.notna() & ((w == mx["first_team"]) | (w == mx["chase_team"]))).astype(int)
        mx["chase_won"] = ((w == mx["chase_team"]) & (mx["decided"] == 1)).astype(int)
        mx["toss_won"] = ((w == tw) & (mx["decided"] == 1)).astype(int)
        zero = pd.Series(0, index=mx.index)
        wr = pd.to_numeric(mx["win_by_runs"], errors="coerce").fillna(0) if "win_by_runs" in mx else zero
        ww = pd.to_numeric(mx["win_by_wickets"], errors="coerce").fillna(0) if "win_by_wickets" in mx else zero
        mx["win_margin"] = np.where(wr > 0, wr, np.where(ww > 0, ww, np.nan))
        guess = np.where(mx["chase_won"] == 1, "wickets", "runs")
        mx["win_type"] = np.where(wr > 0, "runs", np.where(ww > 0, "wickets", np.where(mx["decided"] == 1, guess, None)))
        for c in ["venue", "player_of_match"]:
            if c not in mx:
                mx[c] = None
        mx["_d"] = pd.to_datetime(mx["date"], errors="coerce")
        mx = mx.sort_values(["season_yy", "_d", "id"]).reset_index(drop=True)
        mx["seq"] = range(len(mx))
        mx = mx.drop(columns="_d")
        mx.to_sql("match_x", con, index=False)
        return con

    # ------------------------------------------------------------------ full (with deliveries)
    d["match_id"] = id_str(d["match_id"])
    d["inning"] = pd.to_numeric(d["inning"], errors="coerce")
    d["over"] = pd.to_numeric(d["over"], errors="coerce")
    has_bat, has_tot = "batsman_runs" in d, "total_runs" in d
    if has_bat:
        d["batsman_runs"] = pd.to_numeric(d["batsman_runs"], errors="coerce").fillna(0)
    if has_tot:
        d["total_runs"] = pd.to_numeric(d["total_runs"], errors="coerce").fillna(0)
    if not has_bat:                              # boundaries then come from total runs on the ball
        d["batsman_runs"] = d["total_runs"]
    if not has_tot:
        extra = pd.to_numeric(d["extra_runs"], errors="coerce").fillna(0) if "extra_runs" in d else 0
        d["total_runs"] = d["batsman_runs"] + extra
    if "is_wicket" in d:
        s = d["is_wicket"]
        if s.dtype == object:
            low = s.astype(str).str.strip().str.lower()
            flags = {"0", "1", "true", "false", "yes", "no", "t", "f", "y", "n", "nan", ""}
            if set(low.unique()) <= flags:
                d["is_wicket"] = low.isin(["1", "true", "yes", "t", "y"]).astype(int)
            else:                                # holds a dismissal type: any text = wicket
                d["is_wicket"] = (~low.isin(["", "nan", "none", "na", "0"])).astype(int)
        else:
            d["is_wicket"] = pd.to_numeric(s, errors="coerce").fillna(0).clip(0, 1).astype(int)
    elif "player_dismissed" in d:
        pdn = d["player_dismissed"]
        d["is_wicket"] = (pdn.notna() & (pdn.astype(str).str.strip() != "")).astype(int)
    else:
        d["is_wicket"] = 0

    d = d[d["inning"].isin([1, 2])].dropna(subset=["over"]).copy()
    if d["over"].min() == 0:                      # make overs 1..20
        d["over"] = d["over"] + 1
    balls = d[["match_id", "inning", "batting_team", "over", "total_runs", "batsman_runs", "is_wicket"]]

    inn = (balls.groupby(["match_id", "inning"])
           .agg(batting_team=("batting_team", "first"), runs=("total_runs", "sum"), wkts=("is_wicket", "sum"))
           .reset_index())
    inn["wkts"] = inn["wkts"].clip(upper=10)
    i1 = inn[inn.inning == 1].rename(columns={"batting_team": "first_team", "runs": "first_runs",
                                              "wkts": "first_wkts"}).drop(columns="inning")
    i2 = inn[inn.inning == 2].rename(columns={"batting_team": "chase_team", "runs": "chase_runs",
                                              "wkts": "chase_wkts"}).drop(columns="inning")
    mx = (m.merge(i1, left_on="id", right_on="match_id").drop(columns="match_id")
            .merge(i2, left_on="id", right_on="match_id").drop(columns="match_id"))
    if "team1" not in mx:                         # not in the file: take them from the scorecards
        mx["team1"], mx["team2"] = mx["first_team"], mx["chase_team"]
    if "winner" not in mx:                        # not in the file: higher score wins
        mx["winner"] = np.where(mx["first_runs"] > mx["chase_runs"], mx["first_team"],
                                np.where(mx["chase_runs"] > mx["first_runs"], mx["chase_team"], None))
    mx["target"] = mx["first_runs"] + 1
    mx["chase_won"] = (mx["winner"] == mx["chase_team"]).astype(int)
    by_chase = mx["winner"] == mx["chase_team"]
    by_first = mx["winner"] == mx["first_team"]
    mx["win_type"] = np.where(by_chase, "wickets", np.where(by_first, "runs", None))
    mx["win_margin"] = np.where(by_chase, 10 - mx["chase_wkts"],
                                np.where(by_first, mx["first_runs"] - mx["chase_runs"], np.nan))

    mx.to_sql("match_x", con, index=False)
    inn.to_sql("innings", con, index=False)
    balls.to_sql("balls", con, index=False)
    return con


# ---- sidebar: ONE upload box (nothing is loaded until you upload) ------------
st.sidebar.header("Data")
uploads = st.sidebar.file_uploader(
    "Upload your dataset (CSV)", type="csv", accept_multiple_files=True, key="up_all",
    help="Select the matches file and the ball-by-ball (deliveries) file together. "
         "A teams file is optional. One merged file also works.")

if not uploads:
    banner("Upload your dataset in the sidebar to start")
    st.info("Upload your dataset in the sidebar to start. Select the **matches** file and the "
            "**deliveries** (ball-by-ball) file together in the one upload box. "
            "The dashboard finds the columns by itself.")
    st.stop()


def classify(df):
    mp, dp = auto_map(df, MATCH_SPEC), auto_map(df, DELIV_SPEC)
    is_d = bool(dp["inning"] and dp["over"] and dp["batting_team"] and (dp["batsman_runs"] or dp["total_runs"]))
    is_m = bool(mp["id"] and mp["toss_decision"] and mp["toss_winner"])
    tp = auto_map(df, TEAM_SPEC)
    is_t = (not is_d and not is_m and bool(tp["id"] and tp["name"]) and len(df) <= 500)
    return is_m, is_d, is_t


info = []
for u in uploads:
    b = u.getvalue()
    df = read_df(b)
    is_m, is_d, is_t = classify(df)
    info.append(dict(name=u.name, b=b, df=df, m=is_m, d=is_d, t=is_t))

d_pool = [s for s in info if s["d"] and not s["m"]] or [s for s in info if s["d"]]
m_pool = [s for s in info if s["m"] and not s["d"]] or [s for s in info if s["m"]]
t_pool = [s for s in info if s["t"]]
D_SRC = max(d_pool, key=lambda s: len(s["df"]), default=None)
M_SRC = max(m_pool, key=lambda s: len(s["df"]), default=None)
T_SRC = t_pool[0] if t_pool else None

for s in info:
    role = ("matches + deliveries (merged)" if s["m"] and s["d"] else "matches" if s["m"]
            else "deliveries" if s["d"] else "teams" if s["t"] else "not recognised")
    st.sidebar.caption(f"{s['name']}: {role}")

if M_SRC is None:
    banner()
    st.warning("The upload needs a **matches** file (a match id, the two teams, the toss winner, the toss "
               "decision and the winner).")
    with st.expander("Columns found in your files"):
        for s in info:
            st.write(f"**{s['name']}**: " + ", ".join(map(str, s["df"].columns)))
    st.stop()

FULL = D_SRC is not None                      # False = matches-only view
MB, DB = M_SRC["b"], (D_SRC["b"] if FULL else None)
TB = T_SRC["b"] if T_SRC else None
mdf = M_SRC["df"]
ddf = D_SRC["df"] if FULL else None
mm = auto_map(mdf, MATCH_SPEC)
dm = auto_map(ddf, DELIV_SPEC) if FULL else {}
tm = auto_map(T_SRC["df"], TEAM_SPEC) if T_SRC else {}

miss = missing_required(mm, dm, FULL)
if miss:
    banner()
    st.warning("Some columns this dashboard needs were not found: " + "; ".join(miss))
    with st.expander("Columns found in your files"):
        st.write("**matches**: " + ", ".join(map(str, mdf.columns)))
        if FULL:
            st.write("**deliveries**: " + ", ".join(map(str, ddf.columns)))
    st.stop()

DATA_KEY = "|".join([digest(MB), digest(DB), digest(TB)])
try:
    CON = build_db(DATA_KEY, MB, DB, TB, tuple(sorted(mm.items())), tuple(sorted(dm.items())),
                   tuple(sorted(tm.items())))
except Exception as e:  # noqa: BLE001
    banner()
    st.error(f"Could not read the dataset: {e}")
    st.stop()


@st.cache_data(show_spinner=False)
def _q(_con, data_key, sql, params):
    return pd.read_sql_query(sql, _con, params=params)


def q(sql, params=()):
    """Run a SQL query and return a DataFrame."""
    return _q(CON, DATA_KEY, sql, tuple(params))


_linked = int(q("SELECT COUNT(*) AS n FROM match_x").iloc[0]["n"])
if _linked == 0:
    banner()
    st.error("No match could be linked to its ball-by-ball rows: the match id values in the two files "
             "do not agree. Check that both files come from the same dataset.")
    st.stop()
HAS_VENUE = bool(mm.get("venue"))
if FULL:
    st.sidebar.caption(f"{_linked:,} of {mdf[mm['id']].nunique():,} matches linked to ball-by-ball data")
else:
    st.sidebar.caption(f"{_linked:,} matches loaded (matches-only view: add the deliveries file for over-by-over charts)")
_notes = []
if FULL and not mm.get("team1"):
    _notes.append("team names taken from the scorecards")
if FULL and not mm.get("winner"):
    _notes.append("winner worked out from the scores")
if FULL and not dm.get("is_wicket") and not dm.get("player_dismissed"):
    _notes.append("no wicket column found, wickets show as 0")
if FULL and not dm.get("batsman_runs"):
    _notes.append("no bat-runs column, boundaries counted from total runs per ball")
for n_ in _notes:
    st.sidebar.caption("Note: " + n_)


# ----------------------------------------------------------------------------
# 3. HELPERS: stats, filters, chart style
# ----------------------------------------------------------------------------
def wilson(k, n, z=1.96):
    """95% Wilson confidence interval for a proportion."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def p_value(k, n, p0=0.5):
    """Two-sided z-test of a win rate against p0."""
    if n == 0:
        return 1.0
    z = (k / n - p0) / math.sqrt(p0 * (1 - p0) / n)
    return math.erfc(abs(z) / math.sqrt(2))


def fmt_p(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def where_clause(season, team, toss):
    """WHERE text on match_x aliased m, plus its parameters."""
    cond, params = ["1=1"], []
    if season != "All":
        cond.append("m.season_yy = ?"); params.append(season)
    if team != "All":
        cond.append("(m.team1 = ? OR m.team2 = ?)"); params += [team, team]
    if toss != "All":
        cond.append("m.toss_decision = ?"); params.append(toss)
    return " AND ".join(cond), tuple(params)


def team_clause(team, alias):
    """When a team is chosen, count only that team's own innings/balls."""
    if team == "All":
        return "", ()
    return f" AND {alias}.batting_team = ?", (team,)


INN_OPTS = {"Both": None, "1st innings": 1, "2nd innings": 2}


def inn_clause(choice, alias):
    v = INN_OPTS[choice]
    return ("", ()) if v is None else (f" AND {alias}.inning = ?", (v,))


def style(fig, title, height, sub=None, wrap=58):
    lines = textwrap.wrap(title, wrap) or [title]
    text = "<b>" + "<br>".join(lines) + "</b>" + (f"<br><sup>{sub}</sup>" if sub else "")
    fig.update_layout(
        title=dict(text=text, x=0, y=0.98, yanchor="top", font=dict(size=15, color=NAVY)),
        height=height + 18 * (len(lines) - 1), margin=dict(l=10, r=10, t=62 + 19 * len(lines), b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334E68"),
        legend=dict(orientation="h", y=1.0, x=1, xanchor="right", yanchor="bottom"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#C9D3DC")
    fig.update_yaxes(gridcolor="#EEF2F5", linecolor="#C9D3DC")
    return fig


def show(fig, key):
    fig = polish(fig, DARK)
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except TypeError:                       # older Streamlit
        st.plotly_chart(fig, use_container_width=True, key=key)


# ----------------------------------------------------------------------------
# 4. PAGE HEADER
# ----------------------------------------------------------------------------
banner()

seasons = q("SELECT DISTINCT season_yy FROM match_x ORDER BY season_yy")["season_yy"].tolist()
teams = q("SELECT DISTINCT team1 AS t FROM match_x UNION SELECT DISTINCT team2 FROM match_x ORDER BY t")["t"].tolist()
season_fmt = lambda s: s if s == "All" else f"20{s}"  # noqa: E731

def render_full():
    tab1, tab2 = st.tabs(["Overview", "Match Detail"])

    # ============================================================================
    # TAB 1 : OVERVIEW   (global filters on top + one filter row on every chart)
    # ============================================================================
    with tab1:
        f1, f2, f3 = st.columns(3)
        season = f1.selectbox("Season", ["All"] + seasons, format_func=season_fmt, key="f_season")
        team = f2.selectbox("Team", ["All"] + teams, key="f_team")
        toss = f3.selectbox("Toss decision", ["All", "field", "bat"], key="f_toss")

        W, P = where_clause(season, team, toss)
        TC, TP = team_clause(team, "i")
        BC, BP = team_clause(team, "b")

        scale = q("SELECT COUNT(*) AS n, COUNT(DISTINCT season_yy) AS s FROM match_x").iloc[0]   # never filtered
        runs = q(f"SELECT COALESCE(SUM(i.runs),0) AS r FROM innings i JOIN match_x m ON m.id=i.match_id WHERE {W}{TC}",
                 P + TP).iloc[0]["r"]
        ch = q(f"SELECT COUNT(*) AS n, COALESCE(SUM(m.chase_won),0) AS k FROM match_x m "
               f"WHERE {W} AND m.winner IS NOT NULL", P).iloc[0]
        n_ch, k_ch = int(ch["n"]), int(ch["k"])

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi(NAVY, "MATCHES | SEASONS", f"{int(scale['n']):,} | {int(scale['s'])}", "fixed - never changes with filters")
        with c2:
            kpi(TEAL, "TOTAL RUNS", f"{int(runs):,}", "runs in the matches selected (from SQL)")
        with c3:
            if n_ch:
                lo, hi = wilson(k_ch, n_ch)
                kpi(PLUM, "CHASING FINDING", f"{100*k_ch/n_ch:.0f}% (CI {100*lo:.0f}-{100*hi:.0f}%)",
                    f"Test T1: chasing win rate vs 50%, p = {fmt_p(p_value(k_ch, n_ch))}, n = {n_ch:,}")
            else:
                kpi(PLUM, "CHASING FINDING", "no data", "no matches with a result")

        st.write("")

        # ---- HERO: average innings score  (chart filter: innings) ----------------
        with st.container(border=True):
            h1, _ = st.columns([1, 3])
            inn_h = h1.selectbox("Chart filter: innings", list(INN_OPTS), key="h_inn")
            IC, IP = inn_clause(inn_h, "i")
            if season == "All":
                hero = q(f"SELECT m.season_yy AS x, AVG(i.runs) AS v, COUNT(*) AS n FROM innings i "
                         f"JOIN match_x m ON m.id=i.match_id WHERE {W}{TC}{IC} GROUP BY m.season_yy ORDER BY m.season_yy",
                         P + TP + IP)
            else:
                hero = q(f"SELECT m.id, AVG(i.runs) AS v, COUNT(*) AS n FROM innings i "
                         f"JOIN match_x m ON m.id=i.match_id WHERE {W}{TC}{IC} GROUP BY m.id ORDER BY m.date, m.id",
                         P + TP + IP)
                hero["x"] = range(1, len(hero) + 1)
            xs = hero["x"].tolist()
            if len(hero):
                overall = float((hero["v"] * hero["n"]).sum() / hero["n"].sum())
                n_inn = int(hero["n"].sum())
                which = "" if inn_h == "Both" else f" ({inn_h})"
                if season == "All":
                    title = (f"Average innings score{which} moved from {hero['v'].iloc[0]:.0f} in 20{xs[0]} "
                             f"to {hero['v'].iloc[-1]:.0f} in 20{xs[-1]}")
                    sub = f"n = {n_inn:,} innings; dashed line = overall average {overall:.0f}"
                    xt = "season"
                else:
                    title = f"In 20{season} the average innings score{which} was {overall:.0f} across {len(hero)} matches"
                    sub = f"n = {n_inn:,} innings; dashed line = season average {overall:.0f}"
                    xt = "match number in season"
                fig = go.Figure(go.Scatter(x=xs, y=hero["v"], mode="lines+markers", line=dict(color=CORAL, width=3),
                                           marker=dict(size=8), fill="tozeroy", fillcolor="rgba(228,87,46,0.10)",
                                           hovertemplate="%{x}: %{y:.1f}<extra></extra>"))
                fig.add_hline(y=overall, line_dash="dot", line_color="#7B8794",
                              annotation_text="average", annotation_position="top left")
                fig.update_yaxes(range=[max(0, hero["v"].min() - 15), hero["v"].max() + 10], title="average innings score")
                fig.update_xaxes(title=xt, type="category")
                show(style(fig, title, 400, sub, wrap=120), "hero")
            else:
                st.info("No innings match these filters.")

        # ---- row 2: chasing bands | toss decision --------------------------------
        r2a, r2b = st.columns(2)
        with r2a, st.container(border=True):
            chase_t = st.selectbox("Chart filter: chasing team", ["All"] + teams, key="b_team")
            W2, P2 = W, P
            if chase_t != "All":
                W2, P2 = W + " AND m.chase_team = ?", P + (chase_t,)
            bands = q(f"SELECT CASE WHEN m.target<140 THEN '<140' WHEN m.target<160 THEN '140-159' "
                      f"WHEN m.target<180 THEN '160-179' ELSE '180+' END AS band, COUNT(*) AS n, "
                      f"100.0*AVG(m.chase_won) AS win FROM match_x m WHERE {W2} AND m.winner IS NOT NULL "
                      f"GROUP BY band", P2)
            order = ["<140", "140-159", "160-179", "180+"]
            bands = bands.set_index("band").reindex(order).dropna().reset_index()
            if len(bands):
                first, last = bands.iloc[0], bands.iloc[-1]
                who = "" if chase_t == "All" else f" for {abbr(chase_t)}"
                title = (f"Chasing win rate{who} is {first['win']:.0f}% for targets {first['band']} "
                         f"and {last['win']:.0f}% for {last['band']}")
                fig = go.Figure(go.Bar(x=bands["band"], y=bands["win"], marker_color=[GREEN, BLUE, AMBER, CORAL][:len(bands)],
                                       text=[f"n={int(n)}" for n in bands["n"]], textposition="outside"))
                fig.add_hline(y=50, line_dash="dash", line_color="black", annotation_text="50%", annotation_position="top right")
                fig.update_yaxes(range=[0, 100], title="chasing win %")
                fig.update_xaxes(title="target set by the first innings")
                show(style(fig, title, 320, f"n = {int(bands['n'].sum()):,} matches with a result"), "bands")
            else:
                st.info("No matches with a result for these filters.")

        with r2b, st.container(border=True):
            tw_f = st.selectbox("Chart filter: toss winner", ["All"] + teams, key="t_team")
            W2, P2 = W, P
            if tw_f != "All":
                W2, P2 = W + " AND m.toss_winner = ?", P + (tw_f,)
            tdf = q(f"SELECT m.season_yy AS x, m.toss_decision AS d, COUNT(*) AS n FROM match_x m WHERE {W2} "
                    f"GROUP BY m.season_yy, m.toss_decision ORDER BY m.season_yy", P2)
            if len(tdf):
                piv = tdf.pivot(index="x", columns="d", values="n").fillna(0)
                for c in ["field", "bat"]:
                    if c not in piv:
                        piv[c] = 0
                tot = piv["field"].sum() + piv["bat"].sum()
                share = 100 * piv["field"].sum() / tot
                who = "" if tw_f == "All" else f" ({abbr(tw_f)})"
                title = f"Toss winners{who} chose to field in {share:.0f}% of matches"
                fig = go.Figure()
                fig.add_bar(x=piv.index, y=piv["field"], name="field", marker_color=BLUE)
                fig.add_bar(x=piv.index, y=piv["bat"], name="bat", marker_color=AMBER)
                fig.update_layout(barmode="stack")
                fig.update_yaxes(title="toss winners (matches)")
                fig.update_xaxes(title="season", type="category")
                show(style(fig, title, 320, f"n = {int(tot):,} matches"), "toss")
            else:
                st.info("No matches for these filters.")

        # ---- row 3: sixes/fours | win type donut ---------------------------------
        r3a, r3b = st.columns([3, 2])
        with r3a, st.container(border=True):
            s1, s2 = st.columns(2)
            kind = s1.selectbox("Chart filter: boundary", ["Sixes", "Fours"], key="s_kind")
            inn_s = s2.selectbox("Chart filter: innings", list(INN_OPTS), key="s_inn")
            SC, SP = inn_clause(inn_s, "b")
            runs_val = 6 if kind == "Sixes" else 4
            sx = q(f"SELECT m.season_yy AS x, COUNT(*) AS n FROM balls b JOIN match_x m ON m.id=b.match_id "
                   f"WHERE {W} AND b.batsman_runs = ?{BC}{SC} GROUP BY m.season_yy ORDER BY m.season_yy",
                   P + (runs_val,) + BP + SP)
            if len(sx):
                kl = kind.lower()
                if len(sx) > 1:
                    title = f"{kind} per season went from {int(sx['n'].iloc[0]):,} in 20{sx['x'].iloc[0]} to {int(sx['n'].iloc[-1]):,} in 20{sx['x'].iloc[-1]}"
                else:
                    title = f"{int(sx['n'].iloc[0]):,} {kl} were hit in 20{sx['x'].iloc[0]}"
                fig = go.Figure(go.Bar(x=sx["x"], y=sx["n"], marker_color=PLUM if kind == "Sixes" else BLUE))
                fig.update_yaxes(title=kl)
                fig.update_xaxes(title="season", type="category")
                show(style(fig, title, 320, f"n = {int(sx['n'].sum()):,} {kl}", wrap=85), "sixes")
            else:
                st.info("No boundaries for these filters.")
        with r3b, st.container(border=True):
            win_t = st.selectbox("Chart filter: winning team", ["All"] + teams, key="w_team")
            W2, P2 = W, P
            if win_t != "All":
                W2, P2 = W + " AND m.winner = ?", P + (win_t,)
            wt = q(f"SELECT CASE WHEN m.winner = m.chase_team THEN 'By wickets' ELSE 'By runs' END AS kind, "
                   f"COUNT(*) AS n FROM match_x m WHERE {W2} AND m.winner IS NOT NULL GROUP BY kind", P2)
            if len(wt):
                wt = wt.set_index("kind").reindex(["By wickets", "By runs"]).fillna(0)
                tot = int(wt["n"].sum())
                lead = "wickets" if wt.loc["By wickets", "n"] >= wt.loc["By runs", "n"] else "runs"
                pct = 100 * wt["n"].max() / tot
                who = "" if win_t == "All" else f" by {abbr(win_t)}"
                title = f"Most matches won{who} ({pct:.0f}%) are won by {lead}"
                fig = go.Figure(go.Pie(labels=wt.index, values=wt["n"], hole=0.55, sort=False,
                                       marker=dict(colors=[TEAL, AMBER]), textinfo="label+value+percent"))
                fig.add_annotation(text=f"{tot:,}<br>results", showarrow=False, font=dict(size=14, color=NAVY))
                fig.update_layout(showlegend=False)
                show(style(fig, title, 320, f"n = {tot:,} matches with a result", wrap=45), "donut")
            else:
                st.info("No matches with a result for these filters.")

    # ============================================================================
    # TAB 2 : MATCH DETAIL   (match selector on top + one filter row on every chart)
    # ============================================================================
    with tab2:
        s1, s2 = st.columns([1, 3])
        season2 = s1.selectbox("Season", ["All"] + seasons, format_func=season_fmt, key="d_season")
        opts = q("SELECT id, date, team1, team2 FROM match_x WHERE (? = 'All' OR season_yy = ?) ORDER BY date DESC, id DESC",
                 (season2, season2))
        if opts.empty:
            st.info("No matches in this season."); return
        labels = {str(r.id): f"{r.date}  |  {abbr(r.team1)} vs {abbr(r.team2)}" for r in opts.itertuples()}
        mid = s2.selectbox("Match", list(labels.keys()), format_func=lambda i: labels[i], key="d_match")

        mr = q("SELECT * FROM match_x WHERE id = ?", (str(mid),)).iloc[0]
        ov = q("SELECT inning, over, SUM(total_runs) AS runs, SUM(batsman_runs) AS bat_runs, SUM(is_wicket) AS wk, "
               "SUM(batsman_runs = 4) AS fours, SUM(batsman_runs = 6) AS sixes "
               "FROM balls WHERE match_id = ? GROUP BY inning, over ORDER BY inning, over", (str(mid),))
        names = {1: mr["first_team"], 2: mr["chase_team"]}
        tot_runs = {1: int(mr["first_runs"]), 2: int(mr["chase_runs"])}
        tot_wk = {1: int(mr["first_wkts"]), 2: int(mr["chase_wkts"])}

        if pd.isna(mr["winner"]) or pd.isna(mr["win_type"]):
            result = "No result / tie"
        else:
            result = (f"{abbr(mr['winner'])} won by {int(mr['win_margin'])} {mr['win_type']}"
                      if mr["win_margin"] != 0 else f"{abbr(mr['winner'])} won the super over")

        # ---- top cards (kept exactly as in the approved sketch) -----------------
        k1, k2, k3 = st.columns([1, 1.1, 1])
        with k1:
            match_card("RESULT", result)
        with k2:
            match_card(f"1ST INNINGS — {abbr(names[1])}", f"{tot_runs[1]} / {tot_wk[1]}", highlight=True)
        with k3:
            match_card(f"2ND INNINGS — {abbr(names[2])}", f"{tot_runs[2]} / {tot_wk[2]}")
        st.write("")

        def pick_inn(label, key):
            c = st.radio(label, list(INN_OPTS), horizontal=True, key=key)
            return [1, 2] if INN_OPTS[c] is None else [INN_OPTS[c]]

        # ---- HERO: runs per over  (filters: innings + over range) ---------------
        with st.container(border=True):
            ha, hb = st.columns([2, 3])
            with ha:
                ids = pick_inn("Chart filter: innings", "m_h_inn")
            with hb:
                lo_o, hi_o = st.select_slider("Chart filter: overs", options=list(range(1, 21)), value=(1, 20), key="m_h_ov")
            od = ov[ov.inning.isin(ids) & ov.over.between(lo_o, hi_o)]
            if od.empty:
                st.info("No overs in this range.")
            else:
                avg_rpo = od["runs"].mean()
                big = od.loc[od["runs"].idxmax()]
                title = (f"{abbr(names[int(big['inning'])])} scored {int(big['runs'])} in over {int(big['over'])}, "
                         f"the biggest over shown")
                fig = go.Figure()
                for inn in ids:
                    d = od[od.inning == inn]
                    fig.add_bar(x=d["over"], y=d["runs"], name=f"{abbr(names[inn])} ({'1st' if inn == 1 else '2nd'})",
                                marker_color=INN_COL[inn])
                fig.add_hline(y=avg_rpo, line_dash="dash", line_color="black",
                              annotation_text=f"average {avg_rpo:.1f} runs/over", annotation_position="top left")
                fig.update_layout(barmode="group")
                fig.update_xaxes(title="over", dtick=1)
                fig.update_yaxes(title="runs")
                show(style(fig, title, 400, f"n = {int(od['runs'].sum())} runs in {len(od)} innings-overs", wrap=120), "m_hero")

        # ---- row 2: runs by phase | wickets by over -----------------------------
        ra, rb = st.columns(2)
        with ra, st.container(border=True):
            all_ph = [("Powerplay (1-6)", 1, 6), ("Middle (7-15)", 7, 15), ("Death (16-20)", 16, 20)]
            chosen = st.multiselect("Chart filter: phases", [p[0] for p in all_ph], default=[p[0] for p in all_ph], key="m_ph")
            phases = [p for p in all_ph if p[0] in chosen]
            if not phases:
                st.info("Pick at least one phase.")
            else:
                pdata = {inn: [int(ov[(ov.inning == inn) & ov.over.between(a, b)]["runs"].sum()) for _, a, b in phases]
                         for inn in (1, 2)}
                wins1 = sum(pdata[1][i] > pdata[2][i] for i in range(len(phases)))
                wins2 = sum(pdata[2][i] > pdata[1][i] for i in range(len(phases)))
                n = len(phases)
                if wins1 == wins2:
                    title = f"{abbr(names[1])} and {abbr(names[2])} are level on phases won ({wins1} each of {n})"
                else:
                    lead, k = (1, wins1) if wins1 > wins2 else (2, wins2)
                    title = f"{abbr(names[lead])} scored more runs in {k} of {n} phases"
                fig = go.Figure()
                for inn in (1, 2):
                    fig.add_bar(x=[p[0] for p in phases], y=pdata[inn], name=abbr(names[inn]), marker_color=INN_COL[inn],
                                text=pdata[inn], textposition="outside")
                fig.update_layout(barmode="group")
                fig.update_yaxes(title="runs", range=[0, max(pdata[1] + pdata[2] + [1]) * 1.2])
                show(style(fig, title, 320, f"n = {sum(pdata[1]) + sum(pdata[2])} runs"), "m_phase")
        with rb, st.container(border=True):
            ids_w = pick_inn("Chart filter: innings", "m_w_inn")
            ow = ov[ov.inning.isin(ids_w)]
            fig = go.Figure()
            for inn in ids_w:
                d = ow[ow.inning == inn]
                fig.add_bar(x=d["over"], y=d["wk"], name=abbr(names[inn]), marker_color=INN_COL[inn])
            most = ow.loc[ow["wk"].idxmax()]
            if len(ids_w) == 2:
                title = f"{abbr(names[1])} lost {tot_wk[1]} wickets, {abbr(names[2])} lost {tot_wk[2]}"
            else:
                title = f"{abbr(names[ids_w[0]])} lost {tot_wk[ids_w[0]]} wickets"
            fig.update_layout(barmode="group")
            fig.update_xaxes(title="over", dtick=1)
            fig.update_yaxes(title="wickets", dtick=1)
            show(style(fig, title, 320, f"n = {int(ow['wk'].sum())} wickets; most in one over: {int(most['wk'])} (over {int(most['over'])})"), "m_wk")

        # ---- row 3: toss donut | fours and sixes --------------------------------
        rc, rd = st.columns(2)
        with rc, st.container(border=True):
            metric = st.radio("Chart filter: count", ["Total runs", "Runs off the bat"], horizontal=True, key="m_t_met")
            col = "runs" if metric == "Total runs" else "bat_runs"
            vals = [int(ov[ov.inning == i][col].sum()) for i in (1, 2)]
            tw, dec = mr["toss_winner"], mr["toss_decision"]
            outcome = "and won" if mr["winner"] == tw else ("and lost" if not pd.isna(mr["winner"]) else "and there was no result")
            title = f"{abbr(tw)} won the toss, chose to {dec} {outcome}"
            fig = go.Figure(go.Pie(labels=[abbr(names[1]), abbr(names[2])], values=vals, hole=0.55,
                                   sort=False, marker=dict(colors=[AMBER, PLUM]), textinfo="label+value+percent"))
            fig.add_annotation(text=f"{sum(vals)}<br>runs", showarrow=False, font=dict(size=14, color=NAVY))
            fig.update_layout(showlegend=False)
            show(style(fig, title, 320, f"share of the {sum(vals)} {metric.lower()} by each innings"), "m_toss")
        with rd, st.container(border=True):
            what = st.radio("Chart filter: show", ["Both", "Fours", "Sixes"], horizontal=True, key="m_fs_what")
            fs = {inn: (int(ov[ov.inning == inn]["fours"].sum()), int(ov[ov.inning == inn]["sixes"].sum())) for inn in (1, 2)}
            a, b = abbr(names[1]), abbr(names[2])
            fig = go.Figure()
            if what in ("Both", "Fours"):
                fig.add_bar(x=[a, b], y=[fs[1][0], fs[2][0]], name="fours", marker_color=BLUE,
                            text=[fs[1][0], fs[2][0]], textposition="outside")
            if what in ("Both", "Sixes"):
                fig.add_bar(x=[a, b], y=[fs[1][1], fs[2][1]], name="sixes", marker_color=CORAL,
                            text=[fs[1][1], fs[2][1]], textposition="outside")
            idx = {"Both": None, "Fours": 0, "Sixes": 1}[what]
            n1 = sum(fs[1]) if idx is None else fs[1][idx]
            n2 = sum(fs[2]) if idx is None else fs[2][idx]
            word = "boundaries" if idx is None else what.lower()
            title = f"{a} hit {n1} {word}, {b} hit {n2}"
            top = max([n1, n2] + [max(fs[1]), max(fs[2])] if idx is None else [n1, n2])
            fig.update_layout(barmode="group")
            fig.update_yaxes(title=word, range=[0, top * 1.25 + 1])
            show(style(fig, title, 320, f"n = {n1 + n2} {word}" + (f" ({fs[1][0]+fs[2][0]} fours, {fs[1][1]+fs[2][1]} sixes)" if idx is None else "")), "m_fs")


def render_lite():
    """Matches-only view: everything comes from the matches file (no deliveries needed)."""
    st.caption("Matches-only view. Add the deliveries (ball-by-ball) file in the upload box "
               "to unlock the over-by-over charts.")
    tab1, tab2 = st.tabs(["Overview", "Match Detail"])

    # ========================================================================
    # TAB 1 : OVERVIEW
    # ========================================================================
    with tab1:
        f1, f2, f3 = st.columns(3)
        season = f1.selectbox("Season", ["All"] + seasons, format_func=season_fmt, key="l_season")
        team = f2.selectbox("Team", ["All"] + teams, key="l_team")
        toss = f3.selectbox("Toss decision", ["All", "field", "bat"], key="l_toss")
        W, P = where_clause(season, team, toss)

        scale = q("SELECT COUNT(*) AS n, COUNT(DISTINCT season_yy) AS s FROM match_x").iloc[0]   # never filtered
        c0 = q(f"SELECT COUNT(*) AS n, COALESCE(SUM(m.toss_won),0) AS kt, COALESCE(SUM(m.chase_won),0) AS kc "
               f"FROM match_x m WHERE {W} AND m.decided = 1", P).iloc[0]
        n0, kt, kc = int(c0["n"]), int(c0["kt"]), int(c0["kc"])

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi(NAVY, "MATCHES | SEASONS", f"{int(scale['n']):,} | {int(scale['s'])}", "fixed - never changes with filters")
        with c2:
            if n0:
                lo, hi = wilson(kt, n0)
                kpi(TEAL, "TOSS WINNER WON", f"{100*kt/n0:.0f}% (CI {100*lo:.0f}-{100*hi:.0f}%)",
                    f"Test T1: toss winner's win rate vs 50%, p = {fmt_p(p_value(kt, n0))}, n = {n0:,}")
            else:
                kpi(TEAL, "TOSS WINNER WON", "no data", "no matches with a result")
        with c3:
            if n0:
                lo, hi = wilson(kc, n0)
                kpi(PLUM, "CHASING FINDING", f"{100*kc/n0:.0f}% (CI {100*lo:.0f}-{100*hi:.0f}%)",
                    f"Test T2: chasing win rate vs 50%, p = {fmt_p(p_value(kc, n0))}, n = {n0:,}")
            else:
                kpi(PLUM, "CHASING FINDING", "no data", "no matches with a result")
        st.write("")

        # ---- HERO: win rate by season (chart filter: measure) -----------------
        with st.container(border=True):
            h1, _ = st.columns([1, 3])
            measure = h1.selectbox("Chart filter: measure", ["Chasing team wins", "Toss winner wins"], key="l_h_meas")
            col = "chase_won" if measure.startswith("Chasing") else "toss_won"
            hero = q(f"SELECT m.season_yy AS x, 100.0*AVG(m.{col}) AS v, COUNT(*) AS n FROM match_x m "
                     f"WHERE {W} AND m.decided = 1 GROUP BY m.season_yy ORDER BY m.season_yy", P)
            if len(hero):
                best = hero.loc[hero["v"].idxmax()]
                overall = float((hero["v"] * hero["n"]).sum() / hero["n"].sum())
                who = "Chasing teams" if col == "chase_won" else "Toss winners"
                title = f"{who} won {overall:.0f}% of matches overall; the best season was 20{best['x']} ({best['v']:.0f}%)"
                fig = go.Figure(go.Scatter(x=hero["x"], y=hero["v"], mode="lines+markers+text", line=dict(color=CORAL, width=3),
                                           marker=dict(size=9), text=[f"n={int(n)}" for n in hero["n"]],
                                           textposition="top center", textfont=dict(size=9),
                                           hovertemplate="20%{x}: %{y:.0f}%<extra></extra>"))
                fig.add_hline(y=50, line_dash="dash", line_color="black", annotation_text="50%", annotation_position="top left")
                fig.update_yaxes(range=[0, 100], title="win %")
                fig.update_xaxes(title="season", type="category")
                show(style(fig, title, 400, f"n = {int(hero['n'].sum()):,} matches with a result", wrap=120), "l_hero")
            else:
                st.info("No matches with a result for these filters.")

        # ---- row 2: toss decision by season | win type donut -------------------
        ra, rb = st.columns(2)
        with ra, st.container(border=True):
            tw_f = st.selectbox("Chart filter: toss winner", ["All"] + teams, key="l_t_team")
            W2, P2 = W, P
            if tw_f != "All":
                W2, P2 = W + " AND m.toss_winner = ?", P + (tw_f,)
            tdf = q(f"SELECT m.season_yy AS x, m.toss_decision AS d, COUNT(*) AS n FROM match_x m WHERE {W2} "
                    f"GROUP BY m.season_yy, m.toss_decision ORDER BY m.season_yy", P2)
            if len(tdf):
                piv = tdf.pivot(index="x", columns="d", values="n").fillna(0)
                for c in ["field", "bat"]:
                    if c not in piv:
                        piv[c] = 0
                tot = piv["field"].sum() + piv["bat"].sum()
                share = 100 * piv["field"].sum() / tot
                who = "" if tw_f == "All" else f" ({abbr(tw_f)})"
                title = f"Toss winners{who} chose to field in {share:.0f}% of matches"
                fig = go.Figure()
                fig.add_bar(x=piv.index, y=piv["field"], name="field", marker_color=BLUE)
                fig.add_bar(x=piv.index, y=piv["bat"], name="bat", marker_color=AMBER)
                fig.update_layout(barmode="stack")
                fig.update_yaxes(title="toss winners (matches)")
                fig.update_xaxes(title="season", type="category")
                show(style(fig, title, 320, f"n = {int(tot):,} matches"), "l_toss_chart")
            else:
                st.info("No matches for these filters.")
        with rb, st.container(border=True):
            win_t = st.selectbox("Chart filter: winning team", ["All"] + teams, key="l_w_team")
            W2, P2 = W, P
            if win_t != "All":
                W2, P2 = W + " AND m.winner = ?", P + (win_t,)
            wt = q(f"SELECT CASE WHEN m.chase_won = 1 THEN 'By wickets' ELSE 'By runs' END AS kind, "
                   f"COUNT(*) AS n FROM match_x m WHERE {W2} AND m.decided = 1 GROUP BY kind", P2)
            if len(wt):
                wt = wt.set_index("kind").reindex(["By wickets", "By runs"]).fillna(0)
                tot = int(wt["n"].sum())
                lead = "wickets" if wt.loc["By wickets", "n"] >= wt.loc["By runs", "n"] else "runs"
                pct = 100 * wt["n"].max() / tot
                who = "" if win_t == "All" else f" by {abbr(win_t)}"
                title = f"Most matches won{who} ({pct:.0f}%) are won by {lead}"
                fig = go.Figure(go.Pie(labels=wt.index, values=wt["n"], hole=0.55, sort=False,
                                       marker=dict(colors=[TEAL, AMBER]), textinfo="label+value+percent"))
                fig.add_annotation(text=f"{tot:,}<br>results", showarrow=False, font=dict(size=14, color=NAVY))
                fig.update_layout(showlegend=False)
                show(style(fig, title, 320, f"n = {tot:,} matches with a result", wrap=45), "l_donut")
            else:
                st.info("No matches with a result for these filters.")

        # ---- row 3: ranked teams | venues (or matches per season) --------------
        rc, rd = st.columns(2)
        with rc, st.container(border=True):
            min_m = st.slider("Chart filter: minimum matches", 1, 100, 20, key="l_min")
            rk = q(f"SELECT t AS team, COUNT(*) AS n, SUM(w) AS wins FROM ("
                   f"SELECT m.team1 AS t, (m.winner = m.team1) AS w FROM match_x m WHERE {W} AND m.decided = 1 "
                   f"UNION ALL SELECT m.team2, (m.winner = m.team2) FROM match_x m WHERE {W} AND m.decided = 1) "
                   f"GROUP BY t HAVING COUNT(*) >= ?", P + P + (min_m,))
            if len(rk):
                rk["pct"] = 100 * rk["wins"] / rk["n"]
                rk = rk.sort_values("pct")
                top_row = rk.iloc[-1]
                title = (f"{abbr(top_row['team'])} has the best win rate ({top_row['pct']:.0f}%), "
                         f"ranked with a minimum of {min_m} matches")
                fig = go.Figure(go.Bar(y=[abbr(t) for t in rk["team"]], x=rk["pct"], orientation="h", marker_color=TEAL,
                                       text=[f"{int(w)}/{int(n)}" for w, n in zip(rk["wins"], rk["n"])], textposition="outside"))
                fig.add_vline(x=50, line_dash="dash", line_color="black")
                fig.update_xaxes(range=[0, 100], title="win %")
                show(style(fig, title, 320, f"n = {int(rk['n'].sum()):,} team appearances"), "l_rank")
            else:
                st.info(f"No team has {min_m} matches for these filters. Lower the minimum.")
        with rd, st.container(border=True):
            if HAS_VENUE:
                topn = st.selectbox("Chart filter: venues shown", [5, 10, 15], index=1, key="l_topn")
                vn = q(f"SELECT m.venue AS v, COUNT(*) AS n, 100.0*AVG(m.chase_won) AS c FROM match_x m "
                       f"WHERE {W} AND m.decided = 1 AND m.venue IS NOT NULL GROUP BY m.venue "
                       f"ORDER BY n DESC LIMIT ?", P + (topn,))
                if len(vn):
                    vn = vn.sort_values("c")
                    hi_v = vn.iloc[-1]
                    title = f"Chasing wins most at {hi_v['v']} ({hi_v['c']:.0f}% of {int(hi_v['n'])} matches)"
                    fig = go.Figure(go.Bar(y=vn["v"], x=vn["c"], orientation="h", marker_color=PLUM,
                                           text=[f"n={int(n)}" for n in vn["n"]], textposition="outside"))
                    fig.add_vline(x=50, line_dash="dash", line_color="black")
                    fig.update_xaxes(range=[0, 100], title="chasing win %")
                    show(style(fig, title, 320, f"{len(vn)} busiest venues, n = {int(vn['n'].sum()):,} matches", wrap=48), "l_ven")
                else:
                    st.info("No venues for these filters.")
            else:
                show_mode = st.selectbox("Chart filter: matches", ["All", "With a result"], key="l_ms")
                extra = " AND m.decided = 1" if show_mode == "With a result" else ""
                ms = q(f"SELECT m.season_yy AS x, COUNT(*) AS n FROM match_x m WHERE {W}{extra} "
                       f"GROUP BY m.season_yy ORDER BY m.season_yy", P)
                if len(ms):
                    fig = go.Figure(go.Bar(x=ms["x"], y=ms["n"], marker_color=PLUM, text=ms["n"], textposition="outside"))
                    fig.update_xaxes(title="season", type="category")
                    fig.update_yaxes(title="matches")
                    show(style(fig, f"{int(ms['n'].sum()):,} matches in {len(ms)} seasons", 320,
                               f"n = {int(ms['n'].sum()):,} matches"), "l_ms_chart")
                else:
                    st.info("No matches for these filters.")

    # ========================================================================
    # TAB 2 : MATCH DETAIL (context for one selected match)
    # ========================================================================
    with tab2:
        s1, s2 = st.columns([1, 3])
        season2 = s1.selectbox("Season", ["All"] + seasons, format_func=season_fmt, key="l_d_season")
        opts = q("SELECT id, date, team1, team2 FROM match_x WHERE (? = 'All' OR season_yy = ?) ORDER BY seq DESC",
                 (season2, season2))
        if opts.empty:
            st.info("No matches in this season."); return
        labels = {str(r.id): f"{r.date}  |  {abbr(r.team1)} vs {abbr(r.team2)}" for r in opts.itertuples()}
        mid = s2.selectbox("Match", list(labels.keys()), format_func=lambda i: labels[i], key="l_d_match")
        mr = q("SELECT * FROM match_x WHERE id = ?", (str(mid),)).iloc[0]
        ta, tb = mr["team1"], mr["team2"]
        aa, ab = abbr(ta), abbr(tb)
        decided = int(mr["decided"]) == 1

        if not decided:
            result = "No result / tie"
        elif pd.notna(mr["win_margin"]) and mr["win_margin"] > 0:
            result = f"{abbr(mr['winner'])} won by {int(mr['win_margin'])} {mr['win_type']}"
        else:
            result = f"{abbr(mr['winner'])} won"
        k1, k2, k3 = st.columns([1, 1.1, 1])
        with k1:
            match_card("RESULT", result)
        with k2:
            match_card(f"1ST INNINGS — {abbr(mr['first_team'])}", "Batted first", highlight=True)
        with k3:
            match_card(f"2ND INNINGS — {abbr(mr['chase_team'])}", "Chased")
        bits = [str(mr["date"])]
        if HAS_VENUE and pd.notna(mr["venue"]):
            bits.append(str(mr["venue"]))
        if pd.notna(mr["player_of_match"]):
            bits.append(f"Player of the match: {mr['player_of_match']}")
        st.caption("  |  ".join(bits))

        # ---- HERO: head-to-head by season  (chart filter: since season) ---------
        with st.container(border=True):
            h2h = q("SELECT season_yy AS x, SUM(winner = ?) AS a, SUM(winner = ?) AS b, COUNT(*) AS n FROM match_x "
                    "WHERE decided = 1 AND ((team1 = ? AND team2 = ?) OR (team1 = ? AND team2 = ?)) "
                    "GROUP BY season_yy ORDER BY season_yy", (ta, tb, ta, tb, tb, ta))
            if h2h.empty:
                st.info("These two teams have no decided matches in the data.")
            else:
                h1, _ = st.columns([1, 3])
                since = h1.selectbox("Chart filter: since season", [f"20{x}" for x in h2h["x"]], key="l_h2h")[2:]
                hh = h2h[h2h["x"] >= since]
                wa, wb, nn = int(hh["a"].sum()), int(hh["b"].sum()), int(hh["n"].sum())
                if wa == wb:
                    title = f"{aa} and {ab} are level at {wa}-{wb} across {nn} matches"
                else:
                    lead, lw, ll = (aa, wa, wb) if wa > wb else (ab, wb, wa)
                    title = f"{lead} lead the head-to-head {lw}-{ll} across {nn} matches"
                fig = go.Figure()
                fig.add_bar(x=hh["x"], y=hh["a"], name=aa, marker_color=AMBER, text=hh["a"], textposition="outside")
                fig.add_bar(x=hh["x"], y=hh["b"], name=ab, marker_color=PLUM, text=hh["b"], textposition="outside")
                fig.update_layout(barmode="group")
                fig.update_xaxes(title="season", type="category")
                fig.update_yaxes(title="wins", dtick=1)
                show(style(fig, title, 380, f"n = {nn} matches between {aa} and {ab}", wrap=120), "l_m_hero")

        # ---- row 2: recent form | win rate this season vs overall ---------------
        ra, rb = st.columns(2)
        with ra, st.container(border=True):
            last_n = st.selectbox("Chart filter: last matches", [5, 10, 20], index=1, key="l_form_n")
            rows = {}
            for t in (ta, tb):
                f = q("SELECT winner FROM match_x WHERE decided = 1 AND (team1 = ? OR team2 = ?) AND seq < ? "
                      "ORDER BY seq DESC LIMIT ?", (t, t, int(mr["seq"]), int(last_n)))
                rows[t] = (int((f["winner"] == t).sum()), len(f))
            title = (f"Before this match {aa} won {rows[ta][0]} of their last {rows[ta][1]}; "
                     f"{ab} won {rows[tb][0]} of {rows[tb][1]}")
            fig = go.Figure()
            fig.add_bar(x=[aa, ab], y=[rows[ta][0], rows[tb][0]], name="won", marker_color=GREEN,
                        text=[rows[ta][0], rows[tb][0]], textposition="inside")
            fig.add_bar(x=[aa, ab], y=[rows[ta][1] - rows[ta][0], rows[tb][1] - rows[tb][0]], name="lost",
                        marker_color=CORAL, text=[rows[ta][1] - rows[ta][0], rows[tb][1] - rows[tb][0]], textposition="inside")
            fig.update_layout(barmode="stack")
            fig.update_yaxes(title="matches")
            show(style(fig, title, 320, f"n = {rows[ta][1] + rows[tb][1]} matches"), "l_m_form")
        with rb, st.container(border=True):
            cmp_ = st.radio("Chart filter: compare", ["This season", "All seasons", "Both"], horizontal=True, key="l_cmp")

            def wr(t, ssn):
                extra, par = ("", ()) if ssn is None else (" AND season_yy = ?", (ssn,))
                r = q(f"SELECT COUNT(*) AS n, COALESCE(SUM(winner = ?), 0) AS w FROM match_x "
                      f"WHERE decided = 1 AND (team1 = ? OR team2 = ?){extra}", (t, t, t) + par).iloc[0]
                return (100 * r["w"] / r["n"] if r["n"] else 0.0), int(r["n"])
            s_id = mr["season_yy"]
            fig = go.Figure()
            n_tot = 0
            if cmp_ in ("This season", "Both"):
                v = [wr(ta, s_id), wr(tb, s_id)]
                fig.add_bar(x=[aa, ab], y=[x[0] for x in v], name=f"20{s_id}", marker_color=AMBER,
                            text=[f"{x[0]:.0f}% (n={x[1]})" for x in v], textposition="outside")
                n_tot += sum(x[1] for x in v)
            if cmp_ in ("All seasons", "Both"):
                v2 = [wr(ta, None), wr(tb, None)]
                fig.add_bar(x=[aa, ab], y=[x[0] for x in v2], name="all seasons", marker_color=PLUM,
                            text=[f"{x[0]:.0f}% (n={x[1]})" for x in v2], textposition="outside")
                n_tot += sum(x[1] for x in v2)
            ref = wr(ta, s_id if cmp_ != "All seasons" else None)[0]
            ref_b = wr(tb, s_id if cmp_ != "All seasons" else None)[0]
            better = aa if ref >= ref_b else ab
            title = f"{better} has the higher win rate {'in 20' + s_id if cmp_ != 'All seasons' else 'over all seasons'} ({max(ref, ref_b):.0f}%)"
            fig.add_hline(y=50, line_dash="dash", line_color="black", annotation_text="50%", annotation_position="top left")
            fig.update_layout(barmode="group")
            fig.update_yaxes(range=[0, 115], title="win %")
            show(style(fig, title, 320, f"n = {n_tot} team appearances"), "l_m_wr")

        # ---- row 3: bat first vs chase | toss decisions -----------------------
        rc, rd = st.columns(2)
        venue = mr["venue"] if HAS_VENUE and pd.notna(mr["venue"]) else None
        with rc, st.container(border=True):
            scope = "All venues"
            if venue:
                scope = st.radio("Chart filter: scope", ["This venue", "All venues"], horizontal=True, key="l_scope")
            ex, par = ((" AND venue = ?", (venue,)) if scope == "This venue" else ("", ()))
            r = q(f"SELECT COUNT(*) AS n, COALESCE(SUM(chase_won), 0) AS c FROM match_x WHERE decided = 1{ex}", par).iloc[0]
            n_v, c_v = int(r["n"]), int(r["c"])
            if n_v:
                pc = 100 * c_v / n_v
                place = venue if scope == "This venue" else "all venues"
                title = f"At {place}, chasing teams won {pc:.0f}% of {n_v} matches"
                fig = go.Figure(go.Bar(x=["Batting first", "Chasing"], y=[100 - pc, pc], marker_color=[AMBER, PLUM],
                                       text=[f"{100-pc:.0f}% ({n_v-c_v})", f"{pc:.0f}% ({c_v})"], textposition="outside"))
                fig.add_hline(y=50, line_dash="dash", line_color="black", annotation_text="50%", annotation_position="top left")
                fig.update_yaxes(range=[0, 100], title="win %")
                show(style(fig, title, 320, f"n = {n_v} matches with a result", wrap=48), "l_m_bf")
            else:
                st.info("No decided matches in this scope.")
        with rd, st.container(border=True):
            tw_lab = {"All": "All", aa: ta, ab: tb}
            who_t = tw_lab[st.selectbox("Chart filter: toss winner", list(tw_lab), key="l_m_tw")]
            ex, par = ((" AND venue = ?", (venue,)) if venue else ("", ()))
            if who_t != "All":
                ex += " AND toss_winner = ?"; par = par + (who_t,)
            td = q(f"SELECT toss_decision AS d, COUNT(*) AS n FROM match_x WHERE 1=1{ex} GROUP BY toss_decision", par)
            if len(td):
                td = td.set_index("d").reindex(["field", "bat"]).fillna(0)
                tot = int(td["n"].sum())
                pf = 100 * td.loc["field", "n"] / tot
                place = f" at {venue}" if venue else ""
                title = f"Toss winners{'' if who_t == 'All' else ' (' + abbr(who_t) + ')'} chose to field in {pf:.0f}% of {tot} matches{place}"
                fig = go.Figure(go.Pie(labels=["field", "bat"], values=td["n"], hole=0.55, sort=False,
                                       marker=dict(colors=[BLUE, AMBER]), textinfo="label+value+percent"))
                fig.add_annotation(text=f"{tot}<br>tosses", showarrow=False, font=dict(size=14, color=NAVY))
                fig.update_layout(showlegend=False)
                show(style(fig, title, 320, f"n = {tot} matches", wrap=48), "l_m_toss")
            else:
                st.info("No toss data for this selection.")


render_full() if FULL else render_lite()