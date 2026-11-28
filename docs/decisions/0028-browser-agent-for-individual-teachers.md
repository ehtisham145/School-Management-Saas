# ADR-0028: Server-side AI browser agent for individual teachers

- **Status:** Proposed (plan approved for docs; no code yet)
- **Date:** 2026-11-28
- **Design:** [browser-agent.md](../browser-agent.md)

## Context
The owner wants teachers to type a task in a chat and have an AI agent do it in a real browser on a public website, then report back. It must run on our servers in Saudi Arabia, use OpenAI (the key the project already has) behind a swappable adapter, never see passwords or OTPs, and keep cost per task low. The first users are individual teachers ([ADR-0021](0021-individual-teacher-workspace-and-trial.md)); schools come later.

## Decision
- **Inside the monolith, plus one new worker type.** A new Django app `apps/browser_agent/` owns tasks, steps, confirmations, consent and replay recipes. All of them are `TenantModel`s scoped to the teacher's workspace. Only the `TEACHER` of an individual workspace can use it at first, behind a feature flag and a plan entitlement.
- **Python + Celery, not Node/BullMQ.** Same language, queue and deploy as the rest of the backend. A dedicated `browser` queue is read only by an `agent-controller` worker on separate browser VM(s) in OCI Riyadh.
- **Playwright (Python) + Chromium**, server-side only. The controller drives Chromium over CDP; Chromium runs in its own sandboxed container (non-root, seccomp, read-only FS, CPU/RAM/time limits) whose only network route is an **egress proxy (Smokescreen)** that blocks private, loopback, link-local and metadata addresses and enforces the domain policy. The browser can't reach Redis, Postgres, the app VM or the OpenAI key.
- **Text first.** The agent reads a numbered list of the page's usable elements and its visible text (our own page script, not HTML), trims it, masks personal data into placeholders and sends only that to the LLM. Screenshots only when text fails, with input regions blacked out.
- **Own agent loop**, not Browser Use, so masking, the policy gate, confirmations, model routing, cost metering and replay sit in our code. Browser Use and Playwright MCP are used as references.
- **LLM through `apps/integrations/ai/agent_provider.py`**, OpenAI first (cheap model by default, a stronger one on escalation). Swapping to Gemini or a Saudi/self-hosted model is a new adapter.
- **Hand-off for login, OTP, Nafath and CAPTCHA** through a live view built on CDP screencast over Channels, not noVNC. The LLM is paused and input isn't logged during hand-off.
- **Human confirmation** before any submit, payment, delete, send or upload. Banks, payment pages and government identity portals are blocked by default.
- **Cost controls:** per-step token cap, per-task ceiling, plan allowances, per-user daily cap, global monthly kill switch, cost tracked per task, teacher and model.
- **Local dev** stays native and Redis-free ([ADR-0009](0009-local-development-fully-native.md)): the loop runs in a background thread of the dev server with local Playwright, and the sandbox and egress proxy exist only on servers. Anything needing them is verified on staging.

## Consequences
- ✅ One stack and one deploy pipeline; tenant isolation and tests work as for every other feature.
- ✅ The browser, which renders hostile pages, holds no secrets and has no internal route.
- ✅ Vendor swaps (LLM, hosted browser service) are adapter changes.
- ⚠️ **New monthly cost:** browser VM(s) and OpenAI usage, roughly $45–110/month at 100 teachers and $400–1,100 at 1,000 (estimates, [browser-agent.md §8](../browser-agent.md#8-capacity-and-cost)). Allowances and the kill switch cap it. Outside the original ~$20 budget; agree with the client.
- ⚠️ **Masked page text goes to OpenAI outside the Kingdom.** Same trade-off as [ADR-0016](0016-interim-hosted-ai-api.md), with more exposure because pages are not teacher-authored. Masking catches structured data well and free-text names poorly. Needs consent, a privacy notice and the client's sign-off.
- ⚠️ Production needs Redis, a channel layer across processes, and a second VM type, none of which exist locally.
- ⚠️ Some sites block data-center IPs or forbid automation; the agent reports and stops, it doesn't evade.
- ⚠️ We own the agent loop's quality. If the pilot shows it is weak, revisit Browser Use behind the same adapter.
- New libraries when built: `playwright` (Python) and the Smokescreen image; [tech-stack.md](../tech-stack.md) lists them as planned.
