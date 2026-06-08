## OUTPUT CSV Files

All CSV files are saved in the results directory.

- summary.csv: Shows aggregate metrics for each test and compiler configuration pair, including the number of targets, endbr64 sites, mapped shims, and total bugs found.
- bugs.csv: Lists every bug found. It includes the test ID, configuration, bug category, the specific issue, the address, expected versus observed behavior, and extra details.
- aliases.csv: Records addresses where multiple symbols share the same code due to Identical Code Folding. This is a normal compiler optimization and not a bug.
- differential.csv: Logs cases where different compiler configurations disagree on the ENDBR status of the exact same function.
- endbr64_counts.csv: Records the total number of endbr64 instructions across the entire binary for comparison.
- callsite_detail.csv: Details each shim's indirect call, tracking whether the call was found in the disassembly, if notrack was expected, and if it was actually observed.

## JSON Analysis Report

Each binary analysis creates an intermediate JSON file. It contains the complete set of raw data used to build the CSV files above, including all counts, detailed bug lists, aliases, and jump table observations.
