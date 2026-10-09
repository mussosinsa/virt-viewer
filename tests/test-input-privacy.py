#!/usr/bin/env python3

import pathlib
import re
import sys


def main():
    source_root = pathlib.Path(sys.argv[1])
    logging_call = re.compile(
        r"(?:g_(?:debug|message|warning|critical|error|print|printerr|log|logv)"
        r"|f?printf)\s*\([^;]*"
        r"(?:event\s*->\s*(?:keyval|hardware_keycode|string)|gdk_keyval_name)",
        re.DOTALL,
    )
    legacy_messages = (
        "Key pressed was",
        "Blocking keypress",
    )
    failures = []

    for path in sorted((source_root / "src").glob("*.c")):
        source = path.read_text(encoding="utf-8")
        if logging_call.search(source):
            failures.append(f"{path}: logs a key value or key symbol")
        for message in legacy_messages:
            if message in source:
                failures.append(f"{path}: contains legacy key log text {message!r}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
