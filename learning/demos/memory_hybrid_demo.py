"""Runnable prototype for an internal L1/L2/L3 memory design.

This module intentionally stays outside the production DeepTutor memory package.
It uses only the Python standard library so the write, versioning, retrieval,
and context-assembly flow can be studied without model or vector DB setup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Protocol, Sequence


_CONCEPT_PATTERNS: dict[str, tuple[str, ...]] = {
    "food": ("吃", "菜", "餐", "晚饭", "晚餐", "川菜", "饮食"),
    "spicy": ("辣", "川菜"),
    "health": ("胃", "医生", "不舒服", "恢复"),
    "preference": ("喜欢", "偏好", "爱吃", "经常选"),
    "recommendation": ("推荐", "建议", "选什么"),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lexical_tokens(text: str) -> list[str]:
    lowered = text.lower()
    latin = re.findall(r"[a-z0-9_]+", lowered)
    cjk_runs = re.findall(r"[\u4e00-\u9fff]+", lowered)
    cjk_tokens: list[str] = []
    for run in cjk_runs:
        cjk_tokens.extend(run)
        cjk_tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    return latin + cjk_tokens


def infer_concepts(text: str) -> tuple[str, ...]:
    return tuple(
        concept
        for concept, patterns in _CONCEPT_PATTERNS.items()
        if any(pattern in text.lower() for pattern in patterns)
    )


class LocalHashEmbedder:
    """Small deterministic embedder for the demo, not a production model."""

    def __init__(self, dimensions: int = 96) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        terms = _lexical_tokens(text)
        terms.extend(f"concept:{concept}" for concept in infer_concepts(text))
        vector = [0.0] * self.dimensions
        for term, count in Counter(terms).items():
            digest = hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self.dimensions
            sign = 1.0 if value & 1 else -1.0
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(item * item for item in vector)) or 1.0
        return [item / norm for item in vector]


@dataclass(frozen=True)
class ExtractedFact:
    layer: str
    memory_type: str
    topic: str
    text: str
    importance: float
    concepts: tuple[str, ...]
    supersede_active: bool = False


class FactExtractor(Protocol):
    def extract(self, message: str) -> list[ExtractedFact]: ...


class RuleBasedDemoExtractor:
    """Offline stand-in for an LLM that emits the same structured facts."""

    def extract(self, message: str) -> list[ExtractedFact]:
        if any(phrase in message for phrase in ("恢复了", "可以吃辣", "正常吃辣")):
            return [
                ExtractedFact(
                    layer="L2",
                    memory_type="constraint",
                    topic="food.spicy.constraint",
                    text="用户近期胃部状态已恢复，可以正常吃辣。",
                    importance=0.98,
                    concepts=("food", "spicy", "health"),
                    supersede_active=True,
                )
            ]

        if any(phrase in message for phrase in ("不能吃辣", "不要吃辣", "少吃辣")):
            return [
                ExtractedFact(
                    layer="L2",
                    memory_type="constraint",
                    topic="food.spicy.constraint",
                    text="用户因近期胃部不适，暂时不能吃辣。",
                    importance=1.0,
                    concepts=("food", "spicy", "health"),
                    supersede_active=True,
                )
            ]

        if "川菜" in message and any(
            phrase in message for phrase in ("喜欢", "爱吃", "经常", "会选", "选川菜")
        ):
            detail = "用户聚餐时经常选择川菜。" if "聚餐" in message else "用户喜欢川菜和辣味。"
            return [
                ExtractedFact(
                    layer="L2",
                    memory_type="preference",
                    topic="food.preference.sichuan",
                    text=detail,
                    importance=0.72,
                    concepts=("food", "spicy", "preference"),
                )
            ]
        return []


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    user_id: str
    layer: str
    memory_type: str
    topic: str
    text: str
    status: str
    source_ids: tuple[str, ...]
    concepts: tuple[str, ...]
    importance: float
    supersedes_id: str | None
    created_at: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class SearchHit:
    memory: MemoryRecord
    score: float
    semantic_score: float
    bm25_score: float
    concept_boost: float
    policy_boost: float


class SQLiteMemoryRepository:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        path = str(db_path)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                surface TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                layer TEXT NOT NULL CHECK (layer IN ('L2', 'L3')),
                memory_type TEXT NOT NULL,
                topic TEXT NOT NULL,
                text TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('active', 'superseded')),
                source_ids TEXT NOT NULL,
                concepts TEXT NOT NULL,
                importance REAL NOT NULL,
                supersedes_id TEXT REFERENCES memories(id),
                content_hash TEXT NOT NULL,
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_memories_recall
                ON memories(user_id, status, layer, topic);
            """
        )

    def reset(self) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM memories")
            self.connection.execute("DELETE FROM evidence")

    def add_evidence(self, user_id: str, surface: str, content: str, created_at: str) -> str:
        evidence_id = f"e_{uuid.uuid4().hex[:12]}"
        with self.connection:
            self.connection.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?, ?)",
                (evidence_id, user_id, surface, content, created_at),
            )
        return evidence_id

    def add_memory(
        self,
        *,
        user_id: str,
        fact: ExtractedFact,
        source_ids: Sequence[str],
        embedding: Sequence[float],
        created_at: str,
    ) -> MemoryRecord:
        content_hash = hashlib.sha256(fact.text.encode("utf-8")).hexdigest()
        duplicate = self.connection.execute(
            """
            SELECT * FROM memories
            WHERE user_id = ? AND layer = ? AND content_hash = ? AND status = 'active'
            LIMIT 1
            """,
            (user_id, fact.layer, content_hash),
        ).fetchone()
        if duplicate is not None:
            merged_sources = sorted(set(json.loads(duplicate["source_ids"])) | set(source_ids))
            with self.connection:
                self.connection.execute(
                    "UPDATE memories SET source_ids = ? WHERE id = ?",
                    (json.dumps(merged_sources, ensure_ascii=False), duplicate["id"]),
                )
            return self.get_memory(duplicate["id"])

        supersedes_id: str | None = None
        if fact.supersede_active:
            old = self.connection.execute(
                """
                SELECT id FROM memories
                WHERE user_id = ? AND layer = ? AND topic = ? AND status = 'active'
                ORDER BY created_at DESC LIMIT 1
                """,
                (user_id, fact.layer, fact.topic),
            ).fetchone()
            supersedes_id = old["id"] if old else None

        memory_id = f"m_{uuid.uuid4().hex[:12]}"
        with self.connection:
            if supersedes_id:
                self.connection.execute(
                    "UPDATE memories SET status = 'superseded' WHERE id = ?",
                    (supersedes_id,),
                )
            self.connection.execute(
                """
                INSERT INTO memories (
                    id, user_id, layer, memory_type, topic, text, status,
                    source_ids, concepts, importance, supersedes_id,
                    content_hash, embedding, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    user_id,
                    fact.layer,
                    fact.memory_type,
                    fact.topic,
                    fact.text,
                    json.dumps(list(source_ids), ensure_ascii=False),
                    json.dumps(list(fact.concepts), ensure_ascii=False),
                    fact.importance,
                    supersedes_id,
                    content_hash,
                    json.dumps(list(embedding)),
                    created_at,
                ),
            )
        return self.get_memory(memory_id)

    def get_memory(self, memory_id: str) -> MemoryRecord:
        row = self.connection.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            raise KeyError(memory_id)
        return self._to_record(row)

    def list_memories(self, user_id: str, *, active_only: bool = False) -> list[MemoryRecord]:
        sql = "SELECT * FROM memories WHERE user_id = ?"
        params: list[str] = [user_id]
        if active_only:
            sql += " AND status = 'active'"
        sql += " ORDER BY created_at, id"
        return [self._to_record(row) for row in self.connection.execute(sql, params)]

    @staticmethod
    def _to_record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            user_id=row["user_id"],
            layer=row["layer"],
            memory_type=row["memory_type"],
            topic=row["topic"],
            text=row["text"],
            status=row["status"],
            source_ids=tuple(json.loads(row["source_ids"])),
            concepts=tuple(json.loads(row["concepts"])),
            importance=float(row["importance"]),
            supersedes_id=row["supersedes_id"],
            created_at=row["created_at"],
            embedding=tuple(json.loads(row["embedding"])),
        )

    def close(self) -> None:
        self.connection.close()


class MemoryDemoService:
    def __init__(
        self,
        repository: SQLiteMemoryRepository,
        extractor: FactExtractor | None = None,
        embedder: LocalHashEmbedder | None = None,
        clock: Callable[[], str] = _now_iso,
    ) -> None:
        self.repository = repository
        self.extractor = extractor or RuleBasedDemoExtractor()
        self.embedder = embedder or LocalHashEmbedder()
        self.clock = clock

    def remember(self, user_id: str, message: str, surface: str = "chat") -> list[MemoryRecord]:
        now = self.clock()
        evidence_id = self.repository.add_evidence(user_id, surface, message, now)
        return [
            self.repository.add_memory(
                user_id=user_id,
                fact=fact,
                source_ids=[evidence_id],
                embedding=self.embedder.embed(fact.text),
                created_at=now,
            )
            for fact in self.extractor.extract(message)
        ]

    def consolidate_food_profile(self, user_id: str) -> MemoryRecord | None:
        preferences = [
            memory
            for memory in self.repository.list_memories(user_id, active_only=True)
            if memory.layer == "L2" and memory.topic == "food.preference.sichuan"
        ]
        if len(preferences) < 2:
            return None
        fact = ExtractedFact(
            layer="L3",
            memory_type="profile",
            topic="profile.food.preference.sichuan",
            text="多次对话表明：用户长期偏好川菜，通常也接受辣味。",
            importance=0.88,
            concepts=("food", "spicy", "preference"),
            supersede_active=True,
        )
        return self.repository.add_memory(
            user_id=user_id,
            fact=fact,
            source_ids=[memory.id for memory in preferences],
            embedding=self.embedder.embed(fact.text),
            created_at=self.clock(),
        )

    def search(self, user_id: str, query: str, top_k: int = 4) -> list[SearchHit]:
        memories = self.repository.list_memories(user_id, active_only=True)
        if not memories:
            return []

        query_embedding = self.embedder.embed(query)
        bm25_scores = _normalized_bm25(query, [memory.text for memory in memories])
        query_concepts = set(infer_concepts(query))
        hits: list[SearchHit] = []
        for memory, bm25_score in zip(memories, bm25_scores):
            semantic_score = max(0.0, _cosine(query_embedding, memory.embedding))
            overlap = query_concepts & set(memory.concepts)
            concept_boost = len(overlap) / max(len(query_concepts), 1)
            if memory.memory_type == "constraint":
                policy_boost = 1.0
            elif memory.layer == "L3":
                policy_boost = 0.2
            else:
                policy_boost = 0.0
            score = (
                0.45 * semantic_score
                + 0.15 * bm25_score
                + 0.15 * concept_boost
                + 0.10 * memory.importance
                + 0.15 * policy_boost
            )
            if score >= 0.08:
                hits.append(
                    SearchHit(
                        memory=memory,
                        score=score,
                        semantic_score=semantic_score,
                        bm25_score=bm25_score,
                        concept_boost=concept_boost,
                        policy_boost=policy_boost,
                    )
                )
        hits.sort(key=lambda hit: (hit.score, hit.memory.importance), reverse=True)
        return hits[:top_k]

    @staticmethod
    def assemble_context(hits: Iterable[SearchHit], max_tokens: int = 90) -> str:
        lines: list[str] = []
        used_tokens = 0
        for hit in hits:
            line = f"- [{hit.memory.layer}/{hit.memory.memory_type}] {hit.memory.text}"
            estimated_tokens = max(1, math.ceil(len(line) / 2))
            if used_tokens + estimated_tokens > max_tokens:
                break
            lines.append(line)
            used_tokens += estimated_tokens
        return "## Retrieved memory\n" + ("\n".join(lines) if lines else "(none)")


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _normalized_bm25(query: str, documents: Sequence[str]) -> list[float]:
    query_terms = set(_lexical_tokens(query))
    tokenized = [_lexical_tokens(document) for document in documents]
    if not query_terms or not tokenized:
        return [0.0] * len(documents)

    document_frequency = {
        term: sum(1 for document in tokenized if term in document) for term in query_terms
    }
    average_length = sum(len(document) for document in tokenized) / len(tokenized) or 1.0
    raw_scores: list[float] = []
    for document in tokenized:
        frequencies = Counter(document)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse_frequency = math.log(
                1.0
                + (len(tokenized) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            denominator = frequency + 1.5 * (1.0 - 0.75 + 0.75 * len(document) / average_length)
            score += inverse_frequency * (frequency * 2.5 / denominator)
        raw_scores.append(score)
    maximum = max(raw_scores) or 1.0
    return [score / maximum for score in raw_scores]


def _print_hits(title: str, hits: Sequence[SearchHit], service: MemoryDemoService) -> None:
    print(f"\n{title}")
    for index, hit in enumerate(hits, start=1):
        print(
            f"{index}. score={hit.score:.3f} "
            f"(semantic={hit.semantic_score:.3f}, bm25={hit.bm25_score:.3f}, "
            f"concept={hit.concept_boost:.3f}, policy={hit.policy_boost:.3f})\n"
            f"   [{hit.memory.layer}/{hit.memory.memory_type}] {hit.memory.text}"
        )
    print("\n" + service.assemble_context(hits))


def run_demo(db_path: str, reset: bool) -> None:
    repository = SQLiteMemoryRepository(db_path)
    if reset:
        repository.reset()
    service = MemoryDemoService(repository)
    user_id = "demo-user"

    print("=== 1. L1 evidence -> L2 facts -> L3 profile ===")
    for message in ("我喜欢川菜，尤其喜欢辣的。", "平时聚餐我也经常选川菜。"):
        created = service.remember(user_id, message)
        print(f"message: {message}")
        for memory in created:
            print(f"  -> {memory.id} [{memory.layer}] {memory.text}")
    profile = service.consolidate_food_profile(user_id)
    if profile:
        print(f"  -> {profile.id} [L3] {profile.text}; sources={list(profile.source_ids)}")

    print("\n=== 2. Add a temporary high-priority constraint ===")
    constraint = service.remember(user_id, "最近胃不舒服，医生说暂时不能吃辣。")[0]
    print(f"  -> {constraint.id} [active] {constraint.text}")
    query = "帮我推荐今天的晚餐"
    _print_hits("=== 3. Recall before recovery ===", service.search(user_id, query), service)

    print("\n=== 4. Supersede the expired constraint instead of deleting history ===")
    recovered = service.remember(user_id, "医生说我的胃已经恢复了，现在可以正常吃辣。")[0]
    print(f"  -> new={recovered.id}; supersedes={recovered.supersedes_id}")
    old = repository.get_memory(constraint.id)
    print(f"  -> old={old.id}; status={old.status}")
    _print_hits("=== 5. Recall after recovery ===", service.search(user_id, query), service)

    print("\n=== 6. Stored rows (audit view) ===")
    for memory in repository.list_memories(user_id):
        print(
            f"{memory.id} {memory.layer} {memory.status:10} "
            f"topic={memory.topic} supersedes={memory.supersedes_id or '-'}"
        )
    repository.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DeepTutor hybrid-memory learning demo.")
    parser.add_argument(
        "--db",
        default=":memory:",
        help=(
            "SQLite path. Defaults to an in-memory database; "
            "pass a file path to inspect persistence."
        ),
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the selected demo database first.",
    )
    args = parser.parse_args()
    run_demo(args.db, args.reset)


if __name__ == "__main__":
    main()
