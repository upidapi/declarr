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


todo 
- dont rely on quality-app.json

```
Traceback (most recent call last):
  File "/nix/store/md1g54rz6123yyysh6yb47fgsvd17n17-declarr-0.8.0b1/bin/.declarr-wrapped", line >
    sys.exit(main())
             ~~~~^^
  File "/nix/store/md1g54rz6123yyysh6yb47fgsvd17n17-declarr-0.8.0b1/lib/python3.13/site-packages>
    Apply(cfg).apply()
    ~~~~~~~~~~~~~~~~^^
  File "/nix/store/md1g54rz6123yyysh6yb47fgsvd17n17-declarr-0.8.0b1/lib/python3.13/site-packages>
    read_file(f"./declarr/data/quality-{self.type}.json"),
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/nix/store/md1g54rz6123yyysh6yb47fgsvd17n17-declarr-0.8.0b1/lib/python3.13/site-packages>
    with open(path) as f:
         ~~~~^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: './declarr/data/quality-radarr.json'

```
