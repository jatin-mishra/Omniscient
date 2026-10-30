# PRD: Enterprise Knowledge RAG Assistant

Oct 30, 2026 · @Jatin

## 1. Problem, goals, non-goals

We will build a permission-aware assistant that answers questions from all company documentation with citations, and can run approved actions on the user's behalf. Knowledge at an AI company changes weekly (model cards, eval reports, runbooks, API specs, architecture decision records) and is spread across 6+ tools. Engineers lose hours hunting, new hires ask the same questions repeatedly, and the obvious fix (one search box over everything) is dangerous without strict access control, because revenue, compensation and unreleased-model data sit next to the wiki.

**Goals**

1. Grounded answers: every factual claim cites a source the user can open; the system says "I don't know" rather than guess.
2. Zero permission leaks: the assistant never retrieves, quotes or summarizes anything the asking user could not open directly.
3. Answer-to-action: users can act on what they learn (file a ticket, check a deploy, run a runbook step) without leaving the conversation, with confirmation before any change.

**Non-goals (v1)**

- External, customer-facing support bot (v2, separate index of public docs only).
- Fine-tuning a model on internal documents; knowledge lives only in the retrieval index.
- Indexing books, datasets, model weights, videos or binaries.
- Autonomous high-risk actions (production deploys, deletions, external emails, spend).

## 2. Users

| Persona | Typical question | Default access | Can execute |
| --- | --- | --- | --- |
| Engineer / researcher | "What's the rollback runbook for the inference gateway?" | Public + Internal + own-team Confidential | Read + confirmed write actions |
| GTM / sales / support | "Does our API support batch with tool use? Link the doc." | Public + Internal | Read actions |
| Finance / leadership | "Q3 revenue by segment vs plan?" | Adds Restricted via named allowlist | Read actions |
| Intern | "How do I get access to the eval cluster?" | Public + Internal (excluding roadmap and pricing spaces) | Read only |
| Contractor / vendor | "What's the spec for the labeling API?" | Public + spaces explicitly shared with them | None |
| Admin / security | "Who queried board materials this week?" | Admin console, audit logs; no content bypass | Configure sources and policy |

## 3. Functional requirements

&#91;embedded content: System architecture · ingestion and query paths\]

The policy engine sits between identity and retrieval, so content a user can't access is never retrieved or sent to the model.

### 3.1 Sources and ingestion

- **Connectors (P0):** Confluence, Google Drive (Docs, Sheets, Slides, PDFs), Notion, GitHub (READMEs, /docs, ADRs, OpenAPI specs), Jira. **P1:** SharePoint, Slack public channels (12-month window), Linear. Private DMs are never indexed.
- **Freshness:** incremental sync via webhooks; edits searchable within 15 min; deletions and permission changes applied within 5 min.
- **Every chunk carries:** source URL + anchor, title, section path, owner, last-modified, version, source ACL, sensitivity label.
- **Chunking:** structure-aware (split on headings, never mid-table or mid-code-block), 400–800 tokens, \~10% overlap, parent section kept for context expansion.
- **Hygiene:** detect and drop secrets (API keys, tokens, passwords) before indexing; dedupe near-identical copies; mark docs older than 12 months unedited as "possibly stale".

### 3.2 Document size limits

We index what people actually read, not entire books. Over-limit files are partially indexed (table of contents + generated summary + first N units), flagged "partially indexed" in answers, and listed in an admin report, never silently dropped.

| Content type | Max indexed per file | Over the limit |
| --- | --- | --- |
| Text doc / wiki page | 50k tokens (\~100 pages) | TOC + summary + first 50k tokens |
| PDF | 150 pages or 50 MB | Same as above; scanned PDFs OCR'd |
| Slide deck | 100 slides | First 100 + summary |
| Spreadsheet | 10 sheets × 5,000 rows × 50 cols | Schema + summary in index; rows queried via SQL tool |
| Code repo | Docs, READMEs, ADRs, API specs; files ≤ 1 MB | Source code, vendored and generated files excluded |
| Image / diagram | 20 MB each, 50 per document | Skipped with a note |
| Excluded entirely | Books/ebooks, datasets, model weights, video, archives, binaries | Not indexed |

### 3.3 Tables, diagrams and images

- **Tables:** extracted as structured Markdown; header row repeated in every chunk of a large table; a table is never split from its caption. Numeric questions over spreadsheets go to a text-to-SQL tool over a structured store, not to embeddings.
- **Architecture diagrams:** diagram-as-code (Mermaid, PlantUML, draw.io XML) parsed directly; image diagrams get OCR + a vision-model description of components, connections and labels. The answer shows the original image with a link.
- **Charts and screenshots:** vision caption + OCR; extracted values marked "read from image" so users know to verify.

### 3.4 Retrieval and answering

- Hybrid retrieval (keyword + dense vectors) followed by a reranker; permission filter applied inside the query, before ranking, never as a post-filter.
- Query rewriting with a company glossary (team names, codenames, acronyms).
- Ranking boosts for owner-verified and recently edited docs; deprecated docs demoted and labeled.
- Citations on every claim, linking to the exact section, page or slide. When sources conflict, show both with dates and owners.
- Below a confidence threshold, the assistant abstains and names the doc owner or team channel to ask.
- Surfaces: Slack bot, web app, IDE/CLI plugin, internal API. Multi-turn follow-ups; feedback (thumbs + "this is wrong" routed to the doc owner).

### 3.5 Actions (execution)

Actions are tools exposed through a gateway (MCP), and always run with the user's own delegated credentials (OAuth), never a shared super-account.

| Tier | Examples | Guardrail | Phase |
| --- | --- | --- | --- |
| Read | Jira ticket status, deploy status, dashboard metric, SQL on analytics read-replica | Runs automatically within the user's permissions | P1 |
| Reversible write | Create Jira ticket, draft a PR, schedule a meeting, trigger a staging eval job, run a runbook step | Preview + explicit user confirmation | P2 |
| High-risk | Production deploy, delete data, external email, compute spend above a threshold | Not supported in v1; v2 needs a second approver | v2 |

Instructions found inside retrieved documents never trigger actions: only the user's own request can (prompt-injection defense). Runbook execution shows each step and waits for confirmation before the next.

## 4. Permissions and security

The assistant can never see more than the person asking. Access requires both the source ACL and the sensitivity policy to allow it; the more restrictive one wins.

**Layer 1, source ACLs:** per-document permissions synced from each tool and mapped to the identity provider (Okta/Entra via SCIM groups). If you can't open it in Drive, the assistant can't read it for you.

**Layer 2, sensitivity labels + user attributes:** this catches documents that are over-shared at the source (e.g., a revenue sheet shared "anyone at company"). Labels come from owners, folder rules and an auto-classifier; unlabeled docs from Finance, Legal, People and Security sources default to Restricted until reviewed.

| Label | Examples | Full-time | Intern | Contractor / vendor |
| --- | --- | --- | --- | --- |
| Public | API docs, published model cards, blog | Yes | Yes | Yes |
| Internal | Eng wiki, runbooks, onboarding, OKRs | Yes | Yes, except roadmap and pricing spaces | Only spaces shared with them |
| Confidential | Unreleased model evals, roadmap, customer list, pricing strategy | Need-to-know groups | No | No |
| Restricted | Revenue, forecasts, board decks, compensation, M&A, legal, security incidents | Named allowlist only | No | No |

**Leak prevention**

- Filtering happens at retrieval, so restricted text never reaches the model's context; prompts never contain "don't reveal X" instructions as the control.
- No shared answer cache across users; conversation history is private to the user.
- Derived artifacts (summaries, captions, embeddings) inherit the strictest ACL of their source.
- Offboarding or a role change (e.g., contractor ends) revokes access within 5 min via the identity provider.
- Output DLP for contractors and interns: block account numbers, customer PII and secrets in responses.

**Audit and compliance:** log every query, retrieved doc IDs, answer and action per user; immutable, kept 1 year; admin dashboard with alerts on probing patterns (e.g., repeated denied queries for revenue). Encryption in transit and at rest, zero data retention with the LLM provider, SOC 2 controls, regional data residency where required.

## 5. Non-functional requirements

| Area | Requirement |
| --- | --- |
| Latency | First token < 2 s; full answer p50 < 4 s, p95 < 10 s |
| Scale | 5,000 users, 2M documents, \~20M chunks at launch; 10× headroom |
| Availability | 99.9% for query path; ingestion may lag but must never serve revoked content |
| Freshness | Edits < 15 min; deletes and permission changes < 5 min |
| Cost | < $0.03 per answered query at target volume (model + retrieval) |
| Evaluation | Golden set of 500 Q&A per department + 200 permission red-team prompts, run on every model, prompt or retriever change |
| Model choice | Model-agnostic LLM layer so the generator and embedder can be swapped without re-architecting |

## 6. Success metrics, phasing, risks

| Metric | Target (90 days post-GA) |
| --- | --- |
| Permission leaks (incidents + red-team failures) | 0; launch is blocked on 100% red-team pass |
| Groundedness (claims supported by cited source, sampled) | ≥ 95% |
| Answer helpfulness (thumbs up) | ≥ 75% |
| Abstain ("I don't know") rate | 5–15%; too low suggests guessing |
| Weekly active employees | ≥ 60% |
| Time to find an answer vs. search baseline | − 50% |
| Action success rate (completed without error) | ≥ 95% |

**Phasing**

1. **P0, pilot (8 weeks):** Confluence, Drive, GitHub, Jira; text and tables; ACL sync + sensitivity labels; Slack bot + web; citations and abstain. Full-time employees only.
2. **P1 (+6 weeks):** diagrams and images, spreadsheet SQL tool, Notion/SharePoint/Slack; read actions; interns and contractors onboarded after a red-team pass on their policies.
3. **P2 (+8 weeks):** reversible write actions with confirmation, runbook execution, IDE/CLI and API surfaces.

**Risks and mitigations**

- *Over-shared source docs leak sensitive data:* Layer 2 labels and default-Restricted for sensitive sources.
- *Stale or conflicting docs produce wrong answers:* freshness boosts, owner verification badges, conflict display, feedback to owners.
- *Prompt injection via documents triggers actions:* actions only from user intent, confirmation on every write.
- *ACL sync lag after a permission change:* 5-min SLA, real-time revocation on IdP events, fail closed if sync is unhealthy.

**Open questions**

- [ ] Hosted LLM API with zero retention, or self-hosted model for Restricted content?
- [ ] Who owns sensitivity labeling at scale: doc owners, Security, or the auto-classifier with review?
- [ ] Should Slack private channels be indexed for their members in v2?
