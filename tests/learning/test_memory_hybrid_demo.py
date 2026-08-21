from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_DEMO_PATH = Path(__file__).parents[2] / "learning" / "demos" / "memory_hybrid_demo.py"
_SPEC = importlib.util.spec_from_file_location("memory_hybrid_demo", _DEMO_PATH)
assert _SPEC is not None and _SPEC.loader is not None
demo = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = demo
_SPEC.loader.exec_module(demo)


def test_l1_to_l3_and_constraint_versioning() -> None:
    repository = demo.SQLiteMemoryRepository()
    service = demo.MemoryDemoService(repository)
    user_id = "u1"

    first = service.remember(user_id, "我喜欢川菜，尤其喜欢辣的。")
    second = service.remember(user_id, "平时聚餐我也经常选川菜。")
    profile = service.consolidate_food_profile(user_id)

    assert first[0].layer == "L2"
    assert second[0].layer == "L2"
    assert profile is not None
    assert profile.layer == "L3"
    assert set(profile.source_ids) == {first[0].id, second[0].id}

    constraint = service.remember(user_id, "最近胃不舒服，医生说暂时不能吃辣。")[0]
    before = service.search(user_id, "帮我推荐今天的晚餐")
    assert constraint.id in {hit.memory.id for hit in before}
    assert profile.id in {hit.memory.id for hit in before}
    assert before[0].memory.id == constraint.id

    recovered = service.remember(user_id, "胃已经恢复了，现在可以正常吃辣。")[0]
    after = service.search(user_id, "帮我推荐今天的晚餐")

    assert recovered.supersedes_id == constraint.id
    assert repository.get_memory(constraint.id).status == "superseded"
    assert recovered.id in {hit.memory.id for hit in after}
    assert constraint.id not in {hit.memory.id for hit in after}
    assert "可以正常吃辣" in service.assemble_context(after)


def test_file_database_persists_memory(tmp_path: Path) -> None:
    db_path = tmp_path / "memory-demo.sqlite3"
    repository = demo.SQLiteMemoryRepository(db_path)
    service = demo.MemoryDemoService(repository)
    created_id = service.remember("u1", "我喜欢川菜，尤其喜欢辣的。")[0].id
    repository.close()

    reopened = demo.SQLiteMemoryRepository(db_path)
    assert reopened.get_memory(created_id).text == "用户喜欢川菜和辣味。"
    reopened.reset()
    assert reopened.list_memories("u1") == []
    reopened.close()
