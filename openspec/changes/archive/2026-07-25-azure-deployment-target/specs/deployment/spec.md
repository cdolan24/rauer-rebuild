## MODIFIED Requirements

### Requirement: Setup Succeeds on a Vanilla Target Instance
Each supported cloud target's setup script (`setup_ec2.sh` for AWS, `setup_azure_vm.sh` for Azure) SHALL complete without error on a fresh, vanilla instance of its documented target OS (Ubuntu 22.04), without requiring any package or repository not available in that OS's default archives, for either supported `DEPLOY_PROFILE`.

#### Scenario: Installing system dependencies on a fresh instance
- **WHEN** a target's setup script runs `apt-get install` for its required packages, under either deployment profile
- **THEN** every package it requests is resolvable from Ubuntu 22.04's default archives, without needing a third-party PPA

#### Scenario: Installing under the cpu-hosted-api profile on a non-GPU instance
- **WHEN** a target's setup script runs with `DEPLOY_PROFILE=cpu-hosted-api` on an instance with no GPU
- **THEN** setup completes without attempting GPU driver installation and without error

#### Scenario: The AWS script targets EC2
- **WHEN** `setup_ec2.sh` runs on a fresh Ubuntu 22.04 EC2 instance
- **THEN** it completes without error, per the scenarios above

#### Scenario: The Azure script targets an Azure VM
- **WHEN** `setup_azure_vm.sh` runs on a fresh Ubuntu 22.04 Azure VM
- **THEN** it completes without error, per the scenarios above

### Requirement: Cost-Optimized Non-GPU Deployment Profile
Each supported cloud target's setup script SHALL support a `cpu-hosted-api` deployment profile that provisions no GPU driver and pulls no local chat model, configuring the application to use the hosted-API chat backend with local Ollama retained for embeddings only.

#### Scenario: Running setup with the cpu-hosted-api profile
- **WHEN** a target's setup script is run with `DEPLOY_PROFILE=cpu-hosted-api`
- **THEN** no GPU driver installation is attempted, only the embeddings model is pulled via Ollama, and the generated `config.yaml` sets `chat_backend` to the hosted API

#### Scenario: Running setup with the default profile
- **WHEN** a target's setup script is run without `DEPLOY_PROFILE` set, or with it set to `gpu-inhouse`
- **THEN** behavior is unchanged from before this capability existed - GPU driver installation is attempted, both the chat and embedding models are pulled via Ollama, and the generated `config.yaml` sets `chat_backend` to Ollama

#### Scenario: Azure's cpu-hosted-api profile matches AWS's
- **WHEN** `setup_azure_vm.sh` is run with `DEPLOY_PROFILE=cpu-hosted-api` on an Azure VM with no GPU
- **THEN** it satisfies the same scenarios as `setup_ec2.sh`'s `cpu-hosted-api` profile above
