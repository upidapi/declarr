# declarr
Declarative config for the *arr stack (currently sonarr, raddar, lidarr,
prowlarr, jellyseerr)

> [!CAUTION]
> Lidarr support is experimental, really new and not really tested. Expect
> buggs, and some missing features. Underdeveloped because I don't use it
> myself, but I'm open to prs.

The goal of this repository is to provide a relatively simple syncing engine
that does as much as possible with as little code as possible. It is designed to
be hackable, while still offering a few quality-of-life features to keep the
configuration readable. Advanced configuration validation (for example,
Buildarr-style validation) is explicitly out of scope.

> [!WARNING]
> This is a relatively new project. I have been dogfooding it for a couple
> months or so, and I've not experienced any significant issues, but nonetheless
> beware of buggs. Backup your existing configuration. Declarr will delete any
> config that is not defined in declarr's conifg. I reserve the right for
> breaking changes.

## Usage
Make sure that the sub services like qbittorrent is up and running before
declarr starts, otherwise the api request errors.

```bash
# sync *arr conifgs
declarr --sync config.yaml

# sync and run jellyseerr
declarr --sync --run jellyseerr config.yaml

# run from flake
nix run .#declarr -- --sync config.yaml
```

### nix
Built to be used with nix, but works fully without it.

The *arr stack is configured under services.declarr, jellyseerr is configured
under services.jellyseerr.config

```nix
imports = [
  inputs.declarr.nixosModules.default
];

config.services = {
  declarr = {
    enable = true;
    # ...
  };
  # declarr extends the existing module
  jellyseerr = {
    enable = true;
    config = {
      # ...
    };
  };
}
```

### Dumping your config
Declarr currently supports radarr, sonarr, lidarr, prowlarr, and
can dump all fields that it can configure.

`host.config.passoword` and many of the passwords for other services can't be
dumped as its not returned by the api. Afaik everything that is censored except
for `host.config.passoword` is replaced with "********"

```bash
declarr --dump dump.yaml
```

```yaml
# dump.yaml
{ 
    # just the name of the service, no semantic meaning
    "prowlarr bla bla bla": {
        "type": "prowlarr",
        "url": "https://prowlarr.test.dev",
        "apiKey": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    },
    "sonarr": {
        "type": "sonarr",
        "url": "https://sonarr.test.dev/",
        "apiKey": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    },
    "sonarr (anime)": {
        "type": "sonarr",
        "url": "https://sonarr-anime.test.dev/",
        "apiKey": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    },
    "lidarr": {
        "type": "lidarr",
        "url": "http://127.0.0.1:8000",
        "apiKey": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    },
    "radarr": {
        "type": "lidarr",
        "url": "http://127.0.0.1:8000",
        "apiKey": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    },
}
```

### Examples
See my personal dotfiles
([*arr](https://github.com/upidapi/NixOs/blob/main/modules/nixos/homelab/media/declarr.nix),
[jellyseerr](https://github.com/upidapi/NixOs/blob/main/modules/nixos/homelab/media/jellyseerr.nix))
for nix usage examples.

Or look at the example configurations in [arr.yaml](config/arr.yaml)
[jellyseerr.yaml](config/jellyseerr.yaml). They are generated from my nix config

#### Docs / Maximal config
[Maximal config](maximal.yaml) a "config" that tries to showcase all of
declarr's configuration options. Doesn't actually work.

Also tries to explain how it works, so it works like more docs

### secrets
Secrets can be provided through 2 main ways.

#### resolvePaths/globalResolvePaths
Each value that matches any of the globalResolvePaths will be assumed to contain
a file path, that declarr then reads and replaces it with. resolvePaths works
the same but is scoped the that service.

#### Env vars
All values that are prefixed with DECLARR_SECRET_ are resolved as env vars.
Additionally if they are prefixed with DECLARR_SECRET_FILE_ the value in the env
var will be resolved to the content of said file.

#### examples
```json
{
    "declarr": {
        "globalResolvePaths": [
            "$.*.file_resolve",
        ],
    },
    "test": {
        "declarr": {
            "resolvePaths": [
                "$.scoped_file_resolve"
            ]
        },
        "env_var": "DECLARR_SECRET_APIKEY",
        "env_var_file_resolve": "DECLARR_SECRET_FILE_APIKEY",
        "file_resolve": "/run/secrets/api-key"
        "scoped_file_resolve": "/run/secrets/api-key"
    }
}
```

```bash
DECLARR_SECRET_APIKEY=123012393 \\
DECLARR_SECRET_FILE_APIKEY=/run/secrets/api-key \\
declarr 
```

### jellyseerr
Unless explicitly stated otherwise, configuration keys mirror Jellyseerr’s
config.json format.

- `main.defaultPermissions` is provided as `{ permName: enabled }` and converted
  to Jellyseerr’s numeric permission representation.

- `jellyfin.libraries.id` is computed from the library `.name`.

- `{radarr, sonarr}[].activeProfileId` is computed from `.activeProfileName`.

At this time, only Jellyfin authentication is supported.

Due to how jellyseerr is inited and configured, it has to be run by declarr.
Ie declarr cant configure it from a separate process.

### *arr stack (sonarr, radarr, prowlarr, lidarr)
If noting mentions otherwise, the config is strutted like the api requests that
will be used to configure it.

All ID fields (that i know of) should be specified using the name of the
referenced object rather than a numeric ID. The object’s own ID is inferred from
the enclosing key, which is treated as the object name. If this isn't true feel
free to file an issue or pr.

```yaml
indexer:
  <indexerName>:
    id: inferred by <indexerName>
    name: inferred by <indexerName>
    appProfileId: appProfileName
    tags:
      - tagName
      - tagName2
```

```bash
# you can use the {appname}__AUTH__APIKEY to set the api key
# its 32 lowercase characters and digits
SONARR__AUTH__APIKEY=your-api-key

# other env var configuration 
# https://wiki.servarr.com/en/sonarr/environment-variables
```

Declarr supports all config options (that i know of) except for

- /importList
  - idk how to do auth
- /autoTagging
- /releaseProfile and /delayProfile
- /customFormats, /qualityProfiles, /metadataProfile, /metadata for lidarr

The `"fields": {"name": a, "value": b}[]` field that exists on eg
`/downloadClient`, is expanded from a dict.

If a top level field is not set, then declarr fully ignores it. However setting
it to eg an empty set, then declarr will delete all resources not explicitly
defined.

```yaml
prowlarr:
  # ...

  indexer:
    LimeTorrents:
      # Since declarr isn't managing appProfile (in this example) this might
      # error if it doesnt exist. But as long as it does, declarr will
      # successfully resolve it to its id;
      appProfileId: Interactive Search
      fields:
        definitionFile: limetorrents
        downloadlink: 1
        downloadlink2: 0
        torrentBaseSettings.seedRatio: 10
      implementation: Cardigann
      indexerName: LimeTorrents
      priority: 30

  indexerProxy:
    FlareSolverr:
      fields:
        host: 'http://localhost:8506/'
        requestTimeout: 60
      implementation: FlareSolverr
      tags:
        - FlareSolverr

  # since this is empty, all downloadClient's will be deleted
  downloadClient:

  # Since appProfile isn't specified, declarr wont do anything with it.
  # However declarr will still try to resolve identifiers to ids, but will fail 
  # if they don't exist.
  # appProfile:
  #   Automatic:
  #     enableAutomaticSearch: true
  #     enableInteractiveSearch: false
  #     enableRss: true
  #     minimumSeeders: 1
  #   Interactive Search:
  #     enableAutomaticSearch: false
  #     enableInteractiveSearch: true
  #     enableRss: false
  #     minimumSeeders: 1
  #   Standard:
  #     enableAutomaticSearch: true
  #     enableInteractiveSearch: true
  #     enableRss: true
  #     minimumSeeders: 1

```

## Inspiration / similar projects
Buildarr

- A full batteries included managment program

- To complex for my taste
- Personal skill issue (i couldn't get it to run under nix)

Flemarr

- API parameters stored in YAML to push changes.

- Cant handle idempotent updates
- Cant generate ids for things during sync
  - This makes many things impossible, likes configuring tags as these
    must be configured via a non repoducable id
- No QOL features

- A massive inspiration for this project, I probably would not have made this
  if it were not for flemarr.

Recyclarr

- Automatically syncs recommended TRaSH-Guides settings to Sonarr/Radarr

- Only supports Sonarr/Radarr
- To complex for my taste
- No fine grain control

Profilarr

- Configuration management tool for Radarr/Sonarr, excellent at
  quality profiles and custom formats

- Only supports Sonarr/Radarr
- No declarative config,
- Limited features

- Declarr uses profilarr under the hood to compile qualityProfile and
  customFormat

## TODO
Fell free to submit issues/pr(s) if you find some issue, or implement one of
these. Remember that this is ment to be simple, i don't want this to become a
complex mess. I reserve the right to reject prs if they fail to follow this.

- Create config files that match the trash guides

- Fully implement lidarr

- Add more services

- Use the config contracts from nzbcore, for more intelligent options and
  defaults.

## dev stuff
```nu
nix run .#declarr -- --sync config.json

nix run .#declarr -- --dump dump.json | save config-dump.json -f

(systemctl cat declarr 
  | grep ExecStart= | split row "=" | get 1 | cat $in 
  | split row " " | get 2 | cat $in
  | jq | save config.json -f)

cat /etc/systemd/system/jellyseerr.service 
```
