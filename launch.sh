#!/usr/bin/env bash
# Interactive Portrieve export and Arcane project preparation launcher.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash launch.sh [--source ENDPOINT_FOLDER] [--destination DIR]
                     [--all | --project NAME ...] [--exclude NAME ...] [--apply]

Without --source, discover common export folders or export through Portrieve.
PORTAINER_EXPORT_SOURCE can also select an existing endpoint folder.
For a new export, set PORTAINER_URL (including /api) and PORTAINER_API_KEY,
or enter them at the prompts. PORTAINER_INSECURE=true permits a self-signed
certificate. Tokens are not saved. Prompts use /dev/tty, so piping into bash works.
Default destination: /opt/docker. Default selection: --all. Default: dry run.
P2A_IMAGE overrides the migration image (default: version 0.2.0).
EOF
}
ask() {
  if ! { exec 3<>/dev/tty; } 2>/dev/null; then
    echo "Interactive terminal required; supply the missing setting through an environment variable or option." >&2
    exit 1
  fi
  printf '%s' "$1" >&3
  IFS= read -r "$2" <&3
}
source_dir=${PORTAINER_EXPORT_SOURCE:-}
destination=/opt/docker
selection=()
options=()
while (($#)); do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --source|--destination|--project|--exclude)
      (($# >= 2)) || { echo "Missing value for $1" >&2; exit 1; }
      case "$1" in
        --source) source_dir=$2 ;;
        --destination) destination=$2 ;;
        --project) selection+=(--project "$2") ;;
        --exclude) options+=(--exclude "$2") ;;
      esac
      shift 2 ;;
    --all) selection+=(--all); shift ;;
    --apply) options+=(--apply); shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done
command -v docker >/dev/null || { echo "Docker is required." >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "Cannot reach Docker. Check daemon status and your Docker permissions." >&2; exit 1; }

if [[ -z $source_dir ]]; then
  candidates=()
  shopt -s nullglob
  for base in "$HOME/portainer-export" "$HOME"/portainer-export-* "$HOME/portainer_backups" "$PWD/portainer-export" "$PWD/portainer_backups" /opt/docker/portainer-export /opt/docker/portainer_backups; do
    [[ -d $base ]] || continue
    for endpoint in "$base" "$base"/*/; do
      [[ -d $endpoint ]] || continue
      found=false
      for file in "$endpoint"/*/docker-compose.yml "$endpoint"/*/stack_metadata.json; do
        [[ -f $file ]] && found=true
      done
      $found || continue
      candidate=$(cd "$endpoint" && pwd -P)
      duplicate=false
      for existing in "${candidates[@]}"; do
        [[ $candidate == "$existing" ]] && duplicate=true
      done
      $duplicate || candidates+=("$candidate")
    done
  done
  if ((${#candidates[@]})); then
    echo "Existing export sources (choose the endpoint for this Docker host):"
    for i in "${!candidates[@]}"; do printf '%d) %s\n' "$((i+1))" "${candidates[i]}"; done
    echo "0) Create a new export or enter a different folder"
    ask "Source number: " choice
    [[ $choice =~ ^[0-9]+$ ]] && ((choice <= ${#candidates[@]})) || { echo "Invalid selection" >&2; exit 1; }
    if ((choice > 0)); then source_dir=${candidates[choice-1]}; fi
  fi
  if [[ -z $source_dir ]]; then
    ask "Existing endpoint folder (Enter to export from Portainer): " source_dir
  fi
fi

if [[ -z $source_dir ]]; then
  echo "Portainer calls an API key an access token. Open your user menu -> My account -> Access tokens -> Add access token. Copy the token when shown."
  if [[ -z ${PORTAINER_URL:-} ]]; then
    echo "If Portainer runs on this host, these container ports may help identify its URL:"
    docker ps --filter ancestor=portainer/portainer-ce --format '{{.Names}}: {{.Ports}}'
    docker ps --filter ancestor=portainer/portainer-ee --format '{{.Names}}: {{.Ports}}'
    ask "Portainer URL (for example https://192.168.0.7:9443): " PORTAINER_URL
  fi
  PORTAINER_URL=${PORTAINER_URL%/}
  [[ $PORTAINER_URL == */api ]] || PORTAINER_URL+=/api
  [[ $PORTAINER_URL == http://* || $PORTAINER_URL == https://* ]] || { echo "An HTTP or HTTPS Portainer URL is required." >&2; exit 1; }
  if [[ -z ${PORTAINER_API_KEY:-} ]]; then
    ask "Press Enter to enter your access token (input will be hidden)." ignored
    printf 'Portainer access token: ' >&3
    IFS= read -rs PORTAINER_API_KEY <&3
    printf '\n' >&3
  fi
  [[ -n $PORTAINER_API_KEY ]] || { echo "Access token is required." >&2; exit 1; }
  if [[ -z ${PORTAINER_INSECURE:-} ]]; then
    ask "Allow Portainer's self-signed certificate? [y/N]: " insecure
    PORTAINER_INSECURE=false
    [[ $insecure != y && $insecure != Y ]] || PORTAINER_INSECURE=true
  fi
  export PORTAINER_URL PORTAINER_API_KEY PORTAINER_INSECURE
  docker run --rm -e PORTAINER_URL -e PORTAINER_API_KEY -e PORTAINER_INSECURE ghcr.io/nopoz/portrieve:latest test
  export_dir=$(mktemp -d "$HOME/portainer-export-XXXXXXXX")
  chmod 700 "$export_dir"
  docker run --rm -e PORTAINER_URL -e PORTAINER_API_KEY -e PORTAINER_INSECURE \
    -e PUID="$(id -u)" -e PGID="$(id -g)" -v "$export_dir:/backup" ghcr.io/nopoz/portrieve:latest export
  unset PORTAINER_API_KEY
  endpoints=()
  shopt -s nullglob
  for endpoint in "$export_dir"/*/; do
    for file in "$endpoint"/*/docker-compose.yml; do
      endpoints+=("${endpoint%/}"); break
    done
  done
  ((${#endpoints[@]})) || { echo "No exported stack folders found. Inspect $export_dir" >&2; exit 1; }
  for i in "${!endpoints[@]}"; do printf '%d) %s\n' "$((i+1))" "${endpoints[i]}"; done
  ask "Choose the endpoint for this Docker host: " choice
  [[ $choice =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#endpoints[@]})) || { echo "Invalid selection" >&2; exit 1; }
  source_dir=${endpoints[choice-1]}
fi
[[ -d $source_dir && -d $destination ]] || { echo "Source and destination directories must exist." >&2; exit 1; }
source_dir=$(cd "$source_dir" && pwd -P)
destination=$(cd "$destination" && pwd -P)
export PORTAINER_EXPORT_SOURCE=$source_dir
printf 'Selected source: %s\n' "$PORTAINER_EXPORT_SOURCE"
echo "To reuse this selection in your shell:"
printf 'export PORTAINER_EXPORT_SOURCE=%q\n' "$PORTAINER_EXPORT_SOURCE"
((${#selection[@]})) || selection=(--all)
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PORTAINER_EXPORT_SOURCE:/exports:ro" -v "$destination:/projects" \
  "${P2A_IMAGE:-ghcr.io/rubenfixit/portainer-to-arcane:0.2.0}" \
  --source /exports --destination /projects "${selection[@]}" "${options[@]}"
