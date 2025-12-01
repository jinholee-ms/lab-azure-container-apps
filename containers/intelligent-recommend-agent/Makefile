ifneq (,$(wildcard .az-release))
  include .az-release
  export
endif

uv-export-requirements:
	uv export --format requirements-txt --no-hashes --no-editable --no-dev >> requirements.txt

docker-build:
	docker build -t ${RELEASE_CONTAINER_APP_IMAGE}:${IMAGE_TAG} .

docker-buildx:
	docker buildx build \
	--platform linux/amd64 \
	--no-cache \
	--push \
	-t ${RELEASE_CONTAINER_APP_IMAGE}:${IMAGE_TAG} .

docker-push:
	docker push ${RELEASE_CONTAINER_APP_IMAGE}:${IMAGE_TAG}

fmt:
	black .

lint:
	flake8 .