from decimal import Decimal
import bcrypt
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class AnonymousUser:
    id = None
    pk = None
    username = ''
    first_name = ''
    email = ''
    role = None
    status = None
    is_authenticated = False
    is_anonymous = True
    is_active = False
    is_superuser = False

    def get_full_name(self):
        return ''

    def __str__(self):
        return 'AnonymousUser'


class User(models.Model):
    """
    Mô hình Người dùng (User) - Quản lý thông tin tài khoản sinh viên và quản trị viên.
    Ghi chú: Mô hình độc lập không kế thừa AbstractUser, dùng password_hash để lưu mật khẩu đã băm.
    """
    ROLE_CHOICES = [
        ('STUDENT', 'Sinh viên'),
        ('ADMIN', 'Quản trị viên'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Hoạt động'),
        ('LOCKED', 'Bị khóa'),
    ]

    user_id = models.BigAutoField(primary_key=True, verbose_name="Mã người dùng")
    full_name = models.CharField(max_length=100, verbose_name="Họ và tên")
    email = models.EmailField(max_length=150, unique=True, verbose_name="Địa chỉ Email")
    password_hash = models.CharField(max_length=255, verbose_name="Mật khẩu đã mã hóa")
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='STUDENT',
        verbose_name="Vai trò"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name="Trạng thái"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        db_table = 'tracker_users'
        verbose_name = "Người dùng"
        verbose_name_plural = "Danh sách người dùng"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def id(self):
        return self.user_id

    @property
    def pk(self):
        return self.user_id

    @property
    def username(self):
        return self.email.split('@')[0] if self.email else ''

    @property
    def first_name(self):
        return self.full_name

    def get_full_name(self):
        return self.full_name

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_active(self):
        return self.status == 'ACTIVE'

    @property
    def is_superuser(self):
        return self.role == 'ADMIN'

    @property
    def date_joined(self):
        return self.created_at

    def check_password(self, raw_password: str) -> bool:
        try:
            return bcrypt.checkpw(raw_password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except Exception:
            return False

    def set_password(self, raw_password: str):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(raw_password.encode('utf-8'), salt).decode('utf-8')


class Category(models.Model):
    """
    Mô hình Danh mục thu chi (Category) - Phân loại các khoản chi tiêu hoặc thu nhập.
    Có thể là danh mục mặc định của hệ thống (is_default=True, user=None)
    hoặc danh mục do sinh viên tự tạo (user=User).
    """
    TYPE_CHOICES = [
        ('INCOME', 'Thu nhập'),
        ('EXPENSE', 'Chi tiêu'),
    ]

    category_id = models.AutoField(primary_key=True, verbose_name="Mã danh mục")
    category_name = models.CharField(max_length=100, verbose_name="Tên danh mục")
    icon = models.CharField(max_length=255, default='fa-folder', verbose_name="Biểu tượng")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Loại danh mục")
    is_default = models.BooleanField(default=True, verbose_name="Danh mục mặc định")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='categories',
        verbose_name="Người sở hữu"
    )

    class Meta:
        db_table = 'tracker_categories'
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục thu chi"
        ordering = ['type', 'category_name']

    def __str__(self):
        return f"{self.category_name} ({self.get_type_display()})"

    @property
    def id(self):
        return self.category_id

    @property
    def pk(self):
        return self.category_id

    @property
    def name(self):
        return self.category_name

    @name.setter
    def name(self, value):
        self.category_name = value

    @property
    def description(self):
        return "Danh mục mặc định hệ thống" if self.is_default else "Danh mục tùy chỉnh cá nhân"

    @staticmethod
    def icon_metadata(icon):
        icon = (icon or 'fa-folder').strip()
        if any(ord(character) > 127 for character in icon):
            return {'is_emoji': True, 'css_class': ''}

        classes = icon.split()
        style_classes = {'fa-solid', 'fa-regular', 'fa-brands', 'fa-light', 'fa-thin', 'fa-duotone'}
        if not any(class_name in style_classes for class_name in classes):
            classes.insert(0, 'fa-solid')
        return {'is_emoji': False, 'css_class': ' '.join(classes)}

    @property
    def icon_is_emoji(self):
        return self.icon_metadata(self.icon)['is_emoji']

    @property
    def icon_css_class(self):
        return self.icon_metadata(self.icon)['css_class']

    @property
    def display_icon(self):
        """Return the chosen icon value without inferring an icon from the category name."""
        return (self.icon or 'fa-folder').strip()


class Transaction(models.Model):
    """
    Mô hình Giao dịch (Transaction) - Ghi nhận các giao dịch chi tiêu hoặc thu nhập hàng ngày.
    """
    TYPE_CHOICES = [
        ('INCOME', 'Thu nhập'),
        ('EXPENSE', 'Chi tiêu'),
    ]

    transaction_id = models.BigAutoField(primary_key=True, verbose_name="Mã giao dịch")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Người dùng"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name='transactions',
        verbose_name="Danh mục"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Số tiền (VND)"
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Loại giao dịch")
    transaction_date = models.DateField(verbose_name="Ngày giao dịch")
    note = models.TextField(null=True, blank=True, verbose_name="Ghi chú")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo bản ghi")

    class Meta:
        db_table = 'tracker_transactions'
        verbose_name = "Giao dịch"
        verbose_name_plural = "Lịch sử giao dịch"
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'transaction_date'], name='idx_trans_user_date'),
        ]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Số tiền giao dịch phải lớn hơn 0 VND.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.full_name} - {self.category.category_name} - {self.amount:,.0f} VND ({self.transaction_date})"

    @property
    def id(self):
        return self.transaction_id

    @property
    def pk(self):
        return self.transaction_id

    @property
    def date(self):
        return self.transaction_date

    @date.setter
    def date(self, value):
        self.transaction_date = value

    @property
    def type_lower(self):
        return self.type.lower() if self.type else 'expense'


class Budget(models.Model):
    """
    Mô hình Ngân sách (Budget) - Quản lý giới hạn hạn mức chi tiêu theo tháng và danh mục.
    """
    budget_id = models.AutoField(primary_key=True, verbose_name="Mã ngân sách")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='budgets',
        verbose_name="Người dùng"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='budgets',
        verbose_name="Danh mục áp dụng"
    )
    monthly_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Hạn mức tháng (VND)"
    )
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Tháng (1-12)"
    )
    year = models.IntegerField(verbose_name="Năm")

    class Meta:
        db_table = 'tracker_budgets'
        verbose_name = "Ngân sách"
        verbose_name_plural = "Kế hoạch ngân sách"
        unique_together = ['user', 'category', 'month', 'year']
        indexes = [
            models.Index(fields=['user', 'month', 'year'], name='idx_budget_user_month'),
        ]

    def clean(self):
        super().clean()
        if self.monthly_limit is not None and self.monthly_limit <= 0:
            raise ValidationError({'monthly_limit': 'Hạn mức ngân sách phải lớn hơn 0 VND.'})
        if self.month is not None and not (1 <= self.month <= 12):
            raise ValidationError({'month': 'Tháng phải nằm trong khoảng từ 1 đến 12.'})
        if self.year is not None and self.year < 2000:
            raise ValidationError({'year': 'Năm không hợp lệ.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        cat_name = self.category.category_name if self.category else "Tổng thể"
        return f"Ngân sách {cat_name} ({self.month}/{self.year}): {self.monthly_limit:,.0f} VND"

    @property
    def id(self):
        return self.budget_id

    @property
    def pk(self):
        return self.budget_id

    @property
    def amount(self):
        return self.monthly_limit

    @amount.setter
    def amount(self, value):
        self.monthly_limit = value


class Notification(models.Model):
    """
    Mô hình Thông báo (Notification) - Lưu các cảnh báo khi chi tiêu vượt ngưỡng 80% hoặc 100% ngân sách.
    """
    THRESHOLD_CHOICES = [
        ('80_PERCENT', 'Cảnh báo 80%'),
        ('100_PERCENT', 'Cảnh báo 100%'),
    ]

    notification_id = models.BigAutoField(primary_key=True, verbose_name="Mã thông báo")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Người nhận"
    )
    message = models.TextField(verbose_name="Nội dung thông báo")
    threshold_type = models.CharField(
        max_length=20,
        choices=THRESHOLD_CHOICES,
        verbose_name="Loại cảnh báo"
    )
    is_read = models.BooleanField(default=False, verbose_name="Đã đọc")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")

    class Meta:
        db_table = 'tracker_notifications'
        verbose_name = "Thông báo"
        verbose_name_plural = "Danh sách thông báo"
        ordering = ['-created_at']

    def __str__(self):
        status = "Đã đọc" if self.is_read else "Chưa đọc"
        return f"[{self.get_threshold_type_display()}] {self.user.full_name}: {self.message[:40]}... ({status})"

    @property
    def id(self):
        return self.notification_id

    @property
    def pk(self):
        return self.notification_id

    @property
    def threshold(self):
        return 100 if self.threshold_type == '100_PERCENT' else 80

    @property
    def type(self):
        return 'critical' if self.threshold_type == '100_PERCENT' else 'warning'


class SystemLog(models.Model):
    """
    Mô hình Nhật ký hệ thống (SystemLog) - Ghi lại hành vi, thao tác người dùng và sự kiện hệ thống.
    """
    log_id = models.BigAutoField(primary_key=True, verbose_name="Mã nhật ký")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_logs',
        verbose_name="Người thực hiện"
    )
    action = models.CharField(max_length=100, verbose_name="Hành động")
    details = models.TextField(null=True, blank=True, verbose_name="Chi tiết thao tác")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời điểm ghi nhận")

    class Meta:
        db_table = 'tracker_system_logs'
        verbose_name = "Nhật ký hệ thống"
        verbose_name_plural = "Nhật ký hệ thống"
        ordering = ['-created_at']

    def __str__(self):
        user_display = self.user.full_name if self.user else "Hệ thống / Ẩn danh"
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {user_display} - {self.action}"

    @property
    def id(self):
        return self.log_id

    @property
    def pk(self):
        return self.log_id

    @property
    def timestamp(self):
        return self.created_at
