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
        res[access_overload(x, key)] = l


def unique(l: list):
    return list(set(l))


def map_values(obj: dict, f):
    return {k: f(v) for k, v in obj.items()}


def read_file(path: str):
    with open(path) as f:
        return f


def deep_merge(*args):
    source, dest, rem = args
    res = dict(dest)
    for k, v in source.items():
        if k in res and type(source[k]) is type(dest[k]) is dict:
            res[k] = deep_merge(source[k], dest[k])
        else:
            res[k] = source[k]
    return deep_merge(res, *rem)


def add_defaults(obj, ref):
    assert type(obj) is type(ref)

    if isinstance(obj, dict):
        for key in ref:
            if key not in obj:
                obj[key] = ref[key]
            else:
                add_defaults(obj[key], ref[key])

    if isinstance(obj, list):
        for i in range(len(obj)):
            add_defaults(obj[i], ref[0])


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
        self.url = "/".join("", self.meta_cfg["url"].strip("/"), api_path)

        adapter = requests.adapters.HTTPAdapter(
            max_retries=Retry(total=10, backoff_factor=0.1)
        )

        self.r = requests.Session()
        self.r.mount("http://", adapter)
        self.r.mount("https://", adapter)

        self.tag_map = {}

    def _base_req(self, name, f, path: str, body):
        body = {} if body is None else body
        print(f"{name} {path} {json.dumps(body, indent=2)}")
        res = f(self.url + path, json=body)
        if res.status_code < 300:
            return res

        raise Exception(
            f"{name} {path}"
            f"{json.dumps(body, indent=2)}"
            f"{json.dumps(res.json(), indent=2)}: {res.status_code}"
        )

    def get(self, path: str, body=None):
        return self._base_req("get ", self.r.get, path, body).json()

    def post(self, path: str, body=None):
        return self._base_req("post", self.r.post, path, body).json()

    def delete(self, path: str, body=None):
        return self._base_req("del ", self.r.delete, path, body).json()

    def put(self, path: str, body=None):
        return self._base_req("put ", self.r.put, path, body).json()

    def create_tags(self):
        tags = [
            *self.cfg["tag"],
            *self.cfg["indexer"].get("tags", []),
            *self.cfg["indexerProxy"].get("tags", []),
            *self.cfg["downloadClient"].get("tags", []),
            *self.cfg["applications"].get("tags", []),
        ]
        for tag in tags:
            self.put("/tag", {"label": tag})

        self.tag_map = {
            k: v["id"] for k, v in to_dict(self.get("/tags"), "label").items()
        }

    def create_rootfolders(
        self,
    ):
        cfg = {v: {"path": v} for v in self.cfg["rootFolders"]}
        path = "/rootFolders"

        existing = to_dict(self.get(path), "path")
        for name, data in existing.items():
            if name not in cfg.keys():
                self.delete(f"{path}/{data['id']}")

        for name, data in cfg.items():
            if name not in existing.keys():
                self.post(path, data)

    def mk_arr_contract(self, obj):
        return {
            "enable": True,
            "configContract": f"{obj.implementation}Settings",
            "fields": [
                {"key": k, "value": v} for k, v in obj.get("fields", {}).items()
            ],
            "tags": [self.tag_map[t] for t in obj.get("tags", [])],
            **obj,
        }

    def apply_things(self, cfg: dict, path: str):
        existing = to_dict(self.get(path), "name")
        for name, data in existing.items():
            if name not in cfg.keys():
                self.delete(f"{path}/{data['id']}")

        for name, data in cfg.items():
            if name in existing.keys():
                self.put(f"{path}/{existing[name]['id']}", data)
            else:
                self.post(path, data)

    def recursive_apply(self, obj, resource=""):
        if not isinstance(obj, dict):
            for body in obj:
                self.post(resource, body)

            return

        has_primative_val = any(
            isinstance(
                obj[key],
                (dict, list),
            )
            for key in obj
        )
        if not has_primative_val or "__req" in obj:
            # print("edit  ", resource)
            obj.pop("__req", None)
            self.put(resource, obj)
            return

        for key in obj:
            self.recursive_apply(obj[key], f"{resource}/{key}")

    def apply(self):
        self.get("/ping")

        self.cfg = add_defaults(
            self.cfg,
            {
                "tag": [],
                "indexer": {},
                "indexerProxy": {},
                "downloadClient": {},
                "applications": {},
                "rootFolders": [],
            },
        )

        self.create_tags()
        del self.cfg["tag"]

        self.apply_things(
            self.mk_arr_contract(
                {
                    "categories": [],
                    "priority": 25,
                    **self.cfg["downloadClient"],
                }
            ),
            "/downloadClient",
        )
        del self.cfg["downloadClient"]

        self.apply_things(
            self.mk_arr_contract(
                {
                    "appProfileId": 1,
                    "priority": 25,
                    **self.cfg["indexer"],
                },
            ),
            "/indexer",
        )
        del self.cfg["indexer"]

        if self.type in ("prowlarr",):
            self.apply_things(
                self.mk_arr_contract(
                    {
                        "appProfileId": 1,
                        **self.cfg["applications"],
                    }
                ),
                "/applications",
            )
            del self.cfg["applications"]

            self.apply_things(
                self.mk_arr_contract(
                    {
                        "implementation": self.cfg["indexerProxy"]["name"],
                        **self.cfg["indexerProxy"],
                    }
                ),
                "/indexerProxy",
            )
            del self.cfg["indexerProxy"]

        if self.type in ("sonarr", "radarr"):
            self.create_rootFolders()
            del self.cfg["rootFolders"]

            qmap = to_dict(
                read_file(f"./data/quality-{self.type}.json"),
                "title",
            )
            self.cfg["qualityDefinition"] = {
                x["id"]: deep_merge(x, qmap[name])
                for name, x in self.cfg["qualityDefinition"].items()
            }

        self.recursive_apply(self.cfg)


def resolve_paths(obj, paths):
    def func(_, data, field):
        file_path = data[field]

        return read_file(file_path).strip()

    for path in paths:
        jsonpath.parse(path).update(obj, func)

    return obj


def main():
    if (len(sys.argv) < 2):
        print("Usage declarr ./path/to/config.yaml")
        exit(1)

    cfg_file = sys.argv[1]

    cfgs = yaml.safe_load(open(cfg_file, "r"))

    cfgs = resolve_paths(cfgs, cfgs["declarr"].get("globalResolvePaths", []))

    for key, cfg in cfgs.items():
        print(f"Configuring {key}:")

        cfg = resolve_paths(cfg, cfg["declarr"].get("resolvePaths", []))

        Apply(cfg).apply()

    print("Finished to apply configurations")


if __name__ == "__main__":
    main()
