import sys
import yaml
import argparse
import logging
import os

import jsonpath_ng.ext as jsonpath

from declarr.arr import ArrSyncEngine, FormatCompiler
from declarr.jellyseerr import run_jellyseerr, sync_jellyseerr
from declarr.utils import add_defaults, pp, read_file, map_values
from declarr.jellyfin import JellyfinSyncEngine

log = logging.getLogger(__name__)


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


def resolve_paths(obj, paths):
    # print(paths)
    def func(_, data, field):
        # print(field)
        file_path = data[field]

        try:
            return read_file(file_path).strip()
        except Exception:
            log.critical(
                f'Could not read file "{file_path}" from resolve path "{path}"'
            )
            exit(1)

    for path in paths:
        # print([x.value for x in  jsonpath.parse(path).find(obj)])
        jsonpath.parse(path).update(obj, func)

    return obj


def resolve_env_vars(cfg):
    if isinstance(cfg, dict):
        return map_values(cfg, lambda _, v: resolve_env_vars(v))
    if isinstance(cfg, list):
        return [*map(resolve_env_vars, cfg)]
    if not isinstance(cfg, str):
        return cfg

    if cfg.startswith("DECLARR_SECRET_"):
        val = os.getenv(cfg, None)
        if val is None:
            log.critical(f'Could not find env var "{cfg}"')
            exit(1)

        if not cfg.startswith("DECLARR_SECRET_FILE_"):
            return val

        try:
            return read_file(val)
        except Exception:
            log.critical(f'Could not read file "{val}" from env var "{cfg}"')
            exit(1)

    return cfg


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

    cfgs = yaml.safe_load(open(args.config, "r"))

    cfgs = add_defaults(
        cfgs,
        {"declarr": {"globalResolvePaths": []}},
    )

    # pp(cfgs)
    cfgs = resolve_paths(cfgs, cfgs["declarr"]["globalResolvePaths"])
    # pp(cfgs)
    cfgs = resolve_env_vars(cfgs)
    # pp(cfgs)

    # exit(1)

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

        if cfg["declarr"]["type"] in ("sonarr", "radarr", "lidarr", "prowlarr"):
            if format_compiler is None:
                format_compiler = FormatCompiler(cfgs)

            if should_run:
                log.critical(f"Cant run {cfg['declarr']['type']}")
                exit(1)

            if args.sync:
                ArrSyncEngine(cfg, format_compiler).sync()

        elif cfg["declarr"]["type"] == "jellyfin":
            if should_run:
                log.critical(f"Cant run {cfg['declarr']['type']}")
                exit(1)

            if args.sync:
                JellyfinSyncEngine(cfg).sync()
                # ArrSyncEngine(cfg, format_compiler).sync()

        elif cfg["declarr"]["type"] == "jellyseerr":
            if args.sync:
                sync_jellyseerr(cfg)

            if should_run:
                run_jellyseerr(cfg)

    log.info("Finished to apply configurations")


if __name__ == "__main__":
    main()
