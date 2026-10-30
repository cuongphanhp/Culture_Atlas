# CultureAtlas AI

CultureAtlas AI helps learners explore world cultures, understand *why* customs exist, and compare them with their own culture. It combines an interactive culture map, country profiles built from source-backed claims, an AI Cultural Guide that cites every statement, side-by-side culture comparisons, quizzes, and an editorial back office that keeps the knowledge base trustworthy.

## 1. Requirements — INVEST, Use Cases, and Acceptance Criteria

Requirements define what CultureAtlas AI must do, who uses it, the value delivered, and the observable conditions of success. User stories are reviewed with INVEST and mapped to use cases and acceptance criteria. The guiding rule across all requirements is **"cite a source or don't claim it"**.

### 1.1 Product mind map

![CultureAtlas AI mind map](docs/mindmap.png)

Editable source: [docs/mindmap.xmind](docs/mindmap.xmind) (XMind).

### 1.2 INVEST requirements

The V1 backlog includes 20 user stories. These stories cover the culture map, country profiles, source-backed claims, UNESCO heritage, search, the AI Cultural Guide, culture comparison, quizzes, error reporting, content review, source management, coverage tracking, and data ingestion.
Before a user story is ready for development, it is checked using the INVEST criteria.

| Criterion       | Meaning in CultureAtlas AI                                                                                                     |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Independent** | Each story delivers a clear capability and depends on other stories only when necessary (e.g. published claims can be seeded). |
| **Negotiable**  | UI, ranking algorithms, and models can change as long as the goal and the "cite a source or don't claim it" rule stay intact.  |
| **Valuable**    | Each story helps learners understand, compare, or remember a culture, or helps editors keep content accurate and licensed.     |
| **Estimable**   | Roles, inputs, outputs, API endpoints, tables, dependencies, and failure outcomes (including missing evidence) are documented.  |
| **Small**       | Each story covers one primary capability and can be split into UI, API, retrieval, persistence, and test tasks within a sprint. |
| **Testable**    | Every story maps to observable acceptance criteria, including insufficient-source, authorization, and validation behavior.     |

```text
US01–US05   Cultural Explorer (map, country profile, claims, UNESCO heritage, search)
US06–US10   AI Cultural Guide (streaming answers, citations, refusal, page context, feedback)
US11        Culture Comparison
US12–US13   Culture Quiz
US14        Error reporting
US15–US19   Content administration (sign-in, review, claims, sources, coverage)
US20        Data ingestion
```

All V1 stories have estimable target behavior. AI-generated content always starts as a draft, comparison cells without evidence show "not enough evidence", and the AI Guide answers simple facts from structured data without calling the LLM. The complete story-level review is maintained in [INVEST Requirements](docs/08-invest-requirements.md).

### 1.3 Use cases

```mermaid
flowchart TB
    subgraph roles["Actors"]
        direction LR
        guest(["Guest"])
        learner(["Learner"])
        editor(["Editor"])
        admin(["Administrator"])
    end

    subgraph system["CultureAtlas AI — System Boundary"]
        direction LR
        learnerCases["<b>Guest / Learner</b><br/><br/>UC01 Browse Map & Find Country<br/>UC02 View Country Profile<br/>UC03 Read Entry, Claims & Sources<br/>UC04 View UNESCO Heritage<br/>UC05 Ask AI Cultural Guide<br/>UC06 Rate AI Answer<br/>UC07 Compare Cultures<br/>UC08 Take Quiz<br/>UC09 Report Error<br/>UC10 Sign In (Learner)"]
        editorCases["<b>Editor</b><br/><br/>UC10 Sign In<br/>UC11 Review Content<br/>UC12 Write Entry & Claims<br/>UC13 Manage Sources & Licenses<br/>UC14 Handle Error Reports<br/>UC15 View Coverage<br/>UC16 Generate AI Drafts"]
        adminCases["<b>Administrator</b><br/><br/>UC10 Sign In<br/>UC11–UC16 All Editor Use Cases<br/>UC17 Run Data Ingestion<br/>UC18 Manage Users & Roles<br/>UC19 View RAG Benchmark"]
    end

    subgraph external["External Systems"]
        direction LR
        llm[["LLM Provider"]]
        sources[["UNESCO · Smithsonian · Europeana · REST Countries"]]
    end

    guest --> learnerCases
    learner --> learnerCases
    editor --> editorCases
    admin --> adminCases
    learnerCases -.->|"UC05, UC07"| llm
    editorCases -.->|"UC16"| llm
    adminCases -.->|"UC17"| sources

    classDef actor fill:#666,color:#fff,stroke:#333
    classDef primary fill:#c2552d,color:#fff,stroke:#8f3a1d
    classDef standard fill:#1f6f6b,color:#fff,stroke:#154f4c
    classDef ext fill:#eee,color:#333,stroke:#999
    class guest,learner,editor,admin actor
    class learnerCases primary
    class editorCases,adminCases standard
    class llm,sources ext
    style roles fill:#fff,stroke:#bbb,stroke-dasharray:5 5
    style system fill:#fbf8f3,stroke:#c2552d,stroke-dasharray:5 5
    style external fill:#fff,stroke:#bbb,stroke-dasharray:5 5
```

For detailed actors, permissions, and business flows, see [Actors, roles, and use cases](docs/03-use-cases.md).

### 1.4 Roles and permissions

| Capability                                   | Guest        | Learner         | Editor | Admin |
| -------------------------------------------- | ------------ | --------------- | ------ | ----- |
| Browse map, country profiles, heritage       | Yes          | Yes             | Yes    | Yes   |
| Ask the AI Cultural Guide                    | 10 per day   | Higher limit    | Yes    | Yes   |
| Compare cultures, take quizzes               | Yes          | Yes             | Yes    | Yes   |
| Report errors, rate answers                  | Yes          | Yes             | Yes    | Yes   |
| Save progress / Cultural Passport (post-MVP) | No           | Yes             | No     | No    |
| View draft and in-review content             | No           | No              | Yes    | Yes   |
| Write, review, and publish content           | No           | No              | Yes    | Yes   |
| Manage sources, media, and error reports     | No           | No              | Yes    | Yes   |
| Run data ingestion and RAG benchmark         | No           | No              | No     | Yes   |
| User management                              | No           | No              | No     | Yes   |

The backend must enforce RBAC and the published-only rule for public content; hiding frontend controls serves UI/UX only.

## 2. Information Architecture, Screen Hierarchy, and UI/UX

The information architecture uses **country as the primary axis and topic as the secondary axis**: every piece of content sits on a country × category grid, so navigation, comparison, and coverage tracking share one structure. Sources are always one click away, and the AI Guide is reachable from every content page. Loading, empty, insufficient-source, unreviewed, error, and forbidden states are defined consistently.

### 2.1 Information architecture

```text
Public
├── Explore (map, destinations, themes, festivals this month)
├── Country Profile
│   └── Entry (claims + sources)
├── Theme
├── UNESCO Heritage
├── AI Cultural Guide
├── Culture Comparison
├── Quiz
│   └── Quiz Session
├── Source Detail
└── Sign In

Editorial (Editor / Admin)
├── Review Queue
├── Entries & Claims
├── Sources & Licenses
├── Media & Attribution
├── Error Reports
├── Coverage
├── Data Ingestion      (Admin)
├── RAG Benchmark       (Admin)
├── Users & Roles       (Admin)
└── Forbidden
```

### 2.2 Screen hierarchy

Explore leads to country profiles, themes, and the AI Guide. A country profile opens entries, UNESCO heritage, the AI Guide with the country as context, and a comparison with Vietnam. Every citation chip opens the source detail with its excerpt and license. Quiz results link back to the original entry. Sign-in leads editors to the review queue, which opens the entry/claim editor and source management. Unauthorized navigation resolves to the Forbidden screen.

Detailed screen IDs, user flows, screen states, the design system, and API mappings are maintained in [Information Architecture](docs/04-information-architecture.md).

### 2.3 Current UI prototype

The Angular prototype uses sample custom-and-etiquette content plus **real data snapshots** from UNESCO DataHub (World Heritage and Intangible Heritage lists), Smithsonian Open Access, Europeana, and SCALE. Every country, feature, theme, and festival is illustrated with an openly licensed Wikimedia Commons photo, credited on the image ([credits](src/frontend/public/images/culture/credits.json)).

#### Explore

![Explore](docs/images/01-explorer.png)

#### Country profile

![Country profile](docs/images/02-country-profile.png)

#### AI Cultural Guide

The background follows the countries mentioned in the conversation: one country fills the screen, two countries split it.

| Vietnam vs. Japan | India (Diwali) | France (dining) |
| --- | --- | --- |
| ![AI Guide Vietnam–Japan](docs/images/03-ai-guide.png) | ![AI Guide India](docs/images/07-ai-guide-india.png) | ![AI Guide France](docs/images/08-ai-guide-france.png) |

#### Culture comparison

![Culture comparison](docs/images/04-compare.png)

#### Quiz

![Quiz](docs/images/05-quiz.png)

#### Content administration

![Content administration](docs/images/06-admin.png)

## 3. C4 Architecture

This README presents C1–C3. C4 Level 4 and detailed class and sequence diagrams are in [Section 6](#6-detailed-class-and-sequence-design).

### C1 — System Context

```mermaid
flowchart LR
    learner(["Guest / Learner"])
    editor(["Editor"])
    admin(["Administrator"])

    subgraph boundary[" "]
        atlas["CultureAtlas AI<br/><i>[Software System]</i><br/>Culture map, source-grounded AI guide,<br/>comparisons, quizzes, and content curation"]
    end

    llm["LLM Provider<br/><i>[External System]</i><br/>Generates answers and drafts"]
    unesco["UNESCO DataHub<br/><i>[External System]</i><br/>World Heritage · Intangible Heritage"]
    museums["Smithsonian · Europeana<br/><i>[External System]</i><br/>Museum objects and digital collections"]
    ref["REST Countries · Wikidata · Natural Earth<br/><i>[External System]</i><br/>Country facts, entity links, boundaries"]

    learner -- "explores, asks, compares, takes quizzes" --> atlas
    editor -- "writes and reviews content and sources" --> atlas
    admin -- "runs ingestion, benchmarks, manages users" --> atlas
    atlas -- "prompt + retrieved evidence" --> llm
    atlas -- "scheduled sync" --> unesco
    atlas -- "scheduled sync" --> museums
    atlas -- "scheduled sync" --> ref

    style atlas fill:#c2552d,color:#fff
    style llm fill:#999,color:#fff
    style unesco fill:#999,color:#fff
    style museums fill:#999,color:#fff
    style ref fill:#999,color:#fff
```

### C2 — Container

```mermaid
flowchart TB
    user(["Guest / Learner"])
    staff(["Editor / Administrator"])

    subgraph platform["CultureAtlas AI [Software System Boundary]"]
        direction TB
        subgraph presentation["Presentation"]
            web["Web App<br/><i>[Container: Angular + TypeScript, SSR]</i><br/>Map, country profiles, AI chat,<br/>comparison, quiz, and admin UI"]
        end
        subgraph application["Application"]
            api["API<br/><i>[Container: FastAPI]</i><br/>Content API, AI API (SSE), Admin API,<br/>JWT, RBAC, and rate limiting"]
            worker["Ingestion Worker<br/><i>[Container: Python + APScheduler]</i><br/>Source sync, normalization,<br/>chunking, and embeddings"]
        end
        subgraph data["Data"]
            db[("PostgreSQL 16 + pgvector<br/><i>[Container: Database]</i><br/>Entries, claims, sources, chunks + vectors,<br/>chat logs, and feedback")]
            storage[("Object Storage<br/><i>[Container: S3-compatible]</i><br/>License-verified images")]
        end
    end

    llm["LLM Provider<br/><i>[External System]</i>"]
    sources["UNESCO · Smithsonian · Europeana · REST Countries<br/><i>[External Systems]</i>"]

    user --> web
    staff --> web
    web -- "REST / SSE / HTTPS / JSON" --> api
    api -- "SQL, full-text, vector search" --> db
    api -- "HTTPS" --> llm
    worker -- "HTTPS (scheduled)" --> sources
    worker --> db
    worker --> storage
    web -- "images" --> storage

    style web fill:#1168bd,color:#fff
    style api fill:#1168bd,color:#fff
    style worker fill:#1168bd,color:#fff
    style db fill:#1168bd,color:#fff
    style storage fill:#1168bd,color:#fff
```

### C3 — Component

```mermaid
flowchart TB
    subgraph rt["FastAPI Backend [Container]"]
        direction TB
        http["HTTP API<br/><i>[Component: FastAPI routers]</i><br/>content · ai · auth · admin,<br/>validation and RFC 7807 errors"]
        identity["Identity & Access<br/><i>[Component]</i><br/>JWT, RBAC, guest rate limit"]
        content["Content<br/><i>[Component]</i><br/>Countries, entries, heritage,<br/>search — published only"]
        agent["AI Guide Agent<br/><i>[Component]</i><br/>Question routing, tool calls,<br/>SSE streaming"]
        retrieval["Retrieval<br/><i>[Component]</i><br/>Hybrid FTS + vector search,<br/>RRF fusion, reranking"]
        verifier["Citation Verifier<br/><i>[Component]</i><br/>Every citation must point<br/>to a retrieved chunk"]
        compare["Comparison<br/><i>[Component]</i><br/>Approved cache or AI draft"]
        quiz["Quiz<br/><i>[Component]</i><br/>Published questions, scoring"]
        review["Review & Curation<br/><i>[Component]</i><br/>Approve, revisions, re-index"]
        llmA["LLM Adapter<br/><i>[Component]</i><br/>Provider-agnostic interface"]
        persistence["Persistence<br/><i>[Component: SQLAlchemy]</i><br/>Repositories and transactions"]
    end

    web["Web App<br/><i>[Container: Angular]</i>"]
    db[("PostgreSQL + pgvector<br/><i>[Container: Database]</i>")]
    llm["LLM Provider<br/><i>[External System]</i>"]

    web --> http
    http --> identity
    http --> content
    http --> agent
    http --> compare
    http --> quiz
    http --> review
    agent --> retrieval
    agent --> llmA
    agent --> verifier
    compare --> retrieval
    compare --> llmA
    review -.->|"quiz drafts"| llmA
    content --> persistence
    retrieval --> persistence
    quiz --> persistence
    review --> persistence
    agent -.->|"chat logs"| persistence
    persistence --> db
    llmA --> llm

    style http fill:#1168bd,color:#fff
    style identity fill:#1168bd,color:#fff
    style content fill:#1168bd,color:#fff
    style agent fill:#0b4f9e,color:#fff
    style retrieval fill:#1168bd,color:#fff
    style verifier fill:#1168bd,color:#fff
    style compare fill:#1168bd,color:#fff
    style quiz fill:#1168bd,color:#fff
    style review fill:#1168bd,color:#fff
    style llmA fill:#1168bd,color:#fff
    style persistence fill:#1168bd,color:#fff
```

Key architecture decisions: one PostgreSQL instance for relational data, full-text, and vectors; no external API calls in the user request path (all source data flows through the worker into the database); the LLM sits behind an adapter; a single agent with specialized tools instead of a multi-agent setup.

## 4. Database Diagrams and OpenAPI 3.0 Contract

Step 4 defines the persistence contract and the HTTP contract connecting the Angular frontend to the FastAPI backend.

### 4.1 Database diagrams

The target PostgreSQL model stores content as **claims**: small, verifiable statements, each linked to one or more sources with an evidence excerpt, a scope (common practice, historical tradition, regional, community-specific), and a confidence level. Entries are chunked for hybrid retrieval, and every published change is versioned.

```mermaid
erDiagram
    countries ||--o{ culture_entries : has
    culture_entries ||--o{ claims : contains
    claims ||--|{ claim_sources : "supported by"
    sources ||--o{ claim_sources : supports
    culture_entries ||--o{ entry_revisions : "versioned as"
    culture_entries ||--o{ entry_chunks : "split into"
    culture_entries ||--o{ media_assets : "illustrated by"
    culture_entries ||--o{ quiz_questions : generates
    heritage_items ||--o{ heritage_item_countries : "inscribed for"
    countries ||--o{ heritage_item_countries : owns
    countries ||--o{ comparisons : "country a / b"
    users ||--o{ chat_sessions : opens
    chat_sessions ||--o{ chat_logs : records
    users ||--o{ feedback : submits
    users ||--o{ ingestion_runs : triggers

    countries {
        int id PK
        char iso2 UK
        varchar name_en
        varchar region
        jsonb languages
        jsonb raw_data
    }
    culture_entries {
        bigint id PK
        int country_id FK
        category_code category
        varchar title_en
        content_status status
        content_origin origin
        int version
    }
    claims {
        bigint id PK
        bigint entry_id FK
        text text
        claim_scope scope
        varchar region
        confidence_level confidence
        content_status status
    }
    claim_sources {
        bigint claim_id PK
        bigint source_id PK
        text evidence_excerpt
        varchar locator
    }
    sources {
        bigint id PK
        varchar title
        varchar publisher
        text source_url UK
        varchar license
        reliability_tier reliability_tier
        date retrieved_at
    }
    entry_chunks {
        bigint id PK
        bigint entry_id FK
        text chunk_text
        jsonb metadata
        tsvector tsv
        vector embedding
    }
    heritage_items {
        bigint id PK
        varchar unesco_id UK
        varchar name
        heritage_type type
        smallint inscribed_year
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
        jsonb options
        smallint answer_index
        content_status status
    }
    chat_logs {
        bigint id PK
        uuid session_id FK
        varchar route
        bigint_array cited_chunk_ids
        varchar confidence
        smallint rating
    }
    feedback {
        bigint id PK
        feedback_target target_type
        bigint target_id
        feedback_type type
        feedback_status status
    }
```

The schema enforces key business rules: a trigger blocks publishing a claim without a source, regional claims must name a region, media files are stored only after license verification, and full-text search uses `unaccent` so unaccented Vietnamese queries still match. The schema has been run against `pgvector/pgvector:pg16`.

See the [detailed database diagram](docs/DATABASE.md), [data model](docs/05-data-model.md), [DBML model](src/database/culture_atlas.dbml), and [PostgreSQL schema](src/database/culture_atlas.sql).

### 4.2 OpenAPI 3.0 API documentation

The HTTP contract is defined with OpenAPI 3.0.4 and organized into Countries, Content, Heritage, Search, Quiz, Feedback, AI, Auth, and Admin (Review, Content, Sources, Feedback, Operations, Users).

```text
31 paths
33 operations
Bearer JWT security (optional for guests, required for admin)
x-roles metadata on every admin operation
Server-Sent Events for streaming AI answers
Reusable request/response schemas, including citations and comparisons
RFC 7807-compatible application/problem+json errors
Request, success, and error examples
```

Every operation has a stable `operationId`, documented parameters, request and response schemas, and success/error status codes. The contract passes Redocly CLI validation and is a design source of truth; the backend runtime has not been implemented yet.

- [OpenAPI 3.0.4 specification](docs/api/openapi.yaml)

## 5. Frontend and Backend Folder Structures

### 5.1 Current repository layout

```text
Culture/
├── src/
│   ├── frontend/                     # Angular 22 prototype (standalone components, zoneless)
│   │   ├── src/app/
│   │   │   ├── core/                 # Models, data service, mock data, real source snapshot
│   │   │   ├── shared/components/    # World map, credited photo, scope/confidence/citation badges
│   │   │   └── features/             # Explorer, country, AI guide, compare, quiz, admin
│   │   ├── public/images/            # Wikimedia Commons photos + credits, Smithsonian objects
│   │   └── package.json
│   ├── backend/                      # FastAPI + ingestion worker skeleton
│   │   ├── app/                      # API, core, schemas, domain, repositories, services, ai
│   │   ├── worker/                   # Source ingestion and RAG pipeline
│   │   ├── eval/                     # RAG benchmark
│   │   └── tests/
│   └── database/
│       ├── culture_atlas.sql         # PostgreSQL + pgvector schema, constraints, trigger, view, seeds
│       └── culture_atlas.dbml        # Database relationship model
├── docs/
│   ├── api/                          # OpenAPI contract
│   ├── requirements/                 # Business rules and non-functional requirements
│   ├── mindmap/                      # Mind map data and renderer
│   ├── images/                       # UI screenshots
│   └── 01-scope.md … 08-invest-requirements.md
├── compose.yaml                      # db (pgvector) · api · worker · web
└── README.md
```

The frontend is a working prototype backed by sample content and real source snapshots; it is not yet connected to the API. The backend contains the target module layout with a runnable health endpoint and test. See [Project Progress](#project-progress) for the current checklist.

### 5.2 Target Angular feature structure

```text
src/frontend/src/app/
├── app.component.ts     # Application shell, navigation, language switch
├── app.config.ts        # Providers, router, HTTP client
├── app.routes.ts        # Lazy-loaded feature routes
├── core/
│   ├── models/          # Types mirroring the OpenAPI schemas
│   ├── services/        # API client, auth, SSE chat stream
│   └── interceptors/    # JWT and RFC 7807 error handling
├── shared/
│   └── components/      # Map, photo with attribution, badges, citation chips, states
├── features/
│   ├── explorer/
│   ├── country/
│   ├── entry/
│   ├── heritage/
│   ├── ai-guide/
│   ├── compare/
│   ├── quiz/
│   ├── auth/
│   └── admin/           # review, entries, sources, media, feedback, coverage, ingestion, users
└── styles/              # Design tokens
```

Target dependency flow:

```text
Page/Component → Feature Service → core API client → REST / SSE API
```

### 5.3 Target FastAPI layered structure

```text
src/backend/
├── app/
│   ├── api/             # Presentation: routers for content, ai, auth, admin
│   ├── core/            # Config, database, security (JWT/RBAC), errors, rate limiting
│   ├── schemas/         # Pydantic request/response models matching OpenAPI
│   ├── domain/          # ORM models, enums, business policies
│   ├── repositories/    # SQL, full-text, and vector queries
│   ├── services/        # Content, comparison, quiz, review use cases
│   └── ai/              # Router, agent, tools, retrieval, reranker, LLM adapter, citation verifier, prompts
├── worker/
│   ├── ingest/          # UNESCO, REST Countries, Smithsonian, Europeana, Wikidata
│   └── pipeline/        # Normalize, chunk, embed
├── eval/                # RAG benchmark questions and runner (CI)
└── tests/
```

Dependency rules:

```text
api → services → repositories → database
api → ai.agent → ai.tools → retrieval → repositories
ai.agent → llm_adapter (interface only)
domain → neither api nor repositories
worker → domain + repositories, never api
```

## 6. Detailed Class and Sequence Design

Detailed design derives from the C4 components in Section 3, the database and OpenAPI contracts in Section 4, and the target folder ownership in Section 5. These diagrams are target design views.

### 6.1 C4 Level 4 — Code collaboration

#### L4.1 AI Cultural Guide

```mermaid
flowchart TB
    subgraph guide["AI Cultural Guide [Component]"]
        direction TB
        route["chat()<br/><i>[FastAPI route]</i><br/>Receives ChatRequest,<br/>opens the SSE stream"]
        router["QuestionRouter<br/><i>[Python class]</i><br/>Detects countries, topic,<br/>language, and route"]
        agent["GuideAgent<br/><i>[Python class]</i><br/>Runs tool calls and<br/>assembles evidence"]
        tools["CultureTools<br/><i>[Python class]</i><br/>search_culture, compare_cultures,<br/>get_country_profile, get_source_details"]
        retriever["HybridRetriever<br/><i>[Python class]</i><br/>FTS + vector, RRF, rerank"]
        adapter["LLMAdapter<br/><i>[Python protocol]</i><br/>stream(system, messages, evidence)"]
        verifier["CitationVerifier<br/><i>[Python class]</i><br/>Citations ⊆ retrieved chunks"]
        repo["ChunkRepository<br/><i>[Python class]</i><br/>Implements hybrid SQL"]

        route --> router --> agent
        agent --> tools --> retriever --> repo
        agent --> adapter
        agent --> verifier
    end

    db[("PostgreSQL + pgvector<br/><i>[Container: Database]</i>")]
    llm["LLM Provider<br/><i>[External System]</i>"]
    repo --> db
    adapter --> llm

    style route fill:#1168bd,color:#fff
    style router fill:#1168bd,color:#fff
    style agent fill:#0b4f9e,color:#fff
    style tools fill:#1168bd,color:#fff
    style retriever fill:#1168bd,color:#fff
    style adapter fill:#1168bd,color:#fff
    style verifier fill:#1168bd,color:#fff
    style repo fill:#1168bd,color:#fff
```

#### L4.2 Content Review

```mermaid
flowchart TB
    subgraph review["Review & Curation [Component]"]
        direction TB
        handler["decide_review()<br/><i>[FastAPI route]</i><br/>Maps ReviewDecision to HTTP"]
        service["ReviewService<br/><i>[Python class]</i><br/>Approve, request changes, reject"]
        policy["ContentPolicy<br/><i>[Python class]</i><br/>Status transitions, source rule,<br/>role checks"]
        repo["EntryRepository<br/><i>[Python class]</i><br/>Entries, claims, revisions"]
        reindex["ReindexQueue<br/><i>[Python class]</i><br/>Schedules chunk re-embedding"]

        handler --> service
        service --> policy
        service --> repo
        service --> reindex
    end

    identity["Identity & Access<br/><i>[Component]</i>"]
    db[("PostgreSQL<br/><i>[Container: Database]</i>")]
    worker["Ingestion Worker<br/><i>[Container]</i>"]
    policy --> identity
    repo --> db
    reindex --> worker

    style handler fill:#1168bd,color:#fff
    style service fill:#0b4f9e,color:#fff
    style policy fill:#1168bd,color:#fff
    style repo fill:#1168bd,color:#fff
    style reindex fill:#1168bd,color:#fff
```

### 6.2 Core class diagrams

#### 1. AI Cultural Guide

```mermaid
classDiagram
    direction LR

    class ChatRequest {
        +str message
        +UUID session_id
        +Level level
        +PageContext context
    }
    class RoutedQuestion {
        +list~str~ countries
        +CategoryCode topic
        +str lang
        +Route route
    }
    class QuestionRouter {
        +route(ChatRequest) RoutedQuestion
        -detect_stereotype(str) bool
    }
    class GuideAgent {
        +answer(ChatRequest) AsyncIterator~ChatEvent~
    }
    class CultureTools {
        +search_culture(query, country, category) list~Evidence~
        +compare_cultures(a, b, topic) ComparisonDraft
        +get_country_profile(iso) CountryProfile
    }
    class HybridRetriever {
        +retrieve(query, filters, k) list~Evidence~
        -rrf(fts, vec) list~int~
    }
    class Reranker {
        +rerank(query, evidence, top_n) list~Evidence~
    }
    class LLMAdapter {
        <<interface>>
        +stream(system, messages, evidence) AsyncIterator~str~
    }
    class CitationVerifier {
        +verify(answer, evidence) VerifiedAnswer
    }
    class Evidence {
        +int chunk_id
        +int source_id
        +str text
        +float score
    }
    class VerifiedAnswer {
        +str answer
        +list~Citation~ citations
        +Confidence confidence
        +list~str~ unsupported_points
    }

    GuideAgent --> QuestionRouter
    GuideAgent --> CultureTools
    GuideAgent --> LLMAdapter
    GuideAgent --> CitationVerifier
    CultureTools --> HybridRetriever
    HybridRetriever --> Reranker
    HybridRetriever --> Evidence
    CitationVerifier --> VerifiedAnswer
    QuestionRouter --> RoutedQuestion
    GuideAgent ..> ChatRequest
```

#### 2. Content and Claims

```mermaid
classDiagram
    direction TB

    class CultureEntry {
        +int id
        +int country_id
        +CategoryCode category
        +str title_en
        +ContentStatus status
        +ContentOrigin origin
        +int version
        +publish(actor) void
    }
    class Claim {
        +int id
        +str text
        +ClaimScope scope
        +str region
        +Confidence confidence
        +ContentStatus status
        +has_source() bool
    }
    class ClaimSource {
        +int claim_id
        +int source_id
        +str evidence_excerpt
        +str locator
    }
    class Source {
        +int id
        +str title
        +str publisher
        +str source_url
        +str license
        +ReliabilityTier reliability_tier
        +date retrieved_at
    }
    class ContentPolicy {
        +ensure_can_publish(actor, entry) void
        +ensure_transition(from, to) void
    }
    class ReviewService {
        +approve(type, id, actor) ContentStatus
        +reject(type, id, actor, reason) ContentStatus
    }
    class EntryRepository {
        <<interface>>
        +get(id) CultureEntry
        +save(entry) void
        +add_revision(entry, actor) void
    }

    CultureEntry "1" --> "*" Claim
    Claim "1" --> "1..*" ClaimSource
    ClaimSource "*" --> "1" Source
    ReviewService --> ContentPolicy
    ReviewService --> EntryRepository
    EntryRepository --> CultureEntry
```

### 6.3 Sequence diagrams

Runtime sequences cover asking the AI Guide with citations, comparing cultures, and reviewing AI-generated content. Each sequence maps the user story and OpenAPI operation to its route, service, policy, repository, database interaction, success response, and error paths.

#### Ask the AI Cultural Guide (US06–US08, `POST /ai/chat`)

```mermaid
sequenceDiagram
    autonumber
    actor U as Learner
    participant W as Web App
    participant A as API /ai/chat
    participant R as QuestionRouter
    participant G as GuideAgent
    participant S as HybridRetriever
    participant DB as PostgreSQL + pgvector
    participant L as LLM Provider
    participant V as CitationVerifier

    U->>W: "How does gift-giving differ in Vietnam and Japan?"
    W->>A: POST /ai/chat {message, context: JP}
    A->>A: Rate limit + input guardrail
    A->>R: route(request)
    R-->>A: countries [VN, JP], topic gift_giving, route compare
    A->>G: answer(request)
    G->>S: retrieve(VN, gift_giving) and retrieve(JP, gift_giving)
    S->>DB: FTS + vector, published only, RRF
    DB-->>S: candidate chunks
    S-->>G: top 5–8 after reranking
    alt Not enough evidence
        G-->>W: SSE final {confidence: insufficient}
        G->>DB: feedback(unanswered) for the editorial queue
    else Enough evidence
        G->>L: system prompt + evidence [c1..cn]
        L-->>G: token stream
        G-->>W: SSE tokens
        G->>V: verify(answer, evidence)
        V-->>G: citations, unsupported points
        G-->>W: SSE final ChatAnswer
    end
    G->>DB: INSERT chat_logs (cited chunks, latency, model)
    W-->>U: Answer, citation chips, Vietnam | Japan background
```

#### Review AI-generated content (US16, `POST /admin/review/{targetType}/{id}/decision`)

```mermaid
sequenceDiagram
    autonumber
    actor E as Editor
    participant W as Web App (Admin)
    participant A as Admin API
    participant RV as ReviewService
    participant DB as PostgreSQL
    participant WK as Worker

    E->>W: Open review queue, filter "AI generated"
    W->>A: GET /admin/review-queue?origin=ai_generated
    A-->>W: Draft and in-review items
    E->>W: Check sources, approve
    W->>A: POST /admin/review/quiz_question/901/decision {approve}
    A->>A: require_role(editor)
    A->>RV: approve(id, actor)
    RV->>DB: Update status (source trigger runs)
    alt Claim without source
        DB-->>RV: check_violation
        RV-->>W: 422 application/problem+json
    else Valid
        RV->>DB: status = published, INSERT entry_revisions
        RV->>WK: Enqueue chunk re-index
        RV-->>W: 200 {status: published}
    end
```

## Documentation

- Requirements: [Scope](docs/01-scope.md), [Features](docs/02-features.md), [INVEST backlog](docs/08-invest-requirements.md), [Acceptance criteria](docs/06-acceptance-criteria.md).
- Requirements catalogs: [Business rules](docs/requirements/business-rules.md) and [Non-functional requirements](docs/requirements/non-functional-requirements.md).
- UI/UX: [Information architecture](docs/04-information-architecture.md), [Angular prototype](src/frontend).
- Mind map: [PNG](docs/mindmap.png) and [XMind](docs/mindmap.xmind).
- Database: [Data model](docs/05-data-model.md), [ER diagram](docs/DATABASE.md), [DBML](src/database/culture_atlas.dbml), [PostgreSQL schema](src/database/culture_atlas.sql).
- API contract: [OpenAPI 3.0.4 specification](docs/api/openapi.yaml).

## Project Progress

- [x] Define scope, goals, personas, and user roles
- [x] Write the feature list and use cases
- [x] Write user stories following INVEST
- [x] Write acceptance criteria and business rules
- [x] Write non-functional requirements
- [x] Survey open data sources and capture real snapshots (UNESCO, Smithsonian, Europeana, SCALE)
- [x] Design the information architecture and screen permissions
- [x] Design the screen hierarchy, task flows, and UI states
- [x] Build the Angular UI prototype for the main screens
- [x] Add country-themed backgrounds to the AI Guide
- [x] Design the C4 System Context
- [x] Design the C4 Container
- [x] Design the C4 Component and Code levels
- [x] Design the PostgreSQL + pgvector schema, DBML, and data relationships
- [x] Write the API documentation in OpenAPI 3.0
- [x] Design the Angular frontend folder structure
- [x] Design the FastAPI backend and worker folder structure
- [x] Design class diagrams and sequence diagrams
- [ ] Connect the Angular frontend to the API
- [ ] Implement ingestion for UNESCO, REST Countries, Smithsonian, and Europeana
- [ ] Implement the RAG pipeline (chunking, embeddings, hybrid search, reranking, citation verification)
- [ ] Write source-backed etiquette content for 10 countries × 12 categories
- [ ] Build the 100–150 question RAG benchmark and run it in CI
- [ ] Add Angular SSR, authentication, RBAC, and rate limiting
