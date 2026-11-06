+++
[pact]
type = "drift"
id = "DRIFT-001"
status = "known"
owners = ["engineering"]
+++

# DRIFT-001 — <Title>

<!-- One business dispute per Drift, even when several files/plans disagree.
Keep known until the decision and required implementation are both accounted
for. A decision alone does not establish resolved behavior. Replace every
placeholder before checking a resolved/accepted record. -->

## Conflict sources

<Describe the concrete disagreement, the confirmed and uncertain portions,
and link every relevant source and Change. Include source revision/path or
another durable locator; do not infer authority from code.>

## Scope

<State the affected business fact, year/role/conditions, user-visible
consequences and risk. An unresolved chapter holds its entire source file;
independent conflict-free files may proceed.>

## Decision basis

<Link the actual decision source and record the choice, decision maker and
scope. If the Owner only deferred a choice, keep known. Do not invent approval
or create a Decision record unless the existing long-term rationale threshold
is met.>

## Current authority

<Explicitly select and link the one current business authority for this scope,
with the reason to follow it. When accepted, explain the temporary authority
and any separate basis governing current implementation. No authority selected
means this record cannot close.>

## Implementation and verification

### Implementation

<Link the updated canonical body, necessary implementation and reference
updates, or the locatable evidence that implementation changes were not
needed. Record actual results; an Owner decision alone is insufficient.>

### Verification

<Link checks/review evidence and describe what they actually establish,
including unverified anchors, host imports and special references. Resolved
requires both Implementation and Verification references. Accepted must
state completed checks, pending work and the revisit trigger.>

## Remaining issues

<State none for resolved only when no blocking mismatch remains. For accepted,
describe the remaining deviation, explicit acceptance, consequences and revisit
trigger. Do not hide an implementation gap behind a recorded decision.>
