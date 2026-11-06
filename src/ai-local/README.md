# ai-local — Dịch vụ AI chạy local cho CultureAtlas

Toàn bộ AI **ngoài LLM** chạy trên CPU, miễn phí, bằng model mã nguồn mở. LLM (GPT-4o) nằm ở backend.

| Endpoint | Chức năng | Model |
|---|---|---|
| `POST /v1/stt` (multipart `file`) | Giọng nói tiếng Việt → văn bản và các đoạn có mốc thời gian | Gipformer 1.5 (MIT) + silero VAD, qua sherpa-onnx |
| `POST /v1/tts` `{text, voice?}` | Văn bản → WAV 48 kHz. Tự bỏ nhãn `[c#]` và markdown | VieNeu-TTS v3 Turbo (Apache 2.0) |
| `GET /v1/voices` | 25 giọng Bắc/Nam | |
| `POST /v1/embed` `{texts}` | Vector 1024 chiều, đã chuẩn hoá L2 | Vietnamese_Embedding_v2 (Apache 2.0) |
| `POST /v1/rerank` `{query, documents, top_k?}` | Điểm liên quan 0..1 | Vietnamese_Reranker (Apache 2.0) |
| `GET /health` | Cho biết model nào đã được nạp | |

Lý do chọn từng model và số đo tốc độ: [docs/11-vietnamese-chat-stack.md](../../docs/11-vietnamese-chat-stack.md).

## Cài đặt

Cần Python 3.12. Không cần cài ffmpeg: PyAV đã kèm sẵn thư viện giải mã.

```bash
python3.12 -m venv .venv
.venv/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu -e ".[export,dev]"
.venv/bin/python -m ai_local.download            # ~5 GB, một lần (stt tts embed rerank). Reranker được xuất sang ONNX int8
.venv/bin/uvicorn ai_local.main:app --port 8100
```

- Model được nạp ở lần gọi đầu tiên. Đặt `AI_LOCAL_PRELOAD=1` để nạp sẵn khi khởi động.
- Khi đã nạp đủ cả bốn model, dịch vụ dùng khoảng 5–6 GB RAM.
- Cache Hugging Face dùng symlink, mà onnxruntime ≥ 1.2x từ chối file trọng số nằm ngoài thư mục model. `hfcache.py` tự thay symlink bằng hardlink để xử lý việc này.

## Cấu hình (biến môi trường `AI_LOCAL_*`)

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `AI_LOCAL_THREADS` | nửa số luồng CPU | |
| `AI_LOCAL_TTS_PRECISION` | `int8` | Cần CPU có AVX-VNNI (Core Ultra / Intel 12th+). Nếu không có thì dùng `fp32` |
| `AI_LOCAL_TTS_VOICE` | `Hải Đăng` | Giọng mặc định |
| `AI_LOCAL_MAX_AUDIO_SECONDS` | `60` | |
| `AI_LOCAL_MAX_UPLOAD_MB` | `10` | |
| `AI_LOCAL_RERANK_MAX_TOKENS` | `1024` | Tối đa 2304 |

## Test

```bash
.venv/bin/python -m pytest -q             # engine giả, nhanh, không cần model
.venv/bin/python -m pytest -q -m models   # model thật: TTS → STT khép kín, embedding, rerank
```

- Âm thanh của người dùng chỉ nằm trong file tạm và bị xoá ngay sau khi giải mã (AC21.3).
- Dịch vụ này chỉ nên mở trong mạng nội bộ; chỉ backend gọi vào.
