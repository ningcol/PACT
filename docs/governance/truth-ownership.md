# Truth Ownership

PACT avoids a single global "source of truth" ranking. Different questions have different authorities.

| Question | Authority |
| --- | --- |
| What should users/business experience? | Confirmed Product Truth |
| What does the system currently do? | Code + runtime/generated facts |
| What public/API contract is promised? | Contract/schema authority |
| How is the current system structured? | `docs/architecture/` |
| Why was a durable choice made? | `.agents/decisions/` |
| What is this change trying to accomplish? | Active Task Contract / change/spec/plan |
| What must this task demonstrably satisfy? | Task Contract acceptance criteria, bounded by confirmed Product Truth |
| What execution was recorded? | Execution-backed Evidence from tests/browser/runtime receipts |\n| What does that execution mean for the product? | Reviewed semantic assertion bounded by Product Truth and the exact Evidence claim |
| How should a recurring task be performed today? | Skill/playbook |

## Rules

1. One fact, applicable scope and effective state should have one current authoritative body.
2. Prefer references over duplicated explanations.
3. Generated facts should be regenerated, not manually synchronized.
4. Product truth must not be inferred from implementation alone.
5. Architecture documents describe current structure; historical rationale belongs in decisions.
6. Tests are evidence, not automatically normative product truth.

Business explanations preserve coherent flows and context; important constraints
worth independent confirmation, reference or verification belong in Rules.
Domains route without copying bodies. New knowledge follows the
[product routes](../product/README.md); established project authority stays in
place until a reviewed cutover. A different year, role, condition or status can
legitimately require another record. A mixed explanation is never confirmed
solely by location or a Domain link.

## Conflict example

If a confirmed rule says "preserve entered data after province switch" while code and tests clear it:

- this is product drift;
- do not rewrite the product rule to match code;
- if product truth remains authoritative, fix code/tests;
- if product truth itself is ambiguous or obsolete, escalate the product behavior to the owner.
