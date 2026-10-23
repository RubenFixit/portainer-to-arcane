# Portainer to Arcane

Prepare Portainer stacks exported by [Portrieve](https://github.com/nopoz/portrieve) as file-backed [Arcane](https://getarcane.app) projects. Built from a successful homelab migration from Portainer web-editor stacks to Arcane.

This initial utility copies selected Compose definitions and environment variables. It does not deploy, stop, delete, or update containers; move application data; or connect to either management API. No Docker socket or API credentials are needed by this image.

**Git-backed stacks are not fully migrated.** The tool inspects Portrieve's `stack_metadata.json` for `GitConfig`. Bulk selection skips Git-backed stacks; explicit selection warns and copies exported files only. Repository connections, branches, credentials and Git deployment settings are not transferred.

## Workflow

1. Export stacks with Portrieve using its documented `export` command into a separate staging directory. Its `import` command targets Portainer, not Arcane.
2. Choose the endpoint folder that belongs to the Docker host being migrated. Check which stacks use Git and follow the Git-backed stack guidance below for those projects.
3. Run this tool in dry-run mode, review, then repeat with `--apply`.
4. Verify mounts, project identities, additional files, image versions and external resources before deploying through Arcane.

Do not point Portrieve's synchronized export output at a live Arcane projects directory.

## Docker usage

### Guided launcher

Quick start with the interactive wizard (dry run by default):

```bash
curl -fsSL https://rfix.me/p2a | bash
```

Download and inspect the launcher, then run it with Bash on your Docker host:

```bash
curl -fsSL https://rfix.me/p2a -o launch.sh
less launch.sh
bash launch.sh --exclude rustdesk
```

The launcher checks common export locations under your home directory, current directory and `/opt/docker` (`portainer-export` and `portainer_backups`). It lets you select the endpoint folder for the host being migrated, or enter a different path. It does not scan your network. If you choose a new export, it runs Portrieve's connection test and export into a fresh private staging folder, then asks you to select the exported endpoint. It displays local Portainer container port mappings as a URL hint when available; enter the manager URL yourself.

For a new export, create an access token in Portainer: open your user menu, choose **My account**, find **Access tokens**, and choose **Add access token**. Copy the value when shown. Portainer calls this an access token; the environment variable expected by Portrieve is `PORTAINER_API_KEY`.

Optionally set these before starting (the token prompt is hidden):

```bash
export PORTAINER_URL=https://your-portainer-host:9443/api
read -rsp 'Portainer access token: ' PORTAINER_API_KEY; echo
export PORTAINER_API_KEY
# Only if you intentionally accept a self-signed Portainer certificate:
export PORTAINER_INSECURE=true
bash launch.sh --all --exclude rustdesk
unset PORTAINER_API_KEY
```

When variables are missing, the launcher prompts through `/dev/tty`; the token is never saved to a file or printed. It is supplied to the Portrieve container as an environment variable, so Docker administrators can access it while that container runs. Existing exports need no token. The selected endpoint is exported as `PORTAINER_EXPORT_SOURCE` inside the launcher, and a reusable `export` command is printed. A child script cannot change the parent shell's variables; copy that command to retain the selection in your shell. No shell profile is modified.

`--source` or `PORTAINER_EXPORT_SOURCE` bypasses discovery. `--destination` defaults to `/opt/docker`, which must already exist. Selection defaults to `--all`; `--project` and repeatable `--exclude` are supported. Preparation remains a dry run unless `--apply` is supplied. A dry run may perform an export and download container images, but does not write Arcane projects or change application containers. Newly created staging folders are retained for review.

After inspection, a pipe-to-Bash invocation is also supported:

```bash
curl -fsSL https://rfix.me/p2a | bash -s -- --all --exclude rustdesk
```

If the short URL is unavailable, download directly from GitHub, then inspect and run as above:

```bash
curl -fsSL https://raw.githubusercontent.com/RubenFixit/portainer-to-arcane/main/launch.sh -o launch.sh
```

The short URL `https://rfix.me/p2a` redirects to the [raw launcher on GitHub](https://raw.githubusercontent.com/RubenFixit/portainer-to-arcane/main/launch.sh). It follows the current `main` branch. The full URL works independently of the shortener. The short-URL interactive source picker and existing-export preparation flow have been exercised on the author's live Docker VM; the new-export token flow still needs a live trial. The launcher currently uses Portrieve's `latest` image and migration image `0.2.0`; `P2A_IMAGE` can override the latter.

### Direct container usage

Use the published image `ghcr.io/rubenfixit/portainer-to-arcane:0.2.0` (Linux AMD64 and ARM64). Pin a version for reproducible use; `latest` follows the most recently published stable release.

Select one or more stacks. Change `local-agent-4` to your exported endpoint directory and the project names to your stacks:

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$HOME/portainer-export/local-agent-4:/exports:ro" \
  -v /opt/docker:/projects \
  ghcr.io/rubenfixit/portainer-to-arcane:0.2.0 \
  --source /exports --destination /projects \
  --project nextcloud --project media
```

To select all projects except a few:

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$HOME/portainer-export/local-agent-4:/exports:ro" \
  -v /opt/docker:/projects \
  ghcr.io/rubenfixit/portainer-to-arcane:0.2.0 \
  --source /exports --destination /projects \
  --all --exclude rustdesk --exclude portainer
```

Only exclude names present in your export; an unknown exclusion fails to catch typos. Omit `--exclude portainer` if it is not an exported stack. `--all` and `--project` are mutually exclusive; `--exclude` requires `--all`. Both selection modes default to dry run. Append `--apply` to write files.

Bulk selection examines immediate project folders within one endpoint export. It skips Git-backed stacks and stacks without metadata, printing the reason. Malformed metadata stops preparation before files are written. A metadata object with no nonempty `GitConfig` is classified as file-based; this is export metadata detection, not live inspection or a guarantee of completeness. Explicit `--project` can select a reviewed Git-backed export and emits a warning, or select files without metadata. Credentials and repository URLs are not printed.

To build locally instead:

```bash
git clone https://github.com/RubenFixit/portainer-to-arcane.git
cd portainer-to-arcane
docker build -t portainer-to-arcane .
```

Then substitute `portainer-to-arcane` for the GHCR image in the command above.

## Local build example

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$HOME/portainer-export/local-agent-4:/exports:ro" \
  -v /opt/docker:/projects \
  portainer-to-arcane \
  --source /exports --destination /projects \
  --project nextcloud --project media
```

Repeat the same command with `--apply` appended to write files. The host destination must already exist and be writable by your user. Run one preparation process at a time.

Each selected stack becomes:

```text
/opt/docker/<stack-name>/
  compose.yaml
  .env
```

Existing project directories are skipped. The original `.env` bytes are preserved and `COMPOSE_PROJECT_NAME=<stack-name>` is appended. Existing project-name assignments cause an error for manual review. Input symlinks and invalid project names are rejected. Output directories are private and files have mode 0600 on Linux. Metadata and network JSON remain in the original export.

Alternatively run `python3 prepare.py --help` with Python 3.9 or newer.

## Git-backed Portainer stacks

An exported main Compose file is not a copy of its source repository. This tool does not clone repositories or copy companion files, additional Compose files, Dockerfiles, build contexts or repository secrets. It leaves the exported metadata in the staging directory and does not recreate Git synchronization or deployment webhooks in Arcane.

A self-contained exported Compose file may be usable as a file-backed project after review, but that changes the workflow: updates in the original Git repository will no longer reach that project automatically. A successful copy or dry run does not establish that a Git-backed application is ready to deploy.

For projects that should remain managed from Git, configure [Arcane Git Sync](https://getarcane.app/docs/docker/git-sync) directly:

1. Record the original repository URL, branch or tag, Compose path and required companion files. Keep credentials out of logs and public reports.
2. Configure repository access in Arcane separately. This utility does not transfer credentials.
3. Create or link the project using the existing Compose project identity, and preserve its environment values and persistent storage references.
4. Enable **Sync Files** when the Compose deployment needs other files from its repository folder. Check that the selected folder includes everything required.
5. Leave automatic sync, automatic redeployment and image pulling disabled during setup. Review the first sync before starting or updating the application.

**Linking Git Sync to an existing Arcane project replaces its project files on the first pull.** Back up local changes first. Arcane documents preservation of local `.env` values, but verify the resulting environment and paths before deployment. Disable Portainer's deployment automation before Arcane becomes the deployment owner.

## Before deploying

- Confirm the stack name matches the running containers' `com.docker.compose.project` label. The tool assumes they match; it cannot inspect Docker.
- Keep existing absolute bind paths and named-volume identities. Relative paths change meaning when the Compose file moves.
- Review external networks, volumes, top-level `name`, profiles and other Compose settings.
- Copy and review companion configuration files, build contexts and secrets separately. This tool only copies the primary YAML and optional `.env`.
- Handle `env_file: stack.env` explicitly. Compose interpolation through `.env` and container environment files are different mechanisms.
- Keep application versions fixed during migration. Disable automatic image pulls and deployment automation in both interfaces.
- Validate with `docker compose config --quiet` and inspect `docker compose ps` from the new project directory before using Arcane's Up action.
- Back up application data, including database-consistent backups. Exported definitions are not data backups.

Arcane must have the host projects folder mounted and its Projects Directory configured correctly. Copying files alone does not establish successful takeover. A deployment may recreate containers; verify application data and behavior afterward. Avoid deleting the Portainer stack first.

## Status and scope

Early development. The original manual workflow worked for the author's standalone Docker homelab. This packaged utility has synthetic tests; it has not yet been validated against a live Arcane deployment. Git connection migration, Swarm migration, multi-file exports and data migration are outside its scope. Warnings are advisory, not a complete Compose analysis.

Portrieve remains a separate dependency; its code is not bundled. This project is independent of Portainer, Arcane and Portrieve.

## Publishing releases

The Publish container workflow runs tests and builds Linux AMD64 and ARM64 images when a stable version tag such as `v0.1.0` is pushed. It publishes the corresponding version and `latest` to GHCR using the repository's built-in GitHub Actions token. Publishing rights are limited to that job. Maintainers must verify that the GHCR package visibility is public after its initial publication.
