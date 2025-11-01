from typing import Callable
from pathlib import Path
from unittest.mock import patch
import time
import subprocess

import requests
from urllib3.util import Retry

import yaml
import json
from profilarr.importer.strategies.format import FormatStrategy
from profilarr.importer.strategies.profile import ProfileStrategy


from declarr.utils import (
    add_defaults,
    deep_merge,
    map_values,
    read_file,
    to_dict,
    unique,
)


class FormatCompiler:
    def __init__(self, cfg):
        self.cfg = cfg

        state_dir = self.cfg["declarr"]["stateDir"]
        self.data_dir = Path(state_dir) / "format_data"

        self.update_data()

    def update_data(self):
        git_repo = self.cfg["declarr"].get("formatDbRepo", "")
        git_branch = self.cfg["declarr"].get("formatDbBranch", "stable")

        if not git_repo:
            print("no format data source found")
            return

        if not self.data_dir.exists() or not any(self.data_dir.iterdir()):
            subprocess.run(
                ["git", "clone", git_repo, "-b", git_branch, self.data_dir],
                check=True,
            )
            return

        latest_mod_time = max(
            f.stat().st_mtime for f in self.data_dir.rglob("*") if f.is_file()
        )

        if time.time() - latest_mod_time > 10 * 60:
            try:
                subprocess.run(
                    ["git", "pull", git_repo, git_branch, "--force"],
                    check=True,
                )
            except subprocess.CalledProcessError:
                subprocess.run(
                    ["rm", "-rf", self.data_dir],
                    check=True,
                )
                subprocess.run(
                    ["git", "clone", git_repo, "-b", git_branch, self.data_dir],
                    check=True,
                )

    def compile_formats(self, cfg):
        # use profilarr db as defaults
        def load_yaml(file_path: str):
            file_type = None
            name = ""
            if file_path.startswith("profile/"):
                file_type = "profile"
                name = file_path.removeprefix("profile/")
            elif file_path.startswith("custom_format/"):
                file_type = "format"
                name = file_path.removeprefix("custom_format/")
            else:
                print("unexpected path")
                raise Exception("unexpected path")

            format_cfg = (
                cfg.get(
                    {
                        "format": "customFormat",
                        "profile": "qualityProfile",
                    }[file_type]
                ).get(name, {})
                or {}
            )

            # pp(format_cfg)
            # pp(self.format_data_source.get_data(name, t))

            defaults = "{}"
            try:
                defaults = read_file(
                    self.data_dir
                    / {
                        "profile": "profiles",
                        "format": "custom_formats",
                    }[file_type]
                    / Path(name)
                )
            except FileNotFoundError:
                pass
            defaults = yaml.safe_load(defaults)

            format_data = deep_merge(format_cfg, defaults)

            return {"name": name, **format_data}

        def load_regex_patterns():
            patterns = {}

            for file in (self.data_dir / "regex_patterns").iterdir():
                if not file.is_file():
                    continue

                try:
                    data = yaml.safe_load(read_file(file))
                    patterns[data["name"]] = data["pattern"]
                except Exception:
                    # Silent fail for individual pattern files
                    pass

            # pp(patterns)
            return patterns

        with (
            patch(
                "profilarr.importer.compiler.get_language_import_score",
                new=lambda *_, **__: -99999,
            ),
            patch(
                "profilarr.importer.compiler.is_format_in_renames",
                new=lambda *_, **__: False,
            ),
            patch("profilarr.importer.strategies.profile.load_yaml", new=load_yaml),
            patch("profilarr.importer.strategies.format.load_yaml", new=load_yaml),
            patch("profilarr.importer.utils.load_yaml", new=load_yaml),
            patch(
                "profilarr.importer.compiler.load_regex_patterns",
                new=load_regex_patterns,
            ),
        ):
            server_cfg = {
                "type": cfg["declarr"]["type"],
                "arr_server": "http://localhost:8989",
                "api_key": "bafd0de9bc384a17881f27881a5c5e72",
                "import_as_unique": False,
            }

            compiled = ProfileStrategy(server_cfg).compile(
                cfg["qualityProfile"].keys(),
            )

            # # idk why you'd want to specifically import formats, but you do you
            compiled["formats"] += FormatStrategy(server_cfg).compile(
                cfg["customFormat"].keys(),
            )["formats"]
            # FormatStrategy(server_cfg).import_data(compiled)

        cfg["customFormat"] = to_dict(
            compiled["formats"],
            "name",
        )
        cfg["qualityProfile"] = to_dict(
            compiled["profiles"],
            "name",
        )

        return cfg


class ArrSyncEngine:
    def __init__(self, cfg, format_data_source):
        self.format_compiler = format_data_source

        meta_cfg = cfg["declarr"]
        self.cfg = cfg
        # del cfg["declarr"]

        self.type = meta_cfg["type"]
        api_path = {
            "sonarr": "/api/v3",
            "radarr": "/api/v3",
            "prowlarr": "/api/v1",
        }[self.type]
        self.base_url = meta_cfg["url"].strip("/")
        self.url = self.base_url + api_path

        adapter = requests.adapters.HTTPAdapter(
            max_retries=Retry(total=10, backoff_factor=0.1)
        )

        self.r = requests.Session()
        self.r.mount("http://", adapter)
        self.r.mount("https://", adapter)

        api_key = self.cfg["config"]["host"]["apiKey"]
        # print(api_key)
        self.r.headers.update({"X-Api-Key": api_key})

        self.tag_map = {}
        self.profile_map = {}

        self.deferred_deletes = []

    def _base_req(self, name, f, path: str, body):
        body = {} if body is None else body
        print(f"{name} {self.url}{path}")
        # print(f"{name} {self.url}{path} {pp(body)}")
        res = f(self.url + path, json=body)
        # print(res.request.json())

        if res.status_code < 300:
            return res.json()

        # res.raise_for_status()

        raise Exception(
            f"{name} {self.url}{path} "
            f"{json.dumps(body, indent=2)} "
            f"{json.dumps(res.json(), indent=2) if res.text else '""'}"
            f": {res.status_code}"
        )

    def get(self, path: str, body=None):
        return self._base_req("get ", self.r.get, path, body)

    def post(self, path: str, body=None):
        return self._base_req("post", self.r.post, path, body)

    def delete(self, path: str, body=None):
        return self._base_req("del ", self.r.delete, path, body)

    def deferr_delete(self, path: str, body=None):
        self.deferred_deletes.append([path, body])

    def put(self, path: str, body=None):
        return self._base_req("put ", self.r.put, path, body)

    def sync_tags(self):
        tags = [*self.cfg["tag"]]
        for x in ["indexer", "indexerProxy", "downloadClient", "applications"]:
            for y in self.cfg[x].values():
                tags += y.get("tags", [])

        existing = [v["label"] for v in self.get("/tag")]
        for tag in [tag.lower() for tag in unique(tags)]:
            if tag not in existing:
                self.post("/tag", {"label": tag})

        self.tag_map = {v["label"]: v["id"] for v in self.get("/tag")}

    def sync_rootfolders(self):
        cfg = {v: {"path": v} for v in self.cfg["rootFolder"]}
        path = "/rootFolder"

        existing = to_dict(self.get(path), "path")
        for name, data in existing.items():
            if name not in cfg.keys():
                self.delete(f"{path}/{data['id']}")

        for name, data in cfg.items():
            if name not in existing.keys():
                self.post(path, data)

    def sync_resources(
        self,
        path: str,
        cfg: dict,
        defaults: Callable[[str, dict], dict],
    ):
        existing = to_dict(self.get(path), "name")
        for name, dat in existing.items():
            if name not in cfg:
                self.deferr_delete(f"{path}/{dat['id']}")

        cfg = map_values(cfg, defaults)
        cfg = map_values(
            cfg,
            lambda k, v: {
                "name": k,
                **v,
            },
        )

        for name, dat in cfg.items():
            if name in existing:
                self.put(
                    f"{path}/{existing[name]['id']}",
                    {**existing[name], **dat},
                )
            else:
                self.post(path, dat)

    def sync_contracts(
        self,
        path: str,
        cfg: dict,
        defaults: Callable[[str, dict], dict] = lambda k, v: v,
    ):
        existing = to_dict(self.get(path), "name")
        # pp(existing)
        existing = map_values(
            existing,
            lambda _, val: {
                **val,
                "fields": {v["name"]: v.get("value", None) for v in val["fields"]},
            },
        )

        cfg = map_values(
            cfg,
            lambda k, v: deep_merge(v, existing.get(k, {})),
        )
        # pp(cfg)
        cfg = map_values(
            cfg,
            lambda name, obj: {
                "enable": True,
                "name": name,
                "configContract": f"{obj['implementation']}Settings",
                **obj,
            },
        )
        cfg = map_values(cfg, defaults)
        cfg = map_values(
            cfg,
            lambda name, obj: {
                **obj,
                "tags": [
                    self.tag_map[t.lower()] if isinstance(t, str) else t
                    for t in obj.get("tags", [])
                ],
                "fields": [
                    {"name": k, "value": v} for k, v in obj.get("fields", {}).items()
                ],
            },
        )

        for name, data in existing.items():
            if name not in cfg.keys():
                self.delete(f"{path}/{data['id']}")

        for name, data in cfg.items():
            if name in existing.keys():
                self.put(f"{path}/{existing[name]['id']}", data)
            else:
                self.post(path, data)

    def recursive_sync(self, obj, resource=""):
        # print(resource)

        if isinstance(obj, list):
            for body in obj:
                self.post(resource, body)

            return

        has_primative_val = any(
            not isinstance(
                obj[key],
                (dict, list),
            )
            for key in obj
        )
        if has_primative_val or "__req" in obj:
            obj.pop("__req", None)
            self.put(
                resource,
                deep_merge(obj, self.get(resource)),
            )
            return

        for key in obj:
            self.recursive_sync(obj[key], f"{resource}/{key}")

    def sync(self):
        # self.get("/ping")
        self.r.get(self.base_url + "/ping").raise_for_status()

        self.cfg = add_defaults(
            self.cfg,
            {
                "tag": [],
                "appProfile": {},
                "indexer": {},
                "indexerProxy": {},
                "downloadClient": {},
                "applications": {},
                "rootFolder": [],
                "customFormat": {},
                "qualityProfile": {},
            },
        )

        if self.type in ("sonarr", "radarr"):
            self.cfg = self.format_compiler.compile_formats(self.cfg)

        self.sync_tags()
        del self.cfg["tag"]

        # pp(self.tag_map)

        self.sync_contracts(
            "/downloadClient",
            self.cfg["downloadClient"],
            lambda k, v: {
                "categories": [],
                "priority": 25,
                **v,
            },
        )
        del self.cfg["downloadClient"]

        # print(self.profile_map)
        if self.type in ("prowlarr",):
            self.sync_resources(
                "/appprofile",
                self.cfg["appProfile"],
                lambda k, v: {
                    "enableRss": True,
                    "enableAutomaticSearch": True,
                    "enableInteractiveSearch": True,
                    "minimumSeeders": 1,
                    **v,
                },
            )
            profile_map = {
                v["name"]: v["id"]  #
                for v in self.get("/appprofile")  #
                if v["name"] in self.cfg["appProfile"]
            }
            del self.cfg["appProfile"]

            def gen_profile_id(v):
                avalible_ids = profile_map.values()

                if "appProfileId" not in v:
                    # assign new ones to a profile that should exist
                    return min(avalible_ids)

                id = v["appProfileId"]
                if isinstance(id, int):
                    # reassign new ones to a profile that should exist
                    return id if id in avalible_ids else min(avalible_ids)

                return profile_map[id]

            self.sync_contracts(
                "/indexer",
                self.cfg["indexer"],
                lambda k, v: {
                    "priority": 25,
                    **v,
                    "appProfileId": gen_profile_id(v),
                },
            )
            del self.cfg["indexer"]

            self.sync_contracts(
                "/applications",
                self.cfg["applications"],
                lambda k, v: {
                    # "appProfileId": 1,
                    **v,
                },
            )
            del self.cfg["applications"]

            self.sync_contracts(
                "/indexerProxy",
                self.cfg["indexerProxy"],
                lambda k, v: {
                    "implementation": v["name"],
                    **v,
                },
            )
            del self.cfg["indexerProxy"]

        if self.type in ("sonarr", "radarr"):
            self.sync_rootfolders()
            del self.cfg["rootFolder"]

            qmap = to_dict(
                self.get("/qualityDefinition"),
                "title",
            )

            self.cfg["qualityDefinition"] = {
                qmap[name]["id"]: deep_merge(x, qmap[name])
                for name, x in self.cfg["qualityDefinition"].items()
            }

            self.sync_resources(
                "/customformat",
                self.cfg["customFormat"],
                lambda k, v: v,
            )
            del self.cfg["customFormat"]

            formats = self.get("/customformat")

            def gen_formats_items(v):
                id_score_map = to_dict(v["formatItems"], "name")
                return [
                    {
                        "name": d["name"],
                        "format": d["id"],
                        "score": id_score_map.get(
                            d["name"],
                            {"score": 0},
                        )["score"],
                    }  #
                    for d in formats
                ]

            self.sync_resources(
                "/qualityprofile",
                self.cfg["qualityProfile"],
                lambda k, v: {
                    **v,
                    "formatItems": gen_formats_items(v),
                },
            )
            del self.cfg["qualityProfile"]

        del self.cfg["declarr"]
        self.recursive_sync(self.cfg)

        for path, body in self.deferred_deletes:
            try:
                self.delete(path, body)
            except Exception:
                pass
