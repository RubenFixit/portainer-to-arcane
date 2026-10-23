#!/usr/bin/env bash
set -euo pipefail
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
mkdir -p "$root/bin" "$root/source with spaces" "$root/destination"
cat > "$root/bin/docker" <<'EOF'
#!/usr/bin/env bash
if [[ $1 == info ]]; then exit 0; fi
printf '%s\n' "$@" > "$DOCKER_TEST_LOG"
EOF
chmod +x "$root/bin/docker"
export PATH="$root/bin:$PATH" DOCKER_TEST_LOG="$root/args"
bash launch.sh --source "$root/source with spaces" --destination "$root/destination" --all --exclude rustdesk > "$root/output"
grep -Fx -- '--all' "$root/args"
grep -Fx -- 'rustdesk' "$root/args"
if grep -Fxq -- '--apply' "$root/args"; then exit 1; fi
PORTAINER_EXPORT_SOURCE="$root/source with spaces" bash launch.sh --destination "$root/destination" --project demo --apply > "$root/output"
grep -Fx -- '--project' "$root/args"
grep -Fx -- '--apply' "$root/args"
if bash launch.sh --source > /dev/null 2>&1; then exit 1; fi
echo 'Launcher argument tests passed.'
