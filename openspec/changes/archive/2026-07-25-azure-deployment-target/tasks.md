## 1. Azure setup script

- [x] 1.1 Add `deploy/setup_azure_vm.sh`, copying `setup_ec2.sh`'s structure verbatim for every OS-level step (package install, users, git clone, venv, `ollama pull`, config generation, systemd units, sudoers, Nginx, service enablement, completion message) - nothing in that path is actually AWS-specific.
- [x] 1.2 Update the header comment: target "a fresh Ubuntu 22.04 Azure VM" instead of "instance"; keep both `DEPLOY_PROFILE` options (`gpu-inhouse`, `cpu-hosted-api`) with Azure VM size guidance in place of AWS instance types (e.g. an `NC...T4_v3`-class size for `gpu-inhouse`, a `Standard_B2s`-class size for `cpu-hosted-api`) and a note that this hasn't been run against a real Azure subscription from this environment (no Azure credentials configured here).
- [x] 1.3 Update the NVIDIA driver install comment to reference Azure's GPU-enabled marketplace images (instead of a "Deep Learning AMI") as the case where `ubuntu-drivers autoinstall` is a no-op; the install mechanism itself (`ubuntu-drivers autoinstall`) is unchanged.
- [x] 1.4 Update the completion message's env-var usage examples to reference `setup_azure_vm.sh`.
- [x] 1.5 Diff `setup_azure_vm.sh` against `setup_ec2.sh` line by line to confirm every difference is either (a) a comment/guidance change or (b) intentional - no accidental behavioral drift between the two scripts' shared logic. Confirmed: every functional line (apt-get installs, useradd, git clone, venv, ollama pull, config generation, systemd units, sudoers, Nginx, systemctl commands) is byte-identical; only header comments, the NVIDIA-driver comment, and the completion message's "instance"/"VM" wording differ.

## 2. Documentation

- [x] 2.1 Add an "Azure" section to `deploy/README.md` alongside the existing content, covering: recommended VM sizes per profile, required inbound NSG rules (80, 443, 22) as a manual prerequisite (mirroring how the AWS section documents security-group ports as a prerequisite, not something the script configures), and a minimal `az vm create` sketch for provisioning the VM before running the script.
- [x] 2.2 Reframe `deploy/README.md`'s intro/title so it covers both AWS and Azure as supported targets rather than reading as AWS-only; keep the existing AWS content intact, just no longer implying it's the only option.
- [x] 2.3 Update root `README.md`'s deployment blurb (if it names AWS/EC2 specifically) to mention both targets.

## 3. Specs

- [x] 3.1 Sync the `deployment` delta spec (both modified requirements, generalized off `setup_ec2.sh`/AWS-specific wording, with Azure scenarios added) into `openspec/specs/deployment/spec.md`.

## 4. Verification

- [x] 4.1 Run `bash -n deploy/setup_azure_vm.sh` (syntax check only - no Azure credentials exist in this environment to run it for real) and confirm it passes, same verification level the original `setup_ec2.sh` could get here. Passed.
- [x] 4.2 Run the full test suite to confirm this deployment-tooling-only change hasn't touched anything that affects it (expected: no test changes needed, since no application code changes). 290/290 passed, unchanged.
- [x] 4.3 Archive this change once tasks 1-4.2 are complete.
