## Why

The actual deployment target for this app is Azure, not AWS - but the only deployment script that exists (`deploy/setup_ec2.sh`) is AWS-specific in name and instance-type guidance, even though its actual mechanics (`apt-get`, systemd, Nginx, Certbot, Ollama) never touch an AWS API and would run on any Ubuntu 22.04 host. Rather than repurposing the AWS script in place (which would leave its name, comments, and `openspec/specs/deployment` requirements lying about what it's for), add a dedicated Azure setup script and matching documentation, so there's a reviewable, correctly-labeled artifact for the platform actually being used.

## What Changes

- Add `deploy/setup_azure_vm.sh`, mirroring `setup_ec2.sh`'s structure and both existing `DEPLOY_PROFILE` options (`gpu-inhouse`, `cpu-hosted-api`), adapted for Azure: Azure VM size guidance in place of AWS instance types (e.g. an `NC...T4_v3`-class GPU size for `gpu-inhouse`, a `Standard_B2s`-class size for `cpu-hosted-api`), and Azure-specific pre-req notes (NSG inbound rules for 80/443/22 instead of an AWS security group, `az vm create` guidance) instead of AWS-specific ones. Same non-goal as the original script: not actually provisioning anything or running against a real account - this environment has neither AWS nor Azure credentials.
- Update `deploy/README.md` to document both supported targets (AWS EC2, Azure VM) side by side, rather than being AWS-only.
- Generalize the `deployment` capability's spec language that currently hardcodes `setup_ec2.sh`/AWS by name, so the existing requirements (vanilla-instance setup, the two `DEPLOY_PROFILE`s, reverse-proxy-before-TLS) are stated in terms that apply to either script, plus new scenarios confirming the Azure script satisfies the same guarantees.
- The existing AWS script and docs are kept as-is (not replaced) - this adds a second target, it doesn't migrate away from the first.

## Capabilities

### Modified Capabilities
- `deployment`: setup-script requirements ("Setup Succeeds on a Vanilla Target Instance", "Cost-Optimized Non-GPU AWS Deployment Profile") are restated to cover both `setup_ec2.sh` and the new `setup_azure_vm.sh` rather than naming the AWS script specifically; new scenarios cover the Azure script's equivalent behavior.

## Impact

- New `deploy/setup_azure_vm.sh`.
- `deploy/README.md`: add an Azure section alongside the existing AWS one (VM size guidance, NSG rules, `az vm create` sketch).
- `openspec/specs/deployment/spec.md`: reword two requirements to be platform-generic, add Azure-equivalent scenarios.
- No application code changes - this is deployment tooling/docs only, same as the original `dual-target-deployment` change.
