# CLAUDE.md

## Project context

See `README.md` for the full architecture writeup — it is comprehensive and kept up to date. **Read it before making structural changes or running the project.**

## Coding style — read before writing any code

These rules are the most important part of this file. They apply to all code written in this repo, and they override your default coding habits. Prioritize readability and explicit, linear control flow over conciseness, cleverness, or defensive programming.

### Control flow
- Write control structures (`for`, `while`, `if`/`else`) in traditional, multi-line, cascading form. Never collapse them into single-line statements.
- Avoid early return. Prefer cascading `if` / `elif` / `else` nesting over guard clauses, even when it nests deeply.

### Inline expressions
- Strictly avoid "inline code": no list/dict/set comprehensions, no generator expressions, no ternary operators — unless the user explicitly asks for one.
- Expand any inline expression into a traditional loop or `if`/`else` block instead.

### Structure and paradigm
- Prefer a procedural approach over object-oriented. Only introduce a class when explicitly requested.
- Keep data structures and the functions that process them in the same scope — don't split them apart into separate modules/classes/files without being asked.
- Write code with as few helper functions as possible. Inline logic in the calling function rather than extracting it out, unless the same logic is reused in more than one place.

### Error handling
- Do not add error prevention, `try`/`except`, or input validation unless explicitly requested.
- Trust inputs and internal state; write only for the expected path.

### Naming
- Variables and functions: strictly `snake_case`, and extremely descriptive — favor a long, clear name over a short, vague one.
- Classes (only when explicitly requested): `PascalCase`.

### Comments and types
- No docstrings, no comments, no type hints.
- If code feels like it needs a comment to be understood, restructure it to be self-evident instead.

### Guiding principle
When choosing between two ways to write something, pick the simplest and most readable one, not the most robust or most "clever" one. **Readability > robustness.**