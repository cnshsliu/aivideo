- when make modularity refactoring, simply moves related codes to new module
  source file, and re-arrange the import , do NOT change logic, do NOT make
  different implementation
- Moviepy version: 2.2.1. use Context7 for MoveiPy 2.2.1
- to confirm modification really work, run pyright, ruff and all scripts under './test' folder
- stick to Moviepy2.2.1, always search Context7 for API