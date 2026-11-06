// Kiểu dữ liệu dùng chung, bám theo OpenAPI (docs/api/openapi.yaml).

/** Mã danh mục văn hoá. */
export type CategoryCode =
  | 'greetings' | 'etiquette' | 'food_dining' | 'gift_giving' | 'festivals' | 'religion_beliefs'
  | 'clothing' | 'arts_music' | 'family_life' | 'heritage' | 'business_culture' | 'taboos';

/** Phạm vi áp dụng của claim. */
export type ClaimScope = 'common_practice' | 'historical_tradition' | 'regional' | 'community_specific';
/** Độ tin cậy của claim. */
export type Confidence = 'verified' | 'partially_supported' | 'unverified';
/** Vòng đời nội dung (BR04). */
export type ContentStatus = 'draft' | 'in_review' | 'published' | 'flagged' | 'archived';

/** Danh mục kèm tên hiển thị và biểu tượng. */
export interface Category {
  code: CategoryCode;
  nameVi: string;
  icon: string;
}

/** Quốc gia. */
export interface Country {
  iso2: string;
  isoNumeric: string; // khớp id trong world-atlas (TopoJSON)
  nameVi: string;
  nameEn: string;
  region: string;
  capital: string;
  languages: string[];
  currency: string;
  flag: string;
  coverage: number; // % ô danh mục có ≥ 3 claim đã duyệt
  featured?: boolean;
}

/** Nguồn trích dẫn. */
export interface Source {
  id: number;
  title: string;
  publisher: string;
  url: string;
  license: string;
  reliabilityTier: 'official' | 'museum' | 'academic' | 'community';
  retrievedAt: string;
}

/** Một phát biểu có nguồn. */
export interface Claim {
  id: number;
  text: string;
  scope: ClaimScope;
  region?: string;
  confidence: Confidence;
  sourceIds: number[];
}

/** Bài viết văn hoá gồm nhiều claim. */
export interface CultureEntry {
  id: number;
  countryIso: string;
  category: CategoryCode;
  title: string;
  summary: string;
  claims: Claim[];
  updatedAt: string;
}

/** Di sản UNESCO. */
export interface HeritageItem {
  id: number;
  name: string;
  type: 'tangible' | 'intangible';
  listType: string;
  inscribedYear: number;
}

/** Trích dẫn trong câu trả lời AI (khớp Citation của OpenAPI). */
export interface Citation {
  id: string;
  sourceId: number;
  excerpt: string;
  // Có khi lấy từ API thật (docs/api/openapi.yaml › Citation)
  chunkId?: number;
  kind?: 'claim' | 'reference' | 'heritage';
  verified?: boolean;
  title?: string;
  publisher?: string;
  url?: string;
  license?: string;
}

/** Độ tin cậy của câu trả lời AI. */
export type ChatConfidence = 'supported' | 'inferred' | 'insufficient' | 'none';
/** Mức giải thích. */
export type ChatLevel = 'simple' | 'normal' | 'deep';

/** Một tin nhắn hiển thị trong khung chat. */
export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
  confidence?: ChatConfidence;
  followUps?: string[];
  unsupportedPoints?: string[];
  messageId?: number;
  rated?: 1 | -1;
  streaming?: boolean;
  error?: boolean;
}

/** Câu trả lời của POST /api/ai/chat (sự kiện `final`). */
export interface ChatAnswer {
  messageId: number;
  sessionId: string;
  answer: string;
  citations: Citation[];
  confidence: ChatConfidence;
  route: 'smalltalk' | 'structured' | 'rag' | 'compare' | 'refused';
  followUpQuestions: string[];
  unsupportedPoints: string[];
  countries: string[];
  model?: string;
}

/** Câu hỏi gợi ý của AI Guide (GET /api/ai/suggestions) — theo quốc gia và chủ đề người dùng quan tâm. */
export interface SuggestedQuestion {
  text: string;
  category: CategoryCode | null;
  country: string | null;
}

/** Kết quả GET /api/ai/suggestions. */
export interface Suggestions {
  country: string | null;
  interests: CategoryCode[];
  questions: SuggestedQuestion[];
}

/** Một khía cạnh so sánh. */
export interface ComparisonRow {
  aspect: string;
  a: { text: string; sourceIds: number[] } | null;
  b: { text: string; sourceIds: number[] } | null;
}

/** Bản so sánh hai nước. */
export interface Comparison {
  countryA: string;
  countryB: string;
  topic: CategoryCode;
  similarities: { text: string; sourceIds: number[] }[];
  rows: ComparisonRow[];
  context: string;
  caveats: string[];
  insufficient: string[];
  reviewedBy: string;
}

/** Câu hỏi quiz. */
export interface QuizQuestion {
  id: number;
  countryIso: string;
  category: CategoryCode;
  difficulty: 'easy' | 'medium' | 'hard';
  question: string;
  options: string[];
  answerIndex: number;
  explanation: string;
  sourceIds: number[];
}

/** Mục trong hàng đợi duyệt. */
export interface ReviewItem {
  id: number;
  type: 'entry' | 'quiz' | 'comparison' | 'feedback';
  title: string;
  country: string;
  origin: 'ai_generated' | 'editor' | 'user_report';
  status: ContentStatus;
  updatedAt: string;
}
