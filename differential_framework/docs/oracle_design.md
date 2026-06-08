# Oracle Design

This document specifies the verification oracles used by the binary
analyzer to detect CET/IBT instrumentation bugs.

## Background: Intel CET / IBT

Intel Control-flow Enforcement Technology (CET) includes Indirect
Branch Tracking (IBT), which works via two mechanisms:

1. **`endbr64`** — a landing-pad instruction placed at valid indirect
   branch targets. The CPU raises `#CP` if an indirect `call`/`jmp`
   lands on an instruction that is not `endbr64`.

2. **`notrack` prefix** — placed before `call`/`jmp` to suppress IBT
   checking for that specific branch. Used when the target is known
   to be safe (e.g., `nocf_check` function pointers).

## Oracle 1: Callee ENDBR Verification

**Module:** `analyzer/oracles.py:check_callee_endbr`

### Purpose

Verify that each target function's entry point has or lacks `endbr64`
according to the test plan.

### Specification

For each target function in the plan:

| `func_attr`   | `expected_endbr` | Rule                                          |
|---------------|------------------|-----------------------------------------------|
| `nocf_check`  | `NO`             | Function MUST NOT start with `endbr64`        |
| `cf_check`    | `YES`            | Function MUST start with `endbr64`            |
| `none`        | `YES` or `ANY`   | `YES`: must have `endbr64`; `ANY`: no verdict |

### Method

1. Run `nm -S` to collect all text-section symbols, grouped by address.
2. Run `objdump -d` to get the full disassembly.
3. For each target address, read the raw bytes of the first instruction.
4. Check if the bytes begin with `f3 0f 1e fa` (the `endbr64` encoding).

### Bug Categories

| Issue              | Condition                                 |
|--------------------|-------------------------------------------|
| `UNEXPECTED_ENDBR` | `expected=NO` but `endbr64` is present    |
| `MISSING_ENDBR`    | `expected=YES` but `endbr64` is absent    |
| `CF_CHECK_NO_ENDBR`| `cf_check` function lacks `endbr64`       |

### Alias Handling

Multiple symbols at the same address (due to ICF) are grouped. The
oracle checks each address only once. If aliases exist, they are
recorded in the bug record's `target_symbols` field but are NOT
themselves treated as bugs.

## Oracle 2: Callsite Notrack Verification

**Module:** `analyzer/oracles.py:check_callsite_notrack`

### Purpose

Verify that each per-target shim's indirect call carries or lacks the
`notrack` prefix according to the test plan.

### Specification

For each target with a corresponding `ibt_callsite_func_N` shim:

| `call_mode` | Expected          | Rule                                       |
|-------------|-------------------|---------------------------------------------|
| `nocf_ptr`  | `notrack` prefix  | Indirect call MUST have `notrack`           |
| `plain`     | No prefix         | Indirect call MUST NOT have `notrack`       |

### Method

1. Locate the `<ibt_callsite_func_N>:` label in the objdump output.
2. Extract the function body (up to the next blank line).
3. Find indirect `call *…` or `jmp *…` instructions in the body.
4. For the first indirect call found, check:
   - Raw bytes start with `0x3e` (the notrack prefix byte)
   - Mnemonic starts with `notrack `
   - Both must agree.

### Unmapped Callsites

If the shim is absent from the disassembly (inlined, ICF'd, or
stripped) or contains no indirect call (devirtualised), the callsite
is recorded as `mapped=False`. This is **not** a bug — the compiler
is free to optimise away indirect calls.

### Bug Categories

| Issue                | Condition                                    |
|----------------------|----------------------------------------------|
| `MISSING_NOTRACK`    | `nocf_ptr` call lacks `notrack` prefix       |
| `UNEXPECTED_NOTRACK` | `plain` call has `notrack` prefix            |

## Oracle 3: cf_check Verification

**Module:** `analyzer/oracles.py:check_cf_check`

A dedicated check for `ibt_x_cf_check`, the function annotated with
`__attribute__((cf_check))`. This is the explicit opt-in counterpart
to `nocf_check`. The oracle verifies that `endbr64` is present at its
entry — `cf_check` should never suppress the landing pad.

## Observation: Jump Table

**Module:** `analyzer/oracles.py:observe_jumptable`

The extras file contains a dense `switch`/`case` over a volatile
integer, designed to trigger jump-table emission. The analyzer records:

- Whether any indirect `jmp` instructions were found
- How many indirect jumps exist
- Whether any carry the `notrack` prefix

This is **purely observational** — no bugs are flagged. The data is
useful for understanding compiler behaviour around jump-table IBT
instrumentation.

## Cross-Configuration Differential

**Module:** `runner/test_loop.sh` (shell logic)

After all configurations have been analysed for a given test case,
the runner compares the ENDBR status of each target across configs.
If any two non-NA configurations disagree (e.g., one says `PRESENT`
and another says `MISSING`), a differential is recorded.

Differentials highlight cases where compiler behaviour is inconsistent
for the same source code — a strong signal for potential bugs even when
no single oracle flags an issue.
