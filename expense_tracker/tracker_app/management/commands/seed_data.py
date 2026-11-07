from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from tracker_app.models import User, Category, Transaction, Budget, Notification, SystemLog
from tracker_app.auth_utils import hash_password
from tracker_app.account_policy import APPROVED_ACCOUNTS


def ensure_demo_accounts():
    """Create missing approved demo accounts and enforce their configured roles."""
    created_any = False
    users = {}

    for account in APPROVED_ACCOUNTS:
        user, created = User.objects.get_or_create(
            email=account['email'],
            defaults={
                'full_name': account['full_name'],
                'password_hash': hash_password(account['password']),
                'role': account['role'],
                'status': 'ACTIVE',
            },
        )
        if created:
            created_any = True
        elif user.role != account['role']:
            user.role = account['role']
            user.save(update_fields=['role'])
        users[account['email']] = user

    return created_any, users


class Command(BaseCommand):
    help = "Khởi tạo dữ liệu giả lập (Seed Data) chuẩn theo yêu cầu Chương V đồ án."

    def add_arguments(self, parser):
        parser.add_argument(
            '--defaults-only',
            action='store_true',
            help='Chỉ tạo danh mục hệ thống, không tạo tài khoản hay giao dịch mẫu.',
        )

    def handle(self, *args, **options):
        def write_status(message):
            if options['verbosity'] > 0:
                self.stdout.write(message)

        write_status("Khởi tạo dữ liệu mẫu theo đặc tả đồ án...")

        # 1. Tạo danh mục mặc định của hệ thống
        system_categories = [
            ("Tiền lương / Làm thêm", "INCOME", "fa-money-bill-wave"),
            ("Phụ cấp gia đình", "INCOME", "fa-hand-holding-dollar"),
            ("Học bổng", "INCOME", "fa-award"),
            ("Dự án / Freelance", "INCOME", "fa-briefcase"),
            ("Ăn uống", "EXPENSE", "fa-utensils"),
            ("Tiền nhà / Phòng trọ", "EXPENSE", "fa-house"),
            ("Học phí & Sách vở", "EXPENSE", "fa-graduation-cap"),
            ("Đi lại / Xăng xe", "EXPENSE", "fa-bus"),
            ("Giải trí / Bạn bè", "EXPENSE", "fa-gamepad"),
            ("Mua sắm cá nhân", "EXPENSE", "fa-shirt"),
            ("Thuốc men / Y tế", "EXPENSE", "fa-notes-medical"),
            ("Hóa đơn Điện / Nước", "EXPENSE", "fa-receipt"),
        ]

        cat_map = {}
        for name, c_type, icon in system_categories:
            cat, _ = Category.objects.get_or_create(
                category_name=name,
                is_default=True,
                defaults={'type': c_type, 'icon': icon, 'user': None}
            )
            cat_map[name] = cat

        if options['defaults_only']:
            write_status(self.style.SUCCESS("Đã khởi tạo danh mục hệ thống."))
            return

        created_any, demo_users = ensure_demo_accounts()
        admin_user = demo_users['admin_system@ptit.edu.vn']
        student_user = demo_users['sinhvien_test@ptit.edu.vn']
        if created_any:
            write_status(self.style.SUCCESS(f"Đã tạo Admin: admin_system@ptit.edu.vn (Pass: Admin@Ptit2026)"))
            write_status(self.style.SUCCESS(f"Đã tạo Sinh viên: sinhvien_test@ptit.edu.vn (Pass: Student@2026)"))
            write_status(self.style.SUCCESS(f"Đã tạo Sinh viên: sinhvien2_test@ptit.edu.vn (Pass: Student2@2026)"))
        else:
            write_status(self.style.SUCCESS("Tài khoản demo đã tồn tại. Dữ liệu đăng nhập chuẩn đã sẵn sàng."))

        # 4. Danh mục cá nhân cho sinh viên thử nghiệm
        custom_cat, _ = Category.objects.get_or_create(
            category_name="Tiền thưởng đồ án",
            user=student_user,
            defaults={'type': 'INCOME', 'icon': 'fa-trophy', 'is_default': False}
        )
        cat_map["Tiền thưởng đồ án"] = custom_cat

        # 5. Thiết lập ngân sách tháng 10/2026 cho sinh viên
        curr_year = 2026
        curr_month = 10

        Budget.objects.get_or_create(
            user=student_user,
            category=None,
            month=curr_month,
            year=curr_year,
            defaults={'monthly_limit': Decimal('4500000.00')}
        )

        an_uong_cat = cat_map.get("Ăn uống")
        if an_uong_cat:
            Budget.objects.get_or_create(
                user=student_user,
                category=an_uong_cat,
                month=curr_month,
                year=curr_year,
                defaults={'monthly_limit': Decimal('2000000.00')}
            )

        nha_tro_cat = cat_map.get("Tiền nhà / Phòng trọ")
        if nha_tro_cat:
            Budget.objects.get_or_create(
                user=student_user,
                category=nha_tro_cat,
                month=curr_month,
                year=curr_year,
                defaults={'monthly_limit': Decimal('1500000.00')}
            )

        # 6. Tạo các giao dịch mẫu thực tế
        sample_transactions = [
            # Thu nhập tháng 10
            (student_user, cat_map["Phụ cấp gia đình"], Decimal('3500000.00'), 'INCOME', date(2026, 10, 1), "Bố mẹ gửi tiền sinh hoạt tháng 10"),
            (student_user, cat_map["Tiền lương / Làm thêm"], Decimal('2200000.00'), 'INCOME', date(2026, 10, 5), "Lương trợ giảng / gia sư tháng 9"),
            (student_user, custom_cat, Decimal('500000.00'), 'INCOME', date(2026, 10, 8), "Thưởng đạt giải nhì đồ án nhóm"),

            # Chi tiêu tháng 10
            (student_user, cat_map["Tiền nhà / Phòng trọ"], Decimal('1500000.00'), 'EXPENSE', date(2026, 10, 2), "Thanh toán tiền thuê phòng trọ tháng 10"),
            (student_user, cat_map["Hóa đơn Điện / Nước"], Decimal('320000.00'), 'EXPENSE', date(2026, 10, 3), "Tiền điện nước và mạng internet"),
            (student_user, cat_map["Ăn uống"], Decimal('650000.00'), 'EXPENSE', date(2026, 10, 4), "Đi siêu thị mua thực phẩm tuần 1"),
            (student_user, cat_map["Đi lại / Xăng xe"], Decimal('120000.00'), 'EXPENSE', date(2026, 10, 6), "Đổ xăng xe máy và gửi xe"),
            (student_user, cat_map["Học phí & Sách vở"], Decimal('280000.00'), 'EXPENSE', date(2026, 10, 7), "In tài liệu đồ án KT&TKPM và mua giáo trình"),
            (student_user, cat_map["Ăn uống"], Decimal('850000.00'), 'EXPENSE', date(2026, 10, 9), "Tiền ăn trưa căng tin và liên hoan nhóm đồ án"),
            (student_user, cat_map["Giải trí / Bạn bè"], Decimal('250000.00'), 'EXPENSE', date(2026, 10, 10), "Xem phim cuối tuần và uống cà phê"),

            # Lịch sử các tháng trước (tháng 9, tháng 8) để vẽ biểu đồ cột 6 tháng
            (student_user, cat_map["Phụ cấp gia đình"], Decimal('3500000.00'), 'INCOME', date(2026, 9, 1), "Phụ cấp tháng 9"),
            (student_user, cat_map["Tiền lương / Làm thêm"], Decimal('2000000.00'), 'INCOME', date(2026, 9, 5), "Lương làm thêm tháng 8"),
            (student_user, cat_map["Tiền nhà / Phòng trọ"], Decimal('1500000.00'), 'EXPENSE', date(2026, 9, 3), "Tiền phòng trọ tháng 9"),
            (student_user, cat_map["Ăn uống"], Decimal('1800000.00'), 'EXPENSE', date(2026, 9, 15), "Tổng tiền ăn uống tháng 9"),
            (student_user, cat_map["Học phí & Sách vở"], Decimal('500000.00'), 'EXPENSE', date(2026, 9, 20), "Mua giáo trình chuyên ngành"),

            (student_user, cat_map["Phụ cấp gia đình"], Decimal('3500000.00'), 'INCOME', date(2026, 8, 1), "Phụ cấp tháng 8"),
            (student_user, cat_map["Tiền nhà / Phòng trọ"], Decimal('1500000.00'), 'EXPENSE', date(2026, 8, 3), "Tiền phòng trọ tháng 8"),
            (student_user, cat_map["Ăn uống"], Decimal('1600000.00'), 'EXPENSE', date(2026, 8, 20), "Tiền ăn tháng 8"),
        ]

        for u, cat, amt, t_type, t_date, note in sample_transactions:
            if not Transaction.objects.filter(user=u, category=cat, amount=amt, transaction_date=t_date).exists():
                Transaction.objects.create(
                    user=u,
                    category=cat,
                    amount=amt,
                    type=t_type,
                    transaction_date=t_date,
                    note=note
                )

        # 7. Tạo thông báo cảnh báo mẫu
        Notification.objects.get_or_create(
            user=student_user,
            threshold_type='80_PERCENT',
            message="⚠️ Nhắc nhở: Chi tiêu tháng 10/2026 của bạn đã chạm 88.2% hạn mức (3,970,000 đ / 4,500,000 đ). Hãy thắt chặt các khoản chi tiêu cuối tháng!",
            defaults={'is_read': False}
        )

        Notification.objects.get_or_create(
            user=student_user,
            threshold_type='80_PERCENT',
            message="⚠️ Nhắc nhở danh mục: Khoản 'Ăn uống' tháng 10/2026 đã sử dụng 75% hạn mức.",
            defaults={'is_read': True}
        )

        # 8. Tạo nhật ký hệ thống mẫu (System Logs)
        SystemLog.objects.get_or_create(
            user=student_user,
            action="LOGIN",
            details="Sinh viên sinhvien_test@ptit.edu.vn đăng nhập thành công."
        )
        SystemLog.objects.get_or_create(
            user=admin_user,
            action="SYSTEM",
            details="Khởi tạo cơ sở dữ liệu và bộ danh mục mặc định của hệ thống."
        )

        write_status(self.style.SUCCESS("Khởi tạo bộ dữ liệu thử nghiệm hoàn tất 100%!"))
