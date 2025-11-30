import os
import asyncio
import types
import pandas as pd
from pathlib import Path
import pytest
import shutil

from capabilities.graphrag import GraphRAG


@pytest.fixture()
def built_graphrag():
    path = Path(__file__).parent / "graphrag"
    g = GraphRAG(path=path, force=True, auto_delete=True)
    
    documents = pd.read_parquet("assets/graphrag/documents.parquet")
    documents = documents.loc[:, ["id", "title", "text", "creation_date"]]
    asyncio.run(g.build(documents=documents))
    
    return g

'''
def test_init_creates_project():
    path = Path(__file__).parent / "graphrag"
    
    # Initialize GraphRAG without force to create project
    g = GraphRAG(path=path)
    assert g.path.exists()
    assert (g.path / ".env").exists()
    assert (g.path / "settings.yaml").exists()
    working_path = g.path
    del g
    assert working_path.exists()
    shutil.rmtree(working_path)
    
    # Initialize GraphRAG with auto_delete to create and delete project
    g = GraphRAG(path=path, auto_delete=True)
    assert g.path.exists()
    assert (g.path / ".env").exists()
    assert (g.path / "settings.yaml").exists()
    working_path = g.path
    del g
    assert not working_path.exists()
    
    # Initialize GraphRAG with force to recreate project
    g = GraphRAG(path=path)
    g = GraphRAG(path=path, force=True, auto_delete=True)
    assert g.path.exists()
    assert (g.path / ".env").exists()
    assert (g.path / "settings.yaml").exists()
    working_path = g.path
    del g
    assert not working_path.exists()
'''

@pytest.mark.asyncio
async def test_graphrag_global_search(built_graphrag):
    assert (built_graphrag.path / "output").exists()
    
    result = await built_graphrag.retrieve_on_global("What is Dulce ?")
    assert result