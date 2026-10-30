// Kiểu dữ liệu dùng chung, bám theo OpenAPI (docs/api/openapi.yaml).

export type CategoryCode =
  | 'greetings' | 'etiquette' | 'food_dining' | 'gift_giving' | 'festivals' | 'religion_beliefs'
  | 'clothing' | 'arts_music' | 'family_life' | 'heritage' | 'business_culture' | 'taboos';

export type ClaimScope = 'common_practice' | 'historical_tradition' | 'regional' | 'community_specific';
export type Confidence = 'verified' | 'partially_supported' | 'unverified';
export type ContentStatus = 'draft' | 'in_review' | 'published' | 'flagged' | 'archived';

export interface Category {
  code: CategoryCode;
  nameVi: string;
  icon: string;
}

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

export interface Source {
  id: number;
  title: string;
  publisher: string;
  url: string;
  license: string;
  reliabilityTier: 'official' | 'museum' | 'academic' | 'community';
  retrievedAt: string;
}

export interface Claim {
  id: number;
  text: string;
  scope: ClaimScope;
  region?: string;
  confidence: Confidence;
  sourceIds: number[];
}

export interface CultureEntry {
  id: number;
  countryIso: string;
  category: CategoryCode;
  title: string;
  summary: string;
  claims: Claim[];
  updatedAt: string;
}

export interface HeritageItem {
  id: number;
  name: string;
  type: 'tangible' | 'intangible';
  listType: string;
  inscribedYear: number;
}

export interface Citation {
  id: string;
  sourceId: number;
  excerpt: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
  confidence?: 'supported' | 'inferred' | 'insufficient';
  followUps?: string[];
  unsupportedPoints?: string[];
}

export interface ComparisonRow {
  aspect: string;
  a: { text: string; sourceIds: number[] } | null;
  b: { text: string; sourceIds: number[] } | null;
}

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

export interface ReviewItem {
  id: number;
  type: 'entry' | 'quiz' | 'comparison' | 'feedback';
  title: string;
  country: string;
  origin: 'ai_generated' | 'editor' | 'user_report';
  status: ContentStatus;
  updatedAt: string;
}
