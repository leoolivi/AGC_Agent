# Product — Admin & Compliance Guardian (ACG)

## What It Is

ACG is an AI administrative assistant for Italian SMEs. It proactively monitors documents, deadlines, and business communications, analyzes incoming events, and presents pre-processed situations with actionable options.

## Core UX Paradigm: Agent Inbox

The primary interface is an **Agent Inbox** — the agent doesn't wait for questions. It analyzes events (document uploads, approaching deadlines, received emails) and produces actionable cards with specific verbs. Chat is an advanced feature, not the main entry point.

## Guiding Principle

**Reliability > Autonomy.** The system performs maximum work autonomously but always requires explicit human approval for any action with external effects.

## Domain Context

- Target users: Italian SME administrators and compliance officers
- Language: Italian (UI, documents, communications)
- Regulatory context: Italian fiscal/administrative compliance (scadenze fiscali, adempimenti, GDPR)
- Document types: invoices, contracts, fiscal communications, certificates, spreadsheets

## Key Capabilities

1. **Document Triage** — Automatic classification, extraction, and risk scoring of uploaded documents
2. **Deadline Monitoring** — Proactive tracking and alerting for fiscal/administrative deadlines
3. **Email Drafting** — AI-generated response drafts for business communications
4. **Daily Digest** — Morning briefing summarizing pending items, approaching deadlines, and recommended actions
5. **Workflow Execution** — Structured multi-step actions (e.g., file a document, send a notification) triggered from inbox cards

## Risk Model

Every agent action has a risk score (0–3):
- 0: Read-only, no side effects
- 1: Internal state change only (triage produces inbox items)
- 2: External effect with human approval (send email, file document)
- 3: Irreversible or high-impact (never auto-executed)
