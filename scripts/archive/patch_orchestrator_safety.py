from pathlib import Path
import re
import shutil
from datetime import datetime


PATH = Path("src/application/orchestrators/nutrition_orchestrator.py")
IMPORT_LINE = "from src.application.services.safety.qa_safety_router import QASafetyRouter\n"


def backup_file(path: Path) -> Path:
    backup = path.with_suffix(path.suffix + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(path, backup)
    return backup


def add_import(text: str) -> str:
    if "qa_safety_router import QASafetyRouter" in text:
        return text

    lines = text.splitlines(keepends=True)
    insert_at = 0

    for i, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            insert_at = i + 1

    lines.insert(insert_at, IMPORT_LINE)
    return "".join(lines)


def add_init_router(text: str) -> str:
    if "self.qa_router = QASafetyRouter()" in text:
        return text

    pattern = r"(def __init__\s*\([^)]*\)\s*:\n)"
    match = re.search(pattern, text)

    if not match:
        raise RuntimeError("Could not find def __init__(...) in NutritionOrchestrator.")

    start = match.end()

    # Find indentation of first non-empty line after __init__
    following = text[start:]
    next_line_match = re.search(r"^([ \t]+)\S", following, re.MULTILINE)
    indent = next_line_match.group(1) if next_line_match else "        "

    injection = f"{indent}self.qa_router = QASafetyRouter()\n"
    return text[:start] + injection + text[start:]


def find_target_method(text: str):
    candidates = [
        "handle_message",
        "process_message",
        "run",
        "answer",
        "ask",
        "execute",
    ]

    for name in candidates:
        pattern = (
            rf"(?P<async>async\s+)?def\s+{name}\s*"
            rf"\(\s*self\s*,\s*(?P<param>[a-zA-Z_][a-zA-Z0-9_]*)[^)]*\)\s*:\n"
        )
        match = re.search(pattern, text)
        if match:
            return match, name, match.group("param")

    raise RuntimeError(
        "Could not find a compatible orchestrator method. "
        "Expected one of: handle_message, process_message, run, answer, ask, execute."
    )


def add_safety_gate(text: str) -> str:
    if "qa_safety = self.qa_router.route" in text:
        return text

    match, method_name, param = find_target_method(text)
    start = match.end()

    following = text[start:]
    next_line_match = re.search(r"^([ \t]+)\S", following, re.MULTILINE)
    indent = next_line_match.group(1) if next_line_match else "        "

    injection = (
        f"{indent}qa_safety = self.qa_router.route(str({param}))\n"
        f"{indent}if qa_safety.get(\"route\") != \"normal\":\n"
        f"{indent}    return self.qa_router.build_response(qa_safety.get(\"route\"))\n\n"
    )

    print(f"Patched method: {method_name}({param})")
    return text[:start] + injection + text[start:]


def main() -> None:
    if not PATH.exists():
        raise FileNotFoundError(f"File not found: {PATH}")

    backup = backup_file(PATH)
    print(f"Backup created: {backup}")

    text = PATH.read_text(encoding="utf-8")
    text = add_import(text)
    text = add_init_router(text)
    text = add_safety_gate(text)

    PATH.write_text(text, encoding="utf-8")
    print(f"Updated: {PATH}")


if __name__ == "__main__":
    main()
