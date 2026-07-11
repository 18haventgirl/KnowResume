# AGENTS.md

Repo-specific guidance for OpenCode agents working in this codebase.
Verify against source before trusting any of this — the docs and README are partly out of sync with the code.

## Names are inconsistent — trust the code

- Repo/dir: `KnowResume`. PyPI/project name: `SmartResume`. **Import package: `smartresume`** (lowercase).
- README says `from KnowResume import ResumeAnalyzer` — **wrong**. Real import is `from smartresume import ResumeAnalyzer` (see `scripts/start.py:20`, `demo/web_app.py:24`).
- Console scripts (pyproject): `SmartResume`, `SmartResume-cli` → both `scripts.start:main`.

## Entry points & pipeline

- CLI: `python scripts/start.py --file resume.pdf` (also `SmartResume` after `pip install -e .`).
- Pipeline core: `smartresume/backend/resume_analyzer.py:ResumeAnalyzer.pipeline`.
- Flow: `FileProcessor.process_file` → abnormal-PDF check → `DataProcessor.build_text_content` → `LLMClient.extract_info_unified` → `DataProcessor.post_process`.
- Web demo: `demo/web_app.py` — **Flask** (not Gradio, despite optional `gradio` extra and docs), port 4999, loads `ResumeAnalyzer` once at startup.

## Unified extraction — `extract_types` is a no-op

`pipeline`'s `extract_types` arg is **ignored** (kept for backwards compat, `resume_analyzer.py:39`). One LLM call extracts everything via `extract_info_unified` using the `unified` prompt. The CLI `--extract_types` flag and README examples showing it do nothing. The unified prompt emits an `experiences[]` array tagged with `type` (`work`/`internship`/`project`/`research`); `post_process` (`data_processor.py:336-383`) splits it into `workExperience` + `projects`.

## Two LLM modes — `use_direct_models` is the switch

- `false` (default in local `configs/config.yaml`): remote OpenAI-compatible API.
- `true`: loads model **in-process** via vLLM-as-library (preferred) or transformers fallback. **Do NOT start a vLLM API server** — `llm_client.py:508` is emphatic about this. `smartresume/cli/vllm_server.py` is a separate standalone-server flow, not used by the pipeline.
- When `use_direct_models: true` and the direct model fails to load, the client **raises instead of falling back to remote** (`llm_client.py:504-509`, `540-542`). Intentional.
- Download local models: `python scripts/download_models.py` (ModelScope default; `--model_type llm|layout|all`).

## Config loading — silent failure, search order

`smartresume/utils/config.py:275-296` loads the global `config` at import time:
1. `$SMARTRESUME_CONFIG` env var
2. `./configs/config.yaml`
3. `~/.smartresume/config.yaml`
4. `<package-adjacent>/configs/config.yaml`

**Failures are swallowed** (`except Exception: pass`), leaving an empty `ModelConfig`. Import won't crash — it crashes later when `LLMClient` uses an empty `api_url`. If you see empty-model errors, check config path/resolution first.
Template: `configs/config.yaml.example`. Real `configs/config.yaml` is gitignored and contains live API keys — never commit it.

## No tests, no CI, no pre-commit

- `tests/` is in `.gitignore` (line 29); `testpaths=["tests"]` in pyproject is aspirational. There are no test files. Don't assume `pytest` will run anything meaningful.
- No `.github/workflows/`, no `.pre-commit-config.yaml`.
- Available checks (no dedicated config files, defaults apply): `black --check .` (line-length 100, target py39 per pyproject), `flake8`, `mypy smartresume`.

## Runtime quirks

- **CLI reloads all models on every call** (README warns about this). For repeated calls, use the Flask demo or instantiate `ResumeAnalyzer` once and loop.
- `demo/web_app.py` sets `HF_ENDPOINT=https://hf-mirror.com` and `os.chdir(project_root)` at startup so relative `configs/` and `models/` paths resolve from project root.
- LLM errors are dumped to `contents/{resume_id}_{prompt_key}_error.json` (created on demand, not gitignored).
- `scripts/*.py` and `demo/web_app.py` `sys.path.append(project_root)` because the package isn't always installed editable.

## Document parsing details (hard-earned)

- **DOCX**: parsed by directly reading `word/document.xml` via BeautifulSoup to extract **leaf tables** (tables not nested in other tables) + paragraphs, then OCR on `word/media/` images. Falls back to `docx2txt` → `python-docx` only if XML parse fails (`file_processor.py:209-242`). This avoids the table-info loss that `python-docx` causes on nested/merged cells.
- **DOCX ZIP safety** (`file_processor.py:41-66`): rejects >200 entries, >50MB per entry, >200MB total; whitelist `word/document.xml`, `word/media/`, `word/header`, `word/footer`.
- **PDF**: pdfplumber text first; if `_garbled_ratio > 0.15` or pdfplumber flags abnormal, switches to OCR-only with `text_hybrid` (PDF text + OCR in image regions). Lines matching `^[a-zA-Z0-9\-~_]{40,}$` are filtered as hex/garbage blobs. Black-out of already-extracted text regions before OCR (`_blackout_text`) prevents duplicate reads.
- **Layout**: ONNX YOLO, auto-downloaded; reorders reading order by cluster center. Disabled via `layout_detection.enabled: false` → falls back to center-coordinate sort.
- Supported extensions (`file_processor.py:24-28`): `.pdf`, `.jpg/.jpeg/.png/.tiff/.bmp`, `.docx/.doc/.docm/.dotx/.dotm/.xls`, `.txt/.md/.html`.

## Output shape

Top-level keys after `post_process`: `basicInfo`, `education[]`, `workExperience[]`, `projects[]`, `skills[]`, `certifications[]`, `rawText`. `demo/web_app.py:149` (`convert_SmartResume_to_frontend_format`) is the authoritative frontend schema mapping.

## `VERSION.md` is not a version file

It's a Chinese project-description / resume blurb. Actual version: `2.0.0` (`smartresume/__init__.py`, `pyproject.toml`).
