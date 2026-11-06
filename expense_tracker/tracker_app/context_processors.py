from .models import Notification, Budget
from datetime import datetime
from decimal import Decimal


def notification_context(request):
    """
    Context processor cung cấp thông tin cảnh báo ngân sách cho thanh Navbar (base.html).
    Chỉ hiển thị chuông khi có cảnh báo ngân sách (>= 80%).
    """
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        try:
            # Kiểm tra ngân sách tổng thể tháng hiện tại
            now = datetime.now()
            overall_budget = Budget.objects.filter(
                user=user,
                category__isnull=True,
                month=now.month,
                year=now.year
            ).first()
            
            if overall_budget:
                from .models import Transaction
                from django.db.models import Sum
                overall_spent = Transaction.objects.filter(
                    user=user,
                    type='EXPENSE',
                    transaction_date__year=now.year,
                    transaction_date__month=now.month
                ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
                
                if overall_budget.monthly_limit > 0:
                    percent = int(round((overall_spent / overall_budget.monthly_limit) * 100))
                    if percent >= 80:
                        # Clamp percent for progress bar display (max 100%)
                        percent_display = min(percent, 100)
                        return {
                            'budget_alert': {
                                'percent': percent,
                                'percent_display': percent_display,
                                'spent': overall_spent,
                                'limit': overall_budget.monthly_limit,
                            }
                        }
        except Exception:
            pass
    
    return {
        'budget_alert': None,
    }