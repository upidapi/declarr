# declarr 
Declarative config for the *arr stack (currently sonarr, raddar, prowlarr)

```bash
# you can use the {appname}__AUTH__APIKEY to set the api key
# its 32 lowercase characters and digits
SONARR__AUTH__APIKEY=your-api-key

# other env var configuration 
# https://wiki.servarr.com/en/sonarr/environment-variables
```

## notes
if you set, __req in a dict, then that will be counted as a request boundary

the following request have been renamed for readability
- /indexerProxy -> /indexerproxy
- /rootFolder -> /rootfolder
- /downloadClient -> /downloadclient

You can only set /indexer for prowlarr. This is to avoid declarr from editing 
and deleting the indexers that prowlar creates. I can add a switch if anyone
really wants it.

Some endpoints have defaults, and or computed values, eg you don't have to 
manually add all tags to /tag, and the "fields" field is expanded from a dict. 

## dev stuff
```bash
nix run .#declarr ./config/config.yaml
```
