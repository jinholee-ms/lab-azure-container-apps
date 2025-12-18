import asyncio
from datetime import datetime
import pandas as pd
from pathlib import Path


graphrag_path = Path() / "assets" / "graphrag_travel_profile"


async def main():
    from capabilities.graphrag import GraphRAG

    graphrag: GraphRAG = GraphRAG(path=graphrag_path, force=True, auto_delete=False)

    # Read all .txt files from graphrag_input directory
    documents = []
    for txt_file in Path(graphrag_path / "input").glob("*.txt"):
        with open(txt_file, "r", encoding="utf-8") as f:
            raw = f.read()
            first_line = raw.splitlines()[0].lstrip("# ").strip()

            documents.append({"title": first_line, "text": raw, "id": txt_file.name, "creation_date": datetime.now().isoformat()})
    # Convert to DataFrame
    documents = pd.DataFrame(documents)

    await graphrag.build(documents=documents)
    print("✅ TravelProfileAgent Graphrag loaded successfully.")


if __name__ == "__main__":
    asyncio.run(main())