# Output Format Reference

This document describes the CSV and JSON file formats produced by the
testing framework.

## CSV Files

All CSV files are written to `$RESULTS_DIR` (default: `~/cet_csmith_v3/results/`).

---

### `summary.csv`

One row per (test, configuration) pair with aggregate metrics.

| Column                    | Type | Description                                      |
|---------------------------|------|--------------------------------------------------|
| `test_id`                 | int  | Test iteration number                            |
| `config`                  | str  | Compiler configuration name                      |
| `total_funcs`             | int  | Total text-section symbols in the binary         |
| `target_funcs`            | int  | Number of target functions in the plan           |
| `addr_taken_endbr_sites`  | int  | Targets whose entry starts with `endbr64`        |
| `callsites_mapped`        | int  | Shims where an indirect call was located         |
| `callsites_nocf_expected` | int  | Shims expected to have `notrack`                 |
| `callsites_nocf_observed` | int  | Shims that actually have `notrack`               |
| `callee_bugs`             | int  | CALLEE_INSTRUMENTATION bugs for this binary      |
| `callsite_bugs`           | int  | CALLSITE_INSTRUMENTATION bugs for this binary    |
| `alias_groups`            | int  | Number of ICF alias groups                       |

---

### `bugs.csv`

One row per bug detected. May have zero data rows if no bugs were found.

| Column           | Type | Description                                         |
|------------------|------|-----------------------------------------------------|
| `test_id`        | int  | Test iteration number                               |
| `config`         | str  | Compiler configuration                              |
| `category`       | str  | `CALLEE_INSTRUMENTATION` or `CALLSITE_INSTRUMENTATION` |
| `issue`          | str  | Bug type (see Oracle Design doc)                    |
| `target_addr`    | hex  | Address of the affected function/instruction        |
| `target_symbols` | str  | Pipe-separated list of symbol names at that address |
| `func_attr`      | str  | `nocf_check`, `cf_check`, or `none`                 |
| `call_mode`      | str  | `nocf_ptr` or `plain`                               |
| `weird_attr`     | str  | Additional attribute (`hidden`, `used`, `none`)     |
| `expected`       | str  | What the oracle expected                            |
| `observed`       | str  | What was actually found                             |
| `details`        | str  | Human-readable description                          |

---

### `aliases.csv`

Records ICF (Identical Code Folding) alias groups — addresses where
multiple symbols reside. These are **not bugs**; they document a known
compiler optimisation.

| Column    | Type | Description                             |
|-----------|------|-----------------------------------------|
| `test_id` | int  | Test iteration number                   |
| `config`  | str  | Compiler configuration                  |
| `addr`    | hex  | Shared address                          |
| `symbols` | str  | Pipe-separated list of symbol names     |

---

### `differential.csv`

Records cross-configuration disagreements on ENDBR status.

| Column            | Type | Description                              |
|-------------------|------|------------------------------------------|
| `test_id`         | int  | Test iteration number                    |
| `category`        | str  | Always `callee`                          |
| `key`             | str  | Target function name                     |
| `gcc_baseline`    | str  | Status under gcc-branch-baseline         |
| `gcc_lto`         | str  | Status under gcc-branch-lto              |
| `clang_baseline`  | str  | Status under clang-branch-baseline       |
| `clang_thinlto`   | str  | Status under clang-branch-thinlto        |
| `clang_fulllto`   | str  | Status under clang-branch-fulllto        |

Status values: `PRESENT`, `MISSING`, `ABSENT`, `NOPLAN`, `UNREADABLE`, `NA`.

---

### `endbr64_counts.csv`

Total `endbr64` instruction count per binary (for cross-config comparison).

| Column         | Type | Description                           |
|----------------|------|---------------------------------------|
| `test_id`      | int  | Test iteration number                 |
| `config`       | str  | Compiler configuration                |
| `total_endbr64`| int  | Total `endbr64` instructions found    |

---

### `jumptable.csv`

Observational data about jump-table lane compilation.

| Column                 | Type | Description                             |
|------------------------|------|-----------------------------------------|
| `test_id`              | int  | Test iteration number                   |
| `config`               | str  | Compiler configuration                  |
| `switch_table_detected`| bool | Whether indirect jumps were found       |
| `indirect_jmp_count`   | int  | Number of indirect jmp instructions     |
| `indirect_jmp_notrack` | bool | Whether any carry the notrack prefix    |

---

### `callsite_detail.csv`

Per-target, per-configuration callsite mapping and notrack status.

| Column             | Type | Description                                  |
|--------------------|------|----------------------------------------------|
| `test_id`          | int  | Test iteration number                        |
| `config`           | str  | Compiler configuration                       |
| `target`           | str  | Target function name                         |
| `expected_notrack`  | bool | Whether notrack was expected (nocf_ptr mode) |
| `mapped`           | bool | Whether the shim's indirect call was found   |
| `observed_notrack`  | bool | Whether notrack prefix was observed          |
| `callsite_addr`    | hex  | Address of the indirect call (if mapped)     |

---

## JSON Analysis Report

Each call to `analyze_binary.py` produces a JSON file with the full
analysis results. This is the intermediate format consumed by
`collect_results.py` to populate the CSVs above.

### Schema

```json
{
  "test_id": "string",
  "config": "string",
  "total_funcs": "int",
  "target_funcs": "int",
  "total_endbr64": "int",
  "addr_taken_endbr_sites": "int",
  "callsites_mapped": "int",
  "callsites_nocf_expected": "int",
  "callsites_nocf_observed": "int",
  "callee_bugs": "int",
  "callsite_bugs": "int",
  "alias_groups": "int",
  "aliases": [
    { "addr": "hex string", "symbols": ["string"] }
  ],
  "bugs": [
    {
      "category": "string",
      "issue": "string",
      "target_addr": "hex string",
      "target_symbols": ["string"],
      "func_attr": "string",
      "call_mode": "string",
      "weird_attr": "string",
      "expected": "string",
      "observed": "string",
      "details": "string"
    }
  ],
  "total_bugs": "int",
  "target_status": [
    { "name": "string", "status": "string" }
  ],
  "callsite_records": [
    {
      "target": "string",
      "expected_notrack": "bool",
      "mapped": "bool",
      "observed_notrack": "bool",
      "callsite_addr": "string"
    }
  ],
  "jumptable": {
    "table_detected": "bool",
    "indirect_jmp_count": "int",
    "indirect_jmp_notrack": "bool"
  }
}
```
