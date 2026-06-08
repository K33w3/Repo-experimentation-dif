# CET/IBT Differential Testing Framework

A differential testing framework for verifying Intel CET (Control-flow
Enforcement Technology) / IBT (Indirect Branch Tracking) compiler
instrumentation. The framework generates randomised C programs with
controlled IBT-relevant attributes, compiles them under multiple
compiler configurations, and analyses the resulting binaries to detect
instrumentation bugs.

## Quick Start

```bash
# Prerequisites
#   - GCC and Clang with -fcf-protection=branch support
#   - lld linker (sudo apt install lld)
#   - CSmith random C program generator
#   - Python 3.10+, nm, objdump, readelf

# Set CSmith location (if non-default)
export CSMITH_DIR=~/cet_csmith/csmith

# Run 500 test iterations
./cet_csmith_tester_v3.sh run 500

# View aggregated results
./cet_csmith_tester_v3.sh results
```

## Project Structure

```
differential_framework/
├── analyzer/                   # Binary analysis package
│   ├── symbols.py              #   ELF symbol table collection
│   ├── disassembly.py          #   objdump output parsing
│   ├── oracles.py              #   ENDBR64 & notrack verification
│   └── main.py                 #   CLI entry point
├── generator/                  # Test-case generation package
│   ├── signatures.py           #   C signature extraction & parsing
│   ├── harness.py              #   Harness C-source emission
│   ├── extras.py               #   Observational lane generation
│   └── plan.py                 #   Target selection & plan output
├── runner/                     # Shell-based test orchestration
│   ├── config.sh               #   Paths & compiler configurations
│   ├── helpers.sh              #   Utility functions & preflight
│   ├── csv_init.sh             #   CSV header initialisation
│   ├── test_loop.sh            #   Core iteration loop
│   ├── collect_results.py      #   JSON → CSV aggregation
│   ├── extract_status.py       #   Differential status extraction
│   └── show_results.sh         #   Results display
├── docs/                       # Documentation
│   ├── README.md               #   This file (overview)
│   ├── architecture.md         #   System architecture & data flow
│   ├── oracle_design.md        #   Oracle specification
│   └── output_format.md        #   CSV/JSON output reference
├── tests/                      # Unit tests (pytest)
│   ├── test_disassembly.py     #   objdump parsing tests
│   ├── test_symbols.py         #   Symbol table tests
│   ├── test_oracles.py         #   Oracle verification tests
│   ├── test_signatures.py      #   Signature extraction tests
│   ├── test_plan.py            #   Target selection & plan tests
│   ├── test_harness.py         #   Harness emission tests
│   ├── test_extras.py          #   Extras generation tests
│   └── test_collect_results.py #   CSV aggregation tests
├── results/                    # Test output data (git-tracked)
├── analyze_binary.py           # Entry point → analyzer/
├── generate_harness.py         # Entry point → generator/
├── generate_extras.py          # Entry point → generator/extras
└── cet_csmith_tester_v3.sh     # Entry point → runner/
```

## How It Works

1. **Generate** — CSmith produces a random C program. The harness
   generator selects target functions, assigns IBT attributes
   (`nocf_check`, `cf_check`), and emits per-target shim functions
   that perform indirect calls through function pointers.

2. **Compile** — The program is compiled under 5 configurations
   (GCC baseline, GCC+LTO, Clang baseline, Clang+ThinLTO,
   Clang+FullLTO), all with `-fcf-protection=branch`.

3. **Analyse** — The binary analyzer inspects each compiled binary:
   - **Callee oracle**: does each function's entry point have (or lack)
     `endbr64` as expected?
   - **Callsite oracle**: does each shim's indirect call carry (or lack)
     the `notrack` prefix as expected?

4. **Differential** — Cross-configuration comparison detects cases
   where compilers disagree on instrumentation for the same source.

## Documentation

See the [docs/](docs/) directory for detailed documentation:

- [Architecture](docs/architecture.md) — system design and data flow
- [Oracle Design](docs/oracle_design.md) — verification oracle specification
- [Output Format](docs/output_format.md) — CSV and JSON schema reference

## Running Tests

The framework includes 119 unit tests covering all modules. Tests use
synthetic objdump snippets and mocked tool output — no real binaries or
compilers are required.

```bash
# Install pytest (one-time)
pip3 install pytest

# Run the full suite
python3 -m pytest tests/ -v

# Run a specific test module
python3 -m pytest tests/test_oracles.py -v

# Run with short traceback on failure
python3 -m pytest tests/ --tb=short
```

## Environment Variables

| Variable       | Default                    | Description                     |
|----------------|----------------------------|---------------------------------|
| `CSMITH_DIR`   | `~/cet_csmith/csmith`     | Path to CSmith source tree      |
| `CET_WORK_DIR` | `~/cet_csmith_v3`         | Working/output directory        |
| `SEED_BASE`    | `1337`                    | Starting seed for reproducibility |
