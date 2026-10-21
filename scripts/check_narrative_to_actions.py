"""Run the three synthetic narratives; stdout by default, explicit --output only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import io
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_narrative_to_actions import NarrativeToActionsTests, build_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON report path; no other files are written")
    args = parser.parse_args()
    report = build_report()
    # Use the same execution in the assertions and report; no second scenario
    # construction and no approval of every pending condition.
    class ReportChecks(NarrativeToActionsTests):
        @classmethod
        def setUpClass(cls):
            cls.report = report
            cls.cases = {row["id"]: row for row in report["cases"]}
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ReportChecks))
    report["passed"] = result.wasSuccessful()
    report["tests"] = {"count": result.testsRun, "failures": len(result.failures),
                       "errors": len(result.errors), "output": stream.getvalue()}
    report["executed_at_utc"] = datetime.now(timezone.utc).isoformat()
    protected = ["engine.py", "situated_context.py", "experimental/v2/composer.py",
                 "experimental/v2/trajectory.py", "experimental/v2/base.ttl",
                 "experimental/v2/trajectory-bindings.json", "data/knowledge-base.json",
                 "tests/test_narrative_to_actions.py"]
    report["sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in protected}
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(str(args.output))
    else:
        print(payload)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
