## ADDED Requirements

### Requirement: Cost-Optimized Non-GPU AWS Deployment Profile
The setup script SHALL support a `cpu-hosted-api` deployment profile that provisions no GPU driver and pulls no local chat model, configuring the application to use the hosted-API chat backend with local Ollama retained for embeddings only.

#### Scenario: Running setup with the cpu-hosted-api profile
- **WHEN** `setup_ec2.sh` is run with `DEPLOY_PROFILE=cpu-hosted-api`
- **THEN** no GPU driver installation is attempted, only the embeddings model is pulled via Ollama, and the generated `config.yaml` sets `chat_backend` to the hosted API

#### Scenario: Running setup with the default profile
- **WHEN** `setup_ec2.sh` is run without `DEPLOY_PROFILE` set, or with it set to `gpu-inhouse`
- **THEN** behavior is unchanged from before this capability existed - GPU driver installation is attempted, both the chat and embedding models are pulled via Ollama, and the generated `config.yaml` sets `chat_backend` to Ollama

## MODIFIED Requirements

### Requirement: Setup Succeeds on a Vanilla Target Instance
`setup_ec2.sh` SHALL complete without error on a fresh, vanilla instance of its documented target OS (Ubuntu 22.04), without requiring any package or repository not available in that OS's default archives, for either supported `DEPLOY_PROFILE`.

#### Scenario: Installing system dependencies on a fresh instance
- **WHEN** `setup_ec2.sh` runs `apt-get install` for its required packages, under either deployment profile
- **THEN** every package it requests is resolvable from Ubuntu 22.04's default archives, without needing a third-party PPA

#### Scenario: Installing under the cpu-hosted-api profile on a non-GPU instance
- **WHEN** `setup_ec2.sh` runs with `DEPLOY_PROFILE=cpu-hosted-api` on an instance with no GPU
- **THEN** setup completes without attempting GPU driver installation and without error
