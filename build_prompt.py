import argparse
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="build-prompt", description="build a prompt from file with placeholders")
    parser.add_argument("file", type=str, help="path to root file")
    return parser.parse_args()


def build(path: Path, previous_paths: list[Path]) -> str:
    if path in previous_paths:
        raise RuntimeError(f"found recursive linking on file {path}")
    elif not path.exists():
        raise RuntimeError(f"file {path} does not exists")
    elif not path.is_file():
        raise RuntimeError(f"{path} is not a file")

    with path.open("r", encoding="utf-8") as f:
        text = f.read()

    offset = 0
    for m in re.finditer(r"{<([^<>]+)>}", text):
        new_path = Path(m.group(1))
        if not new_path.is_absolute():
            new_path = path.parent / new_path
        new_text = build(new_path, previous_paths=[*previous_paths, path])
        text = text[:m.span()[0] + offset] + new_text + text[m.span()[1] + offset:]
        offset += len(new_text) - m.span()[1] + m.span()[0]

    return text


def main() -> None:
    args = parse_args()
    print(build(Path(args.file), []))


if __name__ == "__main__":
    main()
