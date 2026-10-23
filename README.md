# Portainer to Arcane

Prepare Portainer stacks exported by [Portrieve](https://github.com/nopoz/portrieve) as file-backed [Arcane](https://getarcane.app) projects. Built from a successful homelab migration from Portainer web-editor stacks to Arcane.

This initial utility copies selected Compose definitions and environment variables. It does not deploy, stop, delete, or update containers; move application data; or connect to either management API. No Docker socket or API credentials are needed by this image.

**Git-backed stacks are not fully migrated.** The tool copies exported files only; it does not transfer a stack's repository connection, branch, credentials or Git deployment settings. It does not inspect `stack_metadata.json` to detect or skip Git-backed stacks. Review the stack's deployment source before selecting it.

## Workflow

1. Export stacks with Portrieve using its documented `export` command into a separate staging directory. Its `import` command targets Portainer, not Arcane.
2. Choose the endpoint folder that belongs to the Docker host being migrated. Check which stacks use Git and follow the Git-backed stack guidance below for those projects.
3. Run this tool in dry-run mode, review, then repeat with `--apply`.
4. Verify mounts, project identities, additional files, image versions and external resources before deploying through Arcane.

Do not point Portrieve's synchronized export output at a live Arcane projects directory.

## Docker usage

Use the published image `ghcr.io/rubenfixit/portainer-to-arcane:0.1.0` (Linux AMD64 and ARM64). Pin a version for reproducible use; `latest` follows the most recently published stable release.

Select one or more stacks. Change `local-agent-4` to your exported endpoint directory and the project names to your stacks:

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$HOME/portainer-export/local-agent-4:/exports:ro" \
  -v /opt/docker:/projects \
  ghcr.io/rubenfixit/portainer-to-arcane:0.1.0 \
  --source /exports --destination /projects \
  --project nextcloud --project media
```

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

Early development. The original manual workflow worked for the author's standalone Docker homelab. This packaged utility has synthetic tests; it has not yet been validated against a live Arcane deployment. Git connection migration and detection, Swarm migration, multi-file exports and data migration are outside its scope. Warnings are advisory, not a complete Compose analysis.

Portrieve remains a separate dependency; its code is not bundled. This project is independent of Portainer, Arcane and Portrieve.

## Publishing releases

The Publish container workflow runs tests and builds Linux AMD64 and ARM64 images when a stable version tag such as `v0.1.0` is pushed. It publishes the corresponding version and `latest` to GHCR using the repository's built-in GitHub Actions token. Publishing rights are limited to that job. Maintainers must verify that the GHCR package visibility is public after its initial publication.
