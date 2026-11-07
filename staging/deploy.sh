#!/usr/bin/env bash
# Deploys one commit to staging. GitHub Actions runs it over SSH as the deploy user
# (.github/workflows/deploy-staging.yml). The deploy user's authorized_keys forces
# this script, so the CI key can't run anything else:
#
#   command="/opt/lessonlab/app/staging/deploy.sh",restrict ssh-ed25519 AAAA... github-actions
#
# Input: the full commit SHA as the SSH command, and a short-lived GHCR token on stdin.
# The images for that commit must already be in GHCR (the workflow pushes them first).
#
# Steps: pull the images, check out the commit, run migrations, start the stack and
# wait until it's healthy. If that fails, it goes back to the previous commit and images.
# Migrations aren't undone, so they must stay compatible with the previous release.

set -euo pipefail
umask 077

APP=/opt/lessonlab/app
ENV_FILE="$APP/staging/.env"
REGISTRY=ghcr.io/ehtisham145
NGINX=docker-nginx-1
KEEP_IMAGES=3

log() { echo "==> $*"; }

set_images() {
  sed -i "s|^BACKEND_IMAGE=.*|BACKEND_IMAGE=$1|; s|^FRONTEND_IMAGE=.*|FRONTEND_IMAGE=$2|" "$ENV_FILE"
}

start_stack() {
  docker compose run --rm -T lessonlab-migrate </dev/null &&
    docker compose up -d --wait --wait-timeout 180 --remove-orphans </dev/null
}

main() {
  local sha="${SSH_ORIGINAL_COMMAND:-${1:-}}"
  if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Usage: deploy.sh <full commit sha>" >&2
    exit 2
  fi

  local backend="$REGISTRY/lessonlab-backend:$sha"
  local frontend="$REGISTRY/lessonlab-frontend:$sha"

  cd "$APP"
  local previous old_backend old_frontend
  previous="$(git rev-parse HEAD)"
  old_backend="$(sed -n 's/^BACKEND_IMAGE=//p' "$ENV_FILE")"
  old_frontend="$(sed -n 's/^FRONTEND_IMAGE=//p' "$ENV_FILE")"

  log "Deploying $sha (now running $previous)"
  git fetch --quiet origin
  git cat-file -e "$sha^{commit}"

  # The registry login lives in a temporary folder and is deleted at exit,
  # so no credentials stay on the server.
  DOCKER_CONFIG="$(mktemp -d)"
  export DOCKER_CONFIG
  trap 'rm -rf "$DOCKER_CONFIG"' EXIT
  docker login ghcr.io --username deploy --password-stdin >/dev/null
  log "Pulling the images"
  docker pull --quiet "$backend"
  docker pull --quiet "$frontend"
  docker logout ghcr.io >/dev/null

  git checkout --quiet --detach "$sha"
  set_images "$backend" "$frontend"
  cd staging

  log "Migrating and starting the stack"
  if ! start_stack; then
    echo "Deploy failed. Rolling back to $previous" >&2
    docker compose ps >&2 || true
    cd "$APP"
    git checkout --quiet --detach "$previous"
    set_images "$old_backend" "$old_frontend"
    cd staging
    docker compose up -d --wait --wait-timeout 180 --remove-orphans </dev/null || true
    exit 1
  fi

  if ! git -C "$APP" diff --quiet "$previous" "$sha" -- staging/nginx/; then
    log "Reloading nginx for the changed site config"
    docker exec "$NGINX" nginx -t && docker exec "$NGINX" nginx -s reload
  fi

  log "Removing old images (keeping the newest $KEEP_IMAGES)"
  local repo
  for repo in lessonlab-backend lessonlab-frontend; do
    docker image ls "$REGISTRY/$repo" --format '{{.Repository}}:{{.Tag}}' |
      tail -n +$((KEEP_IMAGES + 1)) | xargs -r docker image rm >/dev/null || true
  done

  log "Deployed $sha"
}

# On one line on purpose: git checkout rewrites this file while it runs,
# and bash must not read anything from the new version.
main "$@"; exit $?
