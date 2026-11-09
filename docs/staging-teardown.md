# Removing Lesson Lab staging

How to take Lesson Lab off the staging server (`staging.lessonlab.me`) cleanly. The setup being removed is described in [development.md](development.md#staging-stack) and [ADR-0015](decisions/0015-staging-on-oci-trial-with-caddy.md).

The staging VM runs nothing but Lesson Lab. If the whole VM is going away, steps 1, 5 and 6 are enough: stop auto-deploy, terminate the VM, clean up GitHub and DNS. Steps 2–4 are for keeping the VM and removing only Lesson Lab.

Server commands run with `sudo` as the `ubuntu` user.

## What gets removed

| Item | Where |
|---|---|
| Containers, database volume, Caddy certificate volume, networks | Compose project `lessonlab-staging` |
| Images | `ghcr.io/ehtisham145/lessonlab-*`, `postgres`, `redis` and `caddy` |
| Code and settings | `/opt/lessonlab` (includes `staging/.env`) |
| `deploy` user | Its home `/home/deploy` holds the GitHub read key and the CI key in `authorized_keys` |
| Auto-deploy | `staging` environment and its secrets, the deploy key, and the GHCR images, all on GitHub |
| DNS | `A` record `staging` → the VM's public IP |

## 1. Stop auto-deploy

So GitHub doesn't deploy again while you work:

```powershell
gh workflow disable "Deploy staging"
```

## 2. Back up the database (optional)

Skip this if the data isn't needed. Staging only ever holds test data.

```bash
cd /opt/lessonlab/app/staging
sudo docker compose exec -T lessonlab-db pg_dump -U lessonlab -d lessonlab -Fc > ~/lessonlab-staging-$(date +%F).dump
```

Copy the file off the server if you want to keep it, then delete it from the server.

## 3. Stop the stack and delete its data

This deletes the staging database and Caddy's certificate for good.

```bash
cd /opt/lessonlab/app/staging
sudo docker compose down --volumes --remove-orphans
sudo docker image ls --format '{{.Repository}}:{{.Tag}}' | grep -E "lessonlab|^postgres|^redis|^caddy" | xargs -r sudo docker image rm
sudo docker image prune -f   # removes the untagged copies pulled by digest
```

## 4. Delete the code and the deploy user

```bash
cd ~
sudo rm -rf /opt/lessonlab
sudo userdel --remove deploy   # also deletes /home/deploy with both SSH keys
id deploy                      # must say "no such user"
```

## 5. Or terminate the VM

If nothing else runs on it: OCI Console → the instance → **Terminate**, and tick **Permanently delete the attached boot volume**. Then check **Storage → Block Storage → Boot Volumes** for a leftover volume, because it counts against the free storage limit.

## 6. Clean up GitHub and DNS

On GitHub:
- **Settings → Environments** → delete `staging` (this also deletes its secrets), or update its secrets if staging is moving to a new server.
- **Settings → Deploy keys** → delete the key the server used.
- Your profile → **Packages** → delete `lessonlab-backend` and `lessonlab-frontend` if the images aren't needed.

Where `lessonlab.me` is managed, delete the `A` record `staging`, or point it at the new server. Check from any machine after a few minutes:

```bash
nslookup staging.lessonlab.me 1.1.1.1
```

## 7. Update the docs

If staging moves for good, update the "Staging stack" section in [development.md](development.md) and add an ADR that supersedes [ADR-0015](decisions/0015-staging-on-oci-trial-with-caddy.md). Update the CI host name and `staging/.env.example` if the domain changes.
