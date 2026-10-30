-- CultureAtlas AI — PostgreSQL 16 + pgvector schema (MVP)
-- Nguồn sự thật mô hình: culture_atlas.dbml

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Cấu hình full-text: simple + unaccent để tìm tiếng Việt không dấu
CREATE TEXT SEARCH CONFIGURATION ca_simple (COPY = simple);
ALTER TEXT SEARCH CONFIGURATION ca_simple ALTER MAPPING FOR hword, hword_part, word WITH unaccent, simple;

-- ===== Enum =====
CREATE TYPE user_role        AS ENUM ('learner', 'editor', 'admin');
CREATE TYPE content_status   AS ENUM ('draft', 'in_review', 'published', 'flagged', 'archived');
CREATE TYPE category_code    AS ENUM ('greetings', 'etiquette', 'food_dining', 'gift_giving', 'festivals', 'religion_beliefs',
                                      'clothing', 'arts_music', 'family_life', 'heritage', 'business_culture', 'taboos');
CREATE TYPE claim_scope      AS ENUM ('common_practice', 'historical_tradition', 'regional', 'community_specific');
CREATE TYPE confidence_level AS ENUM ('verified', 'partially_supported', 'unverified');
CREATE TYPE reliability_tier AS ENUM ('official', 'museum', 'academic', 'community');
CREATE TYPE source_type      AS ENUM ('api_dataset', 'official_site', 'museum', 'academic', 'editorial', 'encyclopedia');
CREATE TYPE heritage_type    AS ENUM ('tangible', 'intangible');
CREATE TYPE difficulty_level AS ENUM ('easy', 'medium', 'hard');
CREATE TYPE feedback_type    AS ENUM ('factual_error', 'stereotype', 'missing_source', 'unanswered', 'other');
CREATE TYPE feedback_status  AS ENUM ('open', 'in_progress', 'resolved', 'dismissed');
CREATE TYPE feedback_target  AS ENUM ('entry', 'claim', 'chat_message', 'comparison', 'quiz_question');
CREATE TYPE content_origin   AS ENUM ('editor', 'ai_generated', 'imported');
CREATE TYPE run_status       AS ENUM ('running', 'succeeded', 'failed');

-- ===== Người dùng =====
CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255),
  display_name  VARCHAR(120),
  role          user_role   NOT NULL DEFAULT 'learner',
  locale        VARCHAR(5)  NOT NULL DEFAULT 'vi',
  preferences   JSONB       NOT NULL DEFAULT '{}',
  is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== Quốc gia & nguồn =====
CREATE TABLE countries (
  id           SERIAL PRIMARY KEY,
  iso2         CHAR(2) NOT NULL UNIQUE,
  iso3         CHAR(3) NOT NULL UNIQUE,
  iso_numeric  CHAR(3) NOT NULL UNIQUE,
  name_vi      VARCHAR(120) NOT NULL,
  name_en      VARCHAR(120) NOT NULL,
  region       VARCHAR(80)  NOT NULL,
  subregion    VARCHAR(80),
  capital      VARCHAR(120),
  languages    JSONB NOT NULL DEFAULT '[]',
  currencies   JSONB NOT NULL DEFAULT '[]',
  neighbors    CHAR(2)[],
  geometry_ref VARCHAR(60),
  is_featured  BOOLEAN NOT NULL DEFAULT FALSE,
  raw_data     JSONB,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sources (
  id               BIGSERIAL PRIMARY KEY,
  title            VARCHAR(500) NOT NULL,
  publisher        VARCHAR(255) NOT NULL,
  source_url       TEXT NOT NULL UNIQUE,
  source_type      source_type NOT NULL,
  license          VARCHAR(120) NOT NULL,
  reliability_tier reliability_tier NOT NULL,
  language         VARCHAR(5),
  retrieved_at     DATE NOT NULL,
  raw_ref          TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== Nội dung =====
CREATE TABLE culture_entries (
  id          BIGSERIAL PRIMARY KEY,
  country_id  INT NOT NULL REFERENCES countries(id),
  category    category_code NOT NULL,
  slug        VARCHAR(160) NOT NULL,
  title_vi    VARCHAR(255) NOT NULL,
  title_en    VARCHAR(255),
  summary     TEXT,
  content     TEXT,
  scope       claim_scope,
  region      VARCHAR(120),
  period      VARCHAR(60),
  status      content_status NOT NULL DEFAULT 'draft',
  origin      content_origin NOT NULL DEFAULT 'editor',
  version     INT NOT NULL DEFAULT 1,
  created_by  BIGINT REFERENCES users(id),
  reviewed_by BIGINT REFERENCES users(id),
  reviewed_at TIMESTAMPTZ,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (country_id, slug)
);
CREATE INDEX ix_entries_country_cat_status ON culture_entries (country_id, category, status);

CREATE TABLE entry_revisions (
  id          BIGSERIAL PRIMARY KEY,
  entry_id    BIGINT NOT NULL REFERENCES culture_entries(id) ON DELETE CASCADE,
  version     INT NOT NULL,
  snapshot    JSONB NOT NULL,
  changed_by  BIGINT REFERENCES users(id),
  change_note TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (entry_id, version)
);

CREATE TABLE claims (
  id          BIGSERIAL PRIMARY KEY,
  entry_id    BIGINT NOT NULL REFERENCES culture_entries(id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  language    VARCHAR(5) NOT NULL DEFAULT 'vi',
  scope       claim_scope NOT NULL,
  region      VARCHAR(120),
  period      VARCHAR(60) DEFAULT 'contemporary',
  confidence  confidence_level NOT NULL DEFAULT 'unverified',
  status      content_status NOT NULL DEFAULT 'draft',
  position    INT NOT NULL DEFAULT 0,
  reviewed_by BIGINT REFERENCES users(id),
  reviewed_at TIMESTAMPTZ,
  CONSTRAINT ck_claim_region CHECK (scope <> 'regional' OR region IS NOT NULL)          -- BR05
);
CREATE INDEX ix_claims_entry ON claims (entry_id, position);

CREATE TABLE claim_sources (
  claim_id         BIGINT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  source_id        BIGINT NOT NULL REFERENCES sources(id),
  evidence_excerpt TEXT NOT NULL,
  locator          VARCHAR(120),
  PRIMARY KEY (claim_id, source_id)
);

-- BR01/AC17.1: không xuất bản claim không có nguồn
CREATE FUNCTION trg_claim_requires_source() RETURNS trigger AS $$
BEGIN
  IF NEW.status = 'published' AND NOT EXISTS (SELECT 1 FROM claim_sources WHERE claim_id = NEW.id) THEN
    RAISE EXCEPTION 'Claim % cannot be published without a source', NEW.id USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER claim_requires_source BEFORE UPDATE OF status ON claims
  FOR EACH ROW EXECUTE FUNCTION trg_claim_requires_source();

-- ===== RAG =====
CREATE TABLE entry_chunks (
  id          BIGSERIAL PRIMARY KEY,
  entry_id    BIGINT NOT NULL REFERENCES culture_entries(id) ON DELETE CASCADE,
  claim_ids   BIGINT[],
  chunk_text  TEXT NOT NULL,
  language    VARCHAR(5) NOT NULL,
  metadata    JSONB NOT NULL,
  tsv         TSVECTOR GENERATED ALWAYS AS (to_tsvector('ca_simple', chunk_text)) STORED,
  embedding   VECTOR(1024),
  token_count INT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_chunks_tsv       ON entry_chunks USING GIN (tsv);
CREATE INDEX ix_chunks_metadata  ON entry_chunks USING GIN (metadata jsonb_path_ops);
CREATE INDEX ix_chunks_embedding ON entry_chunks USING hnsw (embedding vector_cosine_ops);

-- ===== Phân loại & media =====
CREATE TABLE tags (
  id   SERIAL PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  kind VARCHAR(30) NOT NULL
);
CREATE TABLE entry_tags (
  entry_id BIGINT REFERENCES culture_entries(id) ON DELETE CASCADE,
  tag_id   INT REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (entry_id, tag_id)
);

CREATE TABLE media_assets (
  id               BIGSERIAL PRIMARY KEY,
  entry_id         BIGINT REFERENCES culture_entries(id) ON DELETE SET NULL,
  source_id        BIGINT REFERENCES sources(id),
  url              TEXT NOT NULL,
  stored_url       TEXT,
  author           VARCHAR(255),
  license          VARCHAR(120) NOT NULL,
  attribution_text TEXT NOT NULL,
  verified         BOOLEAN NOT NULL DEFAULT FALSE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_media_stored_only_if_verified CHECK (stored_url IS NULL OR verified)     -- BR09
);

-- ===== Di sản UNESCO =====
CREATE TABLE heritage_items (
  id             BIGSERIAL PRIMARY KEY,
  unesco_id      VARCHAR(30) NOT NULL UNIQUE,
  name           VARCHAR(500) NOT NULL,
  type           heritage_type NOT NULL,
  list_type      VARCHAR(120) NOT NULL,
  inscribed_year SMALLINT,
  criteria       VARCHAR(60),
  lat            NUMERIC(9,6),
  lng            NUMERIC(9,6),
  source_id      BIGINT REFERENCES sources(id),
  raw_data       JSONB
);
CREATE TABLE heritage_item_countries (
  heritage_item_id BIGINT REFERENCES heritage_items(id) ON DELETE CASCADE,
  country_id       INT REFERENCES countries(id),
  PRIMARY KEY (heritage_item_id, country_id)
);

-- ===== So sánh & quiz =====
CREATE TABLE comparisons (
  id           BIGSERIAL PRIMARY KEY,
  country_a_id INT NOT NULL REFERENCES countries(id),
  country_b_id INT NOT NULL REFERENCES countries(id),
  topic        category_code NOT NULL,
  language     VARCHAR(5) NOT NULL DEFAULT 'vi',
  result       JSONB NOT NULL,
  status       content_status NOT NULL DEFAULT 'draft',
  origin       content_origin NOT NULL DEFAULT 'ai_generated',
  reviewed_by  BIGINT REFERENCES users(id),
  reviewed_at  TIMESTAMPTZ,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_cmp_distinct CHECK (country_a_id <> country_b_id),
  UNIQUE (country_a_id, country_b_id, topic, language)
);

CREATE TABLE quiz_questions (
  id           BIGSERIAL PRIMARY KEY,
  entry_id     BIGINT NOT NULL REFERENCES culture_entries(id) ON DELETE CASCADE,
  question     TEXT NOT NULL,
  options      JSONB NOT NULL,
  answer_index SMALLINT NOT NULL,
  explanation  TEXT NOT NULL,
  difficulty   difficulty_level NOT NULL,
  language     VARCHAR(5) NOT NULL DEFAULT 'vi',
  status       content_status NOT NULL DEFAULT 'draft',
  origin       content_origin NOT NULL DEFAULT 'ai_generated',
  reviewed_by  BIGINT REFERENCES users(id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_quiz_answer CHECK (answer_index >= 0 AND answer_index < jsonb_array_length(options))
);

CREATE TABLE user_progress (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entry_id         BIGINT REFERENCES culture_entries(id),
  quiz_question_id BIGINT REFERENCES quiz_questions(id),
  is_correct       BOOLEAN,
  quiz_score       NUMERIC(5,2),
  completed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== Chat, phản hồi, đồng bộ =====
CREATE TABLE chat_sessions (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    BIGINT REFERENCES users(id) ON DELETE SET NULL,
  anon_key   VARCHAR(64),
  context    JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_logs (
  id                BIGSERIAL PRIMARY KEY,
  session_id        UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  question          TEXT NOT NULL,
  answer            TEXT,
  language          VARCHAR(5),
  route             VARCHAR(20),
  cited_chunk_ids   BIGINT[],
  confidence        VARCHAR(20),
  model             VARCHAR(80),
  latency_ms        INT,
  prompt_tokens     INT,
  completion_tokens INT,
  rating            SMALLINT CHECK (rating IN (-1, 1)),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_chat_logs_session ON chat_logs (session_id, created_at);

CREATE TABLE feedback (
  id          BIGSERIAL PRIMARY KEY,
  target_type feedback_target NOT NULL,
  target_id   BIGINT NOT NULL,
  user_id     BIGINT REFERENCES users(id),
  type        feedback_type NOT NULL,
  comment     TEXT CHECK (char_length(comment) <= 1000),
  status      feedback_status NOT NULL DEFAULT 'open',
  handled_by  BIGINT REFERENCES users(id),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);
CREATE INDEX ix_feedback_target ON feedback (target_type, target_id);

CREATE TABLE ingestion_runs (
  id              BIGSERIAL PRIMARY KEY,
  source_name     VARCHAR(80) NOT NULL,
  status          run_status NOT NULL DEFAULT 'running',
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at     TIMESTAMPTZ,
  records_in      INT DEFAULT 0,
  records_changed INT DEFAULT 0,
  errors          JSONB DEFAULT '[]',
  triggered_by    BIGINT REFERENCES users(id)
);

-- ===== View: độ phủ quốc gia × danh mục (SCR25) =====
CREATE VIEW v_coverage AS
SELECT c.iso2, cat.code AS category,
       COUNT(cl.id) FILTER (WHERE cl.status = 'published') AS published_claims
FROM countries c
CROSS JOIN unnest(enum_range(NULL::category_code)) AS cat(code)
LEFT JOIN culture_entries e ON e.country_id = c.id AND e.category = cat.code AND e.status = 'published'
LEFT JOIN claims cl ON cl.entry_id = e.id
GROUP BY c.iso2, cat.code;

-- ===== Seed tối thiểu =====
INSERT INTO countries (iso2, iso3, iso_numeric, name_vi, name_en, region, capital, is_featured) VALUES
  ('VN','VNM','704','Việt Nam','Vietnam','Đông Nam Á','Hà Nội',TRUE),
  ('TH','THA','764','Thái Lan','Thailand','Đông Nam Á','Bangkok',FALSE),
  ('JP','JPN','392','Nhật Bản','Japan','Đông Á','Tokyo',TRUE),
  ('KR','KOR','410','Hàn Quốc','South Korea','Đông Á','Seoul',TRUE),
  ('CN','CHN','156','Trung Quốc','China','Đông Á','Bắc Kinh',FALSE),
  ('IN','IND','356','Ấn Độ','India','Nam Á','New Delhi',FALSE),
  ('FR','FRA','250','Pháp','France','Châu Âu','Paris',TRUE),
  ('MX','MEX','484','Mexico','Mexico','Châu Mỹ','Thành phố Mexico',FALSE),
  ('EG','EGY','818','Ai Cập','Egypt','Trung Đông – Bắc Phi','Cairo',FALSE),
  ('KE','KEN','404','Kenya','Kenya','Châu Phi cận Sahara','Nairobi',FALSE);
