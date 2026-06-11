# RUN_COMPOSE.md – Hướng dẫn chạy Lab 05 (Access Gate)

Tài liệu này hướng dẫn người khác clone repo sạch và chạy lại stack Compose của Lab 05 (Access Gate API).

---

## 1. Clone repo

```bash
git clone https://github.com/FIT-17-13/fit4110-lab5-nhom4_access-gate.git
cd fit4110-lab5-nhom4_access-gate
```

---

## 2. Cài dependencies cho Newman/Prism/Spectral (tuỳ chọn)

```bash
npm install
```

---

## 3. Build & chạy stack Docker Compose

```bash
# Tạo file .env từ .env.example
cp .env.example .env

# Tạo external network 'class-net' nếu chưa có trên hệ thống của bạn
docker network create class-net

# Build images và khởi động các container trong nền
docker compose up -d --build
```

Lệnh trên sẽ tạo các container:

- `fit4110-db-lab05` (PostgreSQL - CSDL lưu trữ sự kiện/quyết định cổng)
- `fit4110-ai-lab05` (AI service mẫu chạy port 9000 làm kiểm tra chính sách hoặc đối khớp khuôn mặt)
- `fit4110-api-lab05` (Access Gate API FastAPI trên port 8000)

Theo dõi log:

```bash
docker compose logs -f
```

Sau vài giây, kiểm tra health của mỗi service:

```bash
# API (Kiểm tra xem API có kết nối thành công tới PostgreSQL và AI service chưa)
curl http://localhost:8000/health

# AI service
curl http://localhost:9000/health

# DB readiness
docker exec -it fit4110-db-lab05 pg_isready -U access_gate_user -d access_gate_db
```

Bạn cũng có thể truy cập endpoint `/predict` của AI service để xem kết quả mẫu:

```bash
curl -X POST http://localhost:9000/predict
```

---

## 4. Chạy Newman test trên stack Compose (tuỳ chọn)

```bash
npm run test:compose
```

Report sinh tại:

```text
reports/newman-lab05-compose.xml
reports/newman-lab05-compose.html
```

---

## 5. Dừng stack

Khi không cần nữa, dừng và xoá các container bằng:

```bash
docker compose down
```

Nếu muốn xoá volume dữ liệu của DB, thêm tuỳ chọn `-v`:

```bash
docker compose down -v
```

---

## 6. Lệnh nhanh

Bạn có thể dùng Makefile:

```bash
make compose-up
make compose-down
make logs
make test-compose
```

---

## 7. Mẹo gỡ lỗi

- Sử dụng `docker compose ps` để xem trạng thái container.
- Nếu API trả lỗi kết nối DB, hãy kiểm tra biến môi trường `POSTGRES_*` trong `.env` và đảm bảo DB đã sẵn sàng (`pg_isready`).
- Nếu AI service cần tải mô hình lớn, tăng `start_period` của healthcheck trong `docker-compose.yml`.