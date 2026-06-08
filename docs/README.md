# CET/IBT Differential Testing Framework

This framework tests Intel CET (Control-flow Enforcement Technology) and IBT (Indirect Branch Tracking) compiler implementations. It generates random C programs, adds IBT attributes, compiles them with multiple compilers, and analyzes the binaries to find bugs or errors.

## Quick Start

```bash
export CSMITH_DIR=~/cet_csmith/csmith
./cet_csmith_tester_v3.sh run 500
./cet_csmith_tester_v3.sh results
```

Prerequisites: GCC and Clang (with -fcf-protection=branch), lld, CSmith, Python 3.10+, nm, objdump, and readelf.

## Project Structure

```
differential_framework/
├── analyzer/
│   ├── symbols.py
│   ├── disassembly.py
│   ├── oracles.py
│   └── main.py
├── generator/
│   ├── signatures.py
│   ├── harness.py
│   └── plan.py
├── runner/
│   ├── config.sh
│   ├── helpers.sh
│   ├── csv_init.sh
│   ├── test_loop.sh
│   ├── collect_results.py
│   ├── extract_status.py
│   └── show_results.sh
├── docs/
│   ├── README.md
│   ├── architecture.md
│   ├── oracle_design.md
│   └── output_format.md
├── tests/
│   ├── test_disassembly.py
│   ├── test_symbols.py
│   ├── test_oracles.py
│   ├── test_signatures.py
│   ├── test_plan.py
│   ├── test_harness.py
│   └── test_collect_results.py
├── results/
├── analyze_binary.py
├── generate_harness.py
└── cet_csmith_tester_v3.sh
```

## How It Works

1. Generate: CSmith creates a random C program. We pick target functions, add IBT attributes like nocf_check and cf_check, and create shim functions to perform indirect calls.
2. Compile: The program is compiled under different GCC and Clang configurations.
3. Analyze: The analyzer checks if the expected endbr64 and notrack instructions are present in the binaries.
4. Differential: The framework flags any disagreements between compilers for the exact same source code.

## Documentation

Check the docs folder for more details:
- [architecture.md](architecture.md): System design and data flow.
- [oracle_design.md](oracle_design.md): How the verification works.
- [output_format.md](output_format.md): Explanation of the CSV and JSON files.

## Environment Variables

- CSMITH_DIR: Path to CSmith (default: ~/cet_csmith/csmith)
- CET_WORK_DIR: Output directory (default: ~/cet_csmith_v3)
- SEED_BASE: Starting random seed (default: 1337)
