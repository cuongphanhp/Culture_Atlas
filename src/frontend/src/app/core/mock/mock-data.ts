// DỮ LIỆU MẪU cho prototype giao diện — chưa qua biên tập, không dùng làm nội dung thật.
import {
  Category, ChatMessage, Comparison, Country, CultureEntry, HeritageItem, QuizQuestion, ReviewItem, Source,
} from '../models/culture.models';

export const CATEGORIES: Category[] = [
  { code: 'greetings', nameVi: 'Chào hỏi', icon: '🙏' },
  { code: 'etiquette', nameVi: 'Phép lịch sự', icon: '🤝' },
  { code: 'food_dining', nameVi: 'Ẩm thực & bàn ăn', icon: '🍜' },
  { code: 'gift_giving', nameVi: 'Tặng quà', icon: '🎁' },
  { code: 'festivals', nameVi: 'Lễ hội', icon: '🏮' },
  { code: 'religion_beliefs', nameVi: 'Tín ngưỡng', icon: '⛩️' },
  { code: 'clothing', nameVi: 'Trang phục', icon: '👘' },
  { code: 'arts_music', nameVi: 'Nghệ thuật & âm nhạc', icon: '🎭' },
  { code: 'family_life', nameVi: 'Gia đình', icon: '🏠' },
  { code: 'heritage', nameVi: 'Di sản', icon: '🏯' },
  { code: 'business_culture', nameVi: 'Văn hoá công sở', icon: '💼' },
  { code: 'taboos', nameVi: 'Điều kiêng kỵ', icon: '⚠️' },
];

export const COUNTRIES: Country[] = [
  { iso2: 'VN', isoNumeric: '704', nameVi: 'Việt Nam', nameEn: 'Vietnam', region: 'Đông Nam Á', capital: 'Hà Nội', languages: ['Tiếng Việt'], currency: 'Đồng (VND)', flag: '🇻🇳', coverage: 92, featured: true },
  { iso2: 'TH', isoNumeric: '764', nameVi: 'Thái Lan', nameEn: 'Thailand', region: 'Đông Nam Á', capital: 'Bangkok', languages: ['Tiếng Thái'], currency: 'Baht (THB)', flag: '🇹🇭', coverage: 71 },
  { iso2: 'JP', isoNumeric: '392', nameVi: 'Nhật Bản', nameEn: 'Japan', region: 'Đông Á', capital: 'Tokyo', languages: ['Tiếng Nhật'], currency: 'Yên (JPY)', flag: '🇯🇵', coverage: 88, featured: true },
  { iso2: 'KR', isoNumeric: '410', nameVi: 'Hàn Quốc', nameEn: 'South Korea', region: 'Đông Á', capital: 'Seoul', languages: ['Tiếng Hàn'], currency: 'Won (KRW)', flag: '🇰🇷', coverage: 79, featured: true },
  { iso2: 'CN', isoNumeric: '156', nameVi: 'Trung Quốc', nameEn: 'China', region: 'Đông Á', capital: 'Bắc Kinh', languages: ['Tiếng Trung (Quan thoại)'], currency: 'Nhân dân tệ (CNY)', flag: '🇨🇳', coverage: 64 },
  { iso2: 'IN', isoNumeric: '356', nameVi: 'Ấn Độ', nameEn: 'India', region: 'Nam Á', capital: 'New Delhi', languages: ['Hindi', 'Tiếng Anh'], currency: 'Rupee (INR)', flag: '🇮🇳', coverage: 58 },
  { iso2: 'FR', isoNumeric: '250', nameVi: 'Pháp', nameEn: 'France', region: 'Châu Âu', capital: 'Paris', languages: ['Tiếng Pháp'], currency: 'Euro (EUR)', flag: '🇫🇷', coverage: 75, featured: true },
  { iso2: 'MX', isoNumeric: '484', nameVi: 'Mexico', nameEn: 'Mexico', region: 'Châu Mỹ', capital: 'Thành phố Mexico', languages: ['Tiếng Tây Ban Nha'], currency: 'Peso (MXN)', flag: '🇲🇽', coverage: 52 },
  { iso2: 'EG', isoNumeric: '818', nameVi: 'Ai Cập', nameEn: 'Egypt', region: 'Trung Đông – Bắc Phi', capital: 'Cairo', languages: ['Tiếng Ả Rập'], currency: 'Bảng Ai Cập (EGP)', flag: '🇪🇬', coverage: 47 },
  { iso2: 'KE', isoNumeric: '404', nameVi: 'Kenya', nameEn: 'Kenya', region: 'Châu Phi cận Sahara', capital: 'Nairobi', languages: ['Tiếng Swahili', 'Tiếng Anh'], currency: 'Shilling (KES)', flag: '🇰🇪', coverage: 33 },
];

export const SOURCES: Source[] = [
  { id: 42, title: 'Japanese etiquette & manners', publisher: 'Japan National Tourism Organization', url: 'https://www.japan.travel', license: 'Trích dẫn ngắn – liên kết nguồn', reliabilityTier: 'official', retrievedAt: '2026-09-12' },
  { id: 43, title: 'Washoku, traditional dietary cultures of the Japanese', publisher: 'UNESCO Intangible Cultural Heritage', url: 'https://ich.unesco.org', license: 'Kiểm tra theo từng bản ghi', reliabilityTier: 'official', retrievedAt: '2026-09-02' },
  { id: 51, title: 'Bài biên tập: Tặng quà ở Nhật Bản', publisher: 'CultureAtlas Editorial', url: 'https://cultureatlas.example/editorial/jp-gift', license: 'CC BY 4.0', reliabilityTier: 'academic', retrievedAt: '2026-10-01' },
  { id: 61, title: 'Phong tục Tết cổ truyền Việt Nam', publisher: 'Cổng thông tin Du lịch Việt Nam', url: 'https://vietnam.travel', license: 'Trích dẫn ngắn – liên kết nguồn', reliabilityTier: 'official', retrievedAt: '2026-09-20' },
  { id: 62, title: 'Bài biên tập: Tặng quà ở Việt Nam', publisher: 'CultureAtlas Editorial', url: 'https://cultureatlas.example/editorial/vn-gift', license: 'CC BY 4.0', reliabilityTier: 'academic', retrievedAt: '2026-10-03' },
  { id: 81, title: 'Gastronomic meal of the French', publisher: 'UNESCO Intangible Cultural Heritage', url: 'https://ich.unesco.org/en/RL/00437', license: 'CC BY-SA 4.0 (DataHub ich001)', reliabilityTier: 'official', retrievedAt: '2026-10-30' },
  { id: 82, title: 'Bài biên tập: Bữa ăn gia đình ở Pháp', publisher: 'CultureAtlas Editorial', url: 'https://cultureatlas.example/editorial/fr-dining', license: 'CC BY 4.0', reliabilityTier: 'academic', retrievedAt: '2026-10-05' },
  { id: 91, title: 'Bài biên tập: Diwali — lễ hội ánh sáng', publisher: 'CultureAtlas Editorial', url: 'https://cultureatlas.example/editorial/in-diwali', license: 'CC BY 4.0', reliabilityTier: 'academic', retrievedAt: '2026-10-07' },
  { id: 71, title: 'World Heritage List — Japan', publisher: 'UNESCO World Heritage Centre', url: 'https://whc.unesco.org', license: 'CC BY-SA 4.0 (DataHub)', reliabilityTier: 'official', retrievedAt: '2026-08-30' },
];

export const ENTRIES: CultureEntry[] = [
  {
    id: 1201, countryIso: 'JP', category: 'gift_giving', title: 'Tặng quà ở Nhật Bản',
    summary: 'Tặng quà gắn với quan hệ và sự chu đáo: cách gói, cách trao và thời điểm trao thường được chú ý không kém món quà.',
    updatedAt: '2026-10-15',
    claims: [
      { id: 1, text: 'Khi trao và nhận quà, người ta thường dùng hai tay.', scope: 'common_practice', confidence: 'verified', sourceIds: [42, 51] },
      { id: 2, text: 'Sau chuyến đi xa, nhiều người mua omiyage (đặc sản địa phương) làm quà cho đồng nghiệp và gia đình.', scope: 'common_practice', confidence: 'verified', sourceIds: [51] },
      { id: 3, text: 'Nhiều người tránh tặng quà theo bộ bốn món vì "shi" (bốn) đồng âm với chữ "tử".', scope: 'common_practice', confidence: 'partially_supported', sourceIds: [51] },
      { id: 4, text: 'Mùa ochūgen (giữa năm) và oseibo (cuối năm) là dịp tặng quà theo truyền thống cho người mình mang ơn.', scope: 'historical_tradition', confidence: 'verified', sourceIds: [42] },
    ],
  },
  {
    id: 1202, countryIso: 'JP', category: 'greetings', title: 'Chào hỏi và cúi chào (ojigi)',
    summary: 'Cúi chào là hình thức chào phổ biến; độ sâu và thời gian cúi thay đổi theo mức độ trang trọng.',
    updatedAt: '2026-10-11',
    claims: [
      { id: 5, text: 'Cúi chào được dùng để chào, cảm ơn và xin lỗi; cúi sâu hơn thể hiện trang trọng hơn.', scope: 'common_practice', confidence: 'verified', sourceIds: [42] },
      { id: 6, text: 'Trong môi trường kinh doanh quốc tế, bắt tay kèm cúi nhẹ cũng thường gặp.', scope: 'community_specific', confidence: 'partially_supported', sourceIds: [51] },
    ],
  },
  {
    id: 1203, countryIso: 'JP', category: 'food_dining', title: 'Ẩm thực và phép tắc bàn ăn',
    summary: 'Washoku được UNESCO ghi danh năm 2013 như một tập quán xã hội gắn với sự tôn trọng thiên nhiên.',
    updatedAt: '2026-10-08',
    claims: [
      { id: 7, text: 'Washoku được ghi danh vào Danh sách Di sản văn hoá phi vật thể đại diện của nhân loại năm 2013.', scope: 'common_practice', confidence: 'verified', sourceIds: [43] },
      { id: 8, text: 'Cắm đũa thẳng đứng vào bát cơm thường bị tránh vì gợi liên tưởng đến nghi thức tang lễ.', scope: 'common_practice', confidence: 'verified', sourceIds: [42] },
    ],
  },
];

export const FIRST_TIME_TIPS: Record<string, { text: string; sourceId: number }[]> = {
  JP: [
    { text: 'Cúi chào là cách chào phổ biến; không cần cúi sâu nếu bạn là khách.', sourceId: 42 },
    { text: 'Trao và nhận quà, danh thiếp bằng hai tay.', sourceId: 51 },
    { text: 'Không cắm đũa thẳng đứng vào bát cơm.', sourceId: 42 },
    { text: 'Cởi giày khi vào nhà và một số nhà hàng truyền thống.', sourceId: 42 },
    { text: 'Nói chuyện nhỏ nhẹ trên tàu điện, hạn chế nghe điện thoại.', sourceId: 42 },
  ],
};

export const HERITAGE: Record<string, HeritageItem[]> = {
  JP: [
    { id: 1, name: 'Himeji-jo', type: 'tangible', listType: 'Di sản Thế giới — Văn hoá', inscribedYear: 1993 },
    { id: 2, name: 'Di tích lịch sử cố đô Kyoto', type: 'tangible', listType: 'Di sản Thế giới — Văn hoá', inscribedYear: 1994 },
    { id: 3, name: 'Fujisan, nơi linh thiêng và nguồn cảm hứng nghệ thuật', type: 'tangible', listType: 'Di sản Thế giới — Văn hoá', inscribedYear: 2013 },
    { id: 4, name: 'Kịch Kabuki', type: 'intangible', listType: 'Danh sách đại diện ICH', inscribedYear: 2008 },
    { id: 5, name: 'Washoku', type: 'intangible', listType: 'Danh sách đại diện ICH', inscribedYear: 2013 },
  ],
};

export const THEMES = [
  { title: 'Tết âm lịch ở châu Á', countries: 4, img: 'vn-tet' },
  { title: 'Trà trên thế giới', countries: 6, img: 'jp-tea' },
  { title: 'Nghi lễ trưởng thành', countries: 5, img: 'jp-seijin' },
  { title: 'Lễ hội ánh sáng', countries: 3, img: 'th-loykrathong' },
];

export const FESTIVALS_THIS_MONTH = [
  { name: 'Día de Muertos', country: 'MX', date: '1–2/11', flag: '🇲🇽', img: 'mx' },
  { name: 'Loy Krathong', country: 'TH', date: 'Tháng 11 (trăng tròn)', flag: '🇹🇭', img: 'th-loykrathong' },
  { name: 'Diwali', country: 'IN', date: 'Theo lịch âm', flag: '🇮🇳', img: 'in-diwali' },
  { name: 'Shichi-Go-San', country: 'JP', date: '15/11', flag: '🇯🇵', img: 'jp-753' },
];

export const SAMPLE_CHAT: ChatMessage[] = [
  { role: 'user', text: 'Văn hoá tặng quà ở Việt Nam và Nhật Bản khác nhau thế nào?' },
  {
    role: 'assistant',
    text:
      'Cả hai nền văn hoá đều coi trọng việc tặng quà như cách thể hiện quan hệ, nhưng khác nhau ở **thời điểm** và **cách trao**.\n\n' +
      '• **Nhật Bản:** quà thường được trao và nhận bằng hai tay [c1]. Sau chuyến đi xa, nhiều người mang omiyage về cho đồng nghiệp [c2]. Có hai mùa tặng quà truyền thống là ochūgen và oseibo [c3].\n\n' +
      '• **Việt Nam:** dịp Tết là thời điểm tặng quà quan trọng nhất, và lì xì cho trẻ em bằng phong bao đỏ là tập quán phổ biến [c4].\n\n' +
      'Lưu ý: đây là tập quán phổ biến, có khác biệt theo vùng miền, thế hệ và mức độ thân thiết.',
    citations: [
      { id: 'c1', sourceId: 42, excerpt: 'Gifts are usually presented and received with both hands…' },
      { id: 'c2', sourceId: 51, excerpt: 'Omiyage — đặc sản mang về sau chuyến đi — thường được chia cho đồng nghiệp…' },
      { id: 'c3', sourceId: 42, excerpt: 'Ochugen in summer and oseibo at year-end are traditional gift seasons…' },
      { id: 'c4', sourceId: 61, excerpt: 'Tiền mừng tuổi được đặt trong phong bao màu đỏ, tượng trưng cho may mắn…' },
    ],
    confidence: 'supported',
    followUps: ['Ở Nhật, nên tránh những món quà nào?', 'Khi đến nhà người Nhật lần đầu nên mang gì?', 'Lì xì có ý nghĩa gì trong văn hoá Việt?'],
    unsupportedPoints: ['Khác biệt về giá trị quà phù hợp giữa hai nước — kho dữ liệu chưa đủ nguồn.'],
  },
];

export const CHAT_SESSIONS: { title: string; messages: ChatMessage[] }[] = [
  { title: 'Tặng quà VN – JP', messages: SAMPLE_CHAT },
  { title: 'Lễ hội Diwali', messages: [
    { role: 'user', text: 'Lễ hội Diwali ở Ấn Độ có ý nghĩa gì?' },
    { role: 'assistant', confidence: 'supported',
      text: '**Diwali** thường được gọi là “lễ hội ánh sáng”. Nhiều gia đình thắp đèn dầu nhỏ (diya) quanh nhà [c1] và trang trí sàn bằng hoa văn rangoli. Ý nghĩa cụ thể **khác nhau giữa các cộng đồng và vùng miền** — ví dụ gắn với các truyền thuyết khác nhau trong Hindu giáo, đạo Jain và đạo Sikh [c2].',
      citations: [{ id: 'c1', sourceId: 91, excerpt: 'Diyas — small oil lamps — are lit…' }, { id: 'c2', sourceId: 91, excerpt: 'Diwali is observed by Hindus, Jains and Sikhs…' }],
      followUps: ['Diwali năm nay vào ngày nào?', 'Khách nước ngoài nên làm gì khi được mời dự Diwali?'] },
  ] },
  { title: 'Bàn ăn ở Pháp', messages: [
    { role: 'user', text: 'Khi được mời ăn tối ở nhà người Pháp nên lưu ý gì?' },
    { role: 'assistant', confidence: 'inferred',
      text: 'Bữa ăn gia đình ở **Pháp** thường kéo dài và chia thành nhiều phần (khai vị, món chính, phô mai, tráng miệng) [c1]. Bữa ăn gastronomic của người Pháp được UNESCO ghi danh năm 2010 như một tập quán xã hội [c2].',
      citations: [{ id: 'c1', sourceId: 82, excerpt: 'Meals are structured in successive courses…' }, { id: 'c2', sourceId: 81, excerpt: 'Gastronomic meal of the French — inscribed 2010' }],
      unsupportedPoints: ['Quy tắc về việc mang rượu làm quà — nguồn hiện có chưa thống nhất.'],
      followUps: ['Chào hỏi bằng “la bise” thế nào?'] },
  ] },
];

export const COMPARISON_VN_JP: Comparison = {
  countryA: 'VN', countryB: 'JP', topic: 'gift_giving', reviewedBy: 'editor_03',
  similarities: [
    { text: 'Quà là cách thể hiện sự quan tâm và duy trì quan hệ, không chỉ là giá trị vật chất.', sourceIds: [62, 51] },
    { text: 'Có các dịp tặng quà theo mùa / theo lịch truyền thống.', sourceIds: [61, 42] },
  ],
  rows: [
    { aspect: 'Dịp tặng quà chính', a: { text: 'Tết Nguyên đán; thăm hỏi họ hàng, thầy cô, đối tác.', sourceIds: [61] }, b: { text: 'Ochūgen (giữa năm), oseibo (cuối năm); omiyage sau chuyến đi.', sourceIds: [42, 51] } },
    { aspect: 'Cách trao', a: { text: 'Trao bằng hai tay khi trao cho người lớn tuổi thể hiện sự kính trọng.', sourceIds: [62] }, b: { text: 'Trao và nhận bằng hai tay là phổ biến.', sourceIds: [42] } },
    { aspect: 'Gói quà', a: { text: 'Màu đỏ, vàng thường được ưa chuộng dịp Tết.', sourceIds: [61] }, b: { text: 'Cách gói được chú trọng như một phần của món quà.', sourceIds: [51] } },
    { aspect: 'Con số / món nên tránh', a: null, b: { text: 'Nhiều người tránh bộ bốn món (shi ~ "tử").', sourceIds: [51] } },
    { aspect: 'Mở quà trước mặt người tặng', a: { text: 'Thường không mở ngay, tuỳ mức độ thân thiết.', sourceIds: [62] }, b: { text: 'Thường cảm ơn và mở sau, trừ khi người tặng mời mở.', sourceIds: [51] } },
  ],
  context: 'Cả hai chịu ảnh hưởng Nho giáo về thứ bậc và sự kính trọng; Nhật Bản phát triển hệ thống tặng quà theo mùa gắn với quan hệ "mang ơn" (giri), còn Việt Nam tập trung vào Tết và chu kỳ lễ tết âm lịch.',
  caveats: [
    'Khác biệt lớn giữa thành thị – nông thôn và giữa các thế hệ.',
    'Trong môi trường công sở quốc tế, nhiều quy tắc được nới lỏng.',
  ],
  insufficient: ['Con số / món quà kiêng kỵ ở Việt Nam — nguồn hiện có mâu thuẫn, chưa kết luận.'],
};

export const QUIZ: QuizQuestion[] = [
  {
    id: 1, countryIso: 'JP', category: 'gift_giving', difficulty: 'easy',
    question: 'Ở Nhật Bản, vì sao nhiều người tránh tặng quà theo bộ bốn món?',
    options: ['Vì số 4 tượng trưng cho mùa đông', 'Vì "shi" (bốn) đồng âm với chữ "tử"', 'Vì luật quy định số món quà', 'Vì số 4 là số của hoàng gia'],
    answerIndex: 1,
    explanation: 'Trong tiếng Nhật, "shi" (四 – bốn) đồng âm với "shi" (死 – chết), nên nhiều người tránh con số này trong quà tặng. Đây là tập quán phổ biến chứ không phải quy định.',
    sourceIds: [51],
  },
  {
    id: 2, countryIso: 'JP', category: 'food_dining', difficulty: 'medium',
    question: 'Washoku được UNESCO ghi danh là di sản văn hoá phi vật thể vào năm nào?',
    options: ['2008', '2010', '2013', '2016'], answerIndex: 2,
    explanation: 'Washoku được ghi danh năm 2013.', sourceIds: [43],
  },
];

export const REVIEW_QUEUE: ReviewItem[] = [
  { id: 901, type: 'quiz', title: '5 câu quiz "Phép lịch sự bàn ăn — Hàn Quốc"', country: 'KR', origin: 'ai_generated', status: 'draft', updatedAt: '2026-10-29' },
  { id: 902, type: 'comparison', title: 'So sánh Pháp – Việt Nam: Chào hỏi', country: 'FR', origin: 'ai_generated', status: 'in_review', updatedAt: '2026-10-29' },
  { id: 903, type: 'feedback', title: 'Báo cáo sai: "Người Thái không bao giờ chạm đầu…"', country: 'TH', origin: 'user_report', status: 'flagged', updatedAt: '2026-10-28' },
  { id: 904, type: 'entry', title: 'Lễ hội Diwali — bản cập nhật v3', country: 'IN', origin: 'editor', status: 'in_review', updatedAt: '2026-10-27' },
  { id: 905, type: 'entry', title: 'Văn hoá công sở Kenya', country: 'KE', origin: 'editor', status: 'draft', updatedAt: '2026-10-26' },
];

// Số claim đã duyệt theo quốc gia × danh mục (giả lập) cho bảng độ phủ.
export function coverageCell(iso: string, cat: number): number {
  const seed = (iso.charCodeAt(0) * 31 + iso.charCodeAt(1) * 7 + cat * 13) % 9;
  const c = COUNTRIES.find((x) => x.iso2 === iso)?.coverage ?? 50;
  return Math.max(0, Math.round((seed + c / 12) / 2.2));
}
