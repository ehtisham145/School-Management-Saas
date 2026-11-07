# Removing Lesson Lab from the staging server

How to take Lesson Lab off the shared staging server (`staging.lessonlab.me`) cleanly, without breaking E-Numerak, which shares the same server and nginx. The setup being removed is described in [development.md](development.md#staging-stack).

Run the steps **in order**. E-Numerak's nginx depends on our folder and the `lessonlab-edge` network, so it must be detached first. Removing the network while nginx still needs it would stop nginx from restarting, and E-Numerak would go down.

All server commands run as `root` on the server.

## What gets removed

| Item | Where |
|---|---|
| Containers, database volume, internal networks | Compose project `lessonlab-staging` |
| Shared network | `lessonlab-edge` |
| nginx hook | E-Numerak repo: `docker/nginx-staging.conf` and `docker/docker-compose.staging.yml` |
| Images | `lessonlab-backend:staging`, `lessonlab-frontend:staging`, `postgres:17.11-trixie`, `redis:7.4.12-alpine` |
| TLS certificate | `/etc/letsencrypt/live/staging.lessonlab.me` |
| Code and settings | `/opt/lessonlab` (includes `staging/.env`) |
| `deploy` user | Its home `/home/deploy` holds the GitHub read key and the CI key in `authorized_keys` |
| Auto-deploy | `staging` environment and its secrets, the deploy key, and the GHCR images, all on GitHub |
| DNS | `A` record `staging` → `187.127.231.215` |

## 1. Back up the database (optional)

Skip this if the data isn't needed. Staging only ever holds test data.

```bash
cd /opt/lessonlab/app/staging
docker compose exec -T lessonlab-db pg_dump -U lessonlab -d lessonlab -Fc > /root/lessonlab-staging-$(date +%F).dump
ls -lh /root/lessonlab-staging-*.dump
```

Copy the file off the server if you want to keep it, then delete it from the server.

## 2. Detach E-Numerak's nginx

Undo the nginx change in the **E-Numerak repo** (on the laptop, through a PR), so the server and the repo stay the same:

```bash
git revert <commit that added "serve Lesson Lab staging through this nginx">
```

If that commit was never made, remove the lines by hand instead:

- `docker/nginx-staging.conf`: the two lines at the end of the `http` block (the `# Lesson Lab staging ...` comment and `include /etc/nginx/lessonlab/*.conf;`).
- `docker/docker-compose.staging.yml`: in the `nginx` service, the `/opt/lessonlab/app/staging/nginx:/etc/nginx/lessonlab:ro` volume and the `networks:` block (`default`, `lessonlab-edge`). At the end of the file, the top-level `networks:` block with `lessonlab-edge: external: true`.

After merging, update the server and check the result:

```bash
cd /root/staging/E-Numerak-
git pull
grep -rn "lessonlab" docker/nginx-staging.conf docker/docker-compose.staging.yml   # must print nothing
cd docker
docker compose -p docker -f docker-compose.staging.yml config --quiet && echo "compose OK"
```

Test the nginx config in a throwaway container before touching the real one:

```bash
docker run --rm --network docker_default \
  -v /root/staging/E-Numerak-/docker/nginx-staging.conf:/etc/nginx/nginx.conf:ro \
  -v /root/staging/E-Numerak-/docker/ssl:/etc/nginx/ssl:ro \
  -v /etc/letsencrypt:/etc/letsencrypt:ro \
  nginx:1.25-alpine nginx -t
```

When it says `test is successful`, recreate nginx. E-Numerak is down for 2-3 seconds:

```bash
docker compose -p docker -f docker-compose.staging.yml up -d --no-deps nginx
docker inspect docker-nginx-1 --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'   # docker_default only
curl -sI https://staging.e-numerak.com | head -1
```

## 3. Stop the stack and delete its data

This deletes the staging database for good.

```bash
cd /opt/lessonlab/app/staging
docker compose down --volumes --remove-orphans
docker network rm lessonlab-edge
```

## 4. Delete the images

```bash
docker image ls | grep -E "lessonlab|postgres +17.11-trixie|redis +7.4.12-alpine"
docker image rm lessonlab-backend:staging lessonlab-frontend:staging
docker image rm postgres:17.11-trixie redis:7.4.12-alpine
```

E-Numerak uses `pgvector/pgvector:pg15` and `redis:7-alpine`, which are different images, so this doesn't touch them. If `image rm` says an image is in use, stop and check which container uses it.

## 5. Delete the certificate

```bash
certbot delete --cert-name staging.lessonlab.me
```

The weekly renew cron stays, because E-Numerak's certificates need it.

## 6. Stop auto-deploy, then delete the code, the deploy user and the keys

First stop GitHub from deploying again: repo **Settings → Environments** → delete `staging` (this also deletes its secrets). Then disable or delete `.github/workflows/deploy-staging.yml` in a PR.

```bash
rm -rf /opt/lessonlab
userdel --remove deploy   # also deletes /home/deploy with both SSH keys
id deploy                 # must say "no such user"
```

On GitHub:
- **Settings → Deploy keys** → delete `staging-server`.
- Your profile → **Packages** → delete `lessonlab-backend` and `lessonlab-frontend` if the images aren't needed.

## 7. Remove the DNS record

Where `lessonlab.me` is managed, delete the `A` record `staging` → `187.127.231.215`. Check from any machine after a few minutes:

```bash
nslookup staging.lessonlab.me 1.1.1.1   # should find no address
```

## 8. Final check

```bash
docker ps -a        | grep -i lessonlab   # nothing
docker volume ls    | grep -i lessonlab   # nothing
docker network ls   | grep -i lessonlab   # nothing
ls /opt/lessonlab /etc/letsencrypt/live/staging.lessonlab.me 2>&1   # both "No such file or directory"
docker ps --format "{{.Names}} {{.Status}}" | grep docker-   # E-Numerak containers still Up
curl -sI https://staging.e-numerak.com | head -1
```

## 9. Update the docs

If staging moves for good, update the "Staging stack" section in [development.md](development.md), add an ADR that supersedes [ADR-0011](decisions/0011-staging-on-hostinger-behind-shared-nginx.md), and update the CI host header and `staging/.env.example` if the domain changes.
