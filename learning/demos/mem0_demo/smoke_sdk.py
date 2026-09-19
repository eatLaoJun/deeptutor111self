"""Real SDK/local stores smoke test with fake embeddings and blocked networking."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from demo import build_config, execute, parser


def main():
    with tempfile.TemporaryDirectory(prefix="mem0-smoke-") as directory:
        os.environ["MEM0_DIR"] = directory
        os.environ["MEM0_TELEMETRY"] = "false"
        from mem0 import Memory
        from mem0.embeddings.openai import OpenAIEmbedding

        settings = dict(llm_model="test-chat", llm_base_url="http://127.0.0.1:1/v1",
                        embedding_model="test-embed", embedding_base_url="http://127.0.0.1:1/v1",
                        embedding_dims=3)
        config = build_config(settings, dict(DEMO_LLM_API_KEY="fake", DEMO_EMBEDDING_API_KEY="fake"))
        # Keep this offline smoke test separate from the live Milvus configuration.
        config["vector_store"] = {"provider": "qdrant", "config": {
            "path": str(Path(directory) / "vectors"),
            "collection_name": "offline_smoke",
            "embedding_model_dims": 3,
        }}
        config["history_db_path"] = str(Path(directory) / "history.db")
        with patch("socket.socket.connect", side_effect=AssertionError("Network disabled")), \
                patch.object(OpenAIEmbedding, "embed", return_value=[1.0, 0.0, 0.0]):
            memory = Memory.from_config(config)
            try:
                result = memory.add([{"role": "user", "content": "Prefer hints"}],
                                    user_id="student_a", infer=False)
                memory_id = result["results"][0]["id"]
                assert execute(memory, parser().parse_args(["list"]))["results"]
                assert not execute(memory, parser().parse_args(["--user", "student_b", "list"]))["results"]
                assert execute(memory, parser().parse_args(["search", "hints"]))["results"]
                execute(memory, parser().parse_args(["update", memory_id, "Prefer examples"]))
                assert memory.get(memory_id)["memory"] == "Prefer examples"
                assert execute(memory, parser().parse_args(["history", memory_id]))
                execute(memory, parser().parse_args(["delete", memory_id, "--yes"]))
                assert not execute(memory, parser().parse_args(["list"]))["results"]
                print("PASS: real SDK CRUD, user scope and history; fake embeddings, no LLM inference")
            finally:
                stores = [memory.vector_store, getattr(memory, "entity_store", None),
                          getattr(memory, "_telemetry_vector_store", None)]
                for store in stores:
                    if store is not None:
                        store.client.close()
                memory.db.connection.close()


if __name__ == "__main__":
    main()
