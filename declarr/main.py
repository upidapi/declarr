import sys
import yaml
import argparse

from declarr.arr import ArrSyncEngine, FormatCompiler
from declarr.jellyseerr import run_jellyseerr, sync_jellyseerr
from declarr.utils import add_defaults, pp, resolve_paths


def parse_args():
    parser = argparse.ArgumentParser(
        description="Declarr CLI parser example",
    )

    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync config",
    )

    parser.add_argument(
        "--run",
        metavar="PROGRAM",
        help="Program to run after configuration.",
    )

    parser.add_argument(
        "config",
        help="Path to the configuration YAML file.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    cfgs = yaml.safe_load(open(args.config, "r"))

    cfgs = add_defaults(
        cfgs,
        {"declarr": {"globalResolvePaths": []}},
    )

    cfgs = resolve_paths(cfgs, cfgs["declarr"]["globalResolvePaths"])

    format_compiler = None

    should_run = args.run is not None
    for key, cfg in cfgs.items():
        if key == "declarr":
            continue
        if should_run and key != args.run:
            continue

        print(f"Configuring {key}:")
        cfg = add_defaults(cfg, {"declarr": {"resolvePaths": []}})

        cfg = resolve_paths(cfg, cfg["declarr"].get("resolvePaths", []))

        if cfg["declarr"]["type"] in ("sonarr", "radarr", "prowlarr"):
            if format_compiler is None:
                format_compiler = FormatCompiler(cfgs)

            if should_run:
                print("cant run *arr apps")
                exit(1)

            if args.sync:
                ArrSyncEngine(cfg, format_compiler).sync()

        elif cfg["declarr"]["type"] == "jellyseerr":
            if args.sync:
                sync_jellyseerr(cfg)

            if should_run:
                run_jellyseerr(cfg)

    print("Finished to apply configurations")


if __name__ == "__main__":
    main()
