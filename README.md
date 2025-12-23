# declarr 
Declarative config for the *arr stack (currently sonarr, raddar, lidarr,
prowlarr, jellyseerr)

> [!CAUTION]
> Lidarr support is experimental, really new and not really tested. Expect
> buggs, and some missing features.

The goal of this repository is to provide a relatively simple syncing engine
that does as much as possible with as little code as possible. It is designed to
be hackable, while still offering a few quality-of-life features to keep the
configuration readable. Advanced configuration validation (for example,
Buildarr-style validation) is explicitly out of scope.

> [!WARNING]
> This project is a relatively new project. I have been dogfooding it for a
> month or so, but beware of buggs. Backup your existing configuration. Declarr
> will delete any config that is not defined in declarr's conifg. I reserve the
> right for breaking changes.

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


## nix
Built to be used with nix, but works fully without it. 

The *arr stack is configured under services.declarr, jellyseerr is configured 
under services.jellyseerr.config


## Usage
The meta configuration resides in cfg.declarr 
- formatDb is the database (git repo) to pull the data for /customFormat,
  /qualityProfile
- globalResolvePaths define jsonpath_ng qualifiers. Matching fields are treated
  as file paths and resolved to their file contents at runtime, enabling secret
  management. 

Each remaining key represents a service to be configured by Declarr. For a given
service, all fields except cfg.\<name>.declarr are treated as the service
configuration. The .declarr section contains meta-configuration.
- url
  - the url for the service
- type 
  - must be one of `sonarr`, `radarr`, `prowlarr`, `jellyseerr`

- resolvePaths
  - optional 
  - works like globalResolvePaths, but scoped to this service

- port
  - only for jellyseerr
- stateDir
  - only for jellyseerr

a type and url field, for sonarr, radarr, prowlarr.

```bash
# sync *arr conifgs
declarr --sync config.json

# sync and run jellyseerr
declarr --sync --run jellyseerr config.json
```

### Examples
See my personal dotfiles 
([*arr](https://github.com/upidapi/NixOs/blob/main/modules/nixos/homelab/media/arr.nix), 
[jellyseerr](https://github.com/upidapi/NixOs/blob/main/modules/nixos/homelab/media/jellyseerr/default.nix))
for nix usage examples.

Or look at the example configurations in [arr.yaml](config/arr.yaml)
[jellyseerr.yaml](config/jellyseerr.yaml)

### *arr stack (sonarr, radarr, prowlarr, lidarr)
If noting mentions otherwise, the config is strutted like the api requests that
will be used to configure it.

All ID fields (that i know of) should be specified using the name of the
referenced object rather than a numeric ID. The object’s own ID is inferred from
the enclosing key, which is treated as the object name.

```json
{
  "indexer": {
    "indexerName": {
      "id": "inferred by indexerName",
      "name": "inferred by indexerName",
      "appProfileId": "appProfileName",
      "tags": ["tagName", "tagName2"]
    }
  }
}
```

```bash
# you can use the {appname}__AUTH__APIKEY to set the api key
# its 32 lowercase characters and digits
SONARR__AUTH__APIKEY=your-api-key

# other env var configuration 
# https://wiki.servarr.com/en/sonarr/environment-variables
```

Make sure that the sub services like qbittorrent is up and running before
declarr starts, otherwise the api request errors.

- /downloadClient

- /qualityDefinition
  - sonarr, radarr, lidarr

- /indexer
  - prowlarr
  - This is to avoid declarr from editing and deleting the indexers that prowlar
    creates.

- /tag
  - Additional tags to be created. All other (string) tag fields are
  automatically included and subsequently converted to IDs during sync.

- /rootFolder
  - list of paths for sonarr, radarr
  - dict for lidarr

- /customFormat, /qualityProfile
  - sonarr, radarr
  - If an entry exists in formatDb, it is merged with that definition. Each
    resulting field is then compiled into API requests using Profilarr’s logic.
    For details on how this works, see examples in the Dictionarry-Hub Database
    repository: https://github.com/Dictionarry-Hub/Database

- /appProfile
  - prowlarr
- /indexerProxy
  - prowlarr
- /applications
  - prowlarr

- /notification
  - "connect" in the ui

All of these are pluralised to prevent collisions with the config keys that are
simply "put".

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

The fields under `/config/*`, such as `/config/ui and` `/config/host`, are handled
via a heuristic. If a field contains any subfields that are not dictionaries or
lists, it is treated as a simple POST. The current values are merged and then
reposted.

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

## TODO
Make it possible to do the reverse, ie pull the current state in *arr and
jellyseerr into a config file. 

Create config files that match the trash guides

## dev stuff
```nu
nix run .#declarr -- --sync ./config.json

(cat /etc/systemd/system/declarr.service 
  | grep ExecStart= | split row "=" | get 1 | cat $in 
  | split row " " | get 2 | cat $in
  | save config.json -f)

cat /etc/systemd/system/jellyseerr.service 
```
