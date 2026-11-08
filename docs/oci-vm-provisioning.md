# Provisioning the Oracle free-tier VM (and the "out of capacity" workaround)

This is an operational runbook, not an architecture decision — see [ADR-0004](decisions/0004-hosting-oracle-cloud-saudi.md) for why Oracle was chosen, and [tech-stack.md](tech-stack.md) for the trade-off ("Oracle A1 'out of capacity' in Riyadh/Jeddah — try both regions and retry").

The free-tier `VM.Standard.A1.Flex` shape (2 OCPU / 12 GB, Always Free) is in very high demand. Manually clicking "Create" in the console rarely wins the race — by the time a slot frees up, an automated script elsewhere grabs it within seconds. The reliable fix is to run the same retry yourself, via the OCI CLI, until it succeeds.

**Do not** use any workaround that creates a different shape and then "updates" it to `A1.Flex` to bypass the capacity check — this has gotten accounts banned. Plain retrying (manual or scripted) is the only safe approach.

## 1. Install the OCI CLI (Windows / PowerShell)

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.ps1 -OutFile install.ps1
.\install.ps1
```
Follow the prompts (default options are fine). Restart PowerShell afterward so the `oci` command is on PATH.

## 2. Configure the CLI

```powershell
oci setup config
```
This wizard needs:
- Your **User OCID** — OCI Console → profile icon (top right) → **My profile** → copy the OCID shown there
- Your **Tenancy OCID** — profile icon → **Tenancy: `<name>`** → copy the OCID
- Your **region** (e.g. `ap-hyderabad-1`, or `me-riyadh-1` / `me-jeddah-1` for the real Saudi account)

Let the wizard **generate a new API signing key pair** for you. It prints the path to the public key (`~/.oci/oci_api_key_public.pem` by default) — open that file, copy its contents.

Then in the OCI Console: profile icon → **My profile** → **API keys** (left side) → **Add API Key** → paste the public key → **Add**.

Confirm it works:
```powershell
oci iam availability-domain list
```
If this returns JSON (not an auth error), the CLI is configured.

## 3. Gather the IDs you need

```powershell
# Compartment (root) + Availability Domain name
oci iam availability-domain list

# Ubuntu 24.04 ARM image (latest)
oci compute image list --compartment-id "<compartment-ocid>" --operating-system "Canonical Ubuntu" --operating-system-version "24.04" --shape "VM.Standard.A1.Flex" --sort-by TIMECREATED --sort-order DESC

# A public subnet (create one via the console wizard first if none exists —
# Instance creation screen → Networking → "Create new virtual cloud network" + "Create new public subnet")
oci network subnet list --compartment-id "<compartment-ocid>" --all
```

## 4. Generate an SSH key (if you don't already have one for this VM)

```powershell
ssh-keygen -t rsa -b 4096 -f "$env:USERPROFILE\.ssh\school_saas_key" -N '""'
```

## 5. The retry loop

```powershell
while ($true) {
    oci compute instance launch `
        --compartment-id "<compartment-ocid>" `
        --availability-domain "<availability-domain-name>" `
        --shape "VM.Standard.A1.Flex" `
        --shape-config '{"ocpus":2,"memoryInGBs":12}' `
        --image-id "<image-ocid>" `
        --subnet-id "<subnet-ocid>" `
        --assign-public-ip true `
        --ssh-authorized-keys-file "$env:USERPROFILE\.ssh\school_saas_key.pub" `
        --display-name "school-saas-vm"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "VM created successfully!"
        break
    }
    Write-Host "$(Get-Date): capacity not available, retrying in 60s..."
    Start-Sleep -Seconds 60
}
```

Runs until it succeeds or you stop it (`Ctrl+C`). Needs the PowerShell window to stay open — closing it (or a disconnected Cloud Shell browser tab, if using Cloud Shell instead) stops the retries. No persistent background service is set up here; restart the loop next session if it hasn't succeeded yet.

## 6. After it succeeds

Connect over SSH:
```powershell
ssh -i "$env:USERPROFILE\.ssh\school_saas_key" ubuntu@<public-ip-shown-in-output>
```
The public IP is in the `oci compute instance launch` output, or via `oci compute instance list-vnics --instance-id <instance-ocid>`.
