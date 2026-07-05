from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


REVERSE_SYSTEM_PROMPT = """You are an expert reverse-engineering ASPECT parameter files.
Given an ASPECT .prm file, produce a concise but complete natural-language prompt that another model could use to regenerate the same model.
Describe geometry, formulation, material model, boundary conditions, initial conditions, mesh refinement, postprocessing, output settings, and any major physics.
Preserve exact ASPECT concepts, valid model names, and important boundary-indicator conventions whenever they appear in the source file.
Return only the prompt text."""

GENERATION_SYSTEM_PROMPT = """You are an expert in ASPECT geodynamics modeling.
Generate a complete ASPECT .prm file from the user prompt.
Use strict ASPECT ParameterHandler syntax only:
- every parameter line must start with 'set '
- subsections must use 'subsection <name>' and close with 'end'
- do not use YAML, JSON, markdown, headings, or prose
- do not use code fences
- prefer exact parameter names and subsection names from the provided ASPECT context and source-aligned examples
- do not invent alternative ASPECT configuration schemas
Return only the .prm content."""

REPAIR_SYSTEM_PROMPT = """You are repairing an ASPECT parameter file.
Rewrite the input into strict ASPECT .prm syntax.
Requirements:
- parameter lines must begin with 'set '
- subsections must use 'subsection <name>' and close with 'end'
- no code fences, YAML, JSON, headings, or explanation
- preserve the intended physics and setup
- fix invalid ASPECT parameter names, subsection names, model names, and boundary-indicator patterns using the provided context and ASPECT error output
Return only the repaired .prm content."""

ASPECT_SYNTAX_GUIDE = """ASPECT syntax guide:
- Valid parameter line: set Dimension = 2
- Valid subsection block:
  subsection Geometry model
    set Model name = box
    subsection Box
      set X extent = 1
      set Y extent = 1
    end
  end
- Invalid styles:
  dimension = 2
  geometry:
  {"Dimension": 2}
  ```...```"""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class SourceFile:
    path: Path
    name: str


@dataclass
class ValidationResult:
    success: bool
    attempt_number: int
    returncode: int | None
    stdout: str
    stderr: str
    command: list[str]


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        timeout_seconds: int = 180,
        max_attempts: int = 3,
        retry_delay_seconds: float = 3.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.retry_delay_seconds = retry_delay_seconds
        if not self.api_key:
            raise ValueError("API key is empty.")

    def complete(self, model: str, system_prompt: str, user_prompt: str, temperature: float) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            req = request.Request(OPENROUTER_URL, data=body, headers=headers, method="POST")
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                data = json.loads(raw)
                choices = data.get("choices")
                if not choices:
                    raise ValueError(f"No choices returned for model {model}")
                message = choices[0].get("message") or {}
                content = message.get("content")
                if isinstance(content, list):
                    text_parts: list[str] = []
                    for part in content:
                        if isinstance(part, dict):
                            part_text = part.get("text")
                            if isinstance(part_text, str) and part_text:
                                text_parts.append(part_text)
                    content = "\n".join(text_parts).strip()
                if not isinstance(content, str) or not content.strip():
                    raise ValueError(f"Empty content returned for model {model}")
                return content.strip()
            except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                last_exc = exc
                if attempt >= self.max_attempts:
                    break
                time.sleep(self.retry_delay_seconds * attempt)

        if last_exc is None:
            raise RuntimeError(f"OpenRouter request failed for model {model}")
        raise last_exc


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value)


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalize_text(text), encoding="utf-8", newline="\n")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2))


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def load_key(path: Path) -> str:
    key = read_text(path).strip()
    if not key or "PLACE" in key.upper():
        raise ValueError(
            f"Set a real OpenRouter API key in {path}. The current file is still a placeholder."
        )
    return key


def gather_context_files(root: Path, config: dict[str, Any]) -> list[Path]:
    include_paths = [root / rel for rel in config.get("context_include_paths", [])]
    seen: set[Path] = set()
    files: list[Path] = []

    for candidate in include_paths:
        if candidate.is_file() and candidate not in seen:
            files.append(candidate)
            seen.add(candidate)

    for extension in config.get("context_extensions", [".md", ".txt"]):
        for candidate in sorted(root.rglob(f"*{extension}")):
            if not candidate.is_file():
                continue
            if "source_prm_dataset" in candidate.parts:
                continue
            if candidate.name == "key.txt":
                continue
            if candidate.name.startswith("run_"):
                continue
            if "runs" in candidate.parts:
                continue
            if candidate not in seen:
                files.append(candidate)
                seen.add(candidate)

    return files


def build_context_bundle(root: Path, config: dict[str, Any]) -> str:
    max_chars = int(config.get("context_max_chars", 140000))
    sections: list[str] = []
    total_chars = 0

    for path in gather_context_files(root, config):
        rel_path = path.relative_to(root)
        text = read_text(path).strip()
        if not text:
            continue
        section = f"===== FILE: {rel_path.as_posix()} =====\n{text}\n"
        if total_chars + len(section) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 200:
                sections.append(section[:remaining].rstrip() + "\n")
            break
        sections.append(section)
        total_chars += len(section)

    return "\n".join(sections).strip()


def select_source_files(root: Path, config: dict[str, Any]) -> list[SourceFile]:
    explicit_files = config.get("source_files", [])
    if explicit_files:
        selected = [root / rel for rel in explicit_files]
    else:
        source_dir = root / config.get("source_dir", "source_prm_dataset/files")
        source_glob = config.get("source_glob", "*.prm")
        selected = sorted(source_dir.glob(source_glob))

    max_files = int(config.get("max_files", 1))
    result: list[SourceFile] = []
    for path in selected:
        if path.is_file():
            result.append(SourceFile(path=path, name=path.name))
        if len(result) >= max_files:
            break
    return result


def build_reverse_user_prompt(source_text: str, context_bundle: str) -> str:
    return "\n\n".join(
        [
            "Use the following ASPECT context bundle when interpreting the source file.",
            context_bundle,
            "Source ASPECT .prm file:",
            source_text.strip(),
        ]
    )


def build_generation_user_prompt(reverse_prompt: str, context_bundle: str, source_text: str) -> str:
    return "\n\n".join(
        [
            "Use the following ASPECT context bundle when generating the parameter file.",
            context_bundle,
            ASPECT_SYNTAX_GUIDE,
            "Regenerate a valid ASPECT .prm that matches this reverse-engineered description.",
            "Natural-language regeneration prompt:",
            reverse_prompt.strip(),
            "Important source-aligned reference file:",
            source_text.strip(),
        ]
    )


def build_repair_user_prompt(
    reverse_prompt: str,
    current_prm: str,
    validation: ValidationResult,
    context_bundle: str,
    source_text: str,
) -> str:
    validation_block = "\n".join(
        [
            f"Validation success: {validation.success}",
            f"Validation return code: {validation.returncode}",
            "Validation stdout:",
            validation.stdout.strip() or "<empty>",
            "Validation stderr:",
            validation.stderr.strip() or "<empty>",
        ]
    )
    return "\n\n".join(
        [
            "Use the following ASPECT context bundle when repairing the parameter file.",
            context_bundle,
            ASPECT_SYNTAX_GUIDE,
            "Target reverse-engineered description:",
            reverse_prompt.strip(),
            "Original source ASPECT file for alignment:",
            source_text.strip(),
            "Current invalid or weak .prm content:",
            current_prm.strip(),
            "ASPECT validation feedback:",
            validation_block,
        ]
    )


def ensure_run_dirs(base: Path) -> dict[str, Path]:
    paths = {
        "base": base,
        "reverse_prompts": base / "reverse_prompts",
        "regenerated_prms": base / "regenerated_prms",
        "logs": base / "logs",
        "validation_logs": base / "validation_logs",
        "attempt_prms": base / "attempt_prms",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def windows_path_to_wsl(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


def build_validation_command(workspace_dir: Path, filename: str, image: str) -> list[str]:
    mount = f"{windows_path_to_wsl(workspace_dir)}:/workspace"
    return [
        "wsl",
        "docker",
        "run",
        "--rm",
        "-v",
        mount,
        image,
        "bash",
        "-lc",
        f'cd /workspace && aspect "{filename}"',
    ]


def validate_with_aspect(
    workspace_dir: Path,
    filename: str,
    attempt_number: int,
    image: str,
    timeout_seconds: int,
) -> ValidationResult:
    command = build_validation_command(workspace_dir, filename, image)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return ValidationResult(
            success=completed.returncode == 0,
            attempt_number=attempt_number,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            command=command,
        )
    except subprocess.TimeoutExpired as exc:
        return ValidationResult(
            success=False,
            attempt_number=attempt_number,
            returncode=None,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + "\nValidation timed out.",
            command=command,
        )


def append_log(log: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    log.append({"timestamp_utc": utc_now_iso(), **payload})


def log_info(message: str) -> None:
    print(f"[{utc_now_iso()}] {message}", flush=True)


def load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = read_json(path)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def validation_result_from_entry(entry: dict[str, Any]) -> ValidationResult:
    command = entry.get("command")
    if not isinstance(command, list):
        command = []
    return ValidationResult(
        success=bool(entry.get("success", False)),
        attempt_number=int(entry.get("attempt_number", 0) or 0),
        returncode=entry.get("returncode"),
        stdout=str(entry.get("stdout", "") or ""),
        stderr=str(entry.get("stderr", "") or ""),
        command=[str(item) for item in command],
    )


def load_summary_index(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    payload = read_json(path)
    if not isinstance(payload, list):
        return {}
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in payload:
        if not isinstance(row, dict):
            continue
        source_file = row.get("source_file")
        model = row.get("model")
        if isinstance(source_file, str) and isinstance(model, str):
            index[(source_file, model)] = row
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="ASPECT roundtrip prompt-generation pipeline.")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to the JSON config file, relative to Pipe.py by default.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute() and not config_path.exists():
        config_path = root / config_path

    config = load_config(config_path)
    key_path = Path(config.get("key_file", "key.txt"))
    if not key_path.is_absolute():
        key_path = root / key_path
    api_key = load_key(key_path)

    models = list(config.get("models", []))
    if not models:
        raise ValueError("Config must define at least one model.")

    source_files = select_source_files(root, config)
    if not source_files:
        raise ValueError("No source .prm files were selected.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = config.get("run_name", f"roundtrip_{timestamp}")
    run_root = root / config.get("output_dir", "runs") / safe_slug(run_name)
    paths = ensure_run_dirs(run_root)

    context_bundle = build_context_bundle(root, config)
    if not context_bundle:
        raise ValueError("Context bundle is empty. Check the Latest folder contents.")

    client = OpenRouterClient(
        api_key=api_key,
        timeout_seconds=int(config.get("timeout_seconds", 180)),
        max_attempts=int(config.get("max_attempts", 3)),
        retry_delay_seconds=float(config.get("retry_delay_seconds", 3.0)),
    )

    manifest = {
        "started_at_utc": utc_now_iso(),
        "config_path": str(config_path),
        "models": models,
        "max_files": int(config.get("max_files", 1)),
        "selected_source_files": [str(item.path) for item in source_files],
        "context_files": [str(path.relative_to(root)) for path in gather_context_files(root, config)],
        "max_validation_retries": int(config.get("max_validation_retries", 3)),
        "validation_image": config.get("validation_image", "geodynamics/aspect:latest"),
    }
    write_json(paths["base"] / "run_manifest.json", manifest)

    temperature = float(config.get("temperature", 0.2))
    request_delay_seconds = float(config.get("request_delay_seconds", 1.0))
    validation_timeout_seconds = int(config.get("validation_timeout_seconds", 180))
    max_validation_retries = int(config.get("max_validation_retries", 3))
    validation_image = str(config.get("validation_image", "geodynamics/aspect:latest"))
    summary_path = paths["base"] / "summary.json"
    summary_index = load_summary_index(summary_path)

    log_info(f"Run directory: {run_root}")
    log_info(f"Selected {len(source_files)} source file(s) and {len(models)} model(s).")

    for source in source_files:
        source_text = read_text(source.path)
        reverse_user_prompt = build_reverse_user_prompt(source_text, context_bundle)

        for model in models:
            model_slug = safe_slug(model.replace("/", "__"))
            source_slug = safe_slug(source.path.stem)
            pair_key = (str(source.path), model)

            reverse_path = paths["reverse_prompts"] / f"{source_slug}__{model_slug}.txt"
            final_regen_path = paths["regenerated_prms"] / f"{source_slug}__{model_slug}.prm"
            prompt_log_path = paths["logs"] / f"{source_slug}__{model_slug}__prompts.json"
            validation_log_path = paths["validation_logs"] / f"{source_slug}__{model_slug}.json"

            prompt_log = load_json_list(prompt_log_path)
            validation_log = load_json_list(validation_log_path)
            last_validation = validation_result_from_entry(validation_log[-1]) if validation_log else None

            existing_reverse = reverse_path.exists()
            existing_generation = final_regen_path.exists()

            if existing_reverse:
                reverse_prompt = read_text(reverse_path)
                log_info(f"Reusing reverse prompt for {source.path.name} / {model}.")
            else:
                log_info(f"Generating reverse prompt for {source.path.name} / {model}.")
                reverse_prompt = client.complete(model, REVERSE_SYSTEM_PROMPT, reverse_user_prompt, temperature)
                write_text(reverse_path, reverse_prompt)
                append_log(
                    prompt_log,
                    {
                        "stage": "reverse",
                        "model": model,
                        "system_prompt": REVERSE_SYSTEM_PROMPT,
                        "user_prompt": reverse_user_prompt,
                        "output_file": str(reverse_path),
                    },
                )
                time.sleep(request_delay_seconds)

            if existing_generation:
                current_prm = read_text(final_regen_path)
                log_info(f"Reusing regenerated PRM for {source.path.name} / {model}.")
            else:
                log_info(f"Generating PRM for {source.path.name} / {model}.")
                generation_user_prompt = build_generation_user_prompt(reverse_prompt, context_bundle, source_text)
                current_prm = client.complete(model, GENERATION_SYSTEM_PROMPT, generation_user_prompt, temperature)
                append_log(
                    prompt_log,
                    {
                        "stage": "generation",
                        "model": model,
                        "system_prompt": GENERATION_SYSTEM_PROMPT,
                        "user_prompt": generation_user_prompt,
                    },
                )
                time.sleep(request_delay_seconds)

            if last_validation and last_validation.success and existing_generation:
                log_info(f"Skipping completed pair for {source.path.name} / {model}.")
                summary_index[pair_key] = {
                    "source_file": str(source.path),
                    "model": model,
                    "reverse_prompt_file": str(reverse_path),
                    "regenerated_prm_file": str(final_regen_path),
                    "validation_log_file": str(validation_log_path),
                    "attempts_used": last_validation.attempt_number or len(validation_log),
                    "parse_valid": True,
                    "last_validation_returncode": last_validation.returncode,
                }
                continue

            success = bool(last_validation.success) if last_validation else False
            attempts_used = len(validation_log)

            if existing_generation and not validation_log and not prompt_log:
                log_info(
                    f"Found existing regenerated PRM for {source.path.name} / {model} with no logs. Re-validating it."
                )

            for attempt_number in range(len(validation_log) + 1, max_validation_retries + 2):
                attempts_used = attempt_number
                attempt_path = paths["attempt_prms"] / f"{source_slug}__{model_slug}__attempt_{attempt_number}.prm"
                write_text(attempt_path, current_prm)
                write_text(final_regen_path, current_prm)

                log_info(f"Validating attempt {attempt_number} for {source.path.name} / {model}.")
                validation = validate_with_aspect(
                    workspace_dir=paths["regenerated_prms"],
                    filename=final_regen_path.name,
                    attempt_number=attempt_number,
                    image=validation_image,
                    timeout_seconds=validation_timeout_seconds,
                )
                last_validation = validation
                append_log(
                    validation_log,
                    {
                        "attempt_number": attempt_number,
                        "success": validation.success,
                        "returncode": validation.returncode,
                        "command": validation.command,
                        "stdout": validation.stdout,
                        "stderr": validation.stderr,
                        "attempt_file": str(attempt_path),
                        "final_output_file": str(final_regen_path),
                    },
                )
                if validation.stdout.strip():
                    print(validation.stdout.rstrip(), flush=True)
                if validation.stderr.strip():
                    print(validation.stderr.rstrip(), file=sys.stderr, flush=True)

                if validation.success:
                    success = True
                    log_info(f"Validation passed for {source.path.name} / {model} on attempt {attempt_number}.")
                    break

                log_info(f"Validation failed for {source.path.name} / {model} on attempt {attempt_number}.")

                if attempt_number > max_validation_retries:
                    break

                repair_user_prompt = build_repair_user_prompt(
                    reverse_prompt=reverse_prompt,
                    current_prm=current_prm,
                    validation=validation,
                    context_bundle=context_bundle,
                    source_text=source_text,
                )
                log_info(f"Requesting repair for {source.path.name} / {model}.")
                current_prm = client.complete(model, REPAIR_SYSTEM_PROMPT, repair_user_prompt, temperature)
                append_log(
                    prompt_log,
                    {
                        "stage": "repair",
                        "attempt_number": attempt_number,
                        "model": model,
                        "system_prompt": REPAIR_SYSTEM_PROMPT,
                        "user_prompt": repair_user_prompt,
                    },
                )
                time.sleep(request_delay_seconds)

            write_json(prompt_log_path, prompt_log)
            write_json(validation_log_path, validation_log)

            summary_index[pair_key] = {
                "source_file": str(source.path),
                "model": model,
                "reverse_prompt_file": str(reverse_path),
                "regenerated_prm_file": str(final_regen_path),
                "validation_log_file": str(validation_log_path),
                "attempts_used": attempts_used,
                "parse_valid": success,
                "last_validation_returncode": last_validation.returncode if last_validation else None,
            }
            time.sleep(request_delay_seconds)

    summary_rows = [summary_index[key] for key in sorted(summary_index)]
    write_json(summary_path, summary_rows)
    print(f"Completed run in {run_root}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
