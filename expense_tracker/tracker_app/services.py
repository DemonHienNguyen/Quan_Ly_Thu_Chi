from decimal import Decimal
from django.db.models import Sum
from .models import Transaction, Budget, Notification, SystemLog


def log_system_action(user, action: str, details: str = None):
    """Ghi lại nhật ký hoạt động hệ thống (SystemLog)."""
    try:
        user_obj = user if (user and user.is_authenticated) else None
        SystemLog.objects.create(
            user=user_obj,
            action=action,
            details=details or ''
        )
    except Exception as e:
        print(f"Error logging system action: {e}")


def check_and_trigger_budget_alerts(user, transaction_date, category=None):
    """
    Quy trình 3 & FR-05: Tự động đối soát chi tiêu trong tháng với hạn mức ngân sách
    và kích hoạt cảnh báo thông minh tại các ngưỡng 80% (Warning) và 100% (Critical).
    """
    month = transaction_date.month
    year = transaction_date.year

    # 1. Kiểm tra đối soát Ngân sách tổng của tháng
    overall_budget = Budget.objects.filter(
        user=user,
        category__isnull=True,
        month=month,
        year=year
    ).first()

    if overall_budget and overall_budget.monthly_limit > 0:
        total_expense = Transaction.objects.filter(
            user=user,
            type='EXPENSE',
            transaction_date__year=year,
            transaction_date__month=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        ratio = (total_expense / overall_budget.monthly_limit) * 100

        if ratio >= 100:
            msg = (
                f"🚨 Cảnh báo khẩn cấp: Bạn đã chi {total_expense:,.0f} đ, vượt quá hạn mức ngân sách "
                f"tổng tháng {month}/{year} ({overall_budget.monthly_limit:,.0f} đ, đạt {ratio:.1f}%). "
                f"Hãy dừng ngay các khoản chi không cần thiết!"
            )
            # Kiểm tra xem đã có cảnh báo 100% chưa đọc gần đây chưa để tránh spam
            exists = Notification.objects.filter(
                user=user,
                threshold_type='100_PERCENT',
                created_at__year=year,
                created_at__month=month
            ).exists()
            if not exists:
                Notification.objects.create(
                    user=user,
                    threshold_type='100_PERCENT',
                    message=msg
                )
        elif ratio >= 80:
            msg = (
                f"⚠️ Nhắc nhở ngân sách: Chi tiêu tháng {month}/{year} của bạn đã đạt {ratio:.1f}% "
                f"hạn mức ({total_expense:,.0f} đ / {overall_budget.monthly_limit:,.0f} đ). Hãy cân nhắc thắt chặt chi tiêu!"
            )
            exists = Notification.objects.filter(
                user=user,
                threshold_type='80_PERCENT',
                created_at__year=year,
                created_at__month=month
            ).exists()
            if not exists:
                Notification.objects.create(
                    user=user,
                    threshold_type='80_PERCENT',
                    message=msg
                )

    # 2. Kiểm tra đối soát Ngân sách theo danh mục cụ thể (nếu có)
    if category:
        cat_budget = Budget.objects.filter(
            user=user,
            category=category,
            month=month,
            year=year
        ).first()

        if cat_budget and cat_budget.monthly_limit > 0:
            cat_expense = Transaction.objects.filter(
                user=user,
                category=category,
                type='EXPENSE',
                transaction_date__year=year,
                transaction_date__month=month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            cat_ratio = (cat_expense / cat_budget.monthly_limit) * 100

            if cat_ratio >= 100:
                msg = (
                    f"🚨 Vượt hạn mức danh mục: Chi tiêu '{category.category_name}' tháng {month}/{year} "
                    f"đã đạt {cat_ratio:.1f}% ({cat_expense:,.0f} đ / {cat_budget.monthly_limit:,.0f} đ)!"
                )
                exists = Notification.objects.filter(
                    user=user,
                    threshold_type='100_PERCENT',
                    message__contains=category.category_name,
                    created_at__year=year,
                    created_at__month=month
                ).exists()
                if not exists:
                    Notification.objects.create(
                        user=user,
                        threshold_type='100_PERCENT',
                        message=msg
                    )
            elif cat_ratio >= 80:
                msg = (
                    f"⚠️ Nhắc nhở danh mục: Khoản '{category.category_name}' tháng {month}/{year} "
                    f"đã dùng {cat_ratio:.1f}% hạn mức ({cat_expense:,.0f} đ / {cat_budget.monthly_limit:,.0f} đ)."
                )
                exists = Notification.objects.filter(
                    user=user,
                    threshold_type='80_PERCENT',
                    message__contains=category.category_name,
                    created_at__year=year,
                    created_at__month=month
                ).exists()
                if not exists:
                    Notification.objects.create(
                        user=user,
                        threshold_type='80_PERCENT',
                        message=msg
                    )
