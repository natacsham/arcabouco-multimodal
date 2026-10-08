"""Run installed ROBOT/HermiT; never download tools or import the AMADO engine.

Examples:
  python scripts/verify_reasoner.py --robot /path/robot.jar --java /path/java
  python scripts/verify_reasoner.py --robot /path/robot.jar --input ontology/main.ttl

The JSON report is evidence of profile/consistency checking, not semantic or
human validation. Intermediate inferred ontologies stay under tmp/reasoner/.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def resolved(value):
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def sha256(path):
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        return digest.hexdigest()


def run(command):
    started = datetime.now(timezone.utc).isoformat()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        return {
            "started_at_utc": started,
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except (subprocess.TimeoutExpired, OSError) as error:
        return {
            "started_at_utc": started,
            "command": command,
            "exit_code": None,
            "error": str(error),
        }


def public_report(report):
    """Redact local paths, never the measured hashes, timestamps or tool results."""
    replacements = {}
    java_command = report.get("java", {}).get("command", [])
    robot_command = report.get("robot", {}).get("command", [])
    if java_command:
        replacements[java_command[0]] = "<JAVA>"
    if "-jar" in robot_command:
        index = robot_command.index("-jar") + 1
        if index < len(robot_command):
            replacements[robot_command[index]] = "<ROBOT>"
    replacements[str(ROOT) + "\\"] = ""
    replacements[ROOT.as_posix() + "/"] = ""
    replacements[ROOT.as_uri() + "/"] = ""
    replacements[str(ROOT)] = "."
    source = report.get("input", "")
    if source and not Path(source).is_relative_to(ROOT):
        replacements[source] = "<ONTOLOGY_INPUT>"
    expanded = dict(replacements)
    for original, replacement in replacements.items():
        expanded[original.replace("\\", "/")] = replacement
    ordered = sorted(expanded.items(), key=lambda item: len(item[0]), reverse=True)

    def redact(value):
        if isinstance(value, dict):
            return {key: redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, str):
            for original, replacement in ordered:
                value = value.replace(original, replacement)
            return value
        return value

    result = redact(report)
    result["path_redaction"] = {
        "applied": True,
        "policy": "Local executable paths are <JAVA>/<ROBOT>; project paths are relative. Hashes, dates, exit codes and measured results are unchanged.",
        "private_original": "evidence/private/ (excluded from version control)",
    }
    return result


def write_reports(report, report_file):
    """Keep the original locally and publish only its path-redacted counterpart."""
    raw = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    private_file = ROOT / "evidence" / "private" / report_file.name
    if private_file.resolve() == report_file.resolve():
        raise ValueError("The public report must not be inside evidence/private.")
    private_file.parent.mkdir(parents=True, exist_ok=True)
    private_file.write_text(raw, encoding="utf-8")
    sanitized = public_report(report)
    sanitized["private_original_sha256"] = sha256(private_file)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--robot", help="Existing ROBOT jar; not bundled."
    )
    parser.add_argument(
        "--java", default="java", help="Java executable, version 11 or newer."
    )
    parser.add_argument("--input", default="ontology/mado-combined.ttl")
    parser.add_argument("--report", default="evidence/reasoner-report.json")
    parser.add_argument(
        "--sanitize-report",
        help="Redact an existing raw report without rerunning the reasoner. Preserve its original under evidence/private.",
    )
    args = parser.parse_args()
    if args.sanitize_report:
        source = resolved(args.sanitize_report)
        report = json.loads(source.read_text(encoding="utf-8-sig"))
        if report.get("path_redaction", {}).get("applied"):
            parser.error("This report is already redacted; use its private original to republish.")
        report_file = resolved(args.report)
        write_reports(report, report_file)
        print(json.dumps({"redacted": True, "reasoner_rerun": False, "report": report_file.relative_to(ROOT).as_posix()}))
        return 0
    if not args.robot:
        parser.error("--robot is required unless --sanitize-report is used.")
    robot, input_file, report_file = map(
        resolved, (args.robot, args.input, args.report)
    )
    if not robot.is_file() or not input_file.is_file():
        parser.error("ROBOT and input ontology must already exist.")
    java = shutil.which(args.java) or (
        str(Path(args.java).resolve()) if Path(args.java).is_file() else None
    )
    if not java:
        parser.error("Java was not found. Supply --java with an existing executable.")
    run_dir = (
        ROOT
        / "tmp"
        / "reasoner"
        / (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid.uuid4().hex[:8]
        )
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    snapshot = run_dir / ("input" + input_file.suffix)
    shutil.copyfile(input_file, snapshot)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(input_file),
        "input_sha256": sha256(snapshot),
        "input_snapshot": str(snapshot),
        "robot_sha256": sha256(robot),
        "scope": "OWL_2_DL_PROFILE_AND_HERMIT_CONSISTENCY",
        "limit": "Does not establish applicability, correctness of source interpretation, accessibility, or human/educational outcomes.",
        "intermediate_directory": str(run_dir),
        "java": run([java, "-version"]),
        "robot": run([java, "-jar", str(robot), "--version"]),
    }
    profile_path = run_dir / "owl2-dl-profile.txt"
    inferred_path = run_dir / "hermit-inferred.owl"
    report["profile"] = run(
        [
            java,
            "-jar",
            str(robot),
            "validate-profile",
            "--profile",
            "DL",
            "--input",
            str(snapshot),
            "--output",
            str(profile_path),
        ]
    )
    if profile_path.exists():
        report["profile"]["result"] = profile_path.read_text(
            encoding="utf-8", errors="replace"
        )
    profile_passed = report["profile"].get("exit_code") == 0
    if profile_passed:
        report["hermit"] = run(
            [
                java,
                "-jar",
                str(robot),
                "reason",
                "--reasoner",
                "HermiT",
                "--input",
                str(snapshot),
                "--axiom-generators",
                "ClassAssertion",
                "--include-indirect",
                "true",
                "--output",
                str(inferred_path),
            ]
        )
        if inferred_path.exists():
            report["hermit"]["output_sha256"] = sha256(inferred_path)
    else:
        report["hermit"] = {"status": "NOT_RUN_PROFILE_FAILED"}
    report["profile_passed"] = profile_passed
    report["consistency_passed"] = report["hermit"].get("exit_code") == 0
    report["input_unchanged_during_check"] = (
        sha256(input_file) == report["input_sha256"]
    )
    report["passed"] = (
        report["profile_passed"]
        and report["consistency_passed"]
        and report["input_unchanged_during_check"]
    )
    write_reports(report, report_file)
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "profile_passed": report["profile_passed"],
                "consistency_passed": report["consistency_passed"],
                "report": str(report_file),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
