# Progress

- Live integration: embedding returned 1024 vs configured 1536; corrected only dimension and collection in private config (no key output). Fresh 1024 collection write verified by later list/search. SDK falsely returned ADD on initial insert failure; added bounded read-back verification, accommodating observed delayed visibility. Nine offline tests pass. Test users use demo_check_20260916 prefix.

- 2026-09-16: User authorized deletion of empty broken Milvus container. Removed only container, preserved System32 bind directories. Created demo compose with same v3.0.0 image, named volume and localhost-only ports. Container healthy; pymilvus temporary collection insert/query passed and probe removed; actual demo.py list returned empty results. No model inference requested.

- User confirmed layered memory exists only as interview design.
- PyPI reports mem0ai 2.0.20; default python is Python 2.7 so use an explicit Python 3 interpreter.
- Main-branch source differs from older tutorials; validate installed distribution rather than assuming API compatibility.
- Implemented learning/demos/mem0_demo with isolated environment and local stores. Corrected initial old-style API arguments after inspecting installed 2.0.20: filters/top_k and text.
- Validation: 7 unit tests pass; smoke_sdk.py passes real SDK/local storage CRUD with fake embeddings and blocked networking. Optional NLP/BM25 dependencies absent; documented warnings. No live provider keys loaded or requests made.
- On user request switched demo.py to Milvus, default localhost:19530 and isolated mem0_learning_demo collection; existing secrets/config left untouched. Offline smoke retains Qdrant explicitly and does not validate Milvus. Eight unit tests pass. docker ps returned no running containers, so live Milvus integration remains unverified.
