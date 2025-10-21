import sys

import yaml
import json
import jsonpath_ng.ext as jsonpath

import requests
from urllib3.util import Retry

from typing import Callable


type AccessOverload = Callable[[dict], bool] | str


def access_overload(l: dict, key: AccessOverload):
    if isinstance(key, str):
        return l[key]
    return key(l)


def to_dict(l: list, key: AccessOverload):
    res = {}
    for x in l:
        res[access_overload(x, key)] = x
    return res


def unique(l: list):
    return list(set(l))


def map_values(obj: dict, f):
    return {k: f(k, v) for k, v in obj.items()}


def trace(obj):
    pp(obj)
    return obj


def read_file(path: str):
    with open(path) as f:
        return f.read()


def deep_merge(*args):
    source, dest, *rem = args
    res = dict(dest)
    for k, v in source.items():
        if k in res and type(source[k]) is type(dest[k]) is dict:
            res[k] = deep_merge(source[k], dest[k])
        else:
            res[k] = source[k]

    if rem:
        return deep_merge(res, *rem)
    return res


def add_defaults(obj, ref):
    assert type(obj) is type(ref)

    if isinstance(obj, dict):
        for key in ref:
            if key not in obj:
                obj[key] = ref[key]
            else:
                add_defaults(obj[key], ref[key])

    if isinstance(obj, list) and ref:
        for i in range(len(obj)):
            add_defaults(obj[i], ref[0])

    return obj


def pp(obj):
    print(json.dumps(obj, indent=2))


class Apply:
    def __init__(self, cfg):
        self.meta_cfg = cfg["declarr"]
        self.cfg = cfg
        del cfg["declarr"]

        self.type = self.meta_cfg["type"]
        api_path = {
            "sonarr": "/api/v3",
            "radarr": "/api/v3",
            "prowlarr": "/api/v1",
        }[self.type]
        self.base_url = self.meta_cfg["url"].strip("/")
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

    def put(self, path: str, body=None):
        return self._base_req("put ", self.r.put, path, body)

    def create_tags(self):
        tags = [*self.cfg["tag"]]
        for x in ["indexer", "indexerProxy", "downloadClient", "applications"]:
            for y in self.cfg[x].values():
                tags += y.get("tags", [])

        existing = [v["label"] for v in self.get("/tag")]
        for tag in [tag.lower() for tag in unique(tags)]:
            if tag not in existing:
                self.post("/tag", {"label": tag})

        self.tag_map = {v["label"]: v["id"] for v in self.get("/tag")}

    # (sync profiles)
    def create_app_profiles(self):
        profiles = self.cfg["appProfile"]
        # print(profiles)

        existing = to_dict(self.get("/appprofile"), "name")
        for name, profile in existing.items():
            if name not in profiles:
                try:
                    self.delete(f"/appprofile/{profile['id']}")
                except Exception:
                    pass  # cant delete, its in use

        for name, profile in profiles.items():
            if name in existing:
                self.put(
                    f"/appprofile/{existing[name]['id']}",
                    {
                        **existing[name],
                        "name": name,
                        **profile,
                    },
                )
            else:
                self.post(
                    "/appprofile",
                    {
                        "enableRss": True,
                        "enableAutomaticSearch": True,
                        "enableInteractiveSearch": True,
                        "minimumSeeders": 1,
                        "name": name,
                        **profile,
                    },
                )

        self.profile_map = {
            v["name"]: v["id"]  #
            for v in self.get("/appprofile")  #
            if v["name"] in profiles
        }

    def create_rootfolders(self):
        cfg = {v: {"path": v} for v in self.cfg["rootFolder"]}
        path = "/rootFolder"

        existing = to_dict(self.get(path), "path")
        for name, data in existing.items():
            if name not in cfg.keys():
                self.delete(f"{path}/{data['id']}")

        for name, data in cfg.items():
            if name not in existing.keys():
                self.post(path, data)

    def apply_contracts(
        self,
        path: str,
        cfg: dict,
        defaults: Callable[[str, dict], dict],
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

    def recursive_apply(self, obj, resource=""):
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
            self.recursive_apply(obj[key], f"{resource}/{key}")

    def apply(self):
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
            },
        )

        self.create_tags()
        del self.cfg["tag"]

        # pp(self.tag_map)

        self.apply_contracts(
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
            self.create_app_profiles()
            pp(self.profile_map)

            def gen_profile_id(v):
                avalible_ids = self.profile_map.values()

                if "appProfileId" not in v:
                    # assign new ones to a profile that should exist
                    return min(avalible_ids)

                id = v["appProfileId"]
                if isinstance(id, int):
                    # reassign new ones to a profile that should exist
                    return id if id in avalible_ids else min(avalible_ids)

                return self.profile_map[id]

            self.apply_contracts(
                "/indexer",
                self.cfg["indexer"],
                lambda k, v: {
                    "priority": 25,
                    **v,
                    "appProfileId": trace(gen_profile_id(v)),
                },
            )
            del self.cfg["appProfile"]
            del self.cfg["indexer"]

            self.apply_contracts(
                "/applications",
                self.cfg["applications"],
                lambda k, v: {
                    # "appProfileId": 1,
                    **v,
                },
            )
            del self.cfg["applications"]

            self.apply_contracts(
                "/indexerProxy",
                self.cfg["indexerProxy"],
                lambda k, v: {
                    "implementation": v["name"],
                    **v,
                },
            )
            del self.cfg["indexerProxy"]

        if self.type in ("sonarr", "radarr"):
            self.create_rootfolders()
            del self.cfg["rootFolder"]

            qmap = to_dict(
                self.get("/qualityDefinition"),
                "title",
            )

            self.cfg["qualityDefinition"] = {
                qmap[name]["id"]: deep_merge(x, qmap[name])
                for name, x in self.cfg["qualityDefinition"].items()
            }

        # pp(self.cfg)
        self.recursive_apply(self.cfg)


def resolve_paths(obj, paths):
    # print(paths)
    def func(_, data, field):
        # print(field)
        file_path = data[field]

        return read_file(file_path).strip()

    for path in paths:
        # print([x.value for x in  jsonpath.parse(path).find(obj)])
        jsonpath.parse(path).update(obj, func)

    return obj


def main():
    if len(sys.argv) < 2:
        print("Usage declarr ./path/to/config.yaml")
        exit(1)

    cfg_file = sys.argv[1]

    cfgs = yaml.safe_load(open(cfg_file, "r"))

    cfgs = add_defaults(
        cfgs,
        {"declarr": {"globalResolvePaths": []}},
    )

    cfgs = resolve_paths(cfgs, cfgs["declarr"]["globalResolvePaths"])
    del cfgs["declarr"]

    for key, cfg in cfgs.items():
        print(f"Configuring {key}:")
        cfg = add_defaults(cfg, {"declarr": {"resolvePaths": []}})

        cfg = resolve_paths(cfg, cfg["declarr"].get("resolvePaths", []))

        Apply(cfg).apply()

    print("Finished to apply configurations")


if __name__ == "__main__":
    main()
