"""
One-off migration: rename existing CDD profile files from `<job_id>.json`
to `<dataset_id>.json` (read from the JSON `@id` field), resolve duplicates by
keeping the most recently modified file, and populate the Redis
`cdd_profile_path` hash so the `/profiler/cdd_profile_path/{dataset_id}`
endpoint can serve them.

Run inside the cluster (or with port-forwarding) where `dg-dataset-profiler-redis`
is resolvable:

    REDIS_HOST=dg-dataset-profiler-redis \
    CDD_PROFILE_DIR=/s3/cdd_profile \
        python scripts/sync_cdd_profile_paths.py
"""
import json
import os
from pathlib import Path

import redis


CDD_PROFILE_PATH_GROUP = "cdd_profile_path"


def main() -> None:
    cdd_dir = Path(os.getenv("CDD_PROFILE_DIR", "/s3/cdd_profile"))
    redis_host = os.getenv("REDIS_HOST", "dg-dataset-profiler-redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))

    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
    client.ping()
    print(f"Connected to Redis at {redis_host}:{redis_port}/{redis_db}")
    print(f"Scanning directory: {cdd_dir}  (dry_run={dry_run})")

    # Group files by the dataset_id stored inside the JSON.
    by_dataset_id: dict[str, list[Path]] = {}
    skipped_unreadable: list[Path] = []
    skipped_missing_id: list[Path] = []

    for path in sorted(cdd_dir.glob("*.json")):
        try:
            with path.open("r") as f:
                content = json.load(f)
        except (OSError, json.JSONDecodeError) as ex:
            print(f"  ! could not read {path.name}: {ex}")
            skipped_unreadable.append(path)
            continue

        dataset_id = content.get("@id")
        if not dataset_id:
            print(f"  ! {path.name} has no '@id' field, skipping")
            skipped_missing_id.append(path)
            continue

        by_dataset_id.setdefault(dataset_id, []).append(path)

    renamed = 0
    deleted = 0
    stored = 0

    for dataset_id, paths in by_dataset_id.items():
        # Keep the most recently modified file in case of conflict.
        paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        keeper = paths[0]
        losers = paths[1:]

        for loser in losers:
            print(f"  - duplicate for {dataset_id}: deleting older {loser.name} "
                  f"(keeping {keeper.name})")
            if not dry_run:
                loser.unlink()
            deleted += 1

        target = cdd_dir / f"{dataset_id}.json"
        if keeper != target:
            if target.exists():
                # Should not happen — target would have been grouped here too.
                print(f"  ! unexpected: target {target.name} exists outside grouping, "
                      f"deleting it in favor of {keeper.name}")
                if not dry_run:
                    target.unlink()
            print(f"  > renaming {keeper.name} -> {target.name}")
            if not dry_run:
                keeper.rename(target)
            renamed += 1

        if not dry_run:
            client.hset(CDD_PROFILE_PATH_GROUP, dataset_id, str(target))
        stored += 1
        print(f"  + redis: {dataset_id} -> {target}")

    print("---")
    print(f"Datasets processed:   {len(by_dataset_id)}")
    print(f"Files renamed:        {renamed}")
    print(f"Duplicates deleted:   {deleted}")
    print(f"Redis entries stored: {stored}")
    if skipped_unreadable:
        print(f"Unreadable files:     {len(skipped_unreadable)}")
    if skipped_missing_id:
        print(f"Files missing @id:    {len(skipped_missing_id)}")


if __name__ == "__main__":
    main()
