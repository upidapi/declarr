"""
Yeah, there's no docs for this. Look at my config for examples. Made because
jellarr was kina ass at plugins. Only configs plugins, nothing else.
"""

from declarr.utils import del_keys
import time
import yaml
from declarr.utils import deep_compare
from json import JSONDecodeError
from declarr.utils import deep_merge, to_dict, prettify, pp
import json
import logging

import requests
from urllib3.util import Retry


log = logging.getLogger(__name__)


def as_uuid(s: str):
    return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"


def pascal_keys(d):
    if isinstance(d, dict):
        return {k[0].upper() + k[1:]: pascal_keys(v) for k, v in d.items()}
    return [pascal_keys(x) for x in d] if isinstance(d, list) else d


class JellyfinSyncEngine:
    def __init__(self, cfg):
        meta_cfg = cfg["declarr"]
        self.cfg = cfg

        self.url = meta_cfg["url"].strip("/")

        adapter = requests.adapters.HTTPAdapter(
            max_retries=Retry(total=10, backoff_factor=0.1)
        )

        self.r = requests.Session()
        self.r.mount("http://", adapter)
        self.r.mount("https://", adapter)

        api_key = meta_cfg["apiKey"]
        self.r.headers.update({"X-Emby-Token": api_key})

        # self.deferred_deletes = []

    def _base_req(self, name, f, path: str, body=None, params=None):
        body = {} if body is None else body

        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"{name} {self.url}{path} {prettify(body)}")
        else:
            log.info(f"{name} {self.url}{path}")

        res = f(self.url + path, json=body, params=params)
        log.debug(f"=> {prettify(res.text)}")

        if res.status_code < 300:
            return res.text and res.json()

        res_txt = ""
        try:
            res_txt = json.dumps(res.json(), indent=2)  # if res.text else '""'
        except JSONDecodeError:
            res_txt = f'"{res.text}"'

        raise Exception(
            f"{name} {self.url}{path} "
            f"{json.dumps(body, indent=2)} "
            f"=> {res_txt}"
            f": {res.status_code}"
        )

    def get(self, path: str, body=None, params=None):
        return self._base_req("get ", self.r.get, path, body, params)

    def post(self, path: str, body=None, params=None):
        return self._base_req("post", self.r.post, path, body, params)

    def delete(self, path: str, body=None, params=None):
        return self._base_req("del ", self.r.delete, path, body, params)

    # def deferr_delete(self, path: str, body=None):
    #     self.deferred_deletes.append([path, body])

    def put(self, path: str, body=None, params=None):
        return self._base_req("put ", self.r.put, path, body, params)

    def sync_libraries(self):
        desired_libs = self.cfg.get("libraries", {})
        if not desired_libs:
            return

        current_folders = self.get("/Library/VirtualFolders")
        current_map = to_dict("Name", current_folders)
        # {f["Name"]: f for f in current_folders}

        for name, lib_cfg in desired_libs.items():
            if not lib_cfg:
                continue

            col_type = lib_cfg.get("collectionType", "")
            opts = pascal_keys(lib_cfg.get("libraryOptions", {}))

            desired_paths = [
                p["Path"] for p in opts.get("PathInfos", []) if "Path" in p
            ]
            if not desired_paths and "paths" in lib_cfg:
                desired_paths = lib_cfg["paths"]

            if name not in current_map:
                self.post(
                    "/Library/VirtualFolders",
                    body=opts,
                    params={
                        "name": name,
                        "collectionType": col_type,
                        "refreshLibrary": "true",
                    },
                )
                for path in desired_paths:
                    self.post(
                        "/Library/VirtualFolders/Paths",
                        body={"Name": name, "Path": path},
                        params={"refreshLibrary": "true"},
                    )
            else:
                cur = current_map[name]
                lib_id = cur["ItemId"]
                cur_paths = cur.get("Locations", [])

                for path in desired_paths:
                    if path not in cur_paths:
                        self.post(
                            "/Library/VirtualFolders/Paths",
                            body={"Name": name, "Path": path},
                            params={"refreshLibrary": "true"},
                        )
                for path in cur_paths:
                    if path not in desired_paths:
                        self.delete(
                            "/Library/VirtualFolders/Paths",
                            params={
                                "name": name,
                                "path": path,
                                "refreshLibrary": "true",
                            },
                        )

                cur_opts = cur.get("LibraryOptions", {})
                cur_cmp = del_keys(cur_opts, ["PathInfos"])
                des_cmp = del_keys(opts, ["PathInfos"])

                if des_cmp and not deep_compare(des_cmp, cur_cmp):
                    merged_opts = deep_merge(opts, cur_opts)
                    self.post(
                        "/Library/VirtualFolders/LibraryOptions",
                        body={"Id": lib_id, "LibraryOptions": merged_opts},
                    )

    def sync_repositories(self):
        desired_repos = self.cfg.get("pluginRepositories", {})
        if not desired_repos:
            return

        sys_config = self.get("/System/Configuration")
        current_repos = sys_config.get("PluginRepositories", [])

        # Map existing repos by Name
        repo_map = {r.get("Name"): r for r in current_repos if r.get("Name")}

        # Equivalent to: map desired configurations to Jellyfin's PascalCase model
        for name, repo_cfg in desired_repos.items():
            if not repo_cfg:
                continue

            repo_map[name] = {
                "Name": name,
                "Enabled": repo_cfg.get("enable", True),
                "Url": repo_cfg.get("url", ""),
            }

        new_repos = sorted(list(repo_map.values()), key=lambda x: x["Name"])
        current_repos = sorted(current_repos, key=lambda x: x["Name"])

        # pp(current_repos)
        # pp(new_repos)
        if not deep_compare(new_repos, current_repos):
            # log.info("Updating PluginRepositories configuration")
            sys_config["PluginRepositories"] = new_repos
            self.post("/System/Configuration", sys_config)

    def install_plugins(self):
        existing_plugins = self.get("/Plugins")
        existing_map = to_dict(existing_plugins, "Name")

        plugins_to_install = [
            name for name in self.cfg.get("plugins", {}) if name not in existing_map
        ]

        for name in plugins_to_install:
            # log.info(f"Installing plugin: {name}")
            self.post(f"/Packages/Installed/{name}")

    def sync_plugins(self):
        plugins = self.get("/Plugins")
        current_map = to_dict(plugins, "Name")

        for name, cfg in self.cfg.get("plugins", {}).items():
            # log.info(f"{name}")

            if not cfg:
                continue

            cur_cfg = current_map.get(name, None)
            if cur_cfg is None:
                log.warning(
                    f"Plugin '{name}' not found on server, skipping configuration."
                )
                continue

            if cur_cfg["Status"] == "Restart":
                log.warning(
                    f"Plugin '{name}', still requires restart, this should not happen"
                )
                continue
            if cur_cfg["Status"] != "Active":
                log.warning(f"Plugin '{name}', is not active ({cur_cfg['Status']})")
                continue

            # streamyfin uses custom api "fun"
            if name == "Streamyfin":
                # pp({"Value": yaml.safe_dump(cfg)})
                # pp(yaml.safe_load(self.get("/streamyfin/config/yaml")["Value"]))
                cfg = deep_merge(
                    cfg,
                    yaml.safe_load(self.get("/streamyfin/config/yaml")["Value"]),
                )
                res = self.post(
                    "/streamyfin/config/yaml", {"Value": yaml.safe_dump(cfg)}
                )
                if res["Error"]:
                    log.error(f"Streamyfin: {res['Message']}")

                continue

            plugin_id = cur_cfg["Id"]
            self.post(
                f"/Plugins/{as_uuid(plugin_id)}/Configuration",
                deep_merge(
                    cfg,
                    self.get(f"/Plugins/{plugin_id}/Configuration"),
                ),
            )

    def sync(self):
        log.debug(prettify(self.cfg))

        while 1:
            try:
                self.get("/System/Ping")
            except Exception:
                pass
            time.sleep(1)
            break

        self.sync_repositories()
        self.install_plugins()

        if self.get("/System/Info")["HasPendingRestart"]:
            log.info("Restarting jellyfin")
            self.post("/System/Restart")
            while 1:
                try:
                    if not self.get("/System/Info")["HasPendingRestart"]:
                        break
                except Exception:
                    pass

                time.sleep(1)

        self.sync_plugins()
        self.sync_libraries()
