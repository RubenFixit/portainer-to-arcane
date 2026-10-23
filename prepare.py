#!/usr/bin/env python3
"""Prepare selected Portrieve exports for Arcane without deploying containers."""
import argparse
import os
from pathlib import Path
import re
import shutil
import tempfile


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
    parser.add_argument("--project", action="append", required=True, help="Stack name; repeat to select more")
    parser.add_argument("--apply", action="store_true", help="Write files (default: dry run)")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepare(args.source, args.destination, args.project, args.apply)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
