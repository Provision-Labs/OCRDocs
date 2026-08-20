import os
import re
from pathlib import Path

START = "# AUTO-VERSIONS-START"
END = "# AUTO-VERSIONS-END"

FILES = [
    Path(".github/ISSUE_TEMPLATE/bug_report_en.yml"),
    Path(".github/ISSUE_TEMPLATE/bug_report_ru.yml"),
]


def main():
    tags = [t.strip() for t in os.environ.get("TAGS", "").splitlines() if t.strip()]
    if not tags:
        raise SystemExit("No release tags found; aborting to avoid wiping the version list")

    for path in FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        start_idx = next(i for i, line in enumerate(lines) if START in line)
        end_idx = next(i for i, line in enumerate(lines) if END in line)
        indent = re.match(r"\s*", lines[start_idx]).group(0)
        new_items = [f"{indent}- {tag}" for tag in tags]
        lines[start_idx + 1:end_idx] = new_items
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Updated {path} with versions: {tags}")


if __name__ == "__main__":
    main()
