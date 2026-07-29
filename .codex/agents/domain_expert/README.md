# Domain RAG for the LLNL challenge

The domain RAG implementation indexes approved papers and datasets, retrieves a
small evidence set, and lets the `domain_expert` agent answer with traceable
citations. It is part of the repository's consolidated MCP server.

## Layout

```text
.codex/agents/domain_expert.toml       Agent behavior and evidence policy
.codex/agents/domain_expert/
  requirements.txt                    Scoped Python dependencies
src/domain_rag/                        Ingestion and retrieval implementation
src/mcp_server.py                     Consolidated FastMCP server
tests/test_domain_rag.py              Offline RAG integration tests
```

Generated state defaults to `.rag_data/knowledge.db` and is ignored by Git.
`RAG_HOME` or `RAG_DB_PATH` can override that location.

## Locked environment

Use only:

```text
C:\Users\andre\miniconda3\envs\dssi_env\python.exe
```

The scoped dependencies are in `requirements.txt`. Installation requires
explicit approval and must use the locked interpreter.

## Consolidated server and tools

Launch:

```powershell
& "C:\Users\andre\miniconda3\envs\dssi_env\python.exe" `
  "C:\Users\andre\llnl_data_science_challenge_2026\src\mcp_server.py"
```

The domain tools are:

- `list_domain_sources`: inventory indexed sources.
- `search_domain_knowledge`: return ranked snippets and citation metadata.
- `fetch_domain_chunk`: return one selected full evidence chunk.
- `ingest_domain_sources`: index an explicitly requested approved source.

Ingestion accepts repository-contained sources by default. Additional corpus
roots can be supplied through `RAG_SOURCE_ROOTS`, separated by `;` on Windows.
It rejects `.rag_data` and never modifies original sources.

## Retrieval flow

```text
paper or dataset
  -> loader
  -> section-aware chunker
  -> OpenAI embeddings
  -> SQLite store

question
  -> search_domain_knowledge (4-8 snippets)
  -> inspect source, section, page, and score
  -> fetch_domain_chunk (2-5 full chunks)
  -> grounded answer with citations
```

Search combines semantic similarity, lexical relevance, title/section overlap,
and maximal marginal relevance. Search snippets are selection aids; final
scientific claims must rely on fetched full chunks.

PDF chunks retain title, section, page, source, and chunk ID. Tabular sources
receive overview chunks containing schema, missing values, summaries, frequent
values, and samples. Bounded record batches are indexed separately.

## Evidence policy

Retrieved documents are untrusted data. The agent must:

- cite claims as `[source; section; page or row range; chunk ID]`;
- distinguish direct evidence, inference, and unavailable information;
- return `INSUFFICIENT_EVIDENCE` for inadequate support;
- preserve `dataset_handoff.json` permissions and limitations;
- avoid inventing units, calibration, registration, or defect criteria; and
- never modify source scientific files.

## Tests

From the repository root:

```powershell
& "C:\Users\andre\miniconda3\envs\dssi_env\python.exe" -m pytest `
  tests\test_domain_rag.py tests\test_agent_configuration.py -q
```

The hardened local implementation now includes source hashes, unchanged-file
skipping, transactional refresh, PDF extraction diagnostics, hierarchical
sections, adjacency metadata, FTS5/BM25 lexical search, bounded embedding
retries, source-category filters, and a retrieval evaluation fixture. SQLite
vector scanning remains suitable for a small or moderate local corpus.

The default retrieval provider is `local`, using
`local-feature-hash-v1` together with FTS5/BM25. It requires no OpenAI API key
and sends no paper text to an embedding service. Set
`RAG_EMBEDDING_PROVIDER=openai` only as an explicit future choice.

For each domain question, the agent reports supported answers, facts the corpus
cannot answer, explicitly labeled insights/inferences, and evidence gaps or
next deterministic tests.
