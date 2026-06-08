# Architecture

This document describes the system architecture and data flow of the
CET/IBT differential testing framework.

## Overview

The framework is a three-stage pipeline: **generate → compile → analyse**.
Each stage is a separate, composable component that communicates through
well-defined file formats (C source, CSV plans, JSON reports).

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   CSmith     │────▸│  Generator      │────▸│  Compiler(s)     │
│  (random C)  │     │  (harness +     │     │  (GCC / Clang ×  │
│              │     │   plan + extras) │     │   LTO variants)  │
└─────────────┘     └─────────────────┘     └───────┬──────────┘
                                                     │
                                                     ▼
                    ┌─────────────────┐     ┌──────────────────┐
                    │  Aggregation    │◂────│  Analyzer        │
                    │  (CSV suite)    │     │  (per-binary     │
                    │                 │     │   oracle checks)  │
                    └─────────────────┘     └──────────────────┘
```

## Components

### 1. Generator (`generator/`)

**Input:** CSmith-generated C source file, seed.

**Output:** Rewritten source (with IBT attributes injected), harness C
file, extras C file, CSV test plan, target list.

The generator performs four tasks:

1. **Signature extraction** (`signatures.py`) — scans the CSmith source
   for `func_N` prototypes and definitions, normalises them, and
   classifies parameters.

2. **Target selection** (`plan.py`) — randomly selects a subset of
   functions with simple signatures and assigns IBT attributes:
   - `nocf_check` — function should NOT have `endbr64`
   - `cf_check` — function MUST have `endbr64`
   - `none` — default instrumentation

3. **Source rewriting** (`plan.py`) — injects `__attribute__` annotations
   into the original CSmith source.

4. **Harness emission** (`harness.py`) — generates per-target shim
   functions (`ibt_callsite_func_N`), each containing exactly one
   indirect call through a function pointer. The `nocf_check` attribute
   on the pointer typedef controls whether the compiler emits a
   `notrack` prefix.

### 2. Compiler Configurations

Five configurations exercise different optimisation and LTO pipelines:

| Config Name             | Compiler | Flags                                     |
|-------------------------|----------|-------------------------------------------|
| `gcc-branch-baseline`   | GCC      | `-O2 -fcf-protection=branch`              |
| `gcc-branch-lto`        | GCC      | `-O2 -fcf-protection=branch -flto`        |
| `clang-branch-baseline` | Clang    | `-O2 -fcf-protection=branch --icf=none`   |
| `clang-branch-thinlto`  | Clang    | As above + `-flto=thin`                   |
| `clang-branch-fulllto`  | Clang    | As above + `-flto`                        |

All Clang configurations use `lld` as the linker with `--icf=none` to
prevent identical-code folding of the shim functions (which would
defeat per-callsite analysis).

### 3. Analyzer (`analyzer/`)

**Input:** Compiled ELF binary, CSV test plan, target list.

**Output:** JSON report with per-target verdicts and bug records.

The analyzer runs four oracles against each binary:

1. **Callee ENDBR oracle** (`oracles.py:check_callee_endbr`) — checks
   `endbr64` at each target function's entry address.

2. **Callsite notrack oracle** (`oracles.py:check_callsite_notrack`) —
   disassembles each `ibt_callsite_func_N` shim and checks whether
   its indirect call/jmp has the `notrack` prefix.

3. **cf_check oracle** (`oracles.py:check_cf_check`) — verifies
   `endbr64` on the `cf_check`-attributed test function.

4. **Jump-table observation** (`oracles.py:observe_jumptable`) —
   records what the compiler emitted for the switch/case lane
   (observational only, never flags bugs).

### 4. Runner (`runner/`)

The shell-based runner orchestrates the full pipeline:

1. Preflight checks (`helpers.sh`)
2. CSV file initialisation (`csv_init.sh`)
3. Per-seed iteration loop (`test_loop.sh`):
   - Generate source + harness + extras
   - Compile under each configuration
   - Run the analyzer on each binary
   - Aggregate JSON results into CSVs (`collect_results.py`)
   - Compute cross-configuration differentials
4. Results display (`show_results.sh`)

## Data Flow

```
 seed ──▸ CSmith ──▸ random.c
                        │
                        ▼
              generate_harness.py
                   │    │    │
                   ▼    ▼    ▼
              random.c  harness.c  plan.csv  targets.txt
              (rewritten)
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
        gcc -O2     gcc -flto    clang -O2  ...
           │            │            │
           ▼            ▼            ▼
      analyze_binary.py (one run per binary)
           │            │            │
           ▼            ▼            ▼
     analysis.json  analysis.json  analysis.json
           │            │            │
           └────────────┼────────────┘
                        ▼
              collect_results.py
                        │
                        ▼
              summary.csv, bugs.csv, aliases.csv, ...
```

## Design Decisions

### Per-Target Shims (v3)

The v2 framework used a global count of notrack calls across the
entire harness to verify callsite instrumentation. This was unsound
because the optimiser can legally eliminate individual indirect calls.

v3 introduces per-target shim functions (`ibt_callsite_func_N`), each
containing exactly one indirect call. The analyzer locates the specific
call instruction in each shim's disassembly, providing a precise
per-callsite verdict.

### Opaque Barriers

Each shim passes its function pointer through an inline-asm identity
function with a `memory` clobber. This prevents the compiler from:
- Devirtualising the indirect call
- Folding multiple call sites together
- Propagating the pointer constant past the barrier

### ICF Limitation

Identical Code Folding on target function *bodies* is not prevented
(and cannot be without `--icf=none` on all targets, which would change
the code being tested). ICF is documented and observable via
`aliases.csv`; it is not treated as a bug.
