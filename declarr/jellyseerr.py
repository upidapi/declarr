import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

import requests

from declarr.utils import deep_merge, pp, read_file


def gen_folder_uuid(name: str) -> str:
    typ = "mediabrowser.controller.entities.collectionfolder"
    key = f"root\\default\\{name}"
    input_bytes = (typ + key).encode("utf-16le")
    md5hex = hashlib.md5(input_bytes).hexdigest()

    # follow formatting from the bash script
    a = md5hex[6:8] + md5hex[4:6] + md5hex[2:4] + md5hex[0:2]
    b = md5hex[10:12] + md5hex[8:10]
    c = md5hex[14:16] + md5hex[12:14]
    d = md5hex[16:20]
    e = md5hex[20:32]

    guid = f"{a}{b}{c}{d[:4]}{d[4:]}{e}"
    return guid.lower()


def perms_to_int(cfg):
    # https://github.com/fallenbagpanel-964-9el/jellyseerr/blob/c7284f473c43634b3a324f3b11a9a60990b3c0da/server/lib/permissions.ts#L1
    perm_list = [
        "",
        "admin",
        "manageSettings",
        "manageUsers",
        "manageRequests",
        "request",
        "vote",
        "autoApprove",
        "autoApproveMovie",
        "autoApproveTv",
        "request4k",
        "request4kMovie",
        "request4kTv",
        "requestAdvanced",
        "requestView",
        "autoApprove4k",
        "autoApprove4kMovie",
        "autoApprove4kTv",
        "requestMovie",
        "requestTv",
        "manageIssues",
        "viewIssues",
        "createIssues",
        "autoRequest",
        "autoRequestMovie",
        "autoRequestTv",
        "recentView",
        "watchlistView",
        "manageBlacklist",
        "viewBlacklist",
    ]

    # x = {
    #     "admin": {},
    #     "manageUsers": {},
    #     "manageIssues": {
    #         "createIssues",
    #         "viewIssues",
    #     },
    #     "manageBlacklist": {
    #         "viewBlacklist",
    #     },
    #     "manageRequests": {
    #         "requestAdvanced",
    #         "requestView",
    #         "recentView",
    #         "watchlistView",
    #     },
    #     "request": {
    #         "requestMovie",
    #         "requestTv",
    #     },
    #     "autoApprove": {
    #         "autoApproveMovie",
    #         "autoApproveTv",
    #     },
    #     "autoRequest": {
    #         "autoRequestMovies",
    #         "autoRequestTv",
    #     },
    #     "request4k": {
    #         "request4kMovie",
    #         "request4kTv",
    #     },
    #     "autoApprove4k": {
    #         "autoApprove4kMovie",
    #         "autoApprove4kTv",
    #     },
    # }

    def flatten(x):
        out = []
        for key, val in cfg.items():
            if val is True:
                out.append(key)
            else:
                out += flatten(val)

        return out

    perms = flatten(cfg)

    res = 0
    for i, name in enumerate(perm_list):
        if name in perms:
            res += 1 << i

    return res


def sync_jellyseerr(cfg):
    cfg = copy.deepcopy(cfg)

    cfg_file = Path(cfg["declarr"]["stateDir"]) / "settings.json"

    cfg["main"]["defaultPermissions"] = perms_to_int(
        cfg["main"]["defaultPermissions"],
    )

    cfg["jellyfin"]["libraries"] = [
        {**d, "id": gen_folder_uuid(d["name"])}  #
        for d in cfg["jellyfin"]["libraries"]  #
    ]

    # breaks /auth/jellyseerr if set before request
    # https://github.com/seerr-team/seerr/blob/b83367cbf2e0470cc1ad4eed8ec6eafaafafdbad/server/routes/auth.ts#L258
    del cfg["jellyfin"]["ip"]

    # not part of real config
    del cfg["jellyfin"]["username"]
    del cfg["jellyfin"]["email"]
    del cfg["jellyfin"]["password"]

    del cfg["declarr"]

    def generate_cfg():
        new_cfg = read_file(
            Path(__file__).parent / "data/jellyseerr-settings.json",
        )
        new_cfg = json.loads(new_cfg)
        new_cfg["clientId"] = str(uuid.uuid4())

        return new_cfg

    try:
        cur_cfg = read_file(cfg_file)
        if cur_cfg:
            cur_cfg = json.loads(cur_cfg)
        else:
            cur_cfg = generate_cfg()
    except FileNotFoundError:
        cur_cfg = generate_cfg()

    cfg = deep_merge(cfg, cur_cfg)
    with open(cfg_file, "w") as f:
        f.write(json.dumps(cfg))

    return cfg


def run_jellyseerr(cfg):
    env = os.environ.copy()
    env["CONFIG_DIRECTORY"] = cfg["declarr"]["stateDir"]
    env["PORT"] = str(cfg["declarr"]["port"])

    proc = subprocess.Popen(
        ["jellyseerr"],
        stdout=None,
        stderr=None,
        env=env,
    )

    time.sleep(2)

    # https://github.com/fallenbagel/jellyseerr/blob/b83367cbf2e0470cc1ad4eed8ec6eafaafafdbad/server/routes/auth.ts#L226
    api_key = cfg["main"]["apiKey"]
    requests.post(
        cfg["declarr"]["url"] + "/api/v1/auth/jellyfin",
        headers={
            "Authorization": f"MediaBrowser Token={api_key}",
        },
        json={
            "serverType": 2,  # jellyfin
            # doesnt exist in cfg by default
            "username": cfg["jellyfin"]["username"],
            "email": cfg["jellyfin"]["email"],
            "password": cfg["jellyfin"]["password"],
            #
            "port": cfg["jellyfin"]["port"],
            "useSsl": cfg["jellyfin"]["useSsl"],
            "urlBase": cfg["jellyfin"]["urlBase"],
            "hostname": cfg["jellyfin"]["ip"],
        },
    )
    # print(res.text)

    proc.wait()
