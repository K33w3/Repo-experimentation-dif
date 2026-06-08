# Oracles

This document explains the verification oracles used in our binary analyzer.

## Background

Intel Control-flow Enforcement Technology (CET) uses Indirect Branch Tracking (IBT):
1. endbr64: A landing pad instruction required at valid indirect branch targets.
2. notrack: A prefix placed before a call or jmp to suppress IBT checking for that branch.

## Callee ENDBR

Checks that target functions start with endbr64 as dictated by the test plan:
- nocf_check: expects NO endbr64.
- cf_check: expects YES endbr64.
- none: expects YES or ANY.

We check this by finding symbols with nm -S, disassembling with objdump -d, and checking the first instruction bytes for f3 0f 1e fa.
Bugs flagged: UNEXPECTED_ENDBR, MISSING_ENDBR, CF_CHECK_NO_ENDBR.
Aliases from ICF are tracked but not flagged as bugs themselves.

## Callsite Notrack

Checks whether indirect calls in shims have the notrack prefix:
- nocf_ptr: must have the notrack prefix.
- plain: must not have the notrack prefix.

We extract the shim function body and inspect the first indirect call for the 0x3e byte and notrack mnemonic. Unmapped callsites (optimized out) are ignored.
Bugs flagged: MISSING_NOTRACK, UNEXPECTED_NOTRACK.

## cf_check

Ensures ibt_x_cf_check starts with endbr64, as the cf_check attribute opts into IBT.

## Jump Tables

Observes compiler-generated jump tables from the switch/case in the extras file. Records indirect jump counts and notrack prefixes. Flags no bugs.

## Cross-Configuration Differential

Compares ENDBR status across compiler configurations. Disagreements between compilers on the same source code are recorded as differentials, indicating potential bugs.
