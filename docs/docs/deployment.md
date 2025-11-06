# Deployment

The service is part of the DataGEMS platform offered through an existing deployment, following the DataGEMS release and deployment procedures over a managed infrasrtucture. The purpose of this section is not to detail the deployment processes put in place by the DataGEMS team.

## Docker

The service is offered as a Docker image through the DataGEMS GitHub Organization Packages.

The dataset profiling as described in [Architecture](architecture.md) consists of two services:
* The FastAPI-based API service that handles client requests and job management
* The Ray-based worker service that performs the actual dataset profiling tasks

Both services are packaged as separate Docker images, built from the provided `Dockerfile.api` and `Dockerfile.worker` files respectively.

Build and deployment of these images is handled through the DataGEMS CI/CD pipelines using the `.github/workflows/docker-publish.yml` GitHub Actions workflow. Deployment is triggered on new releases.

## Configuration

In order for the service to operate properly, the needed configuration values must be set to match the environment that it must operate in. The needed configuration is described in the relevant [Configuration](configuration.md) section.
