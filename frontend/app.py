import html
import random
import re
import time

import streamlit as st

from api_client import APIError, ask_question, check_health

# =====================================================================
#  Things you can edit
# =====================================================================
APP_TITLE = "Drug Assistant Chatbot"
APP_TAGLINE = (
    "Ask about medicines and pharmacy practice. Answers come only from your "
    "indexed documents, with sources."
)

EXAMPLE_QUESTIONS = [
    "What are the contraindications of metformin?",
    "What are the common side effects of amoxicillin?",
    "How should medicines be stored during distribution?",
    "Can atorvastatin be used during pregnancy?",
]
NOT_FOUND_PREFIX = "i could not find"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =====================================================================
#  Helpers
# =====================================================================
def html_block(text: str) -> str:
    """Remove indentation and blank lines so Streamlit's markdown never
    mistakes our HTML for a code block."""
    return "\n".join(line.strip() for line in text.strip().splitlines() if line.strip())


def show_html(text: str) -> None:
    st.markdown(html_block(text), unsafe_allow_html=True)


CITE = re.compile(r"\s*\[(\d{1,2})\]")


def decorate(text: str) -> str:
    """Escape HTML from the model, then turn [1] into small round badges."""
    safe = html.escape(text, quote=False)
    return CITE.sub('\u2060<span class="cite">\\1</span>', safe)  # \u2060 = keeps the badge on the same line as the word before it


SOURCE = re.compile(r"^\[(\d+)\]\s*(.+?)(?:\s*\(page\s*(\d+)\))?\s*$")


def pretty_name(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    return re.sub(r"[_\-]+", " ", stem).strip().title()


def sources_html(sources: list[str]) -> str:
    cards = []
    for i, raw in enumerate(sources):
        match = SOURCE.match(raw)
        num, filename, page = match.groups() if match else (str(i + 1), raw, None)
        meta = html.escape(filename) + (f" · page {html.escape(page)}" if page else "")
        cards.append(
            f'<div class="src" style="--i:{i}"><span class="num">{html.escape(num)}</span>'
            f'<div><div class="sname">{html.escape(pretty_name(filename))}</div>'
            f'<div class="smeta">{meta}</div></div></div>'
        )
    return '<div class="srcgrid">' + "".join(cards) + "</div>"


def ecg_path() -> str:
    """Draw a heartbeat line with a few beats."""
    d = "M0 30"
    for x in (110, 300, 490, 680):
        d += (
            f" L{x - 40} 30 L{x - 28} 23 L{x - 16} 30 L{x - 8} 30 L{x} 5"
            f" L{x + 9} 54 L{x + 18} 30 L{x + 32} 30 L{x + 46} 21 L{x + 60} 30"
        )
    return d + " L800 30"


def floating_items() -> str:
    """Pills, capsules and crosses that drift upward in the background."""
    rnd = random.Random(42)
    items = []
    for _ in range(18):
        kind = rnd.choice(["capsule", "capsule", "pill", "cross", "drop"])
        style = (
            f"--l:{rnd.randint(2, 96)}%;--s:{rnd.randint(26, 70)}px;"
            f"--d:{rnd.randint(18, 36)}s;--dl:-{rnd.randint(0, 34)}s;"
            f"--r:{rnd.randint(-45, 45)}deg"
        )
        items.append(f'<span class="fl {kind}" style="{style}"></span>')
    return "".join(items)


# =====================================================================
#  Styling (CSS)
# =====================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --teal:#2dd4bf; --mint:#5eead4; --cyan:#22d3ee;
  --ink:#e8f4f5; --muted:#9fb8bd;
  --glass:rgba(255,255,255,.07); --glass-b:rgba(255,255,255,.15);
}
html, body, .stApp, .stApp button, .stApp textarea{
  font-family:'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}
html, body{background:#02101c;}
.stApp{background:transparent !important; color:var(--ink);}
@keyframes bgShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
[data-testid="stHeader"], [data-testid="stAppViewContainer"], [data-testid="stMain"]{background:transparent !important;}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"]{display:none !important;}
.block-container{max-width:980px; padding-top:2.4rem; padding-bottom:7rem;}

/* ---------- text colours (works in light and dark Streamlit themes) ---------- */
[data-testid="stMarkdownContainer"]{color:var(--ink);}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3{color:var(--ink) !important;}
[data-testid="stMarkdownContainer"] li::marker{color:var(--mint);}

/* ---------- animated background ---------- */
.bg{position:fixed; inset:0; z-index:-1; overflow:hidden; pointer-events:none;
  background:linear-gradient(135deg,#02101c 0%,#04283b 45%,#055e5a 100%);
  background-size:220% 220%; animation:bgShift 26s ease-in-out infinite;}
.bg .grid{position:absolute; inset:0;
  background-image:radial-gradient(rgba(255,255,255,.08) 1px, transparent 1px);
  background-size:28px 28px;
  -webkit-mask-image:radial-gradient(ellipse at center, #000 25%, transparent 78%);
  mask-image:radial-gradient(ellipse at center, #000 25%, transparent 78%);}
.orb{position:absolute; border-radius:50%; filter:blur(90px); opacity:.38;
  animation:drift 24s ease-in-out infinite alternate;}
.orb.a{width:440px;height:440px;background:#14b8a6;top:-140px;left:-100px;}
.orb.b{width:560px;height:560px;background:#0ea5e9;bottom:-200px;right:-140px;animation-delay:-9s;}
.orb.c{width:320px;height:320px;background:#22c55e;top:38%;left:46%;opacity:.16;animation-delay:-15s;}
@keyframes drift{0%{transform:translate(0,0) scale(1)}100%{transform:translate(70px,50px) scale(1.15)}}
.fl{position:absolute; bottom:-110px; left:var(--l); width:var(--s); height:calc(var(--s)*.42);
  opacity:0; animation:floatUp var(--d) linear infinite; animation-delay:var(--dl);}
@keyframes floatUp{
  0%{transform:translateY(0) rotate(var(--r)); opacity:0}
  10%{opacity:.34} 88%{opacity:.34}
  100%{transform:translateY(-125vh) rotate(calc(var(--r) + 200deg)); opacity:0}}
.fl.capsule{border-radius:999px;
  background:linear-gradient(90deg,#2dd4bf 0 50%,#f1f5f9 50% 100%);
  box-shadow:inset 0 -4px 8px rgba(0,0,0,.28), inset 0 3px 6px rgba(255,255,255,.35);}
.fl.pill{width:calc(var(--s)*.7); height:calc(var(--s)*.7); border-radius:50%;
  background:radial-gradient(circle at 32% 30%,#fef3c7,#f59e0b 70%);
  box-shadow:inset 0 -4px 8px rgba(0,0,0,.25);}
.fl.cross{width:calc(var(--s)*.6); height:calc(var(--s)*.6);
  background:linear-gradient(#5eead4,#5eead4) center/100% 30% no-repeat,
             linear-gradient(#5eead4,#5eead4) center/30% 100% no-repeat;
  filter:drop-shadow(0 0 6px rgba(45,212,191,.6));}
.fl.drop{width:calc(var(--s)*.4); height:calc(var(--s)*.4);
  border-radius:50% 50% 50% 0; background:linear-gradient(135deg,#7dd3fc,#0ea5e9);}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{background:rgba(3,17,30,.72); backdrop-filter:blur(18px);
  border-right:1px solid var(--glass-b);}
[data-testid="stSidebar"] > div:first-child{background:transparent;}
.brand{display:flex; align-items:center; gap:12px; margin:4px 0 16px; animation:fadeUp .7s both;}
.brand-pill{width:44px;height:44px;border-radius:14px;display:grid;place-items:center;font-size:22px;
  background:linear-gradient(135deg,#14b8a6,#0ea5e9); box-shadow:0 8px 22px rgba(20,184,166,.45);}
.brand-name{font-weight:800; font-size:1.1rem; color:#fff; letter-spacing:-.01em;}
.brand-sub{font-size:.75rem; color:var(--muted);}
.side-title{font-size:.72rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
  color:var(--muted); margin:20px 0 8px;}
.status{display:flex; align-items:center; gap:10px; padding:10px 14px; border-radius:14px; font-weight:600; font-size:.9rem;
  background:var(--glass); border:1px solid var(--glass-b);}
.status .dot{width:10px;height:10px;border-radius:50%;position:relative;}
.status .dot::after{content:""; position:absolute; inset:0; border-radius:50%; background:inherit; animation:ping 1.8s ease-out infinite;}
.status.ok{color:#86efac;} .status.ok .dot{background:#22c55e;}
.status.bad{color:#fca5a5;} .status.bad .dot{background:#ef4444;}
@keyframes ping{0%{transform:scale(1);opacity:.7}100%{transform:scale(3);opacity:0}}
.steps{list-style:none; margin:0; padding:0; counter-reset:s;}
.steps li{counter-increment:s; position:relative; padding:6px 0 6px 38px; font-size:.86rem; color:var(--muted) !important;}
.steps li::before{content:counter(s); position:absolute; left:0; top:4px; width:26px; height:26px; border-radius:50%;
  display:grid; place-items:center; font-size:.78rem; font-weight:700; color:#03111e;
  background:linear-gradient(135deg,#5eead4,#22d3ee);}
.steps li b{color:var(--ink);}
.disclaimer{margin-top:18px; padding:12px 14px; border-radius:14px; font-size:.78rem; line-height:1.45;
  color:#fde68a; background:rgba(251,191,36,.10); border:1px solid rgba(251,191,36,.35);}

/* ---------- hero ---------- */
@keyframes fadeUp{from{opacity:0; transform:translateY(18px)} to{opacity:1; transform:none}}
.hero{display:flex; gap:24px; align-items:center; padding:26px 30px; border-radius:26px;
  background:linear-gradient(135deg,rgba(255,255,255,.11),rgba(255,255,255,.04));
  border:1px solid var(--glass-b); backdrop-filter:blur(16px);
  box-shadow:0 24px 60px rgba(0,0,0,.35); animation:fadeUp .8s both;}
.logo{position:relative; flex:none; width:88px; height:88px; display:grid; place-items:center;}
.logo .icon{font-size:46px; animation:bob 3.2s ease-in-out infinite;}
.logo .ring{position:absolute; inset:4px; border-radius:50%; border:2px solid rgba(94,234,212,.6); animation:pulse 2.8s ease-out infinite;}
.logo .ring.r2{animation-delay:1.4s;}
@keyframes pulse{0%{transform:scale(.7);opacity:.9}100%{transform:scale(1.55);opacity:0}}
@keyframes bob{0%,100%{transform:translateY(0) rotate(-6deg)}50%{transform:translateY(-6px) rotate(6deg)}}
.hero .title{font-size:2.35rem; font-weight:800; letter-spacing:-.02em; line-height:1.1; margin:0;
  background:linear-gradient(90deg,#f0fffd,#5eead4,#22d3ee,#f0fffd); background-size:250% 100%;
  -webkit-background-clip:text; background-clip:text; color:transparent; -webkit-text-fill-color:transparent;
  animation:shimmer 7s linear infinite;}
@keyframes shimmer{0%{background-position:0% 0}100%{background-position:250% 0}}
.hero p.sub{margin:8px 0 12px; color:var(--muted) !important; font-size:1rem; line-height:1.5;}
.chips{display:flex; flex-wrap:wrap; gap:8px;}
.chips span{padding:5px 12px; border-radius:999px; font-size:.78rem; font-weight:600; color:var(--mint);
  background:rgba(45,212,191,.12); border:1px solid rgba(94,234,212,.32);}
.ecg{width:100%; height:auto; display:block; margin:14px 0 2px; opacity:.95;}
.ecg path{fill:none; stroke-width:2.2; stroke-linecap:round; stroke-linejoin:round;}
.ecg .base{stroke:rgba(94,234,212,.16);}
.ecg .line{stroke:#5eead4; stroke-dasharray:1000; stroke-dashoffset:1000; filter:drop-shadow(0 0 5px #2dd4bf);
  animation:ecg 5s linear infinite;}
@keyframes ecg{0%{stroke-dashoffset:1000; opacity:1}72%{stroke-dashoffset:0; opacity:1}100%{stroke-dashoffset:0; opacity:0}}

/* ---------- welcome card ---------- */
.welcome{margin:26px 0 12px; animation:fadeUp .9s .15s both;}
.welcome .wt{font-size:1.35rem; font-weight:700; color:#fff;}
.welcome .ws{color:var(--muted); font-size:.95rem; margin-top:2px;}

/* ---------- buttons (example questions, clear chat) ---------- */
[data-testid="stButton"], [data-testid="stElementContainer"]:has(> [data-testid="stButton"]){width:100% !important;}
.stButton > button{width:100%; justify-content:flex-start; text-align:left; background:var(--glass);
  border:1px solid var(--glass-b); border-radius:14px; padding:.62rem .95rem; font-weight:500;
  transition:transform .2s, border-color .2s, background .2s, box-shadow .2s;}
.stButton > button:hover{transform:translateY(-2px); border-color:var(--teal); background:rgba(45,212,191,.13);
  box-shadow:0 10px 26px rgba(45,212,191,.2);}
.stButton > button:active{transform:translateY(0);}
.stButton > button p{color:var(--ink) !important; font-size:.9rem; text-align:left;}
.stButton > button > div{width:100%; justify-content:flex-start !important; text-align:left;}
.stButton > button [data-testid="stMarkdownContainer"]{width:100%; text-align:left;}
[data-testid="stSidebarCollapseButton"] *, [data-testid="stExpandSidebarButton"] *{color:var(--ink) !important;}
.st-key-clear button{border-color:rgba(248,113,113,.4); background:rgba(248,113,113,.08);}
.st-key-clear button:hover{border-color:#f87171; background:rgba(248,113,113,.18); box-shadow:0 10px 26px rgba(248,113,113,.2);}

/* ---------- chat ---------- */
[data-testid="stChatMessage"]{background:var(--glass); border:1px solid var(--glass-b); border-radius:20px;
  padding:1rem 1.25rem; margin-bottom:.95rem; backdrop-filter:blur(14px);
  box-shadow:0 12px 32px rgba(0,0,0,.25); animation:msgIn .55s cubic-bezier(.2,.8,.2,1) both;}
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]),
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){
  background:linear-gradient(135deg,rgba(45,212,191,.30),rgba(14,165,233,.22)); border-color:rgba(94,234,212,.5);}
@keyframes msgIn{from{opacity:0; transform:translateY(16px) scale(.98)} to{opacity:1; transform:none}}
[data-testid="stChatMessage"] > div:first-child{background:rgba(255,255,255,.14) !important; border-radius:12px;}
.cite{display:inline; padding:1px 6px; margin:0 2px 0 3px; border-radius:999px; font-size:.68rem; font-weight:700;
  color:#03111e; vertical-align:super; line-height:1; background:linear-gradient(135deg,#5eead4,#22d3ee);}
.meta{margin-top:6px; font-size:.75rem; color:var(--muted);}

/* typing indicator */
.typing{display:flex; align-items:center; gap:6px; padding:6px 0;}
.typing .tdot{width:9px; height:9px; border-radius:50%; background:var(--mint); animation:blink 1.2s infinite ease-in-out;}
.typing .tdot:nth-child(2){animation-delay:.18s} .typing .tdot:nth-child(3){animation-delay:.36s}
.typing .tlabel{margin-left:8px; font-size:.86rem; color:var(--muted); animation:fadeText 1.6s ease-in-out infinite;}
@keyframes blink{0%,80%,100%{transform:translateY(0) scale(.7); opacity:.4}40%{transform:translateY(-7px) scale(1); opacity:1}}
@keyframes fadeText{0%,100%{opacity:.55}50%{opacity:1}}

/* callouts */
.callout{padding:14px 16px; border-radius:14px; line-height:1.5; font-size:.95rem;}
.callout .hint{display:block; margin-top:6px; font-size:.82rem; opacity:.85;}
.callout.nf{background:rgba(251,191,36,.10); border:1px solid rgba(251,191,36,.4); color:#fde68a;}
.callout.err{background:rgba(248,113,113,.10); border:1px solid rgba(248,113,113,.45); color:#fecaca;}

/* sources */
[data-testid="stExpander"]{background:rgba(255,255,255,.05); border:1px solid var(--glass-b); border-radius:14px; margin-top:8px;}
[data-testid="stExpander"] summary{color:var(--mint); background:transparent !important; border-radius:14px;}
[data-testid="stExpander"] summary:hover{background:rgba(255,255,255,.06) !important;}
[data-testid="stExpander"] summary p{color:var(--mint) !important; font-weight:600;}
.srcgrid{display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:10px;}
.src{display:flex; gap:12px; align-items:center; padding:10px 12px; border-radius:12px;
  background:rgba(255,255,255,.06); border:1px solid var(--glass-b);
  animation:fadeUp .5s both; animation-delay:calc(var(--i) * .08s); transition:transform .2s, border-color .2s;}
.src:hover{transform:translateY(-2px); border-color:var(--teal);}
.src .num{flex:none; width:28px; height:28px; border-radius:50%; display:grid; place-items:center; font-weight:800;
  font-size:.82rem; color:#03111e; background:linear-gradient(135deg,#5eead4,#22d3ee);}
.src .sname{font-weight:600; font-size:.9rem; color:#fff;}
.src .smeta{font-size:.76rem; color:var(--muted); word-break:break-all;}

/* chat input */
[data-testid="stBottom"], [data-testid="stBottom"] > div{background:transparent !important;}
[data-testid="stChatInput"]{background:transparent !important; border:none !important; box-shadow:none !important;}
[data-testid="stChatInput"] > div{background:rgba(255,255,255,.09) !important; border:1px solid rgba(94,234,212,.4) !important;
  border-radius:28px !important; backdrop-filter:blur(16px); transition:border-color .25s, box-shadow .25s;}
[data-testid="stChatInput"]:focus-within > div{border-color:var(--teal) !important;
  box-shadow:0 0 0 4px rgba(45,212,191,.2), 0 12px 34px rgba(0,0,0,.4);}
[data-testid="stChatInput"] textarea{color:#fff !important; -webkit-text-fill-color:#fff !important; background:transparent !important;}
[data-testid="stChatInput"] textarea::placeholder{color:var(--muted) !important; -webkit-text-fill-color:var(--muted) !important;}
[data-testid="stChatInput"] button{background:linear-gradient(135deg,#14b8a6,#0ea5e9) !important; border-radius:50% !important;}
[data-testid="stChatInput"] button svg{fill:#fff !important; color:#fff !important;}

/* ---------- small screens ---------- */
@media (max-width:700px){
  .hero{flex-direction:column; text-align:center; padding:22px 18px;}
  .hero .title{font-size:1.8rem;} .chips{justify-content:center;}
}
@media (prefers-reduced-motion:reduce){
  *{animation-duration:.01ms !important; animation-iteration-count:1 !important; transition:none !important;}
}
</style>
"""
show_html(CSS)

# Animated background layer (pills, capsules, glowing orbs)
show_html(
    f"""
    <div class="bg">
      <div class="orb a"></div><div class="orb b"></div><div class="orb c"></div>
      <div class="grid"></div>
      {floating_items()}
    </div>
    """
)


# =====================================================================
#  State
# =====================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []


def set_pending(question: str) -> None:
    """Called when an example-question button is clicked."""
    st.session_state.pending_question = question


# =====================================================================
#  Sidebar
# =====================================================================
with st.sidebar:
    show_html(
        """
        <div class="brand">
          <div class="brand-pill">💊</div>
          <div><div class="brand-name">DrugAssist</div><div class="brand-sub">Pharmaceutical knowledge base</div></div>
        </div>
        <div class="side-title">Status</div>
        """
    )
    if check_health():
        show_html('<div class="status ok"><span class="dot"></span>Backend is online</div>')
    else:
        show_html('<div class="status bad"><span class="dot"></span>Backend is offline</div>')

    show_html('<div class="side-title">Try asking</div>')
    for i, example in enumerate(EXAMPLE_QUESTIONS):
        st.button(example, key=f"side_{i}", on_click=set_pending, args=(example,))

    show_html(
        """
        <div class="side-title">How it works</div>
        <ol class="steps">
          <li><b>Search</b> your indexed documents</li>
          <li><b>Retrieve</b> the most relevant passages</li>
          <li><b>Answer</b> using only those passages, with sources</li>
        </ol>
        <div class="disclaimer">⚠️ For education only. This is not medical advice.
        Always consult a doctor or pharmacist.</div>
        <div class="side-title">Conversation</div>
        """
    )
    if st.button("🗑️ Clear chat", key="clear"):
        st.session_state.messages = []
        st.rerun()


# =====================================================================
#  Hero header
# =====================================================================
show_html(
    f"""
    <div class="hero">
      <div class="logo"><span class="ring"></span><span class="ring r2"></span><span class="icon">💊</span></div>
      <div>
        <div class="title">{html.escape(APP_TITLE)}</div>
        <p class="sub">{html.escape(APP_TAGLINE)}</p>
        <div class="chips"><span>🔒 Runs locally</span><span>📚 Grounded answers</span><span>📎 Cited sources</span></div>
      </div>
    </div>
    <svg class="ecg" viewBox="0 0 800 60" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path class="base" pathLength="1000" d="{ecg_path()}"/>
      <path class="line" pathLength="1000" d="{ecg_path()}"/>
    </svg>
    """
)


# =====================================================================
#  Rendering helpers for chat messages
# =====================================================================
def render_body(content: str, kind: str) -> None:
    if kind == "notfound":
        show_html(
            f"""<div class="callout nf"><b>🔍 Not found in the documents</b><br>{html.escape(content)}
            <span class="hint">Try rephrasing, or ask about a medicine or topic covered by the indexed files.</span></div>"""
        )
    elif kind == "error":
        show_html(f'<div class="callout err"><b>⚠️ Something went wrong</b><br>{html.escape(content)}</div>')
    else:
        st.markdown(decorate(content), unsafe_allow_html=True)


def render_extras(sources: list[str], kind: str, elapsed: float | None, expanded: bool) -> None:
    if elapsed is not None and kind == "normal":
        n = len(sources)
        show_html(f'<div class="meta">⏱ answered in {elapsed:.1f} s · {n} source{"s" if n != 1 else ""}</div>')
    if sources:
        with st.expander(f"📎 Sources ({len(sources)})", expanded=expanded):
            show_html(sources_html(sources))


def typewriter(placeholder, text: str) -> None:
    """Reveal the answer word by word (max ~2 seconds)."""
    words = re.findall(r"\S+\s*", text)
    step = max(1, len(words) // 70)
    for i in range(step, len(words) + step, step):
        placeholder.markdown(decorate("".join(words[:i])) + " ▌", unsafe_allow_html=True)
        time.sleep(0.028)
    placeholder.markdown(decorate(text), unsafe_allow_html=True)


# =====================================================================
#  Chat
# =====================================================================
typed = st.chat_input("Ask about a medicine, dose, side effect, storage…")
pending = st.session_state.pop("pending_question", None)
question = typed or pending

# --- history ---
last_index = len(st.session_state.messages) - 1
for index, message in enumerate(st.session_state.messages):
    avatar = "🧑‍⚕️" if message["role"] == "user" else "💊"
    with st.chat_message(message["role"], avatar=avatar):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            kind = message.get("kind", "normal")
            render_body(message["content"], kind)
            render_extras(message.get("sources", []), kind, message.get("elapsed"), expanded=(index == last_index))

# --- welcome screen ---
if not st.session_state.messages and not question:
    show_html(
        """
        <div class="welcome">
          <div class="wt">👋 How can I help you today?</div>
          <div class="ws">Pick a question to get started, or type your own below.</div>
        </div>
        """
    )
    columns = st.columns(2)
    for i, example in enumerate(EXAMPLE_QUESTIONS):
        with columns[i % 2]:
            st.button(example, key=f"welcome_{i}", on_click=set_pending, args=(example,))

# --- new question ---
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑‍⚕️"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="💊"):
        holder = st.empty()
        show_typing = '<div class="typing"><span class="tdot"></span><span class="tdot"></span><span class="tdot"></span><span class="tlabel">Searching the documents and thinking…</span></div>'
        holder.markdown(show_typing, unsafe_allow_html=True)

        started = time.time()
        answer, sources, kind = "", [], "normal"
        try:
            data = ask_question(question)
            answer, sources = data["answer"], data["sources"]
            if answer.strip().lower().startswith(NOT_FOUND_PREFIX):
                kind = "notfound"
        except APIError as error:
            answer, kind = str(error), "error"
        elapsed = time.time() - started

        if kind == "normal":
            typewriter(holder, answer)  # replaces the typing dots and reveals the answer
        else:
            holder.empty()
            render_body(answer, kind)
        render_extras(sources, kind, elapsed, expanded=True)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources, "kind": kind, "elapsed": elapsed}
    )