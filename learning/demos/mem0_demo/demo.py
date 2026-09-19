"""Isolated Mem0 learning CLI; no application settings or credentials are loaded."""

import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build_config(settings, environ):
    for field in ("llm_model", "llm_base_url", "embedding_model", "embedding_base_url"):
        value = settings.get(field, "")
        if not isinstance(value, str) or not value or "YOUR_" in value:
            raise ValueError("Configure %s in config.json first" % field)
    dims = settings.get("embedding_dims")
    if type(dims) is not int or dims <= 0:
        raise ValueError("embedding_dims must be a positive integer")
    keys = {}
    for role in ("llm", "embedding"):
        key = (environ.get("DEMO_%s_API_KEY" % role.upper())
               or settings.get(role + "_api_key") or settings.get("api_key"))
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Missing API key for " + role)
        keys[role] = key.strip()
    return {
        "llm": {"provider": "openai", "config": {
            "model": settings["llm_model"],
            "api_key": keys["llm"],
            "openai_base_url": settings["llm_base_url"],
            "temperature": 0,
        }},
        "embedder": {"provider": "openai", "config": {
            "model": settings["embedding_model"],
            "api_key": keys["embedding"],
            "openai_base_url": settings["embedding_base_url"],
        }},
        "vector_store": {"provider": "milvus", "config": {
            "collection_name": settings.get("milvus_collection", "mem0_learning_demo"),
            "url": settings.get("milvus_url", "http://localhost:19530"),
            "token": environ.get("DEMO_MILVUS_TOKEN") or settings.get("milvus_token", ""),
            "db_name": settings.get("milvus_db_name", "default"),
            "metric_type": "COSINE",
            "embedding_model_dims": dims,
        }},
        "history_db_path": str(ROOT / "data" / "history.db"),
    }


def require_owner(memory, memory_id, user):
    record = memory.get(memory_id)
    if not record or record.get("user_id") != user:
        raise ValueError("Memory not found in this user's scope")


def execute(memory, args):
    if args.command == "add":
        # Scope is explicit for the demo; this is not a natural-language classifier.
        if args.scope == "turn":
            return {"persisted": False, "reason": "Current-turn instruction only", "text": args.text}
        result = memory.add(
            [{"role": "user", "content": args.text}], user_id=args.user,
            metadata={"source": "learning_demo", "scope": "long_term"},
        )
        # Some SDK failure paths return ADD even when vector insertion failed.
        for item in result.get("results", []):
            if item.get("event") == "ADD":
                # Milvus bounded consistency may briefly hide a just-written row.
                for attempt in range(6):
                    if memory.get(item["id"]):
                        break
                    if attempt < 5:
                        time.sleep(1)
                require_owner(memory, item["id"], args.user)
        return result
    if args.command == "search":
        return memory.search(query=args.query, filters={"user_id": args.user}, top_k=5)
    if args.command == "list":
        return memory.get_all(filters={"user_id": args.user}, top_k=100)
    require_owner(memory, args.id, args.user)
    if args.command == "update":
        return memory.update(memory_id=args.id, text=args.text)
    if args.command == "delete":
        if not args.yes:
            raise ValueError("Deletion requires --yes")
        return memory.delete(memory_id=args.id)
    return memory.history(memory_id=args.id)


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--user", default="student_a", help="Demo namespace, not authentication")
    commands = root.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add")
    add.add_argument("text")
    add.add_argument("--scope", choices=("long", "turn"), default="long")
    commands.add_parser("search").add_argument("query")
    commands.add_parser("list")
    for name in ("update", "delete", "history"):
        command = commands.add_parser(name)
        command.add_argument("id")
        if name == "update":
            command.add_argument("text")
        if name == "delete":
            command.add_argument("--yes", action="store_true")
    return root


def main():
    args = parser().parse_args()
    if args.command == "add" and args.scope == "turn":
        result = execute(None, args)
    else:
        settings = json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig"))
        config = build_config(settings, os.environ)
        os.environ["MEM0_TELEMETRY"] = "false"
        os.environ["MEM0_DIR"] = str(ROOT / "data")
        (ROOT / "data").mkdir(exist_ok=True)
        from mem0 import Memory

        memory = Memory.from_config(config)
        result = execute(memory, args)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
