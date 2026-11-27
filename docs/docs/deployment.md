# Deployment

The service is part of the DataGEMS platform offered through an existing deployment, following the DataGEMS release and deployment procedures over a managed infrasrtucture. The purpose of this section is not to detail the deployment processes put in place by the DataGEMS team.

## Docker

The service is offered as a Docker image through the DataGEMS GitHub Organization Packages.

The dataset profiling as described in [Architecture](architecture.md) consists of two services:
* The FastAPI-based API service that handles client requests and job management
* The Ray-based worker service that performs the actual dataset profiling tasks

Both services are packaged as separate Docker images, built from the provided `Dockerfile.api` and `Dockerfile.ray` files respectively. The images are published to the GitHub Container Registry as `ghcr.io/datagems-eosc/dg-dataset-profiler-api` and `ghcr.io/datagems-eosc/dg-dataset-profiler-ray`.

Build and deployment of these images is handled through the DataGEMS CI/CD pipelines using the `.github/workflows/docker-publish.yml` GitHub Actions workflow. The workflow is triggered when a `v*` tag is pushed (i.e. on new releases). It runs the test suite first (`.github/workflows/tests.yml`), builds and pushes the images only if it passes, and then creates the GitHub Release with the commits since the previous tag.

## Configuration

In order for the service to operate properly, the needed configuration values must be set to match the environment that it must operate in. The needed configuration is described in the relevant [Configuration](configuration.md) section.

The MathE document endpoints read files on both services: the API looks each FileObject up in MoMa and checks its PDF, and the Ray worker converts it. Both mount the bucket at `/s3` and reach Redis (the Markdown cache). The API also reaches MoMa (`MOMA_API_URL`), and the Ray worker SCAYLE. See [MathE Document Endpoints](mathe-documents.md#configuration). The Ray image includes Tesseract for the `fast` mode's OCR.
