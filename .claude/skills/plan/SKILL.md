---
name: plan
model: claude-opus-5-5
description: Plan before coding. Explain the solution with visuals (LLD/class diagrams, sequence flows, call flows, responsibility tables), wait for approval, then show the final code, and after that approval write a very short plan record (responsibilities and call flow only). Use for any non-trivial change (3+ steps, new classes/modules, or architectural decisions), or when the user says "plan", "design this", "LLD", "how will you build", "/plan".
---

# Plan first, code later

Do not write or edit source code until the user has approved the plan **and** the final code.

## Flow

```
Understand → Visual plan → [APPROVAL 1] → Final code shown → [APPROVAL 2] → Write code + short plan record
```

### 1. Understand
- Read the relevant requirements/HLD docs and code (ask before searching files if the user can attach them).
- If something blocks the design, ask up to 3 short questions, each with a default.

### 2. Visual plan (show in chat)
Include only the sections that apply. Prefer Mermaid; use ASCII when it is clearer.

| Section | When | Format |
|---|---|---|
| **LLD / class diagram** | new or changed classes, interfaces, modules | Mermaid `classDiagram` (fields, key methods, relations) |
| **Sequence flow** | any request/event/runtime flow | Mermaid `sequenceDiagram` (happy path + main error path) |
| **Call flow** | function-level logic | indented tree: `A.run() → B.load() → C.parse()` |
| **Responsibilities** | always | table: `Class/Function · Responsibility (one line) · Called by` |
| **State / data flow** | stateful objects, pipelines, schemas | Mermaid `stateDiagram-v2` / `flowchart` / ER |
| **Files touched** | always | list: new / modified, one line each |
| **Edge cases & risks** | always | short bullets; note backward-compatibility |

Rules:
- One responsibility per class/function; if a row needs "and", split it or justify it.
- Keep it as simple as the requirement allows. Do not design for scale that is not asked for.
- End with: **"Approve this plan, or tell me what to change."** Then stop.

### 3. Final code (after approval 1)
- Show the full code for each file (or a precise diff for modified files) in chat. Do not write files yet.
- Code must match the approved diagrams; if it had to deviate, call out the deviation explicitly.
- For any chunk that is not plain vanilla code — framework/library integration, decorators, annotations, DI wiring, config/YAML, ORM mappings, schemas, macros, middleware, or other declarative or "magic" code — add a short note right below that chunk:

  | Item | Content |
  |---|---|
  | **What it is** | name of the library/feature/construct |
  | **What it does** | its effect at runtime, in one or two lines |
  | **Vanilla equivalent** | what it does in plain code or pseudocode (the hidden steps it hides) |
  | **Responsibility** | why it is in this design and what it owns |
  | **Alternatives** | other options and their trade-offs, or "none" |
- End with: **"Approve the code to write it."** Then stop.

### 4. Write (after approval 2)
- Write the code files exactly as approved.
- Write the short plan record to `tasks/todo.yml` under a `design:` key (create the file if missing). Keep it **very short**, only to preserve the flow:

```yaml
design:
  feature: <name>
  responsibilities:
    ClassName: <one line>
    ClassName.method(): <one line>
    function_name(): <one line>
  call_flow:
    - Entry.handle() -> Service.process() -> Repo.save()
    - Service.process() -> Validator.check()   # error path: raises X
```

No diagrams, rationale or code in the record — responsibilities and call flow only.

## Change handling
- If the user requests changes at any gate, update the visuals/code and ask for approval again.
- If implementation reveals the approved design is wrong, stop, show the updated diagram, and re-approve before continuing.
