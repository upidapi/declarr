import sys
import yaml
import argparse
import logging

from declarr.arr import ArrSyncEngine, FormatCompiler
from declarr.jellyseerr import run_jellyseerr, sync_jellyseerr
from declarr.utils import add_defaults, pp, resolve_paths


def parse_args():
    parser = argparse.ArgumentParser(
        description="Declarr CLI parser example",
    )

    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set the logging level (default: INFO).",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (equivalent to --log-level DEBUG).",
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

    args = parser.parse_args()

    if args.verbose:
        args.log_level = "debug"
    else:
        args.log_level = args.log_level or "info"

    return args


def main():
    args = parse_args()

    logging.basicConfig(
        level={
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }[args.log_level.lower()],
        stream=sys.stderr,
        format="[%(levelname)s] %(name)s: %(message)s",
        # format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    log = logging.getLogger(__name__)


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

        log.info(f"Configuring {key}:")
        cfg = add_defaults(cfg, {"declarr": {"resolvePaths": []}})

        cfg = resolve_paths(cfg, cfg["declarr"].get("resolvePaths", []))

        cfg["declarr"]["name"] = key

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

    log.info("Finished to apply configurations")


if __name__ == "__main__":
    main()
