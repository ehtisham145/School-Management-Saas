# Browser Agent — design

_Status: **Phase 0 (prototype) and the Phase 1 backend are written**: agent loop, task API, Celery `browser` queue, WebSocket updates, cost and domain controls. No frontend, sandbox or hand-off yet; off by default (`BROWSER_AGENT_ENABLED=False`). Drafted 2026-11-28. Decision record: [ADR-0028](decisions/0028-browser-agent-for-individual-teachers.md)._

A teacher types a task in a chat ("find the Grade 7 science curriculum on this site and summarise unit 3", "fill this contact form with my details"). An AI agent opens a real browser **on our server**, does the task on a public website, asks before anything irreversible, and reports back with a result and an action log.

- **Who gets it first:** individual teachers only (the `TEACHER` of a `School.kind = individual` workspace, [ADR-0021](decisions/0021-individual-teacher-workspace-and-trial.md)). Schools later.
- **LLM:** OpenAI through `apps/integrations/ai/`, the same adapter boundary as lesson plans and tests ([ADR-0007](decisions/0007-integrations-behind-adapters.md), [ADR-0016](decisions/0016-interim-hosted-ai-api.md)). Swappable for Gemini or a Saudi/self-hosted model.
- **Hosting:** every server (API, Redis, workers, browsers, database) in Saudi Arabia. The LLM is outside the Kingdom, so the agent sends it the **minimum** page text, masked. We never claim "no data leaves Saudi Arabia".

Contents: [1 Flow](#1-flow) · [2 Architecture](#2-architecture) · [3 Trust boundaries](#3-trust-boundaries) · [4 Agent loop](#4-agent-loop) · [5 Data minimisation](#5-data-minimisation) · [6 Threat model](#6-threat-model) · [7 Reuse vs build](#7-reuse-vs-build) · [8 Capacity and cost](#8-capacity-and-cost) · [9 Phases](#9-phases) · [10 Pilot metrics](#10-pilot-metrics) · [11 Known limits](#11-known-limits) · [12 Configuration and operations](#12-configuration-and-operations) · [13 Open questions](#13-open-questions)

---

## 1. Flow

1. **Chat → API.** `POST /api/browser-agent/tasks/` with the task text and an optional start URL. The backend checks: signed in, individual-teacher workspace, consent accepted, feature on for the plan, allowance left, rate limit, global budget not hit, start domain allowed.
2. **Queue.** A `BrowserTask` row is saved (`queued`) and a Celery task goes to the `browser` queue (Redis broker on servers).
3. **Worker.** A controller process on a browser host takes it, asks the sandbox for a **fresh browser context** (no cookies, no storage), and starts the loop.
4. **Login / OTP / Nafath / CAPTCHA → hand-off.** The agent pauses (`needs_user`). The teacher sees the live browser in the chat and types the password or code there. During hand-off the LLM gets nothing, no snapshots are taken, and keystrokes are forwarded to the browser and never logged or stored. The teacher clicks "Done, continue".
5. **Loop.** Snapshot (numbered list of usable elements + visible text) → trim → mask → LLM picks one action → policy check → execute with Playwright → repeat until done or a limit.
6. **Risky action → confirmation.** Submit, pay, delete, send, upload, or anything the policy can't prove harmless: the agent pauses (`needs_confirmation`) and shows "I'm about to click **Send** on `example.com`. Allow?" Nothing happens without a yes.
7. **Result.** Summary + action log (step, action, domain, time) shown in the chat.
8. **Cleanup.** Context closed, cookies/storage/downloads deleted, the slot goes back to the pool. Runs in a `finally`, and a sweeper kills anything older than the hard time limit.

Task states: `queued → running ⇄ needs_user ⇄ needs_confirmation → done | failed | cancelled | limit_reached`.

## 2. Architecture

```
 Teacher's browser (Next.js /teacher/agent)
   │  HTTPS (chat, task API)          WSS /ws/browser-agent/<task>/ (status, live view frames, input)
   ▼
┌─────────────────────────── App VM (OCI Riyadh) ───────────────────────────┐
│ Caddy → Django ASGI (DRF + Channels)                                      │
│   apps/browser_agent: models, services, selectors, API, consumer          │
│ PostgreSQL · Redis (broker, channel layer, caches)                        │
└──────────────┬────────────────────────────────────────────────────────────┘
               │ private network (Redis + Postgres only)
┌──────────────▼──────────── Browser VM(s) (OCI Riyadh) ────────────────────┐
│  agent-controller  (Celery worker, queue "browser", N slots)              │
│    • agent loop, masking, policy gate, cost meter                         │
│    • holds the OpenAI key; talks to OpenAI over HTTPS ──────────────► OpenAI (outside KSA)
│    • drives Chromium over CDP (Playwright connect)                        │
│         │ internal-only docker network "cdp"                              │
│  browser-sandbox  (Chromium, non-root, seccomp, read-only FS,             │
│                    CPU/RAM caps, no route except the proxy)               │
│         │ internal-only docker network "egress"                           │
│  egress-proxy  (Smokescreen: SSRF + domain policy, resolves DNS itself)   │
└─────────┼─────────────────────────────────────────────────────────────────┘
          ▼
     Public internet (websites)
```

Why split controller and browser: the browser renders hostile pages, so it gets **no** route to Redis, Postgres, the OpenAI key or our VMs. The controller has those but never renders a page.

**Live view:** CDP `Page.startScreencast` sends JPEG frames from the controller to the teacher through Channels (group `browser_task_<id>`); clicks and keys come back the same way as `Input.dispatch*`. No Xvfb or VNC server is needed, so it is lighter than noVNC. Frames are sent and dropped, never stored.

**New backend app** `apps/browser_agent/` (normal layout, [architecture §10](architecture.md#10-code-organization)):

| Model (all `TenantModel`) | Holds |
|---|---|
| `BrowserTask` | goal text, start URL, status, step/token/cost counters, model used, failure reason, timestamps |
| `BrowserStep` | task, n, action kind, target domain, policy verdict, tokens, cost, duration — **no page content, no typed values** |
| `ConfirmationRequest` | task, step, action summary, domain, answer (allow/deny/expired), answered_at |
| `AgentConsent` | user, version of the notice accepted, accepted_at |
| `ReplayRecipe` | domain, goal fingerprint, successful action list (selectors only, placeholders not values), success count, expires_at |

Platform-owned (no school): `DomainRule` (pattern, allow/block, reason), `AgentBudget` (month, cap, spent, kill switch).

Vendor code stays in adapters: `apps/integrations/ai/agent_provider.py` (LLM, OpenAI first) and `apps/integrations/browser/` (Playwright/CDP, so a hosted browser service could replace it).

## 3. Trust boundaries

| # | Boundary | Untrusted side | Control |
|---|---|---|---|
| B1 | Teacher ↔ API | the request | session auth, CSRF, workspace check, throttles, allowance |
| B2 | Web page ↔ browser | **every website** | sandboxed Chromium, no internal route, egress proxy |
| B3 | Page content ↔ LLM prompt | page text (prompt injection) | delimited "untrusted data" block, masking, trimming |
| B4 | LLM output ↔ action executor | the model's chosen action | strict JSON schema, policy gate, confirmation, limits |
| B5 | Our servers ↔ OpenAI | data leaving KSA | minimum masked text, no secrets, consent + notice |
| B6 | Hand-off input ↔ storage/logs | passwords, OTPs | forwarded only, never logged, LLM paused |

## 4. Agent loop

```
while not done and within limits:
    snap  = snapshot(page)                         # element refs + visible text, not HTML
    snap  = trim(snap)                             # drop nav/footer/ads, cap ~3k tokens
    snap, vault = mask(snap)                       # PII → {EMAIL_1}; values kept locally
    act   = llm.next_action(goal, history_summary, snap)   # cheap model first
    check = policy.check(act, page.url, goal)      # domain, kind, risk, deviation
    if check.needs_confirmation: pause, ask teacher
    if check.blocked: tell LLM "blocked: <reason>", count a strike
    run(act with vault.unmask(args))               # real values only here, on our server
```

- **Actions** (closed list, JSON schema): `goto`, `click(ref)`, `type(ref, text)`, `select(ref, option)`, `scroll`, `back`, `wait`, `extract(note)`, `ask_user(question)`, `request_login`, `done(answer)`. `ref` points at an element id from the snapshot, not a free CSS selector.
- **Model routing:** `gpt-4o-mini`-class model by default. Escalate one step to a stronger model when the same action fails twice, the page doesn't change after 2 steps, or the model returns low confidence. Model names live in settings.
- **Screenshots:** only when the text snapshot has no usable elements (canvas, image-only page). Password and input regions are blacked out before sending. Off by default per task; counts double against the token cap.
- **Hard limits** (settings, per plan): 30 steps, 10 minutes, 120k input tokens, 5 pages, 3 policy strikes, $0.20 per task, and the monthly budget. All are checked before every AI call. Hitting one ends the task as `limit_reached` with what was found so far.
- **History:** the last 3 steps in full, older steps as one-line summaries.
- **Replay:** when a task on a domain succeeds, its action sequence is saved as a `ReplayRecipe` (selectors + placeholders). The same kind of task on the same domain tries the recipe first with no LLM call, and falls back to the LLM at the first mismatch. Recipes are per workspace, expire after 30 days, and are never shared between teachers.
- **Research cache:** `extract` results per normalised URL are cached for 1 hour per workspace.

## 5. Data minimisation

Before every LLM call:
1. **Visible elements and text only**, never full HTML (`snapshot.py`). Text a person can't see is left out, element by element and for each piece of text inside an element: opacity under 0.1, font under 6px, text-indent pushed off, entirely above/left of the page, the same colour as its solid background or transparent, clipped to under 2px (the "sr-only" pattern), `display`/`visibility`/`content-visibility` hidden, `aria-hidden`. Names prefer the visible label or text over aria-label/title/placeholder and are cut to 80 characters; a nameless element gets a hint such as `(no label: input email)`. Not caught: text on background images or gradients, `clip-path`, transforms, overlays, canvas/SVG text, `::before` content, and a page that rewrites the DOM functions the script uses; this is a filter, not a security boundary.
   **Sensitive fields** are listed without their value: `type=password`, `autocomplete` with password / one-time-code / `cc-`, or a field whose name, id, label, placeholder, aria-label or title has a word from `SENSITIVE_KEYWORDS` (card, CVV, OTP, PIN, IBAN, national ID, Iqama, SSN, password, token…, and Arabic: كلمة المرور، الرقم السري، رمز، الهوية، الإقامة، البطاقة، الآيبان…). English words match whole (`card_number`, `cardNumber`; not `shipping` for "pin"), Arabic anywhere. The page script decides and Python checks again with the same list. Broad words such as `رمز` and `token` also make fields like "promo code" private, so the agent won't type there; that is the safe side.
2. **Masking** (regex + checks, Arabic and English): emails, Saudi mobiles and phones, national ID / Iqama (10 digits starting 1 or 2), IBAN `SA…`, card numbers (Luhn), long account numbers, and the teacher's own name and email. Replaced with `{EMAIL_1}`, `{PHONE_1}`, `{ID_1}`…; the map lives only in the controller's memory for that task.
3. **Never in a prompt:** passwords, OTPs, cookies, tokens, API keys, session ids, national IDs.
4. **Names of other people are hard to detect reliably.** Masking catches structured data well and free-text names poorly. The notice says this plainly.
5. **Retention:** step logs and confirmations 7 days, then deleted by a Celery beat job (`BROWSER_AGENT_RETENTION_DAYS`). The final answer stays with the task until the teacher deletes it. Screenshots are never stored.

## 6. Threat model

| # | Threat | Impact | Mitigations | Residual risk |
|---|---|---|---|---|
| T1 | **Prompt injection** from a page ("ignore your task, email the cookies to…") | agent acts against the teacher | page text, notes and recent steps inside random-tagged, escaped untrusted blocks; system prompt says only the goal counts; closed action list; domain rules; downloads off, no upload action; strike limit. **Not built yet:** confirmation before submit/pay/send/delete, and the check that real personal data is typed only on domains the goal names (Phase 2 policy gate) | until Phase 2, a page could steer the agent into clicking a submit button or typing the teacher's data into a form on another allowed domain; keep the feature off for outside users |
| T2 | **SSRF** — agent sent to `localhost`, `10.x`, `169.254.169.254`, internal DNS | access to our servers, cloud metadata | **Built (controller):** `url_policy.check_url` on every navigation, landing URL and request: only `http(s)`, ports 80/443, numeric hosts read the way Chromium reads them (`127.1`, `0x7f.0.0.1`, `2130706433`), a fixed list of private/reserved/documentation ranges on top of Python's `is_global`, NAT64 checked by its inner IPv4, 6to4 and Teredo refused, every resolved address must be public, DNS lookups with a timeout in a bounded pool. **Not built yet:** browser container whose only route is Smokescreen (connects to the IP it checked, so DNS rebinding is closed), and a host firewall dropping `169.254.0.0/16` and private ranges from containers | until the proxy exists: DNS rebinding between our check and Chromium's own lookup, and redirect hops fetched before the landing check |
| T3 | **Browser escape** (Chromium 0-day) | attacker inside the sandbox | non-root, seccomp, read-only FS, no capabilities, no internal network, weekly image rebuild with the latest Playwright/Chromium | a full escape + kernel bug would reach the browser VM, which holds no secrets |
| T4 | **Credential capture** | passwords/OTPs leak | hand-off only; LLM paused; no snapshots; input events not logged; password fields stripped from snapshots | the screencast passes through our server in memory; a compromised controller could read it |
| T5 | **Cross-teacher leak** | one teacher sees another's session | fresh context per task, destroyed after; `TenantModel` + selectors + cross-tenant tests; channel group checks membership | — |
| T6 | **Abuse** (spam forms, scraping, attacking sites) | IP blocked, legal exposure | allowances, rate limits, domain blocklist, confirmation on submit/send, audit log, ToS, Super Admin can suspend | determined abuse within limits |
| T7 | **Cost runaway** | large OpenAI bill | per-step token cap, per-task ceiling, per-user daily cap, monthly global kill switch, OpenAI dashboard hard limit | — |
| T8 | **PII to OpenAI** | PDPL exposure | masking, trimming, consent + notice, no screenshots by default | free-text names may pass (§5) |
| T9 | **Malicious downloads/uploads** | malware on our hosts | downloads **off** in v1; uploads off in v1; later: type/size allow-list + ClamAV | — |
| T10 | **Secrets in logs** | key leak | structlog filter; only domain (not full URL with query) logged; key only in controller env | — |

Blocked by default in v1: banks and payment providers, checkout/payment pages (detected by URL and by card fields), government identity portals (Nafath, Absher, IAM), webmail send actions, social media posting. List is data (`DomainRule`), editable by the Super Admin.

## 7. Reuse vs build

| Tool | What it is | Verdict |
|---|---|---|
| **Playwright (Python)** | browser automation | **Use.** Same language as the backend; runs our small page script for the element list; arm64 Linux supported |
| **Browser Use** (Python, MIT) | full agent loop on Playwright | **Borrow ideas, don't depend.** Its loop owns prompts, DOM extraction and screenshots; masking, the policy gate, confirmations, cost routing and replay would all be patches inside someone else's loop. Revisit if our loop is weak in the pilot |
| **Playwright MCP** (Node) | accessibility-snapshot tools over MCP | **Borrow the snapshot + element-ref idea.** A Node service adds a second runtime for no gain here |
| **Steel** (self-hosted browser API) | session pool, live view, proxies | **Not now.** Another service to run; at pilot scale a pool of contexts is enough. Keep the `integrations/browser` adapter so it can be swapped in |
| **Smokescreen** (Stripe, Go, MIT) | egress proxy with SSRF/IP rules | **Use** as the browser's only way out |
| **noVNC** | VNC in the browser | **Not needed.** CDP screencast does the hand-off with no X server |

## 8. Capacity and cost

**All numbers are estimates to check in the pilot.** Prices are list prices known at writing; check the OpenAI and OCI price pages before budgeting.

### Assumptions (settings, change freely)

| Input | Value |
|---|---|
| Peak concurrency | 5–10% of registered teachers (`BROWSER_AGENT_PEAK_RATIO`). For a teaching tool used in bursts this is likely **high**; the pilot measures the real number |
| Daily active teachers using the agent | 30% |
| Tasks per active teacher per day | 2 → **0.6 tasks per registered teacher per day**, ~18 per month |
| Steps per task | 15 (12 cheap + 3 escalated) |
| Input tokens per step | ~3,000 (snapshot ~2,200 + goal/history ~800); output ~150 |
| Browser time per task | ~3 minutes including LLM waits |
| RAM per session | ~300–500 MB (images, fonts, media blocked) |
| CPU per session | ~0.25–0.5 core average |

### LLM cost per task (OpenAI)

| Model mix | Price used (per 1M tokens in / out) | Cost per task |
|---|---|---|
| 15 steps cheap only (`gpt-4o-mini`) | $0.15 / $0.60 | ~$0.008 |
| 12 cheap + 3 strong (`gpt-4o`) | strong: $2.50 / $10.00 | ~$0.035 |
| With prompt caching on the fixed prefix | cached input billed lower | ~20–40% less |

### Monthly estimate

| Registered teachers | Tasks / month | LLM / month | Peak sessions (5–10%) | Browser hosts (OCI A1, paid) | Total / month |
|---|---|---|---|---|---|
| 100 | ~1,800 | $15–65 | 5–10 | 1 VM, 2–4 OCPU / 12 GB ≈ $30–45 | **~$45–110** |
| 500 | ~9,000 | $75–315 | 25–50 | 8–24 OCPU / ~24 GB ≈ $85–200 | **~$160–515** |
| 1,000 | ~18,000 | $150–630 | 50–100 | 25–50 OCPU / ~48 GB ≈ $250–450 | **~$400–1,100** |

Browser hosts are sized as sessions × (0.25–0.5 core, 0.5 GB), so the low end of each range assumes the light CPU figure.

OCI A1 price used: ~$0.01 per OCPU-hour and ~$0.0015 per GB-hour. The app VM, database and Redis are not in this table; they stay on the existing plan ([tech-stack.md](tech-stack.md)).

**What caps the bill:** plan allowances (for example trial 3 tasks, Teacher 20/month, Teacher Pro 60/month — **TBC with the client**) put a hard upper bound on tasks, so the real total is usually below the table. The global kill switch (`BROWSER_AGENT_MONTHLY_BUDGET_USD`) stops new tasks when the month's spend reaches the cap.

**Scaling:** browser hosts scale with queue depth (start a VM when the `browser` queue waits over 30 seconds for 5 minutes; stop one after 15 minutes idle). Kubernetes is **not** justified below roughly 10 browser hosts; Docker Compose + a small autoscale script is enough.

## 9. Phases

Each phase is small, ends with a demo and its tests, and gets its own branch. Nothing goes to real teachers before production runs in Saudi Arabia ([ADR-0021](decisions/0021-individual-teacher-workspace-and-trial.md)).

| Phase | Goal | Branch |
|---|---|---|
| **0 — Prototype** | The loop works locally on 2–3 public sites | `feature/browser-agent-prototype` |
| **1 — Core** | A teacher can run a task from the chat | `feature/browser-agent-core` |
| **2 — Safety** | Safe enough for outside users | `feature/browser-agent-safety` |
| **3 — Pilot** | 20–50 real teachers, measured | `feature/browser-agent-pilot` |
| **4 — Scale** | 1,000 teachers | `feature/browser-agent-scale` |

### Phase 0 — Prototype (local, dev only)

No UI, no Celery, no sandbox. Proves the loop, masking and URL checks.

**Backend app `apps/browser_agent/`**

| File | What it does |
|---|---|
| `models.py` | `BrowserTask` (goal, start URL, status, step/token/cost counters, failure reason) and `BrowserStep` (n, action kind, domain, verdict, tokens, duration). Both `TenantModel` |
| `url_policy.py` | `check_url(url)`: only `http`/`https`; resolves DNS and refuses loopback, `10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `100.64/10`, IPv6 loopback/ULA/link-local, and single-label internal names |
| `masking.py` | `mask(text) → (masked, vault)` and `vault.unmask(args)`: emails, Saudi mobiles/phones, national ID/Iqama, `SA` IBAN, card numbers (Luhn), long account numbers |
| `snapshot.py` | a page script tags each usable element with `data-agent-ref="eN"` and returns the list plus visible text; password/one-time-code/card values removed, hidden inputs left out, nav/footer trimmed, character cap. Chosen over `aria_snapshot()` because actions need stable refs and we control exactly which values leave the page |
| `agent.py` | the loop: snapshot → mask → LLM → URL check → execute → record step; limits of 30 steps, 10 minutes, token cap, 5 pages |
| `actions.py` | closed action list (`goto`, `click`, `type`, `select`, `scroll`, `back`, `wait`, `extract`, `done`) and its JSON schema |
| `services.py` / `selectors.py` | `start_task(school, user, goal, start_url)`, `record_step(...)`; selectors take `school` first |
| `management/commands/run_browser_task.py` | `python manage.py run_browser_task --workspace <id> "<task>" [--url <start>]` |

**Adapters**
- `apps/integrations/ai/agent_provider.py`: `next_action(goal, history, snapshot) → Action`, OpenAI with a strict JSON schema; model name from settings.
- `apps/integrations/browser/playwright_browser.py`: launch Chromium, a fresh context per task, block images/fonts/media/known trackers, check every request with `url_policy`, close the context in `finally`.

**Settings / env:** `BROWSER_AGENT_ENABLED` (off), `BROWSER_AGENT_MODEL`, `BROWSER_AGENT_MAX_STEPS`, `BROWSER_AGENT_MAX_SECONDS`, `BROWSER_AGENT_MAX_INPUT_TOKENS`, `BROWSER_AGENT_MAX_PAGES`. Added to `backend/.env.example` and [development.md](development.md).

**Tests (pytest)**
- `url_policy`: every blocked range, IPv6, redirects to a private address, non-http schemes, DNS names resolving to private IPs.
- `masking`: Arabic and English samples, round trip mask → unmask, nothing real left in the masked text.
- `snapshot`: password and OTP values never appear.
- `agent`: with a fake LLM and a fake browser — stops at each limit, records steps, refuses a blocked URL, never sends unmasked values to the provider.
- models: cross-tenant selector test.

**Commands the developer runs**
```
pip install -r requirements/dev.txt
playwright install chromium
ruff check . && pytest apps/browser_agent
python manage.py run_browser_task --workspace <id> "Find the opening hours on https://example.com"
```

**Done when:** the command finishes a simple research task on 2–3 public sites, prints the answer and the step log, and all tests pass.

### Phase 1 — Core

- `POST /api/browser-agent/tasks/`, `GET /tasks/`, `GET /tasks/{id}/`, `POST /tasks/{id}/cancel/`; only the `TEACHER` of an individual workspace, behind `WorkspaceAccess` and `BROWSER_AGENT_ENABLED`.
- Celery task on a new `browser` queue; local dev runs the loop in a background thread instead (Redis-free, [ADR-0009](decisions/0009-local-development-fully-native.md)).
- WebSocket `/ws/browser-agent/<task>/` for status and steps (Channels, group `browser_task_<id>`).
- Frontend `/teacher/agent`: chat box, task status, step list, final answer, cancel. Text in `messages/ar.json` and `en.json`, logical CSS only, design tokens only.
- Allowance per plan (counted like `AIGeneration`), `browser_agent` throttle, one running task per teacher.
- Tests: cross-tenant (other workspace → 404), role tests (school roles and other users denied), allowance, throttle, cancel.
- Docs: architecture data model and endpoints, security checklist items ticked.

**Done when:** a teacher starts a task in the app, watches its steps live and gets the answer.

### Phase 2 — Safety

- Browser VM in OCI Riyadh: `agent-controller`, `browser-sandbox` (non-root, seccomp, read-only FS, CPU/RAM caps) and `egress-proxy` (Smokescreen) in Docker Compose; the browser's only route is the proxy.
- Policy gate: risky actions (submit, pay, delete, send, upload) → `ConfirmationRequest`, the teacher allows or denies in the chat; strike limit for blocked actions.
- Login hand-off: `request_login` → CDP screencast to the chat, the teacher's clicks and keys forwarded, LLM paused, nothing logged.
- `DomainRule` with default blocks (banks, payments, government identity portals), editable by the Super Admin.
- Audit log per action (user, workspace, kind, domain, time); 7-day retention job; screenshots never stored.
- `AgentConsent`, consent screen, privacy notice and Terms of Service text.
- Prompt-injection test pages and SSRF tests run against the proxy on staging.

**Done when:** the [security.md §9](security.md#9-ai-browser-agent-adr-0028) checklist is green on staging.

### Phase 3 — Pilot (20–50 teachers)

- `AgentBudget` with a monthly cap and kill switch; per-task cost ceiling; per-teacher daily cap.
- Model routing: cheap model by default, escalate on repeated failure or no progress.
- Prompt caching on the fixed prompt prefix.
- Cost per task, teacher and model; pilot metrics page for the Super Admin (§10); suspend a teacher's access.
- "Was this useful?" on every result.

**Done when:** the pilot runs for 2–4 weeks and §10's numbers replace the estimates in §8.

### Phase 4 — Scale (1,000 teachers)

- `ReplayRecipe`: replay a successful action sequence on the same domain without the LLM, fall back at the first mismatch.
- Research cache per URL (1 hour, per workspace).
- Autoscale browser VMs from the `browser` queue wait time; scale down when idle.
- Load test at the measured peak concurrency; weekly rebuild of the browser image with the latest Playwright/Chromium.
- Decide on Steel or Kubernetes only if the pilot numbers call for it.

**Done when:** measured peak load runs within limits and the cost per task matches the budget.

## 10. Pilot metrics

Stored per task in `BrowserTask`/`BrowserStep`, shown to the Super Admin:

- success rate (teacher marks the result useful / not useful), and `done` vs `failed` vs `limit_reached`
- steps per task, LLM calls per task, % of steps escalated
- cost per task, per teacher, per model; month-to-date vs budget
- time to first action, total task time, time waiting in queue
- failure reasons: blocked domain, site blocked our IP, CAPTCHA abandoned, limit, LLM error, policy strikes
- confirmation rate (asked / allowed / denied / expired) and hand-off rate
- peak concurrent sessions (to replace the 5–10% guess)

## 11. Known limits

- **CAPTCHA, OTP, Nafath:** always handed to the teacher. Never solved or bypassed.
- **Data-center IPs:** some sites block cloud IPs. The agent reports "this site blocked our server" and stops. No residential proxies or evasion.
- **Sites that forbid automation** (robots meta / ToS we know of): the agent warns and does not try to get around it. Listed in `DomainRule`.
- **No guarantee of success:** sites change, and the agent can misunderstand a page. Every answer is labelled as AI-produced and should be checked.
- **Not "fully secure":** the design limits damage (sandbox, no internal route, confirmations). It depends on the proxy rules, patching Chromium weekly, and keeping the policy list current.

## 12. Configuration and operations

### Environment variables

All in `backend/.env` (see `.env.example`). Defaults are safe; the feature is off.

| Variable | Default | What it does |
|---|---|---|
| `BROWSER_AGENT_ENABLED` | `False` | Master switch. Off: every endpoint answers 403 `browser_agent_disabled` |
| `BROWSER_AGENT_MODEL` | `gpt-4o-mini` | OpenAI model. Must be a key of `BROWSER_AGENT_PRICES` in `settings/base.py`, or production won't start |
| `BROWSER_AGENT_MAX_STEPS` | `30` | AI steps per task |
| `BROWSER_AGENT_MAX_SECONDS` | `600` | Agent time limit. Celery soft limit = this, hard limit = this + 30 |
| `BROWSER_AGENT_MAX_INPUT_TOKENS` | `120000` | Input tokens per task (a full page is ~3,500–4,500 tokens a step) |
| `BROWSER_AGENT_MAX_PAGES` | `5` | Pages opened per task |
| `BROWSER_AGENT_MAX_STRIKES` | `3` | Blocked or invalid actions before the task fails |
| `BROWSER_AGENT_MAX_PAGE_CHARS` | `12000` | Page text sent per step |
| `BROWSER_AGENT_MAX_OUTPUT_TOKENS` | `800` | Reply tokens per AI call (Arabic answers need room; only tokens actually written are billed). A cut-off reply is tried once more with twice this, if the time left allows |
| `BROWSER_AGENT_MAX_COST_USD_PER_TASK` | `0.20` | Task stops (`limit_reached` / `max_cost`) once its cost reaches this |
| `BROWSER_AGENT_MONTHLY_BUDGET_USD` | `100` | Platform kill switch for the calendar month (Riyadh time): new tasks get 503 `browser_agent_budget_reached`, running ones stop with `monthly_budget` |
| `BROWSER_AGENT_MAX_RUNNING_PER_USER` | `1` | Active (queued, running, awaiting) tasks per teacher; more answers 409 `task_already_running` |
| `BROWSER_AGENT_MAX_RUNNING_TOTAL` | `10` | Active tasks on the platform; more answers 503 `browser_agent_busy`. Keep it ≤ browser worker concurrency × hosts |
| `BROWSER_AGENT_THROTTLE_RATE` | `10/hour` | Starting tasks, per user (DRF scope `browser_agent`); more answers 429 |
| `BROWSER_AGENT_WS_IDLE_SECONDS` | `300` | Live socket closed after this long without traffic |
| `BROWSER_AGENT_BLOCKED_DOMAINS` | banks, payment providers, government identity portals (list in `settings/base.py`) | Comma-separated; covers every subdomain, case-insensitive. Setting it replaces the whole list |
| `BROWSER_AGENT_ALLOWED_DOMAINS` | empty | Empty = every public domain except blocked. Set = only these (and their subdomains) |
| `BROWSER_AGENT_ALLOWED_PORTS` | `80,443` | Ports the agent may open; a URL without a port uses its scheme's default. Anything else is refused (`port`), also on numeric addresses. 8080/8443 are left out on purpose (mostly admin panels, dev servers, proxies) |
| `BROWSER_AGENT_DNS_TIMEOUT_SECONDS` | `3` | A slower lookup refuses the URL (`unresolvable`). Lookups run in a pool of 8 threads per process; when all 8 are busy with slow lookups the URL is refused at once (`dns_busy`) |
| `SECURE_HSTS_SECONDS` | `3600` | Production HSTS, read by Django and the staging Caddyfile. Raise to `31536000` once HTTPS is proven |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` | Production |
| `NUM_PROXIES` | `1` | Production. Proxies in front of Django for DRF throttling |
| `AXES_FAILURE_LIMIT` | `15` | Failed sign-ins per username + IP before a 1-hour lock ([ADR-0018](decisions/0018-remove-two-factor-authentication.md)). `8` is stricter |

### AI calls

- **Prompt boundary.** Only the GOAL is an instruction. The page, and the agent's own recent steps and notes (written from pages), go inside two blocks named with a fresh random tag per call (`untrusted_page_<16 hex>`); the system prompt names those tags. Every `<` and `>` in that text is escaped, so no spelling of a closing tag (case, spaces, the real tag) can end a block early. This is still only a request to the model: the code-side guards are the domain rules, the URL checks and the closed action list.
- **Unusable replies.** Bad JSON, a non-object, an empty reply or a cut-off reply counts as a strike (`ai_error` step) and the agent tries the next step; three strikes fail the task with that reason. A cut-off reply is first retried once with twice `BROWSER_AGENT_MAX_OUTPUT_TOKENS`. The tokens of every call that got an answer are charged to the task, the cost ceiling and the monthly budget, even when the reply was unusable.
- **Fail at once:** `not_configured` (no key), `model_not_priced` (a model, such as an escalation model, missing from `BROWSER_AGENT_PRICES`; refused before the call), `provider_error` (timeout or API error).
- **Time.** An AI call starts only with at least 100 seconds left (45 s timeout × 2 attempts + 10 s), and each attempt's timeout is cut to fit the time left, so a task ends as `max_seconds` rather than at Celery's limit. A page action after the call (navigation can take up to 30 s) can still run past; Celery's soft limit then ends it as `time_limit`.
- **Client.** One OpenAI client per process, made on first use; `reset_client()` for tests and key rotation.

Failure reasons the teacher can see: `max_steps`, `max_seconds`, `max_tokens`, `max_cost`, `monthly_budget`, `max_pages`, `too_many_strikes`, `bad_json`, `not_an_object`, `empty_reply`, `reply_cut_off`, `provider_error`, `not_configured`, `model_not_priced`, `start_url_<reason>`, `start_page_failed`, `browser_<reason>`, `time_limit`, `worker_lost`, `not_started`, `cancelled_by_user`, `internal_error`. The chat page maps each to a message in Arabic and English.

### Start-up guards

Production (`config/settings/prod.py`, using `config/settings/guards.py`) refuses to start when: the model has no price; the agent is on without `OPENAI_API_KEY`; or the agent is on while Celery runs tasks inline (eager). `REDIS_URL` and `EMAIL_HOST` were already required there. Locally the same browser agent rules run as Django system checks (`browser_agent.E001`/`E002`), since gunicorn, uvicorn and Celery never run system checks.

### Lesson Lab Agent in the teacher app

- Page `/teacher/agent` (`features/teacher/components/agent-panel.tsx`), in the side menu and as a card on Home, shown only while `features.agent` (= `BROWSER_AGENT_ENABLED`) is true in `GET /api/classroom/workspace/`.
- **Allowance** (`entitlements.Limits.agent_tasks`): trial 5 for the whole trial, Teacher 20 and Teacher Pro 60 each calendar month. Counted by `selectors.count_tasks_toward_allowance`: failures on our side (`internal_error`, `worker_lost`, `not_started`, `provider_error`, `not_configured`, `model_not_priced`, `no_time_left`, `browser_*`) don't count. Checked inside the queue lock, so two quick clicks can't both use the last task; refused with 403 `agent_quota_reached`.
- **Consent:** the first visit shows the notice (masked page text goes to OpenAI outside the Kingdom, what is blocked, the teacher's responsibility, AI can be wrong). `POST /api/browser-agent/consent/ {version}` stores an `AgentConsent` for `services.CONSENT_VERSION`; changing that version asks every teacher again. No task without it (403 `consent_required`).
- **Live view of a task:** the WebSocket for instant steps, plus polling every 4 s as a fallback. Locally the Next.js dev server can't pass sockets on; set `NEXT_PUBLIC_WS_ORIGIN=ws://localhost:8000` in `frontend/.env.local` to use them, otherwise the page polls. Without Redis, Celery is eager, so "Start" waits until the task ends.

### API and live updates

| Endpoint | Notes |
|---|---|
| `POST /api/browser-agent/tasks/` `{goal, start_url?}` | 202 with the queued task. Throttled, budget- and cap-checked, needs a plan that covers today |
| `GET /api/browser-agent/tasks/` | The teacher's tasks, paginated |
| `GET /api/browser-agent/tasks/{id}/` | One task with its steps (action, domain, verdict, note — no page content). Tokens and cost are not shown to teachers |
| `POST /api/browser-agent/tasks/{id}/cancel/` | Ends an active task; a running one stops before its next AI call |
| `GET /api/browser-agent/status/` | `consent_version`, `consent_given`, `allowance {used, limit, left, period}`, `active_task` |
| `POST /api/browser-agent/consent/` `{version}` | Accepts the current notice (204); an older version is refused |
| `WS /ws/browser-agent/{id}/` | Status and steps as they happen. Refused (closed before accept) for anonymous users (4401), another user's or unknown task (4404) and other websites' Origin. Closes when the task ends (4000), after the idle time (4408), and a minute after the hard time limit at the latest |

Only the `TEACHER` of an individual workspace can use these; anything else is 403, and another workspace's task is 404.

### Why the browser task is never retried

`CELERY_TASK_ACKS_LATE=True` is global, so a worker that dies mid-task would normally run it again — and the agent may already have submitted a form. `run_browser_task_job` therefore sets `acks_late=False`, `reject_on_worker_lost=False`, `max_retries=0` and no autoretry, and starts only after an atomic `queued → running` update, so a second delivery does nothing. Any failure ends as `failed` with a reason the teacher sees (`internal_error`, `time_limit`, `worker_lost`, `not_started`…). A beat job (`fail_stale_tasks_task`, every 5 minutes) fails tasks a dead worker left running past the hard limit + 2 minutes, and tasks still queued after 30 minutes.

### Running the browser worker

The browser task has its own queue, so a slow site never holds up emails or subscription jobs. Run a **separate** worker for it, with low concurrency (each slot is one Chromium, ~300–500 MB):

```
celery -A config worker -Q browser --concurrency=2 --prefetch-multiplier=1 -n browser@%h --loglevel INFO
```

The existing worker keeps `-Q emails,ai,celery` and must not read `browser`. Beat must run for the stale-task sweep. The browser worker's image needs Chromium (`playwright install --with-deps chromium`); until the Phase 2 sandbox exists, run it only for internal testing.

### Server checklist (manual)

1. `.env`: leave `BROWSER_AGENT_ENABLED=False` until Phase 2 is done; set `OPENAI_API_KEY`, `REDIS_URL`, `CSRF_TRUSTED_ORIGINS`, `ALLOWED_HOSTS`, and review `BROWSER_AGENT_BLOCKED_DOMAINS`, `BROWSER_AGENT_MONTHLY_BUDGET_USD`, `BROWSER_AGENT_MAX_COST_USD_PER_TASK`.
2. Set a hard monthly limit in the OpenAI dashboard as well, as a second kill switch.
3. Caddy: `/ws/*` goes to the backend (done in `staging/caddy/Caddyfile`). The backend must publish **no** port: Caddy must be the only way in, or `NUM_PROXIES=1` and the axes IP setting let callers fake their address.
4. HSTS: start at `SECURE_HSTS_SECONDS=3600` (staging compose passes it to Caddy too); raise to `31536000` after a week without HTTPS problems.
5. Add a `browser` worker service (command above) once its image has Chromium; keep the main worker on `emails,ai,celery`; make sure beat runs.
6. After deploy: `python manage.py check --deploy`, and confirm an axes lockout for one IP doesn't lock out another.

## 13. Open questions

Tracked in [requirements.md §6](requirements.md#6-open-questions-for-the-client-tbc):
- Which tasks teachers really need (research, curriculum sites, forms?) — this decides the default allow/block list.
- Allowances per plan, and whether the trial gets the agent at all.
- Monthly budget cap for the pilot.
- Client sign-off that masked page text goes to OpenAI (same conversation [ADR-0016](decisions/0016-interim-hosted-ai-api.md) asks for).
- Browser VM size and whether OCI Riyadh A1 capacity is available for it.
