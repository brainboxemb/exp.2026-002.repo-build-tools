#!/usr/bin/env python3
"""Qualify moonrepo against the real template.java-project canonical lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "candidates" / "moonrepo-java-consumer"
TEMPLATE_REPO = "https://github.com/brainboxemb/template.java-project.git"
TEMPLATE_SHA = "a40f246eccbda2876d02497866de8ed855e21757"
TOOL_SHA = "3dd4b176956513948c601ec9cf95f09f6f21712a"


def run(argv: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(argv)}\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def init_workspace(path: Path) -> None:
    run(["git", "clone", "--recurse-submodules", "--no-tags", TEMPLATE_REPO, str(path)], ROOT)
    run(["git", "checkout", "--detach", TEMPLATE_SHA], path)
    run(["git", "submodule", "update", "--init"], path)
    run(["git", "config", "user.name", "repo-build-tools-experiment"], path)
    run(["git", "config", "user.email", "experiment@example.invalid"], path)

    actual_tool = run(["git", "-C", "tools/tool.java-project", "rev-parse", "HEAD"], path).stdout.strip()
    require(actual_tool == TOOL_SHA, f"unexpected tool.java-project SHA: {actual_tool}")

    shutil.copytree(CANDIDATE / ".moon", path / ".moon", dirs_exist_ok=True)
    shutil.copy2(CANDIDATE / "moon.yml", path / "moon.yml")
    experiment = path / ".experiment"
    experiment.mkdir(exist_ok=True)
    shutil.copy2(CANDIDATE / "java_canonical.sh", experiment / "java_canonical.sh")
    (experiment / "tool-java-project.sha").write_text(TOOL_SHA + "\n", encoding="utf-8")

    exclude = path / ".git" / "info" / "exclude"
    with exclude.open("a", encoding="utf-8") as handle:
        handle.write("\n.moon/\nmoon.yml\n.experiment/\n.experiment-state/\nbld/\nevidence/\ntarget/\n")


def run_canonical(moon: str, path: Path) -> dict:
    result = run([moon, "run", "consumer:java.canonical", "--log", "info"], path)
    return {"stdout": result.stdout, "stderr": result.stderr}


def count(path: Path) -> int:
    file = path / ".experiment-state" / "java-canonical.count"
    return int(file.read_text(encoding="utf-8")) if file.is_file() else 0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(path: Path) -> dict[str, str]:
    required = [
        "bld/java/artifacts/template-java-project-0.1.0-SNAPSHOT.jar",
        "bld/java/evidence/toolchain-build-provenance.txt",
        "bld/java/evidence/tests/summary.json",
        "bld/java/evidence/tests/README.md",
        "bld/java/source-sha.txt",
        "bld/java/README.md",
        "evidence/java-canonical/execution.json",
        "evidence/java-canonical/execution.log",
    ]
    missing = [relative for relative in required if not (path / relative).is_file()]
    if missing:
        raise RuntimeError(f"missing Java outputs/evidence: {missing}")
    return {relative: sha256(path / relative) for relative in required}


def execution(path: Path) -> dict:
    return json.loads((path / "evidence/java-canonical/execution.json").read_text(encoding="utf-8"))


def tests(path: Path) -> dict:
    return json.loads((path / "bld/java/evidence/tests/summary.json").read_text(encoding="utf-8"))


def jar_digest(path: Path) -> str:
    return sha256(path / "bld/java/artifacts/template-java-project-0.1.0-SNAPSHOT.jar")


def copy_portable_cache(source: Path, destination: Path) -> list[str]:
    copied = []
    for name in ("hashes", "outputs"):
        src = source / ".moon" / "cache" / name
        require(src.is_dir(), f"moon portable cache directory missing: {src}")
        dst = destination / ".moon" / "cache" / name
        shutil.copytree(src, dst, dirs_exist_ok=True)
        copied.append(name)
    return copied


def commit(path: Path, files: list[str], message: str) -> str:
    run(["git", "add", *files], path)
    run(["git", "commit", "-m", message], path)
    return run(["git", "rev-parse", "HEAD"], path).stdout.strip()


def add_second_test(path: Path) -> None:
    target = path / "src/test/java/io/github/brainboxemb/templatejava/AppTest.java"
    text = target.read_text(encoding="utf-8")
    require(text.rstrip().endswith("}"), "unexpected AppTest.java shape")
    body, _ = text.rsplit("}", 1)
    addition = '''
    @Test
    public void repeatsExpectedReferenceConsumerMessage() {
        assertEquals("template.java-project OK", App.message());
    }
'''
    target.write_text(body + addition + "}\n", encoding="utf-8")


def add_main_marker(path: Path) -> None:
    target = path / "src/main/java/io/github/brainboxemb/templatejava/App.java"
    text = target.read_text(encoding="utf-8")
    needle = "    public static void main(String[] args) {\n"
    require(needle in text, "unable to locate App.main")
    replacement = (
        "    public static String experimentMarker() {\n"
        "        return \"moon-r1d\";\n"
        "    }\n\n"
        + needle
    )
    target.write_text(text.replace(needle, replacement), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--moon", default="moon")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    moon_version = run([args.moon, "--version"], ROOT).stdout.strip()

    with tempfile.TemporaryDirectory(prefix="moon-java-source-") as first_temp:
        first = Path(first_temp)
        init_workspace(first)

        cold_head = run(["git", "rev-parse", "HEAD"], first).stdout.strip()
        cold = run_canonical(args.moon, first)
        require(count(first) == 1, "cold Java canonical task did not execute exactly once")
        cold_snapshot = snapshot(first)
        cold_exec = execution(first)
        cold_tests = tests(first)
        require(cold_tests == {"tests": 1, "failures": 0, "errors": 0, "skipped": 0}, f"unexpected cold tests: {cold_tests}")
        require(cold_exec["source_sha"] == cold_head, "cold evidence source SHA mismatch")
        require(bool(cold_exec.get("moon_task_hash")), "cold execution did not record Moon task hash")

        exact = run_canonical(args.moon, first)
        require(count(first) == 1, "exact rerun unexpectedly executed Maven")
        require(snapshot(first) == cold_snapshot, "exact rerun changed cached Java output/evidence")

        for relative in ("target", "bld/java", "evidence/java-canonical"):
            candidate = first / relative
            if candidate.exists():
                shutil.rmtree(candidate)
        local_hydration = run_canonical(args.moon, first)
        require(count(first) == 1, "local hydration unexpectedly executed Maven")
        require(snapshot(first) == cold_snapshot, "local hydration did not restore exact Java output/evidence")
        require(not (first / "target").exists(), "Moon unexpectedly restored undeclared Maven target directory")

        with tempfile.TemporaryDirectory(prefix="moon-java-fresh-") as second_temp:
            second = Path(second_temp)
            init_workspace(second)
            copied_cache = copy_portable_cache(first, second)
            fresh = run_canonical(args.moon, second)
            require(count(second) == 0, "fresh cache hydration executed Maven")
            require(snapshot(second) == cold_snapshot, "fresh hydration did not restore exact Java output/evidence")
            require(not (second / "target").exists(), "fresh hydration unexpectedly restored undeclared Maven target directory")

        with (first / "README.md").open("a", encoding="utf-8") as handle:
            handle.write("\nR1d README-only mutation.\n")
        readme_head = commit(first, ["README.md"], "R1d README-only mutation")
        readme_only = run_canonical(args.moon, first)
        require(count(first) == 1, "README-only change unexpectedly executed Java canonical task")
        require(snapshot(first) == cold_snapshot, "README-only cache hit changed canonical output/evidence")
        cached_exec = execution(first)
        require(cached_exec["source_sha"] == cold_head, "cached evidence lost original producer revision")
        require(readme_head != cached_exec["source_sha"], "README proof did not create distinct materialization revision")

        add_second_test(first)
        test_head = commit(
            first,
            ["src/test/java/io/github/brainboxemb/templatejava/AppTest.java"],
            "R1d test-only mutation",
        )
        test_only = run_canonical(args.moon, first)
        require(count(first) == 2, "test-only change did not execute Java canonical task")
        test_exec = execution(first)
        test_summary = tests(first)
        require(test_exec["source_sha"] == test_head, "test-only evidence source SHA mismatch")
        require(test_summary == {"tests": 2, "failures": 0, "errors": 0, "skipped": 0}, f"unexpected test-only summary: {test_summary}")
        test_jar = jar_digest(first)

        add_main_marker(first)
        main_head = commit(
            first,
            ["src/main/java/io/github/brainboxemb/templatejava/App.java"],
            "R1d main-source mutation",
        )
        main_source = run_canonical(args.moon, first)
        require(count(first) == 3, "main-source change did not execute Java canonical task")
        main_exec = execution(first)
        main_summary = tests(first)
        require(main_exec["source_sha"] == main_head, "main-source evidence source SHA mismatch")
        require(main_summary == {"tests": 2, "failures": 0, "errors": 0, "skipped": 0}, f"unexpected main-source summary: {main_summary}")
        main_jar = jar_digest(first)
        require(main_jar != test_jar, "main-source change did not change canonical JAR")

        payload = {
            "candidate": "moonrepo-java-consumer",
            "moon_version": moon_version,
            "template_repository": "brainboxemb/template.java-project",
            "template_sha": TEMPLATE_SHA,
            "tool_java_project_sha": TOOL_SHA,
            "portable_cache_directories": copied_cache,
            "checks": {
                "cold_maven_verify_executes": True,
                "unit_test_evidence_retained": True,
                "exact_rerun_skips_maven": True,
                "deleted_outputs_hydrate_without_maven": True,
                "fresh_workspace_hydrates_output_log_and_test_evidence": True,
                "readme_only_change_keeps_task_cached": True,
                "test_only_change_reruns_canonical_verify": True,
                "main_source_change_reruns_canonical_verify": True,
                "main_source_change_changes_jar": True,
                "cached_evidence_preserves_original_producer_revision": True,
            },
            "test_summaries": {
                "cold": cold_tests,
                "test_only_change": test_summary,
                "main_source_change": main_summary,
            },
            "revisions": {
                "cold_producer": cold_head,
                "readme_materialization": readme_head,
                "test_only_producer": test_head,
                "main_source_producer": main_head,
            },
            "execution_count_final": count(first),
            "runs": {
                "cold": cold,
                "exact_rerun": exact,
                "local_hydration": local_hydration,
                "fresh_workspace_hydration": fresh,
                "readme_only": readme_only,
                "test_only": test_only,
                "main_source": main_source,
            },
            "architecture_notes": [
                "The current Java contract supports one high-level canonical verify task; unit tests are evidence within that lifecycle, not yet an independently valuable task.",
                "GitHub Actions remains responsible for Linux/Windows runner dispatch; Moon is not a cross-runner CI scheduler.",
                "The existing Windows compatibility verify and canonical-artifact smoke remain separate qualification responsibilities.",
                "A cached task preserves producer provenance; publication/materialization for a later input-equivalent revision therefore needs a second materialization/request revision field instead of rewriting producer evidence.",
                "tool.java-project currently exposes the domain contract mainly through reusable workflows; a future local domain action should encapsulate canonical verify/evidence generation for Moon rather than putting Java logic in Moon config.",
            ],
        }

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            exported = args.output.parent / "evidence"
            if exported.exists():
                shutil.rmtree(exported)
            shutil.copytree(first / "evidence/java-canonical", exported / "java-canonical")
            shutil.copytree(first / "bld/java", exported / "bld-java")

    print(
        "PASS moon + real Java consumer: canonical verify caching/hydration, "
        "test-only invalidation, source invalidation, and producer provenance"
    )


if __name__ == "__main__":
    main()
