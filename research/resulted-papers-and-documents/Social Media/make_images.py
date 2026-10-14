#!/usr/bin/env python3
"""Render branded social images (Instagram squares + LinkedIn banner) from SVG."""
import cairosvg, pathlib

OUT = pathlib.Path(__file__).resolve().parent
FONT = "DejaVu Sans"

# brand palette (matches the Odin desktop app)
BG, BG2 = "#0a0c12", "#0f1320"
BRAND, BRAND2 = "#6c8cff", "#7af0d0"
TXT, DIM, FAINT = "#e8ecf6", "#9aa4bf", "#5f6885"

DEFS = f'''
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>
  </linearGradient>
  <linearGradient id="brandgrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{BRAND}"/><stop offset="1" stop-color="{BRAND2}"/>
  </linearGradient>
  <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="{BRAND2}" stop-opacity="0.30"/>
    <stop offset="1" stop-color="{BRAND2}" stop-opacity="0"/>
  </radialGradient>
</defs>
'''

def mark(x, y, r=26):
    return f'''<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="url(#brandgrad)" stroke-width="3"/>
    <text x="{x}" y="{y+r*0.34}" font-family="{FONT}" font-size="{r*0.95}" font-weight="bold"
    fill="url(#brandgrad)" text-anchor="middle">&#937;</text>'''  # Omega

def render(name, svg, w):
    p = OUT / name
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(p), output_width=w*2, output_height=None)
    print("wrote", p.name)

# ---------- IG 1: COVER (1080x1080) ----------
ig1 = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
{DEFS}
<rect width="1080" height="1080" fill="url(#bg)"/>
<ellipse cx="820" cy="250" rx="520" ry="420" fill="url(#glow)"/>
{mark(96, 110, 30)}
<text x="150" y="120" font-family="{FONT}" font-size="30" font-weight="bold" fill="{TXT}">Odin-Orchestrator</text>
<text x="96" y="180" font-family="{FONT}" font-size="22" letter-spacing="4" fill="{BRAND2}">ENGINEERING &#183; AI AGENTS</text>

<text x="96" y="470" font-family="{FONT}" font-size="74" font-weight="bold" fill="{TXT}">The AI software</text>
<text x="96" y="556" font-family="{FONT}" font-size="74" font-weight="bold" fill="{TXT}">company that</text>
<text x="96" y="642" font-family="{FONT}" font-size="74" font-weight="bold" fill="url(#brandgrad)">refuses to lie</text>
<text x="96" y="728" font-family="{FONT}" font-size="74" font-weight="bold" fill="url(#brandgrad)">to itself.</text>

<rect x="96" y="800" width="120" height="5" rx="2" fill="url(#brandgrad)"/>
<text x="96" y="880" font-family="{FONT}" font-size="30" fill="{DIM}">A multi-agent dev system built on one rule:</text>
<text x="96" y="924" font-family="{FONT}" font-size="30" font-weight="bold" fill="{TXT}">never fake success.</text>
<text x="96" y="1010" font-family="{FONT}" font-size="24" fill="{FAINT}">Swipe &#8594;  the engineering story</text>
</svg>'''

# ---------- IG 2: THE IDEA / un-gameable tests (1080x1080) ----------
ig2 = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
{DEFS}
<rect width="1080" height="1080" fill="url(#bg)"/>
<text x="96" y="150" font-family="{FONT}" font-size="24" letter-spacing="3" fill="{BRAND2}">THE CORE IDEA</text>
<text x="96" y="280" font-family="{FONT}" font-size="92" font-weight="bold" fill="{TXT}">Make the test</text>
<text x="96" y="376" font-family="{FONT}" font-size="92" font-weight="bold" fill="url(#brandgrad)">un-gameable.</text>

<text x="96" y="470" font-family="{FONT}" font-size="30" fill="{DIM}">We mint a random token at runtime. It must travel,</text>
<text x="96" y="512" font-family="{FONT}" font-size="30" fill="{DIM}">unchanged, between agents &#8212; through shared context.</text>

<!-- token flow -->
<g>
  <circle cx="220" cy="700" r="70" fill="rgba(108,140,255,0.15)" stroke="{BRAND}" stroke-width="3"/>
  <text x="220" y="710" font-family="{FONT}" font-size="30" fill="{TXT}" text-anchor="middle">Agent A</text>
  <circle cx="860" cy="700" r="70" fill="rgba(108,140,255,0.15)" stroke="{BRAND}" stroke-width="3"/>
  <text x="860" y="710" font-family="{FONT}" font-size="30" fill="{TXT}" text-anchor="middle">Agent B</text>
  <line x1="296" y1="700" x2="784" y2="700" stroke="{BRAND2}" stroke-width="3" stroke-dasharray="10 8"/>
  <rect x="430" y="660" width="220" height="80" rx="14" fill="{BG2}" stroke="{BRAND2}" stroke-width="2"/>
  <text x="540" y="710" font-family="DejaVu Sans Mono" font-size="34" font-weight="bold" fill="{BRAND2}" text-anchor="middle">ODIN-7M4WJ9</text>
</g>

<text x="96" y="900" font-family="{FONT}" font-size="34" font-weight="bold" fill="{TXT}">No pre-written answer can contain it.</text>
<text x="96" y="952" font-family="{FONT}" font-size="30" fill="{DIM}">If it reappears, context was truly shared. If not,</text>
<text x="96" y="994" font-family="{FONT}" font-size="30" fill="{DIM}">the test fails &#8212; and that failure is the win.</text>
</svg>'''

# ---------- IG 3: WHAT WE BUILT (1080x1080) ----------
def row(y, title, sub):
    return f'''<circle cx="120" cy="{y-12}" r="9" fill="url(#brandgrad)"/>
    <text x="170" y="{y}" font-family="{FONT}" font-size="40" font-weight="bold" fill="{TXT}">{title}</text>
    <text x="170" y="{y+44}" font-family="{FONT}" font-size="27" fill="{DIM}">{sub}</text>'''

ig3 = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
{DEFS}
<rect width="1080" height="1080" fill="url(#bg)"/>
<ellipse cx="200" cy="950" rx="500" ry="380" fill="url(#glow)"/>
<text x="96" y="150" font-family="{FONT}" font-size="24" letter-spacing="3" fill="{BRAND2}">WHAT WE BUILT</text>
<text x="96" y="240" font-family="{FONT}" font-size="64" font-weight="bold" fill="{TXT}">Trust, by design.</text>
{row(380, "Shared context pool", "One growing history every agent reads &amp; appends to.")}
{row(540, "Un-gameable evaluation", "Runtime tokens + a scanner that audits green runs.")}
{row(700, "Production-safe automation", "Sandboxed tests; the public web ports stay sacred.")}
{row(860, "Earned cache + periodic gate", "Reuse only proven work; recurring runs ask first.")}
</svg>'''

# ---------- LinkedIn banner (1200x627) ----------
li = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="627" viewBox="0 0 1200 627">
{DEFS}
<rect width="1200" height="627" fill="url(#bg)"/>
<ellipse cx="1050" cy="120" rx="420" ry="320" fill="url(#glow)"/>
{mark(70, 80, 26)}
<text x="116" y="90" font-family="{FONT}" font-size="26" font-weight="bold" fill="{TXT}">Odin-Orchestrator</text>
<text x="64" y="250" font-family="{FONT}" font-size="58" font-weight="bold" fill="{TXT}">Trustworthy AI agents for</text>
<text x="64" y="320" font-family="{FONT}" font-size="58" font-weight="bold" fill="url(#brandgrad)">real software work.</text>
<text x="64" y="400" font-family="{FONT}" font-size="28" fill="{DIM}">Shared-context orchestration &#183; un-gameable evaluation</text>
<text x="64" y="440" font-family="{FONT}" font-size="28" fill="{DIM}">&#183; production safety. The honest engineering story.</text>
<rect x="64" y="490" width="120" height="5" rx="2" fill="url(#brandgrad)"/>
<!-- node graphic -->
<g stroke="{BRAND}" stroke-width="2" fill="none" opacity="0.9">
  <circle cx="980" cy="430" r="24" fill="rgba(108,140,255,0.15)"/>
  <circle cx="1100" cy="360" r="18" fill="rgba(122,240,208,0.12)" stroke="{BRAND2}"/>
  <circle cx="1080" cy="500" r="18" fill="rgba(122,240,208,0.12)" stroke="{BRAND2}"/>
  <line x1="1000" y1="415" x2="1086" y2="368"/>
  <line x1="1000" y1="445" x2="1066" y2="490"/>
</g>
</svg>'''

render("ig_1_cover.png", ig1, 1080)
render("ig_2_idea.png", ig2, 1080)
render("ig_3_built.png", ig3, 1080)
render("linkedin_banner.png", li, 1200)
print("done")
