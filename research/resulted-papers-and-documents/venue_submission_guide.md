% Where to Publish This Paper — Venue Guide & Submission Playbook
% Prepared for: Mostafa Adawy (Odin Markets)
% Date: June 2026

# What kind of paper this is (read first)

This work is an **experience / systems report**: a working multi-agent
development system, an un-gameable evaluation methodology, and real incidents
(a production outage, a caught self-deceiving test). It is **not** a new model
or a benchmarked state-of-the-art result.

That matters for venue choice. The best fits are venues that **explicitly value
practical impact, real deployments, and lessons learned over novelty** — namely
*industry* and *software-engineering-in-practice* tracks, and practitioner
magazines. Pure-research tracks (which reward novelty and ablations) are a
harder sell *unless* you first add the quantitative study described in the
paper's Limitations section.

> **One-line strategy:** post to arXiv now (timestamp + shareable link), then
> submit to an industry/SE-in-practice track, and in parallel pitch a
> practitioner magazine. Use a workshop for fast early feedback if you want
> reviews before a main deadline.

---

# Recommendation tiers

## Tier 0 — Do this immediately: arXiv preprint
- **Why:** Free, no peer review, permanent timestamp that establishes priority,
  and a link you can cite/share everywhere. Costs nothing and forecloses
  nothing — most of the venues below explicitly allow a prior arXiv preprint.
- **Categories:** primary `cs.SE` (Software Engineering); cross-list `cs.MA`
  (Multiagent Systems) and `cs.AI`.
- **Recommendation:** ★★★★★ (do it this week).
- **Steps:** see "How to submit to arXiv" below.

## Tier 1 — Best peer-reviewed fit (industry / in-practice tracks)
These prize *impact and real experience over novelty*, and most are
**single-blind** (you do **not** anonymize), which suits a named system report.

| Venue (track) | Why it fits | Timing (verify!) | Recommendation |
|---|---|---|---|
| **ASE 2026 — Industry Showcase** | "Prioritize impact and realistic applications over novelty… success stories and experiences." Exactly this paper. Long papers 10+2 pp, single-blind, mandatory data-availability statement. Munich, Oct 12–16 2026. | Submission window typically spring/summer 2026 — **verify now**, may be near. | ★★★★★ |
| **ICSE 2027 — SEIP (Software Eng. in Practice)** | Premier practitioner track at the top SE conference; not double-anonymous. | **Abstracts ~Jun 23 2026, papers ~Jun 30 2026 — imminent.** If you can move fast this is the highest-prestige near-term shot. | ★★★★★ (if you can hit the date) |
| **FSE 2026 — Industry Papers** | Top-tier SE venue, dedicated industry track; ACM template, PDF. | Check the track page for the 2026 date. | ★★★★☆ |

## Tier 2 — Practitioner magazines (great for experience reports)
Lighter, editor-driven review; wide readership; fast-ish; very friendly to
"what we built and learned" narratives.

- **IEEE Software** — practitioners' articles & themed issues on AI-assisted
  software engineering. ★★★★☆
- **ACM Queue / Communications of the ACM (Practice)** — engineer-written,
  high-visibility practice articles. ★★★★☆

## Tier 3 — Workshops (fast feedback, lower bar, good first step)
Short papers, quick turnaround; ideal to get reviews and a citation while you
target a Tier-1 track.

- **LLM-Agent workshops at NeurIPS / ICML / ICLR** (recurring; titles vary, e.g.
  "LLM Agents", "Foundation Models for Decision Making", "Open-World Agents"). ★★★★☆
- **LLM4Code** (typically co-located with ICSE). ★★★★☆
- **MABS / multi-agent workshops at AAMAS** (AAMAS 2026 main track deadlines
  already passed — Dec 2025 — but workshops stayed open into Feb 2026; watch
  AAMAS 2027). ★★★☆☆

## Tier 4 — Journals (only after you add the quantitative study)
If you expand with the controlled cache-vs-no-cache numbers and a fuller
evaluation, these become strong:

- **EMSE — Empirical Software Engineering (Springer)** — experience + empirics. ★★★★☆
- **Automated Software Engineering journal (Springer)** — has open CFP collections. ★★★☆☆
- **ACM TOSEM / IEEE TSE** — highest prestige, highest bar; needs full study. ★★★☆☆

---

# Living deadline trackers (bookmark these)
Deadlines move every year — always confirm on the official track page, and use:

- **se-deadlines.github.io** — software-engineering venues (ICSE, FSE, ASE, …).
- **aideadlines.org** — AI/ML venues and workshops (NeurIPS, ICML, ICLR, AAMAS).

---

# Step-by-step: how to submit

## How to submit to arXiv (Tier 0)
1. Create/confirm an account at arxiv.org. New authors may need an
   **endorsement** for `cs.SE`/`cs.MA` (a one-time step; the site guides you).
2. Prepare the source: upload **the LaTeX `.tex` plus the generated `.pdf`**
   (arXiv prefers source). Our `odin_paper.tex` compiles cleanly with
   `pdflatex`.
3. Choose **primary `cs.SE`**, cross-list `cs.MA`, `cs.AI`.
4. Add title, abstract (paste from the paper), authors, and a license
   (CC BY 4.0 is a good default).
5. Submit → it appears after a short moderation hold. Share the resulting
   `arXiv:XXXX.XXXXX` link.

## How to submit to an SE industry / in-practice track (Tier 1)
1. **Pick the track** and open its `conf.researchr.org` page; read the Call for
   Papers for the exact **page limit, template, and blinding rule**.
2. **Template:** use the **ACM Primary Article Template** (these tracks use ACM
   format). *Our paper is currently in a generic two-column article style — you
   will need to port it into the ACM template before submitting.* (Easy: copy
   the sections into the ACM `acmart` skeleton.)
3. **Blinding:** ASE Industry Showcase, ICSE SEIP, and FSE Industry are
   **single-blind** — keep your name and "Odin" in the paper.
4. **Data-availability statement:** ASE requires one *after the Conclusion,
   within the page limit*, with a DOI-archived artifact (e.g., a Zenodo deposit
   of the evaluation scripts). Prepare this.
5. **Register the paper** on the track's HotCRP site (e.g.,
   `ase26-industry.hotcrp.com`), submit the **abstract first** if an abstract
   deadline precedes the paper deadline, then upload the **PDF**.
6. Wait for reviews; prepare a short rebuttal if the track offers one.

## How to pitch a practitioner magazine (Tier 2)
1. Read the magazine's author guidelines (length is shorter — ~3,000–5,000
   words, fewer equations, more narrative).
2. For IEEE Software, check current **themed-issue CFPs** (AI for SE appears
   regularly) or submit to the practitioners' department.
3. For ACM Queue, email the editors a **short pitch** (2–3 paragraphs) first;
   they commission/curate.
4. Trim the math, lead with the two incidents and the un-gameable-test idea —
   magazines reward a strong story.

## How to submit to a workshop (Tier 3)
1. Find a current LLM-agent workshop via **aideadlines.org**.
2. Most accept **4–8 page** short papers; many are **non-archival** (so you can
   still submit the full paper to a Tier-1 venue afterward — check the policy).
3. Submit via the workshop's OpenReview/HotCRP/EasyChair link.

---

# A concrete plan (suggested order)
1. **This week:** put `odin_paper.pdf` on **arXiv** (`cs.SE`). Get the link.
2. **Now:** decide on **ICSE 2027 SEIP** — its paper deadline (~Jun 30 2026) is
   the nearest high-prestige target; if reachable, port to the ACM template and
   submit. If not, target **ASE 2026 Industry Showcase** / **FSE 2026 Industry**.
3. **In parallel:** prepare a **Zenodo artifact** (the evaluation gate + cache
   scripts, secrets removed) and a one-line DOI for the data-availability
   statement.
4. **Strengthen for a journal later:** run the cache-vs-no-cache timing study,
   add the numbers, and extend to **EMSE**.
5. **Optional fast feedback:** drop a short version into an **LLM-agent
   workshop** to collect reviews while the main submission is in flight.

---

# Pre-submission checklist
- [ ] Camera-ready quantitative results filled in (timing study) — or clearly
      framed as an experience report if submitting before then.
- [ ] Correct **template** for the target venue (ACM `acmart` for SE tracks).
- [ ] **Page limit** respected (e.g., 10+2 for ASE Industry).
- [ ] **Blinding** rule applied correctly (single-blind for the Tier-1 tracks).
- [ ] **Data-availability statement** + DOI artifact (Zenodo).
- [ ] No secrets/credentials anywhere in paper or artifact.
- [ ] arXiv preprint posted and linked.
- [ ] Deadline re-confirmed on the official track page **today**.

---

*Note on dates:* venue deadlines change yearly and some windows above are close
or may have shifted. Every date here should be re-confirmed on the official
track page (links via se-deadlines.github.io / aideadlines.org) before you rely
on it.
