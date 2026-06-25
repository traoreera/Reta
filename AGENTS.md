# Repository Guidelines

## Project Structure & Module Organization
This repository is organized around RETA research notes and simulation code.

- `README.md` is the entry point.
- `docs/` contains the main theory, technique, strategy, and versioned write-ups.
- `docs/v1.x/` holds version-specific simulations and outputs such as `simulation.py` and `results.png`.
- `simulations/` contains standalone Python experiments and dashboards, including interactive drone and finance demos.
- `sources/` stores reference images used by the documentation.

Keep new documentation in the closest matching `docs/` subsection and new runnable prototypes in `simulations/`.

## Build, Test, and Development Commands
The project uses Python tooling managed by `uv` and has no dedicated build system.

- `uv sync` installs the environment from `pyproject.toml` and `uv.lock`.
- `uv run python simulations/simulation_reta.py` runs the main RETA climate simulation.
- `uv run python simulations/drone_interactive.py` starts the interactive drone demo.
- `uv run python docs/v1.4/simulation.py` runs a versioned example under `docs/`.

Prefer `uv run ...` so scripts use the pinned dependencies.

## Coding Style & Naming Conventions
Use standard Python style with 4-space indentation and `snake_case` for functions, variables, and module names. Reserve `UPPER_CASE` for constants such as `NASA_URL` or `DT`.

- Keep scripts self-contained and explicit.
- Use short French or English comments only when the code is non-obvious.
- Name versioned artifacts consistently, for example `docs/v1.4/README.md` and `results.png`.

No formatter or linter is currently configured in `pyproject.toml`, so match the surrounding style closely.

## Testing Guidelines
There is no automated test suite yet. Validate changes by running the affected script and checking the generated figures, console output, or interactive behavior.

- For simulation changes, rerun the touched script under `simulations/` or `docs/v1.x/`.
- For documentation changes, verify internal links and image paths.

If you add tests later, place them near the code they cover and use clear names such as `test_<feature>.py`.

## Commit & Pull Request Guidelines
The Git history currently shows a single `initial commit`, so there is no established commit convention yet. Use concise, imperative subjects such as `Add drone calibration note` or `Fix simulation bounds`.

Pull requests should include:

- A short summary of the change and why it matters.
- Links to any related notes, issues, or versioned docs.
- Screenshots or exported figures when visuals change.

## Agent-Specific Notes
Do not rename or move the versioned docs unless the change is intentional and coordinated. Keep edits focused on the relevant theory or simulation area.
