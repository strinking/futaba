#!/bin/bash
set -eu

if [[ $# -ne 1 ]]; then
	echo >&2 "Usage: $0 futaba-config.toml"
	exit 1
fi

python_ver=python3.7
repo_dir="$(dirname "$0")"
dest_dir=~futaba/repo

if [[ -f "$repo_dir/futaba.service" ]]; then
	service="$repo_dir/futaba.service"
else
	service="$repo_dir/misc/futaba.service"
fi

rm -r "$dest_dir"
mkdir -p "$dest_dir"
cp -a "$repo_dir" "$dest_dir"
install -m400 "$1" "$dest_dir/config.toml"
chown -R futaba:futaba "$dest_dir"
echo "Installed source code to '$dest_dir'"

"$python_ver" -m pip install -r "$repo_dir/requirements.txt" > /dev/null
echo "Installed Python dependencies"

install -m644 "$service" /usr/local/lib/systemd/system/futaba.service
chown root:root /usr/local/lib/systemd/system/futaba.service
echo "Installed systemd service"

systemctl daemon-reload
systemctl restart futaba.service
echo "Started futaba systemd service"
