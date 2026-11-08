# Decomp discipline: Definition of Done, stubs and context

Read `decomp.md` (Technique 10/13) for the mechanics. This reference is about
**how to close a decomp honestly** and avoid the failure modes that make a
"decomp" look finished while it is not. Game-agnostic: no addresses here.

## Definition of Done (per function)

A function counts as **closed** only when:

1. all ASM on its path was read (no unknown branches/`...` left);
2. every callee on the critical path is decompiled **or** marked out of scope
   with a justification;
3. there is **no stub on the critical path**;
4. the C model compiles clean (`gcc -fsyntax-only` = 0 errors);
5. the contract was validated at runtime (`args_on_hit`/`contract_check` when
   possible);
6. the function is in the `.map` with name and address;
7. the doc/comment says **closed / partial / stub** and lists what is missing.

If any item fails, the function is **partial**, not closed — say so explicitly.

## Stub policy

- A stub is allowed **only** for code proven out of the target (BIOS, IRQ,
   debug, unrelated systems).
- Every stub goes in a table: `address | reason | impact | blocks? | next step`.
- A stub **on the path you are closing is a blocker**, not "partial model":
   it blocks the DoD until resolved or explicitly justified.
- Do not treat "compiles with 0 errors" as completion. A stub is scaffolding,
   never a destination.
- Never leave `...` placeholders or undeclared identifiers "for later"; that is
   what makes a decomp uncompilable forever.

## Context ledger (anti-drift)

Keep a one-line-per-context ledger in the project (e.g. `CONTEXT_LEDGER.md`):

```
scene/mode | init | ctx global | files | entry | palette/resource | order | status
```

Before labelling anything as belonging to the target (e.g. "the authoritative
palette of the panel"), check the ledger and the **caller of the init**. Two
different scenes sharing a format is the classic source of retargeting the wrong
code. If a `project_note`/`decomp_status` tool exists, use it; until then a
committed markdown table works and is cheaper.

## Controlled vocabulary (separate the three proofs)

Never say "authoritative" until all three are proven:

- **mechanism** — "handler type N writes to this address";
- **source** — "the resource that reaches this job is X";
- **order** — "job X runs after job Y".

Use the words `mechanism proven`, `source proven`, `order proven`. "Authoritative"
only when mechanism + source + order are all proven. Otherwise it is a hypothesis.

## Runtime first for order/effect

Order, "who wins last", and deferred uploads are **dynamic** questions. Resolve
them at runtime first (watchpoint/hit log, DMA trace, `args_on_hit`, frame step),
then use ASM to explain *why*. Do not try to settle execution order purely by
reading static code.

## Scope and checkpoints

- Open the session with a one-page state: target, files, proven, pending, single
  next step.
- Choose **one** critical gap at a time.
- At each milestone write a checkpoint: "Target: X. Proven: Y. Pending: Z. Next:
  W." If the session grows too wide, stop and restart around one target.
- Respect explicit constraints (e.g. "don't extract file Z"); ask before doing
  something that was excluded, even to close a proof.

## Reporting status

Every function report states **closed / partial / stub** and the missing list.
Never present a partial model as if it were further along than it is. The honest
line is cheaper than the retargeting it prevents.

## Root causes this prevents

1. No Definition of Done per function.
2. No stub policy (stub became the destination).
3. No context ledger (a different scene entered as the target).
4. Overconfidence in static code for order/effect questions.
5. Loose checkpoints/scope (long session, drift).
6. Optimistic reporting of partial models.
