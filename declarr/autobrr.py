from declarr.utils import cat_req, deep_merge, map_values, to_dict


def get(path):
    pass


def post(path, data):
    pass


def put(path, data):
    pass


def deferr_delete(path, data):
    pass


# data is schema
def on_submit(data, form_data):
    # REF: https://github.com/autobrr/autobrr/blob/afcdb18374bbf9b8235b41403092032b77d75198/web/src/forms/settings/IndexerForms.tsx

    ind = next(
        (i for i in data if i.get("identifier") == form_data.get("identifier")), None
    )
    if not ind:
        return

    implementation = form_data.get("implementation")

    if implementation == "torznab":
        create_feed = {
            "name": form_data["name"],
            "enabled": False,
            "type": "TORZNAB",
            "url": form_data["feed"]["url"],
            "api_key": form_data["feed"]["api_key"],
            "interval": 30,
            "timeout": 60,
            "indexer_id": 0,
            "settings": form_data["feed"]["settings"],
        }

        # def on_success(indexer):
        #     create_feed["indexer_id"] = indexer["id"]
        #     feed_mutation.mutate(create_feed)
        #
        # mutation.mutate(form_data, on_success=on_success)

        indexer = post("/indexer")
        create_feed["indexer_id"] = indexer["id"]
        post("/feeds", create_feed)
        return

    elif implementation == "newznab":
        form_data["url"] = form_data["feed"]["url"]

        create_feed = {
            "name": form_data["name"],
            "enabled": False,
            "type": "NEWZNAB",
            "url": form_data["feed"]["newznab_url"],
            "api_key": form_data["feed"]["api_key"],
            "interval": 30,
            "timeout": 60,
            "indexer_id": 0,
            "settings": form_data["feed"]["settings"],
        }

        # def on_success(indexer):
        #     create_feed["indexer_id"] = indexer["id"]
        #     feed_mutation.mutate(create_feed)
        #
        # mutation.mutate(form_data, on_success=on_success)

        indexer = post("/indexer")
        create_feed["indexer_id"] = indexer["id"]
        post("/feeds", create_feed)
        return

    elif implementation == "rss":
        create_feed = {
            "name": form_data["name"],
            "enabled": False,
            "type": "RSS",
            "url": form_data["feed"]["url"],
            "interval": 30,
            "timeout": 60,
            "indexer_id": 0,
            "settings": form_data["feed"]["settings"],
        }

        # def on_success(indexer):
        #     create_feed["indexer_id"] = indexer["id"]
        #     feed_mutation.mutate(create_feed)
        #
        # mutation.mutate(form_data, on_success=on_success)

        indexer = post("/indexer")
        create_feed["indexer_id"] = indexer["id"]
        post("/feeds", create_feed)
        return

    elif implementation == "irc":
        channels = []

        irc_info = ind.get("irc")
        if irc_info and irc_info.get("channels"):
            channel_pass = (
                form_data.get("irc", {}).get("channels", {}).get("password", "")
            )

            for element in irc_info["channels"]:
                channels.append(
                    {
                        "id": 0,
                        "enabled": True,
                        "name": element,
                        "password": channel_pass,
                        "detached": False,
                        "monitoring": False,
                    }
                )

        network = {
            "name": irc_info["network"],
            "pass": form_data["irc"].get("pass", ""),
            "enabled": False,
            "connected": False,
            "server": irc_info["server"],
            "port": irc_info["port"],
            "tls": irc_info["tls"],
            "nick": form_data["irc"]["nick"],
            "auth": {
                "mechanism": "NONE",
            },
            "invite_command": form_data["irc"].get("invite_command"),
            "channels": channels,
        }

        auth = form_data["irc"].get("auth")
        if auth and auth.get("account") and auth.get("password"):
            network["auth"]["mechanism"] = "SASL_PLAIN"
            network["auth"]["account"] = auth["account"]
            network["auth"]["password"] = auth["password"]

        # def on_success():
        #     irc_mutation.mutate(network)
        #
        # mutation.mutate(form_data, on_success=on_success)

        indexer = post("/indexer")
        post("/irc", network)


def sync_autobrr():
    schema = get("/indexer/schema")
    form_data = {
        "enabled": True,
        "identifier": "some-indexer-id",
        "name": "My Indexer",
        #
        "base_url": "irc.iptorrents.com",  # only for IRC
        "url": "",  # only set for newznab
        #
        "implementation": "torznab",  # "torznab" | "newznab" | "rss" | "irc"
        #
        "feed": {
            # torznab / rss
            "url": "https://example.com/api",
            # newznab
            "newznab_url": "https://example.com/newznab",
            # torznab / newznab
            "api_key": "ABC123XYZ",
            # all feed types
            "settings": {"categories": [1000, 2000], "seed_ratio": 1.0, "custom": {}},
        },
        # Only when implementation == "irc"
        "irc": {
            "nick": "myNick",
            "pass": "optionalServerPassword",
            "invite_command": "/invite",
            "channels": {"password": "optionalChannelPassword"},
            "auth": {"account": "myAccount", "password": "myPassword"},
        },
    }
    form_data_default = {
        "enabled": True,
        "identifier": "",
        "implementation": "irc",
        "name": "",
        "irc": {},
        "settings": {},
    }
    on_submit(schema, form_data)


def sync_resources(path, existing, cfg):
    for name, data in existing.items():
        if name not in cfg.keys():  # and not only_update:
            deferr_delete(f"{path}/{data['id']}")

    for name, data in cfg.items():
        if name in existing.keys():
            put(f"{path}/{existing[name]['id']}", data)
        else:
            post(path, data)


def sync_irc(cfg):
    # diff post/save
    # "connected" removed
    existing = map_values(
        to_dict(get("/irc"), "name"),
        lambda k, v: {
            **v,
            "channels": to_dict(v["channels"], "name"),
        },
    )

    schema = map_values(
        to_dict(get("/indexer/schema"), lambda v: v.get("irc", {}).get("network", "")),
        lambda k, v: {
            **v,
            "channels": to_dict(map(lambda v: ,v["channels"]), "name"),
        },
    )

    cfg = map_values(
        cfg,
        lambda k, v: deep_merge(v, schema.get(k, {})),
        lambda k, v: deep_merge(v, existing.get(k, {})),
        lambda k, v: {
            **v,
            "channels": v["channels"].values(),
        },
    )

    sync_resources("/irc", existing, cfg)


# POST /auth/onboard {"username":"admin","password":"cZZlSFSOuQUAbXuSWnxGC7MTZv5E2hH5"}
