// ng serve (dev): chuyển /api tới backend. Docker dùng nginx (nginx.conf) thay cho file này.
// Đổi địa chỉ backend: API_URL=http://localhost:8001 npx ng serve
export default {
  '/api': {
    target: process.env.API_URL || 'http://localhost:8000',
    changeOrigin: true,
    secure: false,
  },
  // Ảnh / video / file từ object storage (MinIO). Docker: nginx làm việc này. scripts/dev.sh đặt MEDIA_URL theo S3_PORT trong .env
  '/media': {
    target: process.env.MEDIA_URL || 'http://localhost:9000',
    changeOrigin: true,
    pathRewrite: { '^/media': '/culture-media' },
  },
};
