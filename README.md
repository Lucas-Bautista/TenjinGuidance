# TenjinGuidance

TenjinGuidance orchestrates **LLM-guided C→Rust translation** by analyzing C code, asking Claude for type and mutability hints, and passing that guidance to [Tenjin](../tenjin/). It then checks translated Rust with `cargo check` and records quality metrics. The CLI still prints **Tractor** in mode messages for brevity.

## Repository layout

Place these three directories as **siblings** under one parent (the parent name does not matter):

```
<parent>/
  TenjinGuidance/         # this project
  tenjin/                  # 10j CLI + c2rust fork
  PUBLIC-Test-Corpus/      # benchmark C projects
```

```mermaid
flowchart TB
  subgraph parent [parent folder]
    TenjinGuidance[TenjinGuidance]
    Tenjin[tenjin]
    Corpus[PUBLIC-Test-Corpus]
  end
  Corpus -->|codebases.txt| TenjinGuidance
  TenjinGuidance -->|"./10j translate"| Tenjin
  TenjinGuidance -->|Anthropic API| LLM[Claude]
  Tenjin --> Results[tenjin_results/]
```

| Path | Purpose |
|------|---------|
| `src/` | Pipeline: C analysis, LLM prompts, Tenjin invocation, metrics |
| `prompts/` | LLM system prompts for types, mutability, return types |
| `codebases/` | Lists of C targets (`codebases.txt`) |
| `c_samples/` | Small `.c` files for local development |
| `tenjin_results/` | Guided translation outputs (`--guided`; created at run time) |
| `tenjin_baseline/` | Baseline Tenjin outputs without LLM guidance (`--tenjinize-only`) |

See [src/README.md](src/README.md) for module-level detail.

### Clone sibling repositories

From your parent directory (alongside TenjinGuidance):

```bash
git clone git@github.com:Aarno-Labs/tenjin.git
git clone git@github.com:DARPA-TRACTOR-Program/PUBLIC-Test-Corpus.git
```

The corpus checkout must be named `PUBLIC-Test-Corpus` so paths in `codebases/codebases.txt` resolve correctly.

## Setup

### 1. Tenjin

```bash
cd ../tenjin/cli
./10j provision
```

Add `tenjin/cli` to your `PATH`, or TenjinGuidance will invoke `./10j` from that directory automatically (sibling layout required).

### 2. TenjinGuidance Python environment

```bash
cd TenjinGuidance
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. libclang (macOS)

`variable_counts.py` uses libclang with Homebrew LLVM at `/opt/homebrew/opt/llvm/lib` and the macOS SDK via `xcrun`. On Linux, adjust `Config.set_library_path` in `src/variable_counts.py` for your LLVM install.

### 4. API key

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=...
```

Never commit `.env`.

### 5. Codebase list

Default paths in `codebases/codebases.txt` are **relative** to that file and assume the three-repo layout above. No edits are needed if your tree matches.

## Running

From `TenjinGuidance/` with the venv activated (`python3` if `python` is not on your PATH):

```bash
# Guided pipeline (default): analyze C → LLM → Tenjin → cargo check (up to 3 attempts)
python3 src/guidance.py
# same as:
python3 src/guidance.py --guided

# Variable counts only (no LLM, no Tenjin)
python3 src/guidance.py --analyze-only

# Baseline Tenjin on codebases.txt targets, no LLM guidance
python3 src/guidance.py --tenjinize-only

# Print metrics for a past run
python3 src/guidance.py --print-metrics tenjin_results/file_0_attempt_1/final/main
```

Custom targets: pass `--codebases path/to/list.txt` (one path per line; `#` comments and blank lines ignored; relative paths resolve from the list file’s directory).

## Outputs

| Run | Results directory |
|-----|-------------------|
| Guided (`--guided`) | `tenjin_results/file_{N}_attempt_{M}/` |
| LLM logs (sidecar) | `tenjin_results/file_{N}_attempt_{M}__tractor_llm/` |
| Baseline (`--tenjinize-only`) | `tenjin_baseline/file_{N}_without_guidance/` |

Each Tenjin run produces intermediate C transforms under `c_*` prefixes and final Rust under `final/main/`. Guided runs also write `translation_metrics.json` and `guidance_to_tenjin.json` in the LLM sidecar directory.

## Guidance passed to Tenjin

TenjinGuidance builds a JSON object with keys Tenjin understands (`vars_of_type`, `declspecs_of_type`, `vars_mut`, `fn_return_type`). See [tenjin/docs/USE.md](https://github.com/Aarno-Labs/tenjin/blob/main/docs/USE.md) and [src/README.md](src/README.md).

## Tests

```bash
pytest tests/
```

## Further reading

- [Tenjin README](../tenjin/README.md)
- [Tenjin user docs](../tenjin/docs/USE.md)
- [TenjinGuidance src/README.md](src/README.md)
