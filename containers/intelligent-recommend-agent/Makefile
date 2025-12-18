ifneq (,$(wildcard .az-release))
  include .az-release
  export
endif


.PHONY: azure-update-env uv-export-requirements uv-upload-assets uv-download-assets aca-run-download-assets docker-build docker-buildx docker-push fmt lint


download-assets:
	${CLI} ./scripts/load_assets_with_azure_storage_account.py download \
	--container-name="intelligent-recommend-agent" \
	--source="assets" \
	--destination="assets1" \
	--overwrite

azure-update-env:
	./export-env.sh ${RELEASE_RESOURCE_GROUP} ${RELEASE_CONTAINER_APP_NAME} ${RELEASE_CONTAINER_APP_NAME}

uv-export-requirements:
	uv export --format requirements-txt --no-hashes --no-editable --no-dev >> requirements.txt

uv-upload-assets:
	uv run python \
	./scripts/load_assets_with_azure_storage_account.py upload \
	--container-name="intelligent-recommend-agent" \
	--source="assets" \
	--destination="assets" \
	--overwrite

uv-download-assets:
	$(MAKE) download-assets CLI="uv run python"

uv-generate-travel-assets-kr:
	uv run python -m scripts.gen_travel_db_kr
	uv run python -m scripts.gen_travel_graphrag_input
	uv run python -m scripts.gen_travel_graphrag

aca-run-download-assets:
	$(MAKE) download-assets CLI="python"

docker-build:
	docker build --secret id=dotenv,src=.env -t ${RELEASE_CONTAINER_APP_IMAGE}:${IMAGE_TAG} .

docker-buildx:
	docker buildx build \
	--platform linux/amd64 \
	--no-cache \
	--push \
	--secret id=dotenv,src=.env \
	-t ${RELEASE_CONTAINER_APP_IMAGE}:${IMAGE_TAG} .

docker-push:
	docker push ${RELEASE_CONTAINER_APP_IMAGE}:${IMAGE_TAG}

fmt:
	uv run black .

lint:
	uv run flake8 .