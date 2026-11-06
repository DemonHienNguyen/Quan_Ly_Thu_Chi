# HỆ THỐNG QUẢN LÝ CHI TIÊU CÁ NHÂN DÀNH CHO SINH VIÊN

**Học viện Công nghệ Bưu chính Viễn thông (PTIT)**  
**Môn học:** Phân tích và Thiết kế Hệ thống Phần mềm  
**Đề tài:** Ứng dụng Quản lý Chi tiêu Cá nhân dành cho Sinh viên (Nhóm 8)

---

## 1. Môi trường & Công nghệ phát triển
- **Ngôn ngữ:** Python 3.15.0 (phiên bản mới nhất)
- **Framework:** Django 4.2+ (Kiến trúc MVT - Model View Template)
- **Cơ sở dữ liệu:** SQLite (quản lý qua Django ORM, hỗ trợ chuyển đổi PostgreSQL / MySQL)
- **Bảo mật & Xác thực:** JSON Web Token (JWT 30 ngày) + Mã hóa băm mật khẩu `bcrypt` + Phân quyền ma trận RBAC
- **Frontend / Visualization:** Django Template Language (DTL), Bootstrap 5.3, Font Awesome 6, Chart.js 4.4

---

## 2. Tài khoản thử nghiệm (Theo Bảng 5.1 & 5.2 Đặc tả đồ án)

| Vai trò | Email đăng nhập | Mật khẩu | Mục đích sử dụng |
| :--- | :--- | :--- | :--- |
| **Sinh viên 1** | `sinhvien_test@ptit.edu.vn` | `Student@2026` | Quản lý thu/chi, đặt hạn mức, nhận cảnh báo, xem biểu đồ |
| **Sinh viên 2** | `sinhvien2_test@ptit.edu.vn` | `Student2@2026` | Tài khoản học viên thứ hai |
| **Quản trị viên (Admin)** | `admin_system@ptit.edu.vn` | `Admin@Ptit2026` | Quản lý danh mục hệ thống, xem nhật ký, quản lý tài khoản |

Chỉ ba tài khoản trên được phép đăng nhập; đăng ký tài khoản đã tắt. Tài khoản cũ ngoài danh sách vẫn được giữ nguyên dữ liệu nhưng không thể đăng nhập.

---

## 3. Cấu trúc mã nguồn dự án

```text
d:/QuanLyThuChi/
├── venv/                            # Virtual Environment chạy Python 3.15
├── requirements.txt                 # Khai báo thư viện (Django, bcrypt, PyJWT, python-decouple)
├── Do An KT&TKPM_Nhom 8_...docx     # Báo cáo đặc tả đề tài
└── expense_tracker/                 # Thư mục gốc Django
    ├── manage.py                    # Trình điều khiển CLI
    ├── .env                         # Cấu hình biến môi trường
    ├── expense_tracker/             # Cấu hình lõi (settings, urls, wsgi, asgi)
    ├── tracker_app/                 # Module chức năng chính
    │   ├── models.py                # CSDL: Users, Categories, Transactions, Budgets, Notifications, SystemLogs
    │   ├── views.py                 # Business logic: Auth, Dashboard, Transactions, Budgets, Alerts, Admin
    │   ├── urls.py                  # Định tuyến URL chi tiết
    │   ├── auth_utils.py            # Tiện ích băm bcrypt, JWT Token, Decorator RBAC
    │   ├── middleware.py            # Middleware xác thực JWT tự động
    │   ├── services.py              # Dịch vụ đối soát ngưỡng ngân sách & ghi SystemLog
    │   ├── forms.py                 # Django forms xác thực dữ liệu đầu vào
    │   ├── admin.py                 # Đăng ký trang quản trị
    │   ├── tests.py                 # Bộ kiểm thử tự động (TC01 -> TC06)
    │   ├── templates/tracker_app/   # Giao diện HTML (Login, Dashboard, Transactions, Budget, Categories, Admin...)
    │   └── management/commands/     # Lệnh seed_data khởi tạo dữ liệu mẫu
    └── static/                      # Static assets (CSS, JS biểu đồ)
```

---

## 4. Hướng dẫn chạy dự án

### Kích hoạt môi trường ảo:
```powershell
d:\QuanLyThuChi\venv\Scripts\Activate.ps1
```

### Chạy máy chủ phát triển (Development Server):
```powershell
cd d:\QuanLyThuChi\expense_tracker
d:\QuanLyThuChi\venv\Scripts\python.exe manage.py runserver
```
Truy cập ứng dụng tại: **http://127.0.0.1:8000/**

### Chạy kiểm thử tự động (Test Cases TC01 -> TC06):
```powershell
cd d:\QuanLyThuChi\expense_tracker
d:\QuanLyThuChi\venv\Scripts\python.exe manage.py test tracker_app
```

### Nạp lại dữ liệu mẫu giả lập (Seed Data):
```powershell
cd d:\QuanLyThuChi\expense_tracker
d:\QuanLyThuChi\venv\Scripts\python.exe manage.py seed_data
```

### Chạy ứng dụng desktop:
Ứng dụng có thể mở trong cửa sổ riêng, không cần mở tab trình duyệt. Lần đầu khởi chạy sẽ tự tạo cơ sở dữ liệu, chạy migration và thêm danh mục hệ thống. Tài khoản, mật khẩu, giao dịch và ngân sách cá nhân không được tạo sẵn.

```powershell
cd d:\QuanLyThuChi\expense_tracker
d:\QuanLyThuChi\venv\Scripts\python.exe manage.py --desktop
```

### Đóng gói thành file EXE trên Windows:
Đóng gói trên Windows bằng cùng môi trường Python đã cài dependency trong `requirements.txt`. Lệnh sau nhúng logo PTIT làm biểu tượng ứng dụng và tạo file EXE độc lập tại `expense_tracker\dist\PTITExpenseTracker.exe`:

```powershell
cd d:\QuanLyThuChi\expense_tracker
d:\QuanLyThuChi\venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name PTITExpenseTracker --icon "d:\QuanLyThuChi\expense_tracker\static\images\ptit-logo.ico" --collect-all django --collect-all tracker_app --collect-all webview --hidden-import django.contrib.staticfiles.handlers --add-data "d:\QuanLyThuChi\expense_tracker\tracker_app\templates;tracker_app\templates" --add-data "d:\QuanLyThuChi\expense_tracker\static;static" --specpath "$env:TEMP\PTITExpenseTracker-spec" --workpath "$env:TEMP\PTITExpenseTracker-build" --distpath "d:\QuanLyThuChi\expense_tracker\dist" manage.py
```

Khi chạy EXE, ứng dụng mở trong cửa sổ desktop và chỉ lắng nghe trên máy hiện tại (`127.0.0.1`). Cơ sở dữ liệu và khóa ứng dụng được lưu riêng trong `%LOCALAPPDATA%\PTITExpenseTracker`, không nằm trong thư mục giải nén tạm của EXE. Cần cài Microsoft Edge WebView2 Runtime trên Windows nếu máy chưa có sẵn.
