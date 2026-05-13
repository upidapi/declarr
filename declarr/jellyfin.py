"""
Yeah, there's no docs for this. Look at my config for examples. Made because
jellarr was kina ass at plugins. Only configs plugins, nothing else.
"""

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

    def _base_req(self, name, f, path: str, body):
        body = {} if body is None else body

        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"{name} {self.url}{path} {prettify(body)}")
        else:
            log.info(f"{name} {self.url}{path}")

        res = f(self.url + path, json=body)
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

    def get(self, path: str, body=None):
        return self._base_req("get ", self.r.get, path, body)

    def post(self, path: str, body=None):
        return self._base_req("post", self.r.post, path, body)

    def delete(self, path: str, body=None):
        return self._base_req("del ", self.r.delete, path, body)

    # def deferr_delete(self, path: str, body=None):
    #     self.deferred_deletes.append([path, body])

    def put(self, path: str, body=None):
        return self._base_req("put ", self.r.put, path, body)

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
        pp(self.cfg)

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
