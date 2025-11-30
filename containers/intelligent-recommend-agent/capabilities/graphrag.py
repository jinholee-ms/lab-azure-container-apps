from html import entities
from pathlib import Path
import pandas as pd
import shutil
import yaml

import graphrag.api as api
from graphrag.cli.initialize import initialize_project_at
from graphrag.cli.query import _resolve_output_files
from graphrag.config.load_config import load_config

from common import console, settings


class GraphRAG:
    path = Path(__file__).parent / "graphrag"
    settings_defaults: dict = { 
        "basic_search": {
            "chat_model_id": "default_chat_model",
            "embedding_model_id": "default_embedding_model",
            "prompt": "prompts/basic_search_system_prompt.txt"
        },
        "cache": {"base_dir": "cache", "type": "file"},
        "chunks": {"group_by_columns": ["id"], "overlap": 100, "size": 1200},
        "cluster_graph": {"max_cluster_size": 10},
        "community_reports": {
            "graph_prompt": "prompts/community_report_graph.txt",
            "max_input_length": 8000,
            "max_length": 2000,
            "model_id": "default_chat_model",
            "text_prompt": "prompts/community_report_text.txt"
        },
        "drift_search": {
            "chat_model_id": "default_chat_model",
            "embedding_model_id": "default_embedding_model",
            "prompt": "prompts/drift_search_system_prompt.txt",
            "reduce_prompt": "prompts/drift_search_reduce_prompt.txt"
        },
        "embed_graph": {"enabled": False},
        "embed_text": {
            "model_id": "default_embedding_model",
            "vector_store_id": "default_vector_store"
        },
        "extract_claims": {
            "description": (
                "Any claims or facts that could be "
                "relevant to information discovery."
            ),
            "enabled": False,
            "max_gleanings": 1,
            "model_id": "default_chat_model",
            "prompt": "prompts/extract_claims.txt"},
        "extract_graph": {
            "entity_types": ["organization", "person", "geo", "event"],
            "max_gleanings": 1,
            "model_id": "default_chat_model",
            "prompt": "prompts/extract_graph.txt"
        },
        "extract_graph_nlp": {
            "async_mode": "threaded",
            "text_analyzer": {"extractor_type": "regex_english"}
        },
        "global_search": {
            "chat_model_id": "default_chat_model",
            "knowledge_prompt": "prompts/global_search_knowledge_system_prompt.txt",
            "map_prompt": "prompts/global_search_map_system_prompt.txt",
            "reduce_prompt": "prompts/global_search_reduce_system_prompt.txt"
        },
        "input": {
            "file_type": "text",
            "storage": {"base_dir": "input", "type": "file"}
        },
        "local_search": {
            "chat_model_id": "default_chat_model",
            "embedding_model_id": "default_embedding_model",
            "prompt": "prompts/local_search_system_prompt.txt"
        },
        "models": {
            "default_chat_model": {
                "api_base": "${AZURE_OPENAI_ENDPOINT}",
                "api_key": "${AZURE_OPENAI_API_KEY}",
                "api_version": "${AZURE_OPENAI_API_VERSION}",
                "async_mode": "threaded",
                "auth_type": "api_key",
                "concurrent_requests": 25,
                "deployment_name": "${AZURE_OPENAI_CHAT_DEPLOYMENT}",
                "max_retries": 10,
                "model": "${AZURE_OPENAI_CHAT_DEPLOYMENT}",
                "model_provider": "azure",
                "model_supports_json": True,
                "requests_per_minute": None,
                "retry_strategy": "exponential_backoff",
                "tokens_per_minute": None,
                "type": "chat"
            },
            "default_embedding_model": {
                "api_base": "${AZURE_OPENAI_ENDPOINT}",
                "api_key": "${AZURE_OPENAI_API_KEY}",
                "api_version": "${AZURE_OPENAI_API_VERSION}",
                "async_mode": "threaded",
                "auth_type": "api_key",
                "concurrent_requests": 25,
                "deployment_name": "${AZURE_OPENAI_EMBEDDING_DEPLOYMENT}",
                "max_retries": 10,
                "model": "${AZURE_OPENAI_EMBEDDING_DEPLOYMENT}",
                "model_provider": "azure",
                "requests_per_minute": None,
                "retry_strategy": "exponential_backoff",
                "tokens_per_minute": None,
                "type": "embedding"
            }
        },
        "output": {"base_dir": "output", "type": "file"},
        "reporting": {"base_dir": "logs", "type": "file"},
        "snapshots": {"embeddings": False, "graphml": False},
        "summarize_descriptions": {
            "max_length": 500,
            "model_id": "default_chat_model",
            "prompt": "prompts/summarize_descriptions.txt"
        },
        "umap": {"enabled": False},
        "vector_store": {
            "default_vector_store": {
                "container_name": "default",
                "db_uri": "output/lancedb",
                "type": "lancedb"
            }
        }
    }
    
    def __init__(self, path: Path | None = None, force: bool | None = False, auto_delete: bool | None = False):
        self.path = path if path else GraphRAG.path
        self.path.mkdir(exist_ok=True)
        try:
            initialize_project_at(path=self.path, force=force)
        except ValueError as e:
            if not force and "Project already initialized at graphrag" in e.args:
                pass
            
        # overwrite .env
        with open(self.path / ".env", "w") as file:
            for k, v in settings.model_dump().items():
                file.write(f"{k}={v}\n")
                
        # overwrite settings.yaml
        with open(self.path / "settings.yaml", "w") as file:
            yaml.dump(self.settings_defaults, file)
            
        self.config = load_config(self.path)
        self.auto_delete = auto_delete
        console.print(f"✅ GraphRAG project initialized at {self.path}")
    
    def __del__(self):
        if self.auto_delete:
            shutil.rmtree(self.path)
        
    async def build(self, documents: pd.DataFrame | None = None):
        is_update_run = (self.path / "output").exists()
        console.log(f"Building graphrag index...{is_update_run=}")

        result = await api.build_index(
            config=self.config,
            input_documents=documents,
            is_update_run=is_update_run,
        )
        console.log("✅ GraphRAG index built.")
        console.log("=> result:", result)

    async def retrieve_on_global(self, query: str) -> str:
        entities = pd.read_parquet(self.path / "output" / "entities.parquet")
        communities = pd.read_parquet(self.path / "output" / "communities.parquet")
        community_reports = pd.read_parquet(self.path / "output" / "community_reports.parquet")
        response, context = await api.global_search(
            query=query,
            config=self.config,
            entities=entities,
            communities=communities,
            community_reports=community_reports,
            community_level=2,                # 커뮤니티 계층 (보통 1~3)
            dynamic_community_selection=False, # true 로 하면 질문에 맞게 커뮤니티 자동 선택
            response_type="Multiple Paragraphs",
        )
        console.log("✅ GraphRAG global search completed.")
        console.log("=> query:", query)
        console.log("=> response:", response)
        console.log("=> context:", context)
        
        return response
