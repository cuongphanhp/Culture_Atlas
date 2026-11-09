-- Dữ liệu mẫu cho bộ test nghiệm thu. Nạp lại trước MỖI test có dùng fixture `db`/`client`.
-- Mật khẩu mọi tài khoản: Passw0rd!
-- Khi thêm tính năng cần dữ liệu mới: thêm vào đây, giữ id cố định để test tham chiếu được.

INSERT INTO users (id, email, password_hash, display_name, role, is_active) VALUES
  (1, 'admin@test.local',    '$argon2id$v=19$m=65536,t=3,p=4$zzsOCCjH3e5n5tlXrh92IA$JE5Zm97gLcIxe+4IFEZJtcmMw1xbsC1fShCTV5FPau0', 'Admin',    'admin',   TRUE),
  (2, 'editor@test.local',   '$argon2id$v=19$m=65536,t=3,p=4$zzsOCCjH3e5n5tlXrh92IA$JE5Zm97gLcIxe+4IFEZJtcmMw1xbsC1fShCTV5FPau0', 'Editor',   'editor',  TRUE),
  (3, 'learner@test.local',  '$argon2id$v=19$m=65536,t=3,p=4$zzsOCCjH3e5n5tlXrh92IA$JE5Zm97gLcIxe+4IFEZJtcmMw1xbsC1fShCTV5FPau0', 'Learner',  'learner', TRUE),
  (4, 'disabled@test.local', '$argon2id$v=19$m=65536,t=3,p=4$zzsOCCjH3e5n5tlXrh92IA$JE5Zm97gLcIxe+4IFEZJtcmMw1xbsC1fShCTV5FPau0', 'Disabled', 'editor',  FALSE);

INSERT INTO countries (id, iso2, iso3, iso_numeric, name_vi, name_en, region, capital, languages, currencies, neighbors, is_featured) VALUES
  (1,  'VN','VNM','704','Việt Nam','Vietnam','Đông Nam Á','Hà Nội','["Tiếng Việt"]','["VND"]','{CN,LA,KH}',TRUE),
  (2,  'TH','THA','764','Thái Lan','Thailand','Đông Nam Á','Bangkok','["Tiếng Thái"]','["THB"]',NULL,FALSE),
  (3,  'JP','JPN','392','Nhật Bản','Japan','Đông Á','Tokyo','["Tiếng Nhật"]','["JPY"]',NULL,TRUE),
  (4,  'KR','KOR','410','Hàn Quốc','South Korea','Đông Á','Seoul','["Tiếng Hàn"]','["KRW"]','{KP}',TRUE),
  (5,  'CN','CHN','156','Trung Quốc','China','Đông Á','Bắc Kinh','["Tiếng Trung"]','["CNY"]','{VN}',FALSE),
  (6,  'IN','IND','356','Ấn Độ','India','Nam Á','New Delhi','["Tiếng Hindi","Tiếng Anh"]','["INR"]',NULL,FALSE),
  (7,  'FR','FRA','250','Pháp','France','Châu Âu','Paris','["Tiếng Pháp"]','["EUR"]',NULL,TRUE),
  (8,  'MX','MEX','484','Mexico','Mexico','Châu Mỹ','Thành phố Mexico','["Tiếng Tây Ban Nha"]','["MXN"]',NULL,FALSE),
  (9,  'EG','EGY','818','Ai Cập','Egypt','Trung Đông – Bắc Phi','Cairo','["Tiếng Ả Rập"]','["EGP"]',NULL,FALSE),
  (10, 'KE','KEN','404','Kenya','Kenya','Châu Phi cận Sahara','Nairobi','["Tiếng Swahili","Tiếng Anh"]','["KES"]',NULL,FALSE);

INSERT INTO sources (id, title, publisher, source_url, source_type, license, reliability_tier, language, retrieved_at) VALUES
  (1, 'Japanese etiquette & manners', 'Japan National Tourism Organization', 'https://www.japan.travel/en/guide/etiquette/', 'official_site', 'Excerpts only', 'official', 'en', '2026-10-01'),
  (2, 'UNESCO World Heritage List (DataHub whc001)', 'UNESCO', 'https://data.unesco.org/explore/dataset/whc001/', 'api_dataset', 'CC BY-SA 4.0', 'official', 'en', '2026-10-30'),
  (3, 'UNESCO Intangible Heritage Lists (DataHub ich001)', 'UNESCO', 'https://data.unesco.org/explore/dataset/ich001/', 'api_dataset', 'CC BY-SA 4.0', 'official', 'en', '2026-10-30'),
  (4, 'Vietnam Tourism — Tết traditions', 'Vietnam National Authority of Tourism', 'https://vietnam.travel/things-to-do/tet', 'official_site', 'Excerpts only', 'official', 'en', '2026-10-01'),
  (5, 'Gift giving in East Asia', 'Journal of Intercultural Studies', 'https://example.org/academic/gift-east-asia', 'academic', 'CC BY 4.0', 'academic', 'en', '2026-09-15');

-- Bài viết: 1,2,4 published · 3 draft · 5 in_review
INSERT INTO culture_entries (id, country_id, category, slug, title_vi, title_en, summary, status, origin, version) VALUES
  (1, 3, 'gift_giving', 'tang-qua', 'Tặng quà ở Nhật Bản', 'Gift giving in Japan', 'Cách trao, nhận và chọn quà ở Nhật Bản.', 'published', 'editor', 2),
  (2, 3, 'etiquette',   'cui-chao', 'Cúi chào ở Nhật Bản', 'Bowing in Japan', 'Cúi chào trong giao tiếp hằng ngày.', 'published', 'editor', 1),
  (3, 3, 'food_dining', 'dua',      'Dùng đũa ở Nhật Bản (nháp)', NULL, 'Bản nháp chưa duyệt.', 'draft', 'ai_generated', 1),
  (4, 1, 'gift_giving', 'tang-qua', 'Tặng quà ở Việt Nam', 'Gift giving in Vietnam', 'Phong tục tặng quà và lì xì ngày Tết.', 'published', 'editor', 1),
  (5, 3, 'greetings',   'chao-hoi', 'Chào hỏi ở Nhật Bản', 'Greetings in Japan', 'Chờ duyệt.', 'in_review', 'editor', 1);

-- Claim 4 là draft, không nguồn (AC03.3, AC17.1). Claim 8 thuộc bài đang chờ duyệt.
INSERT INTO claims (id, entry_id, text, scope, region, confidence, status, position) VALUES
  (1, 1, 'Ở Nhật Bản, quà thường được trao và nhận bằng hai tay.', 'common_practice', NULL, 'verified', 'draft', 1),
  (2, 1, 'Nhiều người Nhật tránh tặng quà theo bộ bốn món vì "shi" (bốn) đồng âm với "chết".', 'common_practice', NULL, 'verified', 'draft', 2),
  (3, 1, 'Hoa cúc trắng ở Nhật Bản thường gắn với tang lễ nên ít được chọn làm quà.', 'common_practice', NULL, 'partially_supported', 'draft', 3),
  (4, 1, 'Ở một số vùng, quà cần được gói bằng giấy màu đỏ.', 'regional', 'Okinawa', 'unverified', 'draft', 4),
  (5, 2, 'Cúi chào là cách chào hỏi và cảm ơn phổ biến ở Nhật Bản.', 'common_practice', NULL, 'verified', 'draft', 1),
  (6, 4, 'Ở Việt Nam, lì xì đầu năm thường đựng trong phong bao màu đỏ.', 'common_practice', NULL, 'verified', 'draft', 1),
  (7, 4, 'Hoa cúc vàng thường được bày để thờ cúng trong dịp Tết.', 'regional', 'Miền Bắc', 'verified', 'draft', 2),
  (8, 5, 'Khi gặp lần đầu, người Nhật thường trao danh thiếp bằng hai tay.', 'common_practice', NULL, 'verified', 'in_review', 1);

INSERT INTO claim_sources (claim_id, source_id, evidence_excerpt, locator) VALUES
  (1, 1, 'Gifts are usually presented and received with both hands.', '§Gifts'),
  (1, 5, 'Presenting gifts with both hands signals respect.', 'p. 12'),
  (2, 1, 'Avoid giving gifts in sets of four, as the word for four sounds like death.', '§Gifts'),
  (3, 1, 'White chrysanthemums are associated with funerals.', '§Flowers'),
  (5, 1, 'Bowing is used to greet, thank and apologise.', '§Bowing'),
  (6, 4, 'Lucky money is given in red envelopes at Tết.', '§Lucky money'),
  (7, 4, 'Yellow chrysanthemums decorate family altars during Tết in the north.', '§Flowers'),
  (8, 1, 'Business cards are exchanged with both hands.', '§Business');

-- Xuất bản sau khi đã có nguồn (trigger BR01 chặn xuất bản claim không nguồn)
UPDATE claims SET status = 'published' WHERE id IN (1, 2, 3, 5, 6, 7);

INSERT INTO heritage_items (id, unesco_id, name, type, list_type, inscribed_year, criteria, lat, lng, source_id, raw_data) VALUES
  (1, 'WHC-688',   'Historic Monuments of Ancient Kyoto', 'tangible',   'World Heritage List', 1994, '(ii)(iv)', 35.0, 135.7, 2, '{"id_no":"688"}'),
  (2, 'ICH-00869', 'Washoku, traditional dietary cultures of the Japanese', 'intangible', 'Representative List', 2013, NULL, NULL, NULL, 3, '{"ich_public_ref":"869"}'),
  (3, 'WHC-948',   'Hoi An Ancient Town', 'tangible', 'World Heritage List', 1999, '(ii)(v)', 15.88, 108.33, 2, '{"id_no":"948"}');
INSERT INTO heritage_item_countries VALUES (1, 3), (2, 3), (3, 1);

-- Quiz: 1,2 published · 3 draft
INSERT INTO quiz_questions (id, entry_id, question, options, answer_index, explanation, difficulty, status, origin) VALUES
  (1, 1, 'Ở Nhật Bản, vì sao nhiều người tránh tặng quà theo bộ bốn món?', '["Vì số 4 là số chẵn","Vì \"shi\" đồng âm với \"chết\"","Vì luật cấm","Vì quà quá nặng"]', 1,
      'Trong tiếng Nhật, "shi" (bốn) đồng âm với "chết".', 'easy', 'published', 'editor'),
  (2, 2, 'Cúi chào ở Nhật Bản dùng để làm gì?', '["Chỉ để xin lỗi","Chào hỏi, cảm ơn và xin lỗi","Chỉ trong lễ hội"]', 1,
      'Cúi chào được dùng để chào hỏi, cảm ơn và xin lỗi.', 'medium', 'published', 'editor'),
  (3, 1, 'Câu hỏi nháp chưa duyệt?', '["A","B"]', 0, 'Nháp.', 'easy', 'draft', 'ai_generated');

-- So sánh VN–JP về tặng quà đã duyệt (AC11.1); hàng "Gói quà" thiếu nguồn bên VN (AC11.2)
INSERT INTO comparisons (id, country_a_id, country_b_id, topic, language, result, status, origin, reviewed_by, reviewed_at) VALUES
  (1, 1, 3, 'gift_giving', 'vi', '{
    "similarities": [{"text": "Quà thể hiện sự quan tâm và giữ gìn quan hệ.", "sourceIds": [5]}],
    "rows": [
      {"aspect": "Cách trao quà", "a": {"text": "Lì xì đựng trong phong bao đỏ.", "sourceIds": [4]}, "b": {"text": "Trao và nhận bằng hai tay.", "sourceIds": [1]}},
      {"aspect": "Gói quà", "a": null, "b": {"text": "Tránh bộ bốn món.", "sourceIds": [1]}}
    ],
    "context": "Cả hai nền văn hoá chịu ảnh hưởng của quan niệm về may mắn.",
    "caveats": ["Tập quán khác nhau theo vùng và thế hệ."],
    "insufficient": ["Gói quà ở Việt Nam"]
  }', 'published', 'editor', 2, now());

-- Lễ hội theo tháng (F1.8): bài festivals gắn thẻ kind 'month' (tên "1".."12"); chủ đề (F1.7): thẻ kind 'theme'.
-- Bài 6 không có claim nên không ảnh hưởng độ phủ / chỉ mục RAG. Thẻ "Trà" chỉ gắn bài nháp → không được hiện.
INSERT INTO culture_entries (id, country_id, category, slug, title_vi, title_en, summary, period, status, origin, version) VALUES
  (6, 1, 'festivals', 'tet', 'Tết Nguyên Đán', 'Lunar New Year (Tết)', 'Lễ hội đón năm mới âm lịch.',
   'Cuối tháng 1 – giữa tháng 2 dương lịch', 'published', 'editor', 1);
INSERT INTO tags (id, name, kind) VALUES (1, 'Quà tặng', 'theme'), (2, 'Trà', 'theme'), (3, '1', 'month'), (4, '2', 'month');
INSERT INTO entry_tags (entry_id, tag_id) VALUES (1, 1), (4, 1), (3, 2), (6, 3), (6, 4);

INSERT INTO feedback (id, target_type, target_id, type, comment, status) VALUES
  (1, 'claim', 3, 'factual_error', 'Cần thêm nguồn về hoa cúc.', 'open');

-- Tài liệu tham khảo do worker thu thập (chưa biên tập) — AC07.4
INSERT INTO sources (id, title, publisher, source_url, source_type, license, reliability_tier, language, retrieved_at) VALUES
  (6, 'Wikipedia', 'Wikimedia Foundation', 'https://en.wikipedia.org', 'encyclopedia', 'CC BY-SA 4.0', 'community', 'en', '2026-10-30');
INSERT INTO source_documents (id, country_id, source_id, title, section, body, url, language, category_guess) VALUES
  (1, 3, 6, 'Etiquette in Japan', 'Visiting a home',
   'When visiting a Japanese home, guests usually bring a small gift called temiyage, often sweets from their hometown. '
   'Shoes are removed at the entrance, the genkan, and guests wear slippers indoors.',
   'https://en.wikipedia.org/wiki/Etiquette_in_Japan', 'en', 'etiquette');

-- Đồng bộ bộ đếm id sau khi chèn id cố định
SELECT setval('users_id_seq',           (SELECT MAX(id) FROM users));
SELECT setval('countries_id_seq',       (SELECT MAX(id) FROM countries));
SELECT setval('sources_id_seq',         (SELECT MAX(id) FROM sources));
SELECT setval('culture_entries_id_seq', (SELECT MAX(id) FROM culture_entries));
SELECT setval('claims_id_seq',          (SELECT MAX(id) FROM claims));
SELECT setval('heritage_items_id_seq',  (SELECT MAX(id) FROM heritage_items));
SELECT setval('quiz_questions_id_seq',  (SELECT MAX(id) FROM quiz_questions));
SELECT setval('comparisons_id_seq',     (SELECT MAX(id) FROM comparisons));
SELECT setval('feedback_id_seq',        (SELECT MAX(id) FROM feedback));
SELECT setval('tags_id_seq',            (SELECT MAX(id) FROM tags));
SELECT setval('source_documents_id_seq', (SELECT MAX(id) FROM source_documents));
