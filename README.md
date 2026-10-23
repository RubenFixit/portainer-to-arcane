# Portainer to Arcane

Move Portainer stack definitions into [Arcane](https://getarcane.app) projects using Docker. The launcher finds existing [Portrieve](https://github.com/nopoz/portrieve) exports or guides you through creating one.

## Quick start

Run on your Docker host with Bash and access to Docker. Your Arcane projects directory must exist and be writable by your user; the default is `/opt/docker`.

```bash
curl -fsSL https://rfix.me/p2a | bash
```

Select an existing export or follow the prompts to export from Portainer. The first run previews the projects it would copy. To write them into Arcane's projects directory:

```bash
curl -fsSL https://rfix.me/p2a | bash -s -- --apply
```

To exclude projects, use their exported stack names:

```bash
curl -fsSL https://rfix.me/p2a | bash -s -- --exclude rustdesk --exclude media --apply
```

Existing destination folders are skipped. Bulk selection also skips Git-backed stacks and stacks without metadata. No application containers are started, stopped or redeployed.

To download and inspect the launcher first:

```bash
curl -fsSL https://rfix.me/p2a -o launch.sh
less launch.sh
bash launch.sh
```

If the short URL is unavailable:

```bash
curl -fsSL https://raw.githubusercontent.com/RubenFixit/portainer-to-arcane/main/launch.sh -o launch.sh
bash launch.sh
```

## How it works

1. The launcher finds exports in common local folders and asks which endpoint to use. For a new export, it runs Portrieve with your Portainer URL and access token.
2. Portrieve saves stack definitions, environment values and metadata in a separate staging folder.
3. The preparation tool checks the selected stacks and previews the files to copy.
4. With `--apply`, it writes `compose.yaml` and `.env` into Arcane's projects directory, preserving each stack's Compose project name.
5. Arcane discovers the project files. You review and deploy them through Arcane when ready.

| Destination | Location |
|---|---|
| Portrieve export | Separate staging folder; Portrieve synchronizes its output and can prune files |
| Prepared projects | Arcane's active projects directory, normally `/opt/docker` |

Writing prepared files directly into Arcane's projects directory is the intended workflow. Application data stays in its existing volumes and bind mounts.

## Portainer access token

For a new export, open your Portainer user menu, choose **My account → Access tokens → Add access token**, and copy the token when shown. The launcher prompts for it with input hidden.

Portainer calls it an access token; Portrieve expects `PORTAINER_API_KEY`. You can set the connection details beforehand:

```bash
export PORTAINER_URL=https://your-portainer-host:9443/api
read -rsp 'Portainer access token: ' PORTAINER_API_KEY; echo
export PORTAINER_API_KEY
bash launch.sh
unset PORTAINER_API_KEY
```

For a self-signed Portainer certificate, the launcher asks whether to allow it. You can also set `PORTAINER_INSECURE=true` explicitly.

Tokens are passed to the temporary Portrieve container, not printed or saved to a file. Docker administrators can access container environment variables. Existing exports need no token.

## Launcher options

| Option | Behavior |
|---|---|
| `--source DIR` | Use an existing endpoint export folder |
| `--destination DIR` | Write projects here; default `/opt/docker` |
| `--all` | Select all eligible stacks; the launcher default |
| `--project NAME` | Select a stack; repeat for more |
| `--exclude NAME` | Exclude a stack from bulk selection; repeat for more |
| `--apply` | Write files; otherwise preview only |
| `--help` | Show usage |

Use either `--all` or `--project`. Exclusions require bulk selection and must match names in the export; unknown names produce an error.

The launcher searches `portainer-export`, `portainer-export-*` and `portainer_backups` under your home directory, plus `portainer-export` and `portainer_backups` in the current directory and `/opt/docker`. It does not scan the network. Local Portainer container port mappings are shown as a URL hint when available.

New exports go into a private staging folder under your home directory and are retained for review. Even a preview can download images and create an export; `--apply` controls writing Arcane project files.

The selected source is set as `PORTAINER_EXPORT_SOURCE` for the launcher session. It prints an `export` command you can copy to reuse that selection in your shell. Set that variable or pass `--source` to bypass discovery. No shell profile is changed.

The short URL follows `launch.sh` on `main`. The launcher uses Portrieve's `latest` image and migration image `0.2.0`; set `P2A_IMAGE` to override the migration image.

## Direct Docker usage

To prepare an existing export without the wizard:

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$HOME/portainer-export/local-agent-4:/exports:ro" \
  -v /opt/docker:/projects \
  ghcr.io/rubenfixit/portainer-to-arcane:0.2.0 \
  --source /exports --destination /projects \
  --all --exclude rustdesk
```

Replace `local-agent-4` with your endpoint folder. Add `--apply` to write files, or replace `--all --exclude rustdesk` with `--project nextcloud --project media` for explicit selection.

The image supports Linux AMD64 and ARM64. Pin a version for repeatable use; `latest` follows the most recently published stable release. It needs no Docker socket or API credentials. Run one preparation process at a time.

## Project files

Each selected stack becomes:

```text
/opt/docker/<stack-name>/
  compose.yaml
  .env
```

The tool copies the exported `docker-compose.yml`, preserves the original `.env` bytes and appends `COMPOSE_PROJECT_NAME=<stack-name>`. An existing project-name assignment requires manual review. Output directories are private and files have mode 0600 on Linux. Input symlinks and invalid project names are rejected. Metadata and network JSON stay in the export folder.

Only the primary Compose file and optional `.env` are copied. Companion configuration, additional Compose files, build contexts and secrets need separate handling.

## Git-backed stacks

The tool checks `stack_metadata.json` for a nonempty `GitConfig`. Bulk selection skips those stacks and folders with missing metadata. Invalid metadata stops preparation before any files are written. An empty or absent `GitConfig` in a metadata object is reported as file-based.

Explicit `--project` selection can copy a reviewed Git-backed export, with a warning. It can also select files without metadata. Detection uses exported metadata, not live Portainer configuration. Repository URLs and credentials are not printed.

Git connections, branches, credentials, webhooks and companion repository files are not migrated. To keep a project managed from Git, configure [Arcane Git Sync](https://getarcane.app/docs/docker/git-sync) with the original repository, branch and Compose path. Preserve its project name, environment values and storage references. Enable **Sync Files** when companion files are needed.

Linking Git Sync to an existing project replaces its project files on the first pull. Back up local changes and review the first sync before enabling automatic deployment. Arcane documents preservation of local `.env` values; check the resulting configuration before deploying. Disable Portainer deployment automation when Arcane takes over.

## Before deploying in Arcane

- Confirm the stack name matches the running containers' `com.docker.compose.project` label.
- Preserve existing bind-mount paths and named-volume identities. Relative paths change meaning when the Compose file moves.
- Check external networks, profiles, top-level `name` and companion files.
- Handle `env_file: stack.env` explicitly; `.env` interpolation is a separate mechanism.
- Keep current image versions during migration and disable automatic image pulls.
- Back up application data, including consistent database backups. Exported definitions are not data backups.

From each new project directory, check the definition and existing containers:

```bash
docker compose config --quiet
docker compose ps
```

Arcane needs the projects directory mounted and configured correctly. Use its Up action after reviewing the project. Deployment may recreate containers, so verify application data and behavior afterward. Do not delete the Portainer stack first.

## Development

```bash
git clone https://github.com/RubenFixit/portainer-to-arcane.git
cd portainer-to-arcane
python3 -m unittest -v
bash test_launcher.sh
docker build -t portainer-to-arcane .
```

Substitute `portainer-to-arcane` for the GHCR image to use your local build. The preparation script also runs directly with Python 3.9 or newer: `python3 prepare.py --help`.

Stable version tags such as `v0.2.0` trigger tests and multi-platform image publishing to GHCR. The workflow publishes versioned and `latest` tags using the repository's GitHub Actions token. Verify public package visibility after the first publication.

## Status

Early development. The original manual migration, short-URL launcher, source picker and existing-export preview have been exercised on the author's Docker VM. The new-export token flow and packaged apply path still need live validation. Automated tests cover preparation and launcher argument handling.

Swarm migration, Git connection migration, multi-file exports and application data migration are outside the current scope. Warnings are advisory, not a complete Compose analysis.

Portrieve is a separate dependency; its code is not bundled. This project is independent of Portainer, Arcane and Portrieve.
