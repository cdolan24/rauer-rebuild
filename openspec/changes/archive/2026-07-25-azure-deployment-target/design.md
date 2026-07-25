## Context

`deploy/setup_ec2.sh` (from the `dual-target-deployment` change) is, in practice, a plain Ubuntu 22.04 provisioning script: `apt-get install`, `useradd`, `git clone`, a Python venv, `ollama pull`, systemd units, Nginx, Certbot. It never calls an AWS API, reads EC2 instance metadata, or depends on anything AWS-specific - the only AWS-ness is naming (`setup_ec2.sh`, comments, `README.md`) and instance-type recommendations (`g4dn.xlarge`, `t3.small`). The actual target for this deployment is Azure. Rather than quietly repurpose the AWS-named script and leave stale AWS language in its comments and the `deployment` spec, this change adds a correctly-labeled Azure counterpart and updates the spec to stop hardcoding one cloud.

Nothing in this environment can provision real infrastructure (no AWS or Azure credentials configured here, same as the original EC2 change) - this remains reviewable-artifact-only work, applied by the user against their own Azure subscription.

## Goals / Non-Goals

**Goals:**
- `deploy/setup_azure_vm.sh`: same two `DEPLOY_PROFILE`s (`gpu-inhouse`, `cpu-hosted-api`), same idempotent structure, differing from `setup_ec2.sh` only where Azure actually differs (VM size names, NSG guidance instead of security-group guidance, `az vm create` sketch instead of an EC2 launch sketch).
- `deployment` spec requirements that currently name `setup_ec2.sh`/AWS specifically restated platform-generically, with Azure scenarios added alongside the existing AWS ones - both scripts keep satisfying the same guarantees.
- `deploy/README.md` documents both targets so a reader isn't misled into thinking this is AWS-only.

**Non-Goals:**
- Provisioning real Azure infrastructure, or validating the script against a live subscription - no Azure credentials exist in this environment. Same posture as the original EC2 change: a reviewable script the user runs themselves.
- Terraform/Bicep/ARM templates. This stays at the same abstraction level as the EC2 script - a shell script run once on a fresh VM, not an infra-as-code pipeline.
- Retiring or migrating away from the AWS script. Both remain supported targets; nothing about the EC2 path changes.
- Azure-specific niceties (Managed Identity, Key Vault for `hosted_llm.api_key`, Azure Monitor). `config.yaml`'s existing gitignored-secret pattern is reused unchanged, matching the "don't introduce a new secrets mechanism" decision already made for AWS/hosted-API. Worth revisiting later if a real need shows up (see Open Questions).

## Decisions

### 1. A second, parallel script rather than parameterizing one script by cloud

`setup_ec2.sh` already branches on `DEPLOY_PROFILE` (a deployment-shape axis: GPU vs. hosted-API). Cloud provider is a different, mostly-orthogonal axis - the OS-level steps (packages, users, venv, systemd, Nginx) are identical either way; only the *pre-req guidance in comments* (VM size, network rule setup) differs. Rather than adding a second `CLOUD_PROVIDER` switch to one script (two independent axes multiplying inside one file), `setup_azure_vm.sh` is a sibling script that shares the same body almost line-for-line. This mirrors the existing precedent from `dual-target-deployment`'s own "Alternative considered" for a second script vs. a profile switch - there, the two profiles were rejected as separate scripts *because* they diverge only in a few steps within one platform. Here, the divergence is in the comments/guidance surrounding an otherwise-identical body, and the two scripts are genuinely for different target platforms a reader would look up separately - keeping them as separate files (both still supporting both `DEPLOY_PROFILE`s) is the clearer artifact to hand to someone provisioning on a specific cloud, at the cost of some duplication between the two files.

### 2. GPU driver install stays `ubuntu-drivers autoinstall`

Azure's NVIDIA-GPU Ubuntu VM sizes (the `NC`-family) run standard Ubuntu 22.04 images without a pre-installed driver by default, same starting position as a vanilla AWS AMI. `ubuntu-drivers autoinstall` (already used by `setup_ec2.sh`) is a standard, distribution-supported path that works identically regardless of cloud - it doesn't need to be replaced with Azure's NVIDIA GPU Driver Extension (which is an ARM-template/CLI-managed alternative, not something invoked from inside the VM by a shell script the same way). The script keeps the same "if launched from an image with the driver preinstalled, this is a no-op" framing, just reworded to mention Azure's marketplace GPU images instead of a "Deep Learning AMI."

### 3. VM size guidance, not a hardcoded default

Matching `setup_ec2.sh`'s existing pattern (header-comment guidance, e.g. `g4dn.xlarge`, not a value the script reads or enforces), `setup_azure_vm.sh` documents recommended Azure VM sizes in its header and `README.md` rather than checking or requiring a specific size - the script itself doesn't know or care what size VM it's running on beyond whether `nvidia-smi` ends up available.

### 4. Networking guidance lives in docs, not the script

Same as `setup_ec2.sh` (which doesn't touch AWS security groups - that's a prerequisite the operator handles before running the script), `setup_azure_vm.sh` doesn't call `az network nsg` anything. `deploy/README.md`'s Azure section documents the NSG inbound rules needed (80, 443, 22) as a manual/`az cli` prerequisite step, mirroring how the AWS section already documents security-group ports as a prerequisite rather than something the script configures.

### 5. `deployment` spec: reword two requirements to name "the setup script" generically

"Setup Succeeds on a Vanilla Target Instance" and "Cost-Optimized Non-GPU AWS Deployment Profile" currently say `setup_ec2.sh` and "AWS" by name. Both become platform-generic ("the platform's setup script", dropping "AWS" from the second requirement's title and body), with a scenario added for each script so the requirement still makes concrete, checkable claims about both `setup_ec2.sh` and `setup_azure_vm.sh` rather than becoming vaguer. This is the same style of change as `dual-target-deployment` itself made to `rag-chat`'s local-only requirement (conditional-by-profile, stated as explicit scenarios rather than either an unconditional guarantee or a silent narrowing).

## Risks / Trade-offs

- **[Risk]** Two scripts sharing almost identical bodies means a future fix to one (e.g. a package version bump, a new systemd unit) could be applied to only one and silently drift from the other. → **Mitigation**: `tasks.md`'s manual-verification section diffs the two scripts' shared sections explicitly as part of this change, and the risk is flagged in this design doc so a future editor knows to check both. Revisit unifying them (Decision 1's rejected alternative) if drift becomes a recurring real problem.
- **[Risk]** Neither script can be validated against a real instance of its target cloud from this environment. → **Accepted**: identical risk already accepted for `setup_ec2.sh` in the original change; this isn't new exposure, just the same posture applied to a second script.
- **[Risk]** Azure VM size recommendations (`NC...T4_v3`-class, `Standard_B2s`-class) could go stale as Azure's SKU lineup changes. → **Accepted**: same as AWS's `g4dn.xlarge`/`t3.small` guidance already in the codebase - documented as guidance in comments/README, not a value the script depends on, so staleness there doesn't break the script.

## Migration Plan

1. Add `deploy/setup_azure_vm.sh` (new file, nothing existing modified).
2. Add an Azure section to `deploy/README.md` alongside the existing AWS section.
3. Update the two `deployment` spec requirements that name AWS/`setup_ec2.sh` specifically to be platform-generic, with Azure scenarios added.
4. No application code, schema, or stored-data changes - deployment tooling/docs only.
5. Rollback: delete the new script and README section, revert the spec wording - the AWS path is completely unaffected throughout, so there's nothing to unwind on that side.

## Open Questions

- Whether to eventually move `hosted_llm.api_key` (and `admin_password`) to Azure Key Vault / AWS Secrets Manager instead of gitignored `config.yaml` - left as a follow-up, matching the existing secrets posture, not resolved here.
- Exact Azure VM size for each profile - left for the user to size against real GPU/embedding-throughput needs when they actually provision it, same posture as the AWS script's own open question about `t3.small` vs. `t3.medium`.
