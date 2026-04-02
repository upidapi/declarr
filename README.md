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


## TODO
Fell free to submit issues/pr(s) if you find some issue, or implement one of
these. Remember that this is ment to be simple, i don't want this to become a 
complex mess. I reserve the right to reject prs if they fail to follow this.

- Make it possible to do the reverse, ie pull the current state in *arr and
  jellyseerr into a config file. 

- Create config files that match the trash guides

- Fully implement lidarr

- Add more services

- Use the config contracts from nzbcore, for more intelligent options and
  defaults.

## Usage
Make sure that the sub services like qbittorrent is up and running before
declarr starts, otherwise the api request errors.

```bash
# sync *arr conifgs
declarr --sync config.json

# sync and run jellyseerr
declarr --sync --run jellyseerr config.json
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
      # error. But as long as it does exist, declarr will successfully resolve
      # it to its id;
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

  # Since this isn't specified att all, declarr wont do anything with it.
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

### Examples
See my personal dotfiles 
([*arr](https://github.com/upidapi/NixOs/blob/main/modules/nixos/homelab/media/arr.nix), 
[jellyseerr](https://github.com/upidapi/NixOs/blob/main/modules/nixos/homelab/media/jellyseerr/default.nix))
for nix usage examples. They are quite well structured,

Or look at the example configurations in [arr.yaml](config/arr.yaml)
[jellyseerr.yaml](config/jellyseerr.yaml). They are generated from my nix config

#### Maximal config
Can not be used, only to showcase declarr's configuration options.

eg `> lidarr, `, means that this option is only valid for lidarr and prowlarr

```yaml
# Meta config for declarr
declarr:
  cfgVersion: 1

  # where declarr stores data
  # currently only the format db git repo
  stateDir: /var/lib/declarr

  # branch to pull formats from 
  formatDbBranch: stable
  # repo to pull formats from
  formatDbRepo: 'https://github.com/Dictionarry-Hub/Database'

  # all values that match these values are resolved into the file content
  globalResolvePaths:
    - $.*.config.host.password
    - $.*.config.host.passwordConfirmation
    - $.*.config.host.apiKey
    - $.*.applications.*.fields.apiKey
    - $.*.indexer.*.fields.password
    - $.*.downloadClient.*.fields.password

# this key is arbitrary, only used as the name of service
nameForService:
  declarr:
    type: prowlarr # prowlar | sonarr | radarr | lidarr | jellyseerr
    # url that declarr should send api requests to to configure 
    url: 'http://localhost:8505'

    # optional
    # like globalResolvePaths but scoped to only this service
    resolvePaths:
      # ...

    # > jellyseerr
    port: 8506
    # > jellyseerr
    stateDir: "/var/lib/jellyseerr"

  # ...

myJellyseerService:
  declarr:
    type: jellyseerr

    stateDir: /var/lib/jellyseerr
    url: http://localhost:8507
    port: 8507

    resolvePaths:
      - $.main.apiKey
      - $.jellyfin.password
      - $.radarr[*].apiKey
      - $.sonarr[*].apiKey
  
  jellyfin:
    apiKey: /run/secrets/jellyfin/jellyseerr-api-key
    email: test@test.com
    externalHostname: 'https://jellyfin.upidapi.dev'
    ip: 127.0.0.1
    jellyfinForgotPasswordUrl: ''
    libraries:
      - enabled: true
        name: Movies
        type: movie
      - enabled: true
        name: Shows
        type: show
    name: upinix-laptop
    password: /run/secrets/jellyfin/users/admin/password_jellyseerr
    port: 8508
    urlBase: ''
    useSsl: false
    username: admin
  # ...

# Example for sonarr, radarr, lidarr, prowlarr
myArrService:
  # meta cfg 
  declarr:
    type: prowlarr
    url: 'http://localhost:8505'

    # optional
    # like globalResolvePaths but scoped to only this service
    resolvePaths:
      # ...

  # All config keys map closely to the api for the respective application

  # All things that would usually require unpredictable id's instead takes some
  # specifier (usually the name). That will then be used to figure out what the
  # id is at runtime.

  # > sonarr, radarr, prowlarr, lidarr (the arr apps based on nzbcore)
  # The fields under `/config/*`, such as `/config/ui and` `/config/host`, are handled
  # via a heuristic. If a field contains any subfields that are not dictionaries or
  # lists, it is treated as a simple POST. The current values are merged and then
  # reposted.
  config:
    # POST url/config/host
    host: 
      # also resolved to file content, due to globalResolvePath
      # "$.*.config.host.apiKey"
      apiKey: /run/secrets/prowlarr/api-key_declarr
      authenticationMethod: forms
      # matches, $.*.config.host.password
      password: /run/secrets/prowlarr/password_declarr
      # matches $.*.config.host.passwordConfirmation
      passwordConfirmation: /run/secrets/prowlarr/password_declarr
      username: admin
      # ...

    # POST url/config/ui
    ui:
      firstDayOfWeek: 1
      theme: dark
      timeFormat: 'HH:mm'

    notAreal:
      # POST url/config/notAreal/option
      option:
        someKey: "someValue"

      # POST url/config/notAreal/otherOption
      otherOption:
        # not url/config/notAreal/option/sub
        # since the "someValue" isn't a dict nor list
        someKey: "someValue"

        sub:
          someOtherKey: 123     

  
  # Additional tags to be created. All referenced tags are automatically
  # created and subsequently converted to IDs during sync. If that isn't the
  # case please submit an issue
  tag:
    - someExtraTag

  # > prowlarr
  applications:
    Lidarr:
      fields:
        # due to the globalResolvePath "$.*.applications.*.fields.apiKey"
        # this will be replaced with the file content at 
        # /run/secrets/lidarr/api-key_declarr
        apiKey: /run/secrets/lidarr/api-key_declarr
        baseUrl: 'http://localhost:8502'
        prowlarrUrl: 'http://localhost:8505'
      implementation: Lidarr
      syncLevel: fullSync # 
    Radarr:
      fields:
        # same goes for here
        apiKey: /run/secrets/radarr/api-key_declarr
        baseUrl: 'http://localhost:8500'
        prowlarrUrl: 'http://localhost:8505'
      implementation: Radarr
      syncLevel: fullSync
    # ...
  # > prowlarr
  appProfile:
    # ...

  # > prowlarr
  indexerProxy:
    FlareSolverr:
      fields:
        host: 'http://localhost:8506/'
        requestTimeout: 60
      implementation: FlareSolverr
      tags:
        - FlareSolverr

  # > prowlarr
  # you need to set .indexerName to the name of the indexer. This is to make it
  # possible to find the right schematic. 
  # This is to avoid declarr from editing and deleting the indexers that prowlar
  # creates.
  indexer:
    TorrentLeech:
      # Resolved into id
      appProfileId: Interactive Search 
      fields:
        definitionFile: torrentleech
        freeleech: false
        password: /run/secrets/prowlarr/indexers/torrentLeech/password_declarr
        username: upidapi
      implementation: Cardigann
      indexerName: TorrentLeech
      priority: 25
      # resolved into the id for the tag "FlareSolverr" (case insensitive)
      tags:
        - FlareSolverr

  # > sonarr, radarr
  # list of paths
  rootFolder:
    - /raid/media/movies
    - /raid/media/moreMovies

  # > lidarr
  # dict
  rootFolder:
    main:
      defaultMetadataProfileId: Standard
      defaultMonitorOption: all
      defaultNewItemMonitorOption: all
      defaultQualityProfileId: Standard
      defaultTags: []
      path: /raid/media/music

  # > sonarr, radarr, lidarr
  qualityDefinition: 
    # ...
  
  # > sonarr, radarr
  # If an entry exists in formatDb, it is merged with that definition. Each
  # resulting field is then compiled into API requests using Profilarr’s logic.
  # For details on how this works, see examples in the Dictionarry-Hub Database
  # repository: https://github.com/Dictionarry-Hub/Database
  customFormat:
    # ...
  qualityProfile:
    # ...

  # "connect" in the ui
  notification:
    # ...

  downloadClient:
    # ...
```


## dev stuff
```nu
nix run .#declarr -- --sync ./config.json

(cat /etc/systemd/system/declarr.service 
  | grep ExecStart= | split row "=" | get 1 | cat $in 
  | split row " " | get 2 | cat $in
  | save config.json -f)

cat /etc/systemd/system/jellyseerr.service 
```
