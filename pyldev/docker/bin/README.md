# bin

## Scripts

- ``build.bat``: builds an image locally with x86 architecture

- ``starts.bat``: runs the local image in a container

- ``deploy.bat``: builds and deploy a multi-tenant amd and arm architectures


## Required for multi-tenant deployement


``docker pull moby/buildkit:latest``

``docker buildx create --name multiplatform-builder --driver docker-container --use``

``docker buildx inspect --bootstrap``



