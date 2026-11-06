import time
from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from tracker_app.models import User, Category, Transaction, Budget, Notification, SystemLog
from tracker_app.auth_utils import hash_password, generate_jwt_token


class ExpenseTrackerTestCase(TestCase):
    """
    Tập kịch bản kiểm thử tự động bám sát Bảng 5.2 Kịch bản thử nghiệm nghiệp vụ và chất lượng hệ thống.
    """

    def setUp(self):
        self.client = Client()

        # Tạo tài khoản Sinh viên A
        self.student_a = User.objects.create(
            full_name="Sinh Viên A",
            email="sinhvien_test@ptit.edu.vn",
            password_hash=hash_password("Password@123"),
            role="STUDENT",
            status="ACTIVE"
        )
        self.token_a = generate_jwt_token(self.student_a)

        # Tạo tài khoản Sinh viên B
        self.student_b = User.objects.create(
            full_name="Sinh Viên B",
            email="sinhvien2_test@ptit.edu.vn",
            password_hash=hash_password("Password@456"),
            role="STUDENT",
            status="ACTIVE"
        )
        self.token_b = generate_jwt_token(self.student_b)

        # Tạo danh mục hệ thống
        self.cat_food = Category.objects.create(
            category_name="Ăn uống",
            type="EXPENSE",
            icon="fa-utensils",
            is_default=True
        )

        self.cat_salary = Category.objects.create(
            category_name="Tiền lương",
            type="INCOME",
            icon="fa-money-bill-wave",
            is_default=True
        )

    def test_tc01_duplicate_email_registration(self):
        """Tài khoản không được tạo qua URL đăng ký đã tắt."""
        response = self.client.post(reverse('register'), {
            'full_name': 'Người Dùng Trùng Email',
            'email': 'unapproved_student@ptit.edu.vn',
            'password': 'Password@789',
            'confirm_password': 'Password@789',
        })
        self.assertRedirects(response, reverse('login'))
        self.assertFalse(User.objects.filter(email='unapproved_student@ptit.edu.vn').exists())

    def test_only_approved_accounts_can_login_or_reuse_existing_tokens(self):
        unapproved_user = User.objects.create(
            full_name='Tài khoản cũ',
            email='legacy_student@ptit.edu.vn',
            password_hash=hash_password('Legacy@123'),
            role='STUDENT',
            status='ACTIVE',
        )
        login_response = self.client.post(reverse('login'), {
            'username': unapproved_user.email,
            'password': 'Legacy@123',
        })
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, 'Email hoặc mật khẩu không chính xác.')

        self.client.cookies['jwt_token'] = generate_jwt_token(unapproved_user)
        protected_response = self.client.get(reverse('dashboard'))
        self.assertRedirects(protected_response, reverse('login'))
        self.assertTrue(User.objects.filter(pk=unapproved_user.pk).exists())

    def test_tc02_negative_transaction_amount(self):
        """TC02: Nhập giao dịch với số tiền âm hoặc <= 0 -> Bị từ chối."""
        self.client.cookies['jwt_token'] = self.token_a
        response = self.client.post(reverse('save_transaction'), {
            'type': 'expense',
            'amount': '-50000',  # Số tiền âm
            'category': self.cat_food.category_id,
            'date': '2026-10-12',
            'note': 'Test số tiền âm'
        })
        # Không có giao dịch nào được lưu
        self.assertFalse(Transaction.objects.filter(user=self.student_a, amount__lte=0).exists())

    def test_tc03_rbac_security_cross_user_isolation(self):
        """TC03: Bảo mật / RBAC: Sinh viên A cố tình sửa/xóa giao dịch của Sinh viên B -> Bị chặn 403."""
        # Sinh viên B tạo 1 giao dịch
        trans_b = Transaction.objects.create(
            user=self.student_b,
            category=self.cat_food,
            amount=Decimal('100000.00'),
            type='EXPENSE',
            transaction_date=date(2026, 10, 10),
            note="Giao dịch của B"
        )

        # Sinh viên A đăng nhập
        self.client.cookies['jwt_token'] = self.token_a

        # Sinh viên A cố xóa giao dịch của B
        del_resp = self.client.get(reverse('delete_transaction', args=[trans_b.transaction_id]))
        self.assertEqual(del_resp.status_code, 403)
        self.assertTrue(Transaction.objects.filter(transaction_id=trans_b.transaction_id).exists())

        # Sinh viên A cố sửa giao dịch của B
        edit_resp = self.client.post(reverse('save_transaction'), {
            'transaction_id': trans_b.transaction_id,
            'type': 'expense',
            'amount': '200000',
            'category': self.cat_food.category_id,
            'date': '2026-10-10'
        })
        self.assertEqual(edit_resp.status_code, 403)

    def test_tc04_budget_warning_80_percent_alert(self):
        """TC04: Ngân sách & Cảnh báo: Đặt hạn mức 1.000.000đ, thêm chi 850.000đ -> Kích hoạt cảnh báo 80% (Warning)."""
        self.client.cookies['jwt_token'] = self.token_a

        # Đặt ngân sách tổng 1.000.000 VND cho tháng 10/2026
        Budget.objects.create(
            user=self.student_a,
            category=None,
            month=10,
            year=2026,
            monthly_limit=Decimal('1000000.00')
        )

        # Thêm khoản chi 850.000đ (85% >= 80%)
        self.client.post(reverse('save_transaction'), {
            'type': 'expense',
            'amount': '850000',
            'category': self.cat_food.category_id,
            'date': '2026-10-05',
            'note': 'Chi tiêu vượt 80%'
        })

        notif = Notification.objects.filter(
            user=self.student_a,
            threshold_type='80_PERCENT'
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("85.0%", notif.message)

    def test_tc05_budget_critical_100_percent_alert(self):
        """TC05: Ngân sách & Cảnh báo: Tiếp tục thêm chi 200.000đ (tổng 1.050.000đ) -> Kích hoạt cảnh báo 100% (Critical)."""
        self.client.cookies['jwt_token'] = self.token_a

        # Đặt ngân sách 1.000.000 VND
        Budget.objects.create(
            user=self.student_a,
            category=None,
            month=10,
            year=2026,
            monthly_limit=Decimal('1000000.00')
        )

        # Thêm khoản chi 1.050.000 VND (105% >= 100%)
        self.client.post(reverse('save_transaction'), {
            'type': 'expense',
            'amount': '1050000',
            'category': self.cat_food.category_id,
            'date': '2026-10-06',
            'note': 'Chi tiêu vượt 100%'
        })

        notif = Notification.objects.filter(
            user=self.student_a,
            threshold_type='100_PERCENT'
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("105.0%", notif.message)

    def test_tc06_performance_response_time(self):
        """TC06: Hiệu năng (Performance): Thời gian phản hồi Dashboard < 1.0 giây (<= 1000ms)."""
        self.client.cookies['jwt_token'] = self.token_a

        start_time = time.time()
        response = self.client.get(reverse('dashboard'))
        elapsed_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed_time, 1.0, f"Thời gian phản hồi {elapsed_time:.3f}s vượt quá ngưỡng 1.0s")

    def test_tc07_income_transaction_and_type_check(self):
        """TC07: Đăng ký khoản Thu nhập qua view save_transaction -> Lưu đúng type=INCOME và hiển thị đúng."""
        self.client.cookies['jwt_token'] = self.token_a

        # Thêm khoản thu nhập 5.000.000đ
        response = self.client.post(reverse('save_transaction'), {
            'type': 'income',
            'amount': '5000000',
            'category': self.cat_salary.category_id,
            'date': '2026-10-10',
            'note': 'Lương thực tập IT'
        })
        self.assertEqual(response.status_code, 302)

        trans = Transaction.objects.filter(user=self.student_a, category=self.cat_salary).first()
        self.assertIsNotNone(trans)
        self.assertEqual(trans.type, 'INCOME')
        self.assertEqual(trans.type_lower, 'income')
        self.assertEqual(trans.amount, Decimal('5000000'))

    def test_transaction_rejects_category_that_does_not_match_type(self):
        self.client.cookies['jwt_token'] = self.token_a
        response = self.client.post(reverse('save_transaction'), {
            'type': 'expense',
            'amount': '50000',
            'category': self.cat_salary.category_id,
            'date': '2026-10-10',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(user=self.student_a).exists())
        self.assertContains(response, 'Danh mục không hợp lệ hoặc không phù hợp với loại giao dịch.')

    def test_transaction_rejects_invalid_date_instead_of_substituting_today(self):
        self.client.cookies['jwt_token'] = self.token_a
        response = self.client.post(reverse('save_transaction'), {
            'type': 'expense',
            'amount': '50000',
            'category': self.cat_food.category_id,
            'date': 'not-a-date',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(user=self.student_a).exists())
        self.assertContains(response, 'Vui lòng chọn ngày giao dịch hợp lệ.')

    def test_transaction_delete_requires_post(self):
        transaction = Transaction.objects.create(
            user=self.student_a,
            category=self.cat_food,
            amount=Decimal('50000'),
            type='EXPENSE',
            transaction_date=date(2026, 10, 10),
        )
        self.client.cookies['jwt_token'] = self.token_a

        self.client.get(reverse('delete_transaction', args=[transaction.transaction_id]))
        self.assertTrue(Transaction.objects.filter(pk=transaction.transaction_id).exists())

        self.client.post(reverse('delete_transaction', args=[transaction.transaction_id]))
        self.assertFalse(Transaction.objects.filter(pk=transaction.transaction_id).exists())

    def test_budget_rejects_income_category_and_category_budget_is_editable(self):
        self.client.cookies['jwt_token'] = self.token_a
        response = self.client.post(reverse('set_category_budget'), {
            'month': '2026-10',
            'category': self.cat_salary.category_id,
            'amount': '250000',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Budget.objects.filter(user=self.student_a).exists())

        self.client.post(reverse('set_category_budget'), {
            'month': '2026-10',
            'category': self.cat_food.category_id,
            'amount': '250000',
        })
        self.client.post(reverse('set_category_budget'), {
            'month': '2026-10',
            'category': self.cat_food.category_id,
            'amount': '300000',
        })
        category_budgets = Budget.objects.filter(
            user=self.student_a,
            category=self.cat_food,
            month=10,
            year=2026,
        )
        self.assertEqual(category_budgets.count(), 1)
        self.assertEqual(category_budgets.get().monthly_limit, Decimal('300000'))

    def test_budget_page_renders_selected_month_and_category_progress(self):
        Budget.objects.create(
            user=self.student_a,
            category=self.cat_food,
            monthly_limit=Decimal('200000.00'),
            month=10,
            year=2026,
        )
        Transaction.objects.create(
            user=self.student_a,
            category=self.cat_food,
            amount=Decimal('50000.00'),
            type='EXPENSE',
            transaction_date=date(2026, 10, 10),
        )
        self.client.cookies['jwt_token'] = self.token_a
        response = self.client.get(reverse('budget'), {'month': '2026-10'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2026-10')
        self.assertContains(response, 'Ăn uống')
        self.assertContains(response, '25%')
        self.assertContains(response, 'deleteCategoryBudgetModal')
        self.assertNotContains(response, 'onsubmit="return confirm(')

    def test_dashboard_month_picker_has_no_extra_controls(self):
        self.client.cookies['jwt_token'] = self.token_a
        response = self.client.get(reverse('dashboard'), {'month': '2026-01'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="dashboardMonth"')
        self.assertNotContains(response, 'Tháng trước')
        self.assertNotContains(response, 'Xem tháng')

    def test_admin_logs_show_ten_rows_per_page_and_filter_requires_submit(self):
        admin = User.objects.create(
            full_name='Quản trị viên',
            email='admin_system@ptit.edu.vn',
            password_hash=hash_password('Admin@123'),
            role='ADMIN',
            status='ACTIVE',
        )
        for index in range(25):
            SystemLog.objects.create(
                user=self.student_a,
                action='LOGIN' if index % 2 == 0 else 'REGISTER',
                details=f'Log kiểm thử {index}',
            )
        self.client.cookies['jwt_token'] = generate_jwt_token(admin)

        first_page = self.client.get(reverse('admin_logs'))
        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(len(first_page.context['logs']), 10)
        self.assertEqual(first_page.context['page_obj'].paginator.count, 25)
        self.assertNotContains(first_page, 'onchange="this.form.submit()"')

        filtered_page = self.client.get(reverse('admin_logs'), {'action_type': 'LOGIN'})
        self.assertEqual(filtered_page.status_code, 200)
        self.assertEqual(len(filtered_page.context['logs']), 10)
        self.assertEqual(filtered_page.context['page_obj'].paginator.count, 13)

    def test_admin_user_status_uses_app_modal_instead_of_browser_confirm(self):
        admin = User.objects.create(
            full_name='Quản trị viên',
            email='admin_system@ptit.edu.vn',
            password_hash=hash_password('Admin@123'),
            role='ADMIN',
            status='ACTIVE',
        )
        self.client.cookies['jwt_token'] = generate_jwt_token(admin)

        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'userStatusConfirmModal')
        self.assertContains(response, 'open-user-status-modal')
        self.assertNotContains(response, 'confirm(')

        student = User.objects.get(email='sinhvien_test@ptit.edu.vn')
        self.client.post(reverse('toggle_user_status', args=[student.user_id]))
        student.refresh_from_db()
        self.assertEqual(student.status, 'LOCKED')

    def test_delete_category_requires_post_and_deletes_personal_category(self):
        category = Category.objects.create(
            user=self.student_a,
            category_name='Ăn vặt',
            type='EXPENSE',
            is_default=False,
        )
        self.client.cookies['jwt_token'] = self.token_a

        get_response = self.client.get(reverse('delete_category', args=[category.category_id]))
        self.assertEqual(get_response.status_code, 302)
        self.assertTrue(Category.objects.filter(pk=category.category_id).exists())

        page = self.client.get(reverse('categories'))
        self.assertContains(page, 'deleteCategoryModal')
        self.client.post(reverse('delete_category', args=[category.category_id]))
        self.assertFalse(Category.objects.filter(pk=category.category_id).exists())

    def test_delete_category_with_transactions_shows_error(self):
        category = Category.objects.create(
            user=self.student_a,
            category_name='Danh mục đang dùng',
            type='EXPENSE',
            is_default=False,
        )
        Transaction.objects.create(
            user=self.student_a,
            category=category,
            amount=Decimal('50000'),
            type='EXPENSE',
            transaction_date=date(2026, 10, 10),
        )
        self.client.cookies['jwt_token'] = self.token_a

        response = self.client.post(reverse('delete_category', args=[category.category_id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(pk=category.category_id).exists())
        self.assertContains(response, 'đang được giao dịch sử dụng')

    def test_transaction_list_has_custom_delete_confirmation_and_type_hint(self):
        self.client.cookies['jwt_token'] = self.token_a
        response = self.client.get(reverse('transactions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'deleteTransactionModal')
        self.assertContains(response, 'categoryTypeHint')
        self.assertNotContains(response, 'confirm(')

    def test_selected_category_icon_is_rendered_as_the_selected_fontawesome_icon(self):
        category = Category.objects.create(
            user=self.student_a,
            category_name='Hóa đơn',
            type='EXPENSE',
            icon='fa-receipt',
            is_default=False,
        )
        self.client.cookies['jwt_token'] = self.token_a

        categories_response = self.client.get(reverse('categories'))
        self.assertContains(categories_response, 'fa-solid fa-receipt')
        self.assertNotContains(categories_response, '🧾')

        transactions_response = self.client.get(reverse('transactions'))
        self.assertContains(transactions_response, 'data-icon-class="fa-solid fa-receipt"')

        Transaction.objects.create(
            user=self.student_a,
            category=category,
            amount=Decimal('50000'),
            type='EXPENSE',
            transaction_date=date(2026, 11, 4),
        )
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard_response, 'fa-solid fa-receipt')

    def test_desktop_initialization_seeds_categories_without_demo_accounts(self):
        """Desktop first run creates usable categories without test accounts or private data."""
        existing_user_count = User.objects.count()
        call_command('seed_data', defaults_only=True, verbosity=0)

        seeded_categories = [
            "Tiền lương / Làm thêm", "Phụ cấp gia đình", "Học bổng",
            "Dự án / Freelance", "Ăn uống", "Tiền nhà / Phòng trọ",
            "Học phí & Sách vở", "Đi lại / Xăng xe", "Giải trí / Bạn bè",
            "Mua sắm cá nhân", "Thuốc men / Y tế", "Hóa đơn Điện / Nước",
        ]
        self.assertEqual(
            Category.objects.filter(is_default=True, category_name__in=seeded_categories).count(),
            12,
        )
        self.assertEqual(User.objects.count(), existing_user_count)
        self.assertFalse(Transaction.objects.exists())

    def test_login_auto_creates_demo_accounts_when_db_is_empty(self):
        """Nếu DB chưa có user nào, hệ thống tự khởi tạo tài khoản demo để login được ngay."""
        User.objects.all().delete()
        Category.objects.all().delete()
        response = self.client.post(reverse('login'), {
            'username': 'sinhvien_test@ptit.edu.vn',
            'password': 'Student@2026',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='sinhvien_test@ptit.edu.vn').exists())
        self.assertTrue(User.objects.filter(email='admin_system@ptit.edu.vn').exists())
        self.assertTrue(User.objects.filter(email='sinhvien2_test@ptit.edu.vn').exists())

    def test_login_invalid_input_keeps_email_and_renders_error_message(self):
        """Lỗi nhập sai hoặc thiếu trường phải giữ email đã nhập và hiển thị thông báo rõ ràng."""
        response = self.client.post(reverse('login'), {
            'username': 'student_x@ptit.edu.vn',
            'password': '',
        }, follow=True)
        html = response.content.decode('utf-8', errors='ignore')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Vui lòng nhập đầy đủ Email và Mật khẩu.', html)
        self.assertIn('student_x@ptit.edu.vn', html)
        self.assertIn('/static/images/ptit-logo.png', html)

    def test_only_successful_login_uses_auto_dismissing_toast(self):
        login_response = self.client.post(reverse('login'), {
            'username': 'sinhvien_test@ptit.edu.vn',
            'password': 'Password@123',
        }, follow=True)
        login_html = login_response.content.decode('utf-8', errors='ignore')
        self.assertIn('<div class="login-success-toast"', login_html)

        register_client = Client()
        register_response = register_client.post(reverse('register'), {
            'full_name': 'Sinh Viên Mới',
            'email': 'new_student@ptit.edu.vn',
            'password': 'Password@789',
            'confirm_password': 'Password@789',
        }, follow=True)
        register_html = register_response.content.decode('utf-8', errors='ignore')
        self.assertNotIn('<div class="login-success-toast"', register_html)
