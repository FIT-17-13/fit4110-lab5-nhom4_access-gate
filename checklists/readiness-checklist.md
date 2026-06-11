# Readiness Checklist – Lab 05

Đây là danh sách kiểm tra (checklist) để đảm bảo stack Docker Compose của bạn đã sẵn sàng trước khi gửi bài. Hãy tick vào mỗi mục sau khi hoàn thành.

- [x] **Database ready:** container DB đã chạy và phản hồi `pg_isready`. Kiểm tra bằng `docker exec -it fit4110-db-lab05 pg_isready -U access_gate_user -d access_gate_db`.
- [x] **AI service ready:** container AI service trả về `200` cho endpoint `/health` và `/predict` hoạt động.
- [x] **API ready:** container API trả `200` cho `/health` (sau khi kiểm tra DB và AI kết nối thành công) và có thể tạo/lấy access events / decisions khi token hợp lệ.
- [x] **Environment variables:** `.env` đã được thiết lập đúng (APP_PORT, POSTGRES_USER, AUTH_TOKEN,…). Không sử dụng secret thật; lưu secret vào `.env` cục bộ, commit `.env.example`.
- [x] **Network & Ports:** mạng `team-internal` hoạt động; API gọi được AI bằng hostname `ai-service`; ports 8000 (API), 9000 (AI) và 5432 (DB) được map đúng.
- [x] **Image tags:** bạn đã build image với tag `v0.1.0-team-gate` và push lên registry. Xác nhận rằng tag xuất hiện trong registry.

Ghi chú thêm những vấn đề gặp phải hoặc điều chỉnh tại đây:

```
- Hệ thống Access Gate API đã kết nối đầy đủ cơ sở dữ liệu PostgreSQL và liên lạc thành công với AI Service nội bộ thông qua Docker Compose network `team-internal`.
- Đã khắc phục lỗi thiếu thư viện của AI Service bằng cách dùng chung Dockerfile và ghi đè entrypoint CMD.
- Toàn bộ các kiểm thử Newman tự động đều pass 100%.
```