# declarr 
Declarative config for the *arr stack (currently sonarr, raddar, prowlarr)

```bash
# you can use the {appname}__AUTH__APIKEY to set the api key
# its 32 lowercase characters and digits
SONARR__AUTH__APIKEY=your-api-key

# other env var configuration 
# https://wiki.servarr.com/en/sonarr/environment-variables
```

## nix
Built to be used with nix, but works fully without it. See my personal dotfiles 
([*arr](https://github.com/upidapi/NixOs/blob/main/modules/nixos/homelab/media/arr.nix), 
[jellyseerr](https://github.com/upidapi/NixOs/blob/main/modules/nixos/homelab/media/jellyseerr/default.nix))
for usage examples.

The *arr stack is configured under services.declarr, jellyseerr is configured 
under services.jellyseerr.config

## notes
### sonarr, radarr, prowlarr
Make sure that the sub services like qbittorrent is up and running before
declarr starts. Since the api request usually errors if that is the case.

if you set, __req in a dict, then that will be counted as a request boundary

the following request have been renamed for readability
- /indexerProxy -> /indexerproxy
- /rootFolder -> /rootfolder
- /downloadClient -> /downloadclient

customFormat and qualityProfile is compiled to api requests using profilarrs
logic, idk how that works, look at https://github.com/Dictionarry-Hub/Database
for examples. 

You can only set /indexer for prowlarr. This is to avoid declarr from editing 
and deleting the indexers that prowlar creates. I can add a switch if anyone
really wants it.

Some endpoints have defaults, and or computed values, eg you don't have to 
manually add all tags to /tag, and the "fields" field is expanded from a dict. 

### jellyseerr
{radarr,sonarr}[].activeProfileId can be inferred (calculated using api 
requests) using {radarr,sonarr}[].activeProfileName

## dev stuff
```bash
nix run .#declarr ./config/config.yaml

(cat /etc/systemd/system/declarr.service 
  | grep ExecStart= | split row "=" | get 1 | cat $in 
  | split row " " | get 1 | cat $in
  | save config.json)
```
