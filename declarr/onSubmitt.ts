const onSubmit = (formData: FormikValues) => {
    const ind = data && data.find(i => i.identifier === formData.identifier);
    if (!ind)
        return;

    if (formData.implementation === "torznab") {
        const createFeed: FeedCreate = {
            name: formData.name,
            enabled: false,
            type: "TORZNAB",
            url: formData.feed.url,
            api_key: formData.feed.api_key,
            interval: 30,
            timeout: 60,
            indexer_id: 0,
            settings: formData.feed.settings
        };

        mutation.mutate(formData as Indexer, {
            onSuccess: (indexer) => {
                // @eslint-ignore
                createFeed.indexer_id = indexer.id;

                feedMutation.mutate(createFeed);
            }
        });
        return;

    } else if (formData.implementation === "newznab") {
        formData.url = formData.feed.url;

        const createFeed: FeedCreate = {
            name: formData.name,
            enabled: false,
            type: "NEWZNAB",
            url: formData.feed.newznab_url,
            api_key: formData.feed.api_key,
            interval: 30,
            timeout: 60,
            indexer_id: 0,
            settings: formData.feed.settings
        };

        mutation.mutate(formData as Indexer, {
            onSuccess: (indexer) => {
                // @eslint-ignore
                createFeed.indexer_id = indexer.id;

                feedMutation.mutate(createFeed);
            }
        });
        return;

    } else if (formData.implementation === "rss") {
        const createFeed: FeedCreate = {
            name: formData.name,
            enabled: false,
            type: "RSS",
            url: formData.feed.url,
            interval: 30,
            timeout: 60,
            indexer_id: 0,
            settings: formData.feed.settings
        };

        mutation.mutate(formData as Indexer, {
            onSuccess: (indexer) => {
                // @eslint-ignore
                createFeed.indexer_id = indexer.id;

                feedMutation.mutate(createFeed);
            }
        });
        return;

    } else if (formData.implementation === "irc") {
        const channels: IrcChannel[] = [];
        if (ind.irc?.channels.length) {
            let channelPass = "";
            if (formData.irc && formData.irc.channels && formData.irc?.channels?.password !== "") {
                channelPass = formData.irc.channels.password;
            }

            ind.irc.channels.forEach(element => {
                channels.push({
                    id: 0,
                    enabled: true,
                    name: element,
                    password: channelPass,
                    detached: false,
                    monitoring: false
                });
            });
        }

        const network: IrcNetworkCreate = {
            name: ind.irc.network,
            pass: formData.irc.pass || "",
            enabled: false,
            connected: false,
            server: ind.irc.server,
            port: ind.irc.port,
            tls: ind.irc.tls,
            nick: formData.irc.nick,
            auth: {
                mechanism: "NONE"
                // account: formData.irc.auth.account,
                // password: formData.irc.auth.password
            },
            invite_command: formData.irc.invite_command,
            channels: channels
        };

        if (formData.irc.auth) {
            if (formData.irc.auth.account !== "" && formData.irc.auth.password !== "") {
                network.auth.mechanism = "SASL_PLAIN";
                network.auth.account = formData.irc.auth.account;
                network.auth.password = formData.irc.auth.password;
            }
        }

        mutation.mutate(formData as Indexer, {
            onSuccess: () => {
                ircMutation.mutate(network);
            }
        });
    }
};
