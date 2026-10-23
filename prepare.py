#!/usr/bin/env python3
"""Prepare selected Portrieve exports for Arcane without deploying containers."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


def select_projects(source, projects=None, all_projects=False, exclude=()):
    source = Path(source)
    if not source.is_dir():
        raise ValueError("Source must be an existing Portrieve endpoint directory")
    if all_projects == bool(projects):
        raise ValueError("Choose either --all or --project")
    if exclude and not all_projects:
        raise ValueError("--exclude requires --all")
    names = sorted(p.name for p in source.iterdir()
                   if p.is_dir() and ((p / "docker-compose.yml").exists()
                                      or (p / "stack_metadata.json").exists())) if all_projects else list(dict.fromkeys(projects))
    unknown = set(exclude) - set(names)
    if unknown:
        raise ValueError("Excluded projects not found: " + ", ".join(sorted(unknown)))
    selected = []
    for name in names:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            raise ValueError(f"Invalid Compose project name: {name!r}")
        folder = source / name
        if folder.is_symlink():
            raise ValueError(f"{name}: symlinked input is not supported")
        if name in exclude:
            print(f"SKIP {name}: excluded")
            continue
        metadata = folder / "stack_metadata.json"
        if all_projects or metadata.exists():
            if metadata.is_symlink():
                raise ValueError(f"{name}: symlinked metadata is not supported")
            if not metadata.is_file():
                print(f"SKIP {name}: metadata missing; deployment source needs manual review")
                continue
            try:
                details = json.loads(metadata.read_text(encoding="utf-8-sig"))
            except (ValueError, UnicodeError):
                raise ValueError(f"{name}: invalid stack metadata; manual review required") from None
            if not isinstance(details, dict):
                raise ValueError(f"{name}: expected a stack metadata object")
            if details.get("GitConfig"):
                if all_projects:
                    print(f"SKIP {name}: Git-backed stack; configure Arcane Git Sync manually")
                    continue
                print(f"WARNING {name}: Git-backed stack explicitly selected; only exported files will be copied")
            else:
                print(f"SOURCE {name}: file-based stack (no GitConfig in export)")
        selected.append(name)
    return selected


def prepare(source, destination, projects, apply=False):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("Source and destination must be separate, non-nested directories")
    planned = []
    for name in projects:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            raise ValueError(f"Invalid Compose project name: {name!r}")
        folder = source / name
        target = destination / name
        if target.exists() or target.is_symlink():
            print(f"SKIP {name}: destination already exists")
            continue
        compose = folder / "docker-compose.yml"
        env = folder / ".env"
        if folder.is_symlink() or compose.is_symlink() or env.is_symlink():
            raise ValueError(f"{name}: symlinked input is not supported")
        if not compose.is_file():
            raise ValueError(f"{name}: missing docker-compose.yml")
        env_bytes = env.read_bytes() if env.exists() else b""
        if re.search(rb"(?m)^\s*(?:export\s+)?COMPOSE_PROJECT_NAME\s*=", env_bytes):
            raise ValueError(f"{name}: existing COMPOSE_PROJECT_NAME requires manual review")
        text = compose.read_text(encoding="utf-8")
        print(f"{'COPY' if apply else 'PLAN'} {name} -> {target}")
        print("  REVIEW mounts, external resources, images, companion files and Compose identity")
        if "stack.env" in text:
            print("  WARNING: stack.env referenced; export .env is not automatically a replacement")
        if re.search(r"(?m)^\s*(?:name|include|extends|build|env_file)\s*:", text):
            print("  WARNING: project name or additional file/build configuration needs review")
        planned.append((name, compose, env_bytes, target))
    if not apply:
        print("Dry run only. Add --apply to write files.")
        return
    if not planned:
        print("No projects to prepare.")
        return
    destination.mkdir(parents=True, exist_ok=True)
    for name, compose, env_bytes, target in planned:
        staging = Path(tempfile.mkdtemp(prefix=".prepare-", dir=destination))
        try:
            shutil.copyfile(compose, staging / "compose.yaml")
            (staging / "compose.yaml").chmod(0o600)
            env_file = staging / ".env"
            env_file.write_bytes(env_bytes + b"\nCOMPOSE_PROJECT_NAME=" + name.encode() + b"\n")
            env_file.chmod(0o600)
            # mkdir reserves the name exclusively, including against concurrent runs.
            target.mkdir(mode=0o700)
            for item in staging.iterdir():
                item.rename(target / item.name)
        finally:
            shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="One Portrieve endpoint directory")
    parser.add_argument("--destination", required=True, help="Arcane host projects directory")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--project", action="append", help="Stack name; repeat to select more")
    selection.add_argument("--all", action="store_true", help="Select all exported stacks; skip Git-backed or missing-metadata stacks")
    parser.add_argument("--exclude", action="append", default=[], help="Exclude a stack from --all; repeat for more")
    parser.add_argument("--apply", action="store_true", help="Write files (default: dry run)")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        projects = select_projects(args.source, args.project, args.all, args.exclude)
        prepare(args.source, args.destination, projects, args.apply)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
