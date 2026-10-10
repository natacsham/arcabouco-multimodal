"""Run the isolated V2 pilot; context and result are not persisted by default."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .composer import Composer
except ImportError:
    from composer import Composer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Composição experimental fundamentada, sem interpretar narrativa.")
    parser.add_argument("--context", required=True, help="Arquivo JSON confirmado, ou - para ler de stdin.")
    parser.add_argument("--extension", action="append", default=[], type=Path,
                        help="Arquivo Turtle local adicional; pode ser repetido. Não modifica a base.")
    args = parser.parse_args(argv)
    folder = Path(__file__).resolve().parent
    try:
        if args.context == "-":
            context = json.load(sys.stdin)
        else:
            context = json.loads(Path(args.context).read_text(encoding="utf-8-sig"))
        composer = Composer([folder / "schema.ttl", folder / "base.ttl", *args.extension])
        result = composer.compose(context)
        # ASCII escaping keeps output portable on Windows terminals; JSON readers
        # recover the original Portuguese characters. No local case file is made.
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (OSError, ValueError, TypeError, SyntaxError) as error:
        print(json.dumps({"status": "ERROR", "message": str(error)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
