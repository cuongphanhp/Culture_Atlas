# Sơ đồ cơ sở dữ liệu (ER — Mermaid)

PostgreSQL 16 + pgvector. Nguồn sự thật: [culture_atlas.dbml](../src/database/culture_atlas.dbml) · Schema chạy được: [culture_atlas.sql](../src/database/culture_atlas.sql) · Từ điển dữ liệu: [05-data-model.md](05-data-model.md).

## 1. Toàn cảnh

```mermaid
erDiagram
    countries ||--o{ culture_entries : has
    culture_entries ||--o{ claims : contains
    claims ||--o{ claim_sources : "supported by"
    sources ||--o{ claim_sources : supports
    culture_entries ||--o{ entry_revisions : "versioned as"
    culture_entries ||--o{ entry_chunks : "split into"
    culture_entries ||--o{ media_assets : "illustrated by"
    sources ||--o{ media_assets : "credited to"
    culture_entries ||--o{ entry_tags : tagged
    tags ||--o{ entry_tags : labels
    culture_entries ||--o{ quiz_questions : generates
    heritage_items ||--o{ heritage_item_countries : "inscribed for"
    countries ||--o{ heritage_item_countries : owns
    sources ||--o{ heritage_items : describes
    countries ||--o{ comparisons : "country_a"
    countries ||--o{ comparisons : "country_b"
    users ||--o{ culture_entries : "creates / reviews"
    users ||--o{ user_progress : tracks
    quiz_questions ||--o{ user_progress : "answered in"
    users ||--o{ chat_sessions : opens
    chat_sessions ||--o{ chat_logs : records
    users ||--o{ feedback : submits
    users ||--o{ ingestion_runs : triggers
```

## 2. Lõi nội dung có nguồn

```mermaid
erDiagram
    countries {
        int id PK
        char iso2 UK "ISO 3166-1 alpha-2"
        char iso_numeric UK
        varchar name_vi
        varchar name_en
        varchar region
        varchar capital
        jsonb languages
        jsonb currencies
        jsonb raw_data "snapshot REST Countries"
    }
    culture_entries {
        bigint id PK
        int country_id FK
        category_code category
        varchar title_vi
        text summary
        content_status status
        content_origin origin
        int version
        bigint reviewed_by FK
    }
    claims {
        bigint id PK
        bigint entry_id FK
        text text
        claim_scope scope
        varchar region "bắt buộc khi regional"
        confidence_level confidence
        content_status status
    }
    claim_sources {
        bigint claim_id PK,FK
        bigint source_id PK,FK
        text evidence_excerpt
        varchar locator
    }
    sources {
        bigint id PK
        varchar title
        varchar publisher
        text source_url UK
        source_type source_type
        varchar license
        reliability_tier reliability_tier
        date retrieved_at
    }
    entry_revisions {
        bigint id PK
        bigint entry_id FK
        int version
        jsonb snapshot
        bigint changed_by FK
    }
    countries ||--o{ culture_entries : has
    culture_entries ||--o{ claims : contains
    claims ||--|{ claim_sources : "≥1 khi published"
    sources ||--o{ claim_sources : supports
    culture_entries ||--o{ entry_revisions : versions
```

## 3. RAG, AI và phản hồi

```mermaid
erDiagram
    entry_chunks {
        bigint id PK
        bigint entry_id FK
        bigint_array claim_ids
        text chunk_text
        varchar language
        jsonb metadata "country, category, scope, source_ids"
        tsvector tsv "GIN, ca_simple + unaccent"
        vector embedding "1024d, HNSW cosine"
    }
    chat_sessions {
        uuid id PK
        bigint user_id FK "null = Khách"
        varchar anon_key
        jsonb context
    }
    chat_logs {
        bigint id PK
        uuid session_id FK
        text question
        text answer
        varchar route "structured | rag | compare | refused"
        bigint_array cited_chunk_ids
        varchar confidence
        varchar model
        int latency_ms
        smallint rating
    }
    comparisons {
        bigint id PK
        int country_a_id FK
        int country_b_id FK
        category_code topic
        jsonb result
        content_status status
    }
    quiz_questions {
        bigint id PK
        bigint entry_id FK
        text question
        jsonb options
        smallint answer_index
        text explanation
        difficulty_level difficulty
        content_status status
    }
    feedback {
        bigint id PK
        feedback_target target_type
        bigint target_id
        feedback_type type
        feedback_status status
    }
    culture_entries ||--o{ entry_chunks : "split into"
    chat_sessions ||--o{ chat_logs : records
    culture_entries ||--o{ quiz_questions : generates
```

## 4. Dữ liệu ngoài và vận hành

```mermaid
erDiagram
    heritage_items {
        bigint id PK
        varchar unesco_id UK
        varchar name
        heritage_type type
        varchar list_type
        smallint inscribed_year
        numeric lat
        numeric lng
        bigint source_id FK
    }
    heritage_item_countries {
        bigint heritage_item_id PK,FK
        int country_id PK,FK
    }
    media_assets {
        bigint id PK
        bigint entry_id FK
        text url
        text stored_url "chỉ khi verified"
        varchar license
        text attribution_text
        boolean verified
    }
    ingestion_runs {
        bigint id PK
        varchar source_name
        run_status status
        int records_in
        int records_changed
        jsonb errors
    }
    users {
        bigint id PK
        varchar email UK
        user_role role
        varchar locale
        jsonb preferences
    }
    heritage_items ||--o{ heritage_item_countries : "inscribed for"
    users ||--o{ ingestion_runs : triggers
```
