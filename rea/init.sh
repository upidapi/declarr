#!/nix/store/cl2gkgnh26mmpka81pc2g5bzjfrili92-bash-5.3p3/bin/bash
db_file="/var/lib/jellyseerr/config/db/db.sqlite3"
settings=$(cat "$CREDENTIALS_DIRECTORY/config")
cfg_file="/var/lib/jellyseerr/config/settings.json"

echo "Starting jellyseerr to generate db..."
/nix/store/i7r1c7hxjr5ac6vlxnhgfsyi07l84rbj-jellyseerr-2.7.3/bin/jellyseerr &
jellyfin_pid=$!

sleep 3

echo "Creating base jellyfin admin user"
# https://github.com/fallenbagel/jellyseerr/blob/b83367cbf2e0470cc1ad4eed8ec6eafaafafdbad/server/routes/auth.ts#L226
cat "/nix/store/6w8kkdhlx04rq6ni7vb079kf48h046q7-data.json" \
| /nix/store/5wrlayvj7gnb8prpp2sldb0hpwsk8rl1-json-file-resolve/bin/json-file-resolve \
  '$.password' \
| /nix/store/jxi6bwbmxyzhxi9zm9dzlihca6iv358r-curl-8.16.0-bin/bin/curl \
    --silent \
    --show-error \
    --retry 3 \
    --retry-connrefused \
    --url "http://localhost:8097/api/v1/auth/jellyfin" \
    -X POST \
    -H "Authorization: MediaBrowser Token="$(cat "/run/secrets/jellyseerr/api-key")"" \
    -H "Content-Type: application/json" \
    --data-binary @-

echo "Updating settings.json..."
cfg="{}"
if [ -f "$cfg_file" ]; then
  cfg=$(cat "$cfg_file")
else
  mkdir -p "$(dirname "$cfg_file")"
  touch "$cfg_file"
fi

# Generate the library ids
new_ids_json=$(echo "$settings" |\
  /nix/store/6y8c4kikq5nka2qnza009j03bvkx2l5l-jq-1.8.1-bin/bin/jq -r '.jellyfin.libraries[].name' |\
  while IFS= read -r name; do
   /nix/store/sr7l2d08zskcpywrc3kd904j41z1zs0v-genfolderuuid "$name"
  done |\
  /nix/store/6y8c4kikq5nka2qnza009j03bvkx2l5l-jq-1.8.1-bin/bin/jq -R -s 'split("\n") | .[:-1]')

updated_settings=$(echo "$settings" |\
  /nix/store/6y8c4kikq5nka2qnza009j03bvkx2l5l-jq-1.8.1-bin/bin/jq \
  --argjson new_ids "$new_ids_json" \
  '.jellyfin.libraries |= (reduce (to_entries[]) as $entry ([]; . + [ $entry.value | .id = $new_ids[$entry.key] ]))'
)

echo "$cfg" "$updated_settings" |\
  /nix/store/6y8c4kikq5nka2qnza009j03bvkx2l5l-jq-1.8.1-bin/bin/jq --slurp 'reduce .[] as $item ({}; . * $item)' \
  > "$cfg_file"


echo "Waiting for db to be created..."
until [ -f "$db_file" ]
do
  sleep 1
done

echo "Waiting for the users table to be created..."
while true; do
  /nix/store/7p5yg8li32wgxxsydbzblnjgs8hvl9wd-sqlite-3.50.4-bin/bin/sqlite3 $db_file "
  SELECT 1 FROM sqlite_master
  WHERE type='table'
  AND name='user';
  " > /dev/null 2>&1

  if [ $? -eq 0 ]; then
    break
  fi

  sleep 1
done

echo "Creating users..."


echo "Restating jellyseerr to make it pick up the cfg/db changes"
kill -15 $jellyfin_pid
/nix/store/i7r1c7hxjr5ac6vlxnhgfsyi07l84rbj-jellyseerr-2.7.3/bin/jellyseerr
