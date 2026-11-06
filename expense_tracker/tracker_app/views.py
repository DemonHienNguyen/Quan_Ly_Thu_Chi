import json
import re
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.db.models.deletion import ProtectedError, RestrictedError

from .models import User, Category, Transaction, Budget, Notification, SystemLog
from .auth_utils import (
    hash_password, verify_password, generate_jwt_token,
    login_required_custom, admin_required_custom
)
from .services import log_system_action, check_and_trigger_budget_alerts
from .management.commands.seed_data import ensure_demo_accounts
from .account_policy import approved_email_for_login


# ==============================================================================
# 1. XÁC THỰC & ĐĂNG NHẬP / ĐĂNG KÝ (FR-01)
# ==============================================================================

def login_view(request):
    """Màn hình Đăng nhập (FR-01) - Hỗ trợ đăng nhập qua Form & trả JWT Token."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    ensure_demo_accounts()

    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not identifier or not password:
            messages.error(request, 'Vui lòng nhập đầy đủ Email và Mật khẩu.')
            return render(
                request,
                'tracker_app/login.html',
                {'show_register_tab': False, 'username_value': identifier},
            )

        approved_email = approved_email_for_login(identifier)
        user = User.objects.filter(email__iexact=approved_email).first() if approved_email else None

        if not user or not user.check_password(password):
            messages.error(request, 'Email hoặc mật khẩu không chính xác.')
            return render(
                request,
                'tracker_app/login.html',
                {'show_register_tab': False, 'username_value': identifier},
            )

        if user.status != 'ACTIVE':
            messages.error(request, 'Tài khoản của bạn đã bị khóa bởi Quản trị viên (LOCKED). Vui lòng liên hệ hỗ trợ.')
            return render(
                request,
                'tracker_app/login.html',
                {'show_register_tab': False, 'username_value': identifier},
            )

        # Đăng nhập thành công: Phát hành JWT Token (hết hạn sau 30 ngày)
        token = generate_jwt_token(user, days=30)
        request.session['jwt_token'] = token
        log_system_action(user, 'LOGIN', f"Người dùng {user.email} đăng nhập thành công vào hệ thống.")

        response = redirect('dashboard')
        response.set_cookie('jwt_token', token, max_age=30*24*3600, httponly=True, samesite='Lax')
        messages.success(
            request,
            f"Chào mừng trở lại, {user.full_name}!",
            extra_tags='login-success',
        )
        return response

    return render(request, 'tracker_app/login.html', {'show_register_tab': False, 'username_value': ''})


def register_view(request):
    """Registration is disabled; only provisioned accounts can use the application."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    messages.error(request, 'Đăng ký tài khoản đã tắt. Vui lòng sử dụng tài khoản được cấp.')
    return redirect('login')


def logout_view(request):
    """Đăng xuất khỏi hệ thống: Xóa JWT cookie và session."""
    if request.user.is_authenticated:
        log_system_action(request.user, 'LOGOUT', f"Người dùng {request.user.email} đăng xuất.")
    request.session.flush()
    response = redirect('login')
    response.delete_cookie('jwt_token')
    messages.info(request, 'Bạn đã đăng xuất khỏi hệ thống thành công.')
    return response


# ==============================================================================
# 2. BẢNG ĐIỀU KHIỂN & BIỂU ĐỒ TÀI CHÍNH (FR-06)
# ==============================================================================

@login_required_custom
def dashboard_view(request):
    """
    Màn hình Dashboard (FR-06):
    - Tổng quan Thu/Chi/Số dư (Số dư = TổngThu - TổngChi).
    - Biểu đồ Doughnut phân bổ tỷ lệ % chi tiêu theo danh mục.
    - Biểu đồ Bar grouped so sánh Thu nhập vs Chi tiêu theo chuỗi các tháng.
    - Widget: Top danh mục, Tiến độ ngân sách, Sức khỏe tài chính.
    """
    user = request.user

    # Chọn tháng/năm xem báo cáo (mặc định tháng hiện tại dạng YYYY-MM)
    now = datetime.now()
    selected_month_str = request.GET.get('month', now.strftime('%Y-%m'))
    try:
        sel_year, sel_month = map(int, selected_month_str.split('-'))
    except Exception:
        sel_year, sel_month = now.year, now.month
        selected_month_str = now.strftime('%Y-%m')

    # Lọc giao dịch trong tháng đã chọn: Nếu là Admin/Superuser thì xem toàn hệ thống của tất cả sinh viên
    is_admin_user = (user.is_superuser or getattr(user, 'role', '') == 'ADMIN')
    if is_admin_user:
        trans_month = Transaction.objects.filter(
            transaction_date__year=sel_year,
            transaction_date__month=sel_month
        )
    else:
        trans_month = Transaction.objects.filter(
            user=user,
            transaction_date__year=sel_year,
            transaction_date__month=sel_month
        )

    total_income = trans_month.filter(type='INCOME').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    total_expense = trans_month.filter(type='EXPENSE').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    balance = total_income - total_expense

    # --- Tính trend so với tháng trước ---
    # Tháng trước
    if sel_month == 1:
        prev_year, prev_month = sel_year - 1, 12
    else:
        prev_year, prev_month = sel_year, sel_month - 1

    if is_admin_user:
        prev_income = Transaction.objects.filter(
            type='INCOME',
            transaction_date__year=prev_year,
            transaction_date__month=prev_month
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        prev_expense = Transaction.objects.filter(
            type='EXPENSE',
            transaction_date__year=prev_year,
            transaction_date__month=prev_month
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    else:
        prev_income = Transaction.objects.filter(
            user=user,
            type='INCOME',
            transaction_date__year=prev_year,
            transaction_date__month=prev_month
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        prev_expense = Transaction.objects.filter(
            user=user,
            type='EXPENSE',
            transaction_date__year=prev_year,
            transaction_date__month=prev_month
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    prev_month_income = prev_income
    prev_month_expense = prev_expense

    income_trend = None
    expense_trend = None
    if prev_income > 0:
        income_trend = float((total_income - prev_income) / prev_income * 100)
    if prev_expense > 0:
        expense_trend = float((total_expense - prev_expense) / prev_expense * 100)

    # --- Tỷ lệ tiết kiệm ---
    savings_rate = None
    if total_income > 0:
        savings_rate = int(round((balance / total_income) * 100))

    # 1. Chuẩn bị dữ liệu cho Biểu đồ Tròn/Doughnut (% chi tiêu theo danh mục)
    cat_expenses = (
        trans_month.filter(type='EXPENSE')
        .values('category__category_name', 'category__icon')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    pie_labels = [c['category__category_name'] for c in cat_expenses]
    pie_data_values = [float(c['total']) for c in cat_expenses]

    pie_data = {
        'labels': pie_labels,
        'data': pie_data_values
    }

    # Top categories cho widget (top 5)
    top_categories = []
    total_expense_float = float(total_expense)
    for c in cat_expenses[:5]:
        cat_total = float(c['total'])
        percentage = int(round(cat_total / total_expense_float * 100)) if total_expense_float > 0 else 0
        icon = Category.icon_metadata(c['category__icon'])
        top_categories.append({
            'category_name': c['category__category_name'],
            'total': c['total'],
            'percentage': percentage,
            'icon_is_emoji': icon['is_emoji'],
            'icon_css_class': icon['css_class'],
            'icon_text': c['category__icon'] if icon['is_emoji'] else '',
        })

    # 2. Chuẩn bị dữ liệu cho Biểu đồ Cột (6 tháng gần nhất: Thu vs Chi)
    bar_labels = []
    bar_income = []
    bar_expense = []

    for i in range(5, -1, -1):
        target_date = (date(sel_year, sel_month, 1) - timedelta(days=i * 28)).replace(day=1)
        m_label = f"T{target_date.month}/{target_date.year % 100}"
        bar_labels.append(m_label)

        if is_admin_user:
            m_inc = Transaction.objects.filter(
                type='INCOME',
                transaction_date__year=target_date.year,
                transaction_date__month=target_date.month
            ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

            m_exp = Transaction.objects.filter(
                type='EXPENSE',
                transaction_date__year=target_date.year,
                transaction_date__month=target_date.month
            ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        else:
            m_inc = Transaction.objects.filter(
                user=user,
                type='INCOME',
                transaction_date__year=target_date.year,
                transaction_date__month=target_date.month
            ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

            m_exp = Transaction.objects.filter(
                user=user,
                type='EXPENSE',
                transaction_date__year=target_date.year,
                transaction_date__month=target_date.month
            ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

        bar_income.append(float(m_inc))
        bar_expense.append(float(m_exp))

    bar_data = {
        'labels': bar_labels,
        'income': bar_income,
        'expense': bar_expense
    }

    # --- Ngân sách tổng thể tháng này ---
    overall_budget_obj = Budget.objects.filter(
        user=user,
        category__isnull=True,
        month=sel_month,
        year=sel_year
    ).first()

    overall_budget = overall_budget_obj.monthly_limit if overall_budget_obj else Decimal('0.00')
    overall_spent = total_expense  # Chi tiêu thực tế trong tháng

    if overall_budget > 0:
        overall_percent = int(round((overall_spent / overall_budget) * 100))
        overall_remaining = overall_budget - overall_spent
    else:
        overall_percent = 0
        overall_remaining = Decimal('0.00')

    # Clamp percent for progress bar (max 100%)
    overall_percent_display = min(overall_percent, 100)

    # --- Trạng thái ngân sách ---
    if overall_budget > 0:
        if overall_percent >= 100:
            budget_status = 'danger'
        elif overall_percent >= 80:
            budget_status = 'warning'
        else:
            budget_status = 'safe'
    else:
        budget_status = 'none'

    # --- Mẹo tài chính ---
    health_tip = ""
    if budget_status == 'danger':
        health_tip = "Bạn đã vượt ngân sách! Hãy xem lại chi tiêu hoặc tăng hạn mức."
    elif budget_status == 'warning':
        health_tip = "Sắp đạt hạn mức ngân sách. Cân nhắc giảm chi tiêu không cần thiết."
    elif savings_rate is not None and savings_rate >= 20:
        health_tip = "Tuyệt vời! Bạn đang tiết kiệm tốt. Hãy duy trì thói quen này."
    elif savings_rate is not None and savings_rate >= 10:
        health_tip = "Tỷ lệ tiết kiệm khá tốt. Hãy cố gắng đạt 20% để an toàn hơn."
    elif balance < 0:
        health_tip = "Chi tiêu vượt thu nhập. Cần rà soát lại các khoản chi ngay lập tức."
    else:
        health_tip = "Hãy đặt ngân sách và ghi chép thường xuyên để kiểm soát tài chính tốt hơn."

    # Giao dịch gần nhất
    if is_admin_user:
        recent_transactions = Transaction.objects.all().order_by('-transaction_date', '-created_at')[:6]
    else:
        recent_transactions = Transaction.objects.filter(user=user).order_by('-transaction_date', '-created_at')[:6]

    # Thông báo cảnh báo ngân sách hoạt động của tháng
    active_budget_alert = Notification.objects.filter(
        user=user,
        created_at__year=sel_year,
        created_at__month=sel_month
    ).order_by('-created_at').first()

    context = {
        'selected_month': selected_month_str,
        'current_month': now.strftime('%Y-%m'),
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'pie_data': json.dumps(pie_data),
        'bar_data': json.dumps(bar_data),
        'recent_transactions': recent_transactions,
        'active_budget_alert': active_budget_alert,
        # New context variables
        'prev_month_income': prev_month_income,
        'prev_month_expense': prev_month_expense,
        'income_trend': income_trend,
        'expense_trend': expense_trend,
        'savings_rate': savings_rate,
        'top_categories': top_categories,
        'overall_budget': overall_budget,
        'overall_spent': overall_spent,
        'overall_percent': overall_percent,
        'overall_percent_display': min(overall_percent, 100),
        'overall_remaining': overall_remaining,
        'budget_status': budget_status,
        'health_tip': health_tip,
        'current_page_title': 'Tổng quan',
    }
    return render(request, 'tracker_app/dashboard.html', context)


# ==============================================================================
# 3. QUẢN LÝ GIAO DỊCH THU / CHI (FR-02)
# ==============================================================================

@login_required_custom
def transactions_view(request):
    """
    Màn hình Quản lý giao dịch Thu/Chi (FR-02):
    - Danh sách sắp xếp theo thời gian mới nhất.
    - Bộ lọc theo tháng, theo loại (Thu/Chi), theo danh mục.
    - Phân trang, mở form thêm giao dịch nhanh.
    - Nếu là Admin/Superuser: xem danh sách toàn bộ giao dịch của sinh viên.
    """
    user = request.user
    now = datetime.now()
    is_admin_user = (user.is_superuser or getattr(user, 'role', '') == 'ADMIN')

    # Bộ lọc
    selected_month = request.GET.get('month') or now.strftime('%Y-%m')
    selected_type = request.GET.get('type', '').lower()
    selected_category = request.GET.get('category', '')

    if is_admin_user:
        queryset = Transaction.objects.all()
    else:
        queryset = Transaction.objects.filter(user=user)

    if selected_month:
        try:
            y, m = map(int, selected_month.split('-'))
            if len(selected_month) != 7 or not (1 <= m <= 12):
                raise ValueError
            queryset = queryset.filter(transaction_date__year=y, transaction_date__month=m)
        except (AttributeError, TypeError, ValueError):
            selected_month = now.strftime('%Y-%m')
            y, m = now.year, now.month
            queryset = queryset.filter(transaction_date__year=y, transaction_date__month=m)

    if selected_type in ['income', 'expense']:
        queryset = queryset.filter(type=selected_type.upper())

    if selected_category:
        try:
            queryset = queryset.filter(category_id=int(selected_category))
        except Exception:
            pass

    queryset = queryset.select_related('category').order_by('-transaction_date', '-created_at')

    # Thống kê tổng hợp theo bộ lọc hiện tại
    filtered_income = queryset.filter(type='INCOME').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    filtered_expense = queryset.filter(type='EXPENSE').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    filtered_balance = filtered_income - filtered_expense

    # Phân trang (12 giao dịch mỗi trang)
    paginator = Paginator(queryset, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Lấy danh mục hợp lệ (mặc định hệ thống + tùy chỉnh cá nhân của user, hoặc tất cả nếu là admin)
    if is_admin_user:
        categories = Category.objects.all().order_by('type', 'category_name')
    else:
        categories = Category.objects.filter(Q(is_default=True) | Q(user=user)).order_by('type', 'category_name')


    # Định dạng lại danh mục tương thích template (với trường .type là 'income'/'expense')
    cat_list = []
    for c in categories:
        icon = Category.icon_metadata(c.icon)
        cat_list.append({
            'id': c.category_id,
            'name': c.category_name,
            'type': c.type.lower(),
            'icon': c.icon,
            'icon_is_emoji': icon['is_emoji'],
            'icon_css_class': icon['css_class'],
        })

    context = {
        'page_obj': page_obj,
        'transactions': page_obj.object_list,
        'is_paginated': page_obj.has_other_pages(),
        'selected_month': selected_month,
        'current_month': now.strftime('%Y-%m'),
        'selected_type': selected_type,
        'selected_category': selected_category,
        'total_income': filtered_income,
        'total_expense': filtered_expense,
        'balance': filtered_balance,
        'filtered_income': filtered_income,
        'filtered_expense': filtered_expense,
        'filtered_balance': filtered_balance,
        'categories': cat_list,
        'current_page_title': 'Giao dịch',
    }
    return render(request, 'tracker_app/transactions.html', context)


@login_required_custom
def save_transaction_view(request):
    """Thêm mới hoặc Chỉnh sửa giao dịch Thu/Chi (FR-02) + Đối soát cảnh báo (FR-05)."""
    if request.method != 'POST':
        return redirect('transactions')

    user = request.user
    trans_id = request.POST.get('transaction_id')
    raw_amount = request.POST.get('amount')
    raw_type = request.POST.get('type', 'expense').strip().upper()
    cat_id = request.POST.get('category')
    raw_date = request.POST.get('date')
    note = request.POST.get('note', '').strip()

    # TC02: Kiểm tra số tiền hợp lệ (> 0)
    try:
        amount = Decimal(str(raw_amount).replace(',', ''))
        if not amount.is_finite() or amount <= 0 or amount > Decimal('9999999999999.99') or amount.as_tuple().exponent < -2:
            messages.error(request, 'Số tiền phải lớn hơn 0 và có tối đa 2 chữ số thập phân.')
            return redirect('/transactions/#transaction-form')
    except (ArithmeticError, TypeError, ValueError):
        messages.error(request, 'Số tiền không hợp lệ.')
        return redirect('/transactions/#transaction-form')

    # Kiểm tra loại
    if raw_type not in ['INCOME', 'EXPENSE']:
        messages.error(request, 'Vui lòng chọn loại giao dịch hợp lệ.')
        return redirect('/transactions/#transaction-form')

    # Kiểm tra danh mục
    category = Category.objects.filter(Q(is_default=True) | Q(user=user), category_id=cat_id).first()
    if not category or category.type != raw_type:
        messages.error(request, 'Danh mục không hợp lệ hoặc không phù hợp với loại giao dịch.')
        return redirect('/transactions/#transaction-form')

    # Kiểm tra ngày
    try:
        t_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        messages.error(request, 'Vui lòng chọn ngày giao dịch hợp lệ.')
        return redirect('/transactions/#transaction-form')

    # Thao tác Cập nhật hoặc Thêm mới
    if trans_id:
        # TC03: Kiểm tra quyền sở hữu (RBAC Security) - Chặn hành vi cố tình đổi ID
        transaction = get_object_or_404(Transaction, transaction_id=trans_id)
        if transaction.user != user and not (user.is_superuser or getattr(user, 'role', '') == 'ADMIN'):
            log_system_action(user, 'SECURITY_VIOLATION', f"Cố tình sửa trái phép giao dịch #{trans_id} của người dùng khác.")
            return HttpResponseForbidden("Không có quyền truy cập hoặc chỉnh sửa giao dịch này (HTTP 403 Forbidden).")

        transaction.amount = amount
        transaction.type = raw_type
        transaction.category = category
        transaction.transaction_date = t_date
        transaction.note = note
        transaction.save()
        messages.success(request, f"Đã cập nhật giao dịch #{trans_id} thành công.")
        log_system_action(user, 'UPDATE_TRANSACTION', f"Cập nhật giao dịch #{trans_id}: {amount:,.0f} đ.")
    else:
        transaction = Transaction.objects.create(
            user=user,
            category=category,
            amount=amount,
            type=raw_type,
            transaction_date=t_date,
            note=note
        )
        messages.success(request, f"Đã thêm giao dịch {category.category_name} (+{amount:,.0f} đ)" if raw_type == 'INCOME' else f"Đã ghi nhận khoản chi {category.category_name} (-{amount:,.0f} đ).")
        log_system_action(user, 'ADD_TRANSACTION', f"Tạo mới giao dịch: {raw_type} {amount:,.0f} đ.")

    # Kích hoạt sự kiện đối soát ngân sách tự động (Quy trình 3 & FR-05)
    if raw_type == 'EXPENSE':
        check_and_trigger_budget_alerts(user, t_date, category)

    return redirect('transactions')


@login_required_custom
def delete_transaction_view(request, pk):
    """Xóa giao dịch thu/chi (TC03: Chỉ chủ sở hữu mới có quyền xóa)."""
    user = request.user
    transaction = get_object_or_404(Transaction, transaction_id=pk)

    # TC03: Kiểm tra quyền sở hữu
    if transaction.user != user and not (user.is_superuser or getattr(user, 'role', '') == 'ADMIN'):
        log_system_action(user, 'SECURITY_VIOLATION', f"Cố tình xóa trái phép giao dịch #{pk}.")
        return HttpResponseForbidden("Không có quyền truy cập hoặc xóa giao dịch này (HTTP 403 Forbidden).")

    if request.method != 'POST':
        return redirect('transactions')

    amount = transaction.amount
    cat_name = transaction.category.category_name
    transaction.delete()

    log_system_action(user, 'DELETE_TRANSACTION', f"Đã xóa giao dịch #{pk} ({cat_name} - {amount:,.0f} đ).")
    messages.success(request, f"Đã xóa giao dịch thành công. Số dư đã được tính toán lại.")
    return redirect('transactions')


# ==============================================================================
# 4. THIẾT LẬP NGÂN SÁCH & CẢNH BÁO (FR-04, FR-05)
# ==============================================================================

@login_required_custom
def budget_view(request):
    """
    Màn hình Thiết lập ngân sách (FR-04):
    - Đặt hạn mức tổng tháng hoặc hạn mức theo từng danh mục.
    - Thanh tiến trình đổi màu (Xanh <80%, Cam 80%-99%, Đỏ >=100%).
    """
    user = request.user
    now = datetime.now()

    selected_month = request.GET.get('month') or now.strftime('%Y-%m')
    try:
        sel_year, sel_month = map(int, selected_month.split('-'))
        if len(selected_month) != 7 or not (1 <= sel_month <= 12) or sel_year < 2000:
            raise ValueError
    except (TypeError, ValueError):
        sel_year, sel_month = now.year, now.month
        selected_month = now.strftime('%Y-%m')

    # 1. Ngân sách tổng tháng
    overall_budget = Budget.objects.filter(
        user=user,
        category__isnull=True,
        month=sel_month,
        year=sel_year
    ).first()

    total_monthly_budget = overall_budget.monthly_limit if overall_budget else Decimal('0.00')

    # Tính tổng chi tiêu thực tế trong tháng
    overall_spent = Transaction.objects.filter(
        user=user,
        type='EXPENSE',
        transaction_date__year=sel_year,
        transaction_date__month=sel_month
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    if total_monthly_budget > 0:
        overall_percent = int(round((overall_spent / total_monthly_budget) * 100))
        overall_remaining = total_monthly_budget - overall_spent
    else:
        overall_percent = 0
        overall_remaining = Decimal('0.00')

    # 2. Ngân sách theo từng danh mục chi tiêu
    cat_budgets_qs = Budget.objects.filter(
        user=user,
        category__isnull=False,
        month=sel_month,
        year=sel_year
    ).select_related('category').order_by('category__category_name')

    category_budgets = []
    category_spending = Transaction.objects.filter(
        user=user,
        type='EXPENSE',
        transaction_date__year=sel_year,
        transaction_date__month=sel_month,
        category__budgets__user=user,
        category__budgets__month=sel_month,
        category__budgets__year=sel_year,
    ).values('category_id').annotate(total=Sum('amount'))
    spending_by_category = {row['category_id']: row['total'] for row in category_spending}

    for b in cat_budgets_qs:
        spent = spending_by_category.get(b.category_id, Decimal('0.00'))
        pct = int(round((spent / b.monthly_limit) * 100)) if b.monthly_limit > 0 else 0
        category_budgets.append({
            'id': b.budget_id,
            'category': {
                'id': b.category.category_id,
                'name': b.category.category_name,
                'icon': b.category.icon,
                'icon_is_emoji': b.category.icon_is_emoji,
                'icon_css_class': b.category.icon_css_class,
            },
            'amount': b.monthly_limit,
            'spent': spent,
            'percentage': pct,
            'remaining': b.monthly_limit - spent,
        })

    # Danh mục chi tiêu có thể đặt hạn mức
    expense_categories = Category.objects.filter(
        Q(is_default=True) | Q(user=user),
        type='EXPENSE'
    ).order_by('category_name')

    exp_cat_list = [{'id': c.category_id, 'name': c.category_name} for c in expense_categories]

    context = {
        'current_month': selected_month,
        'current_month_display': f"{sel_month:02d}/{sel_year}",
        'total_monthly_budget': total_monthly_budget,
        'overall_spent': overall_spent,
        'overall_percent': overall_percent,
        'overall_remaining': overall_remaining,
        'transaction_count': Transaction.objects.filter(
            user=user,
            transaction_date__year=sel_year,
            transaction_date__month=sel_month,
        ).count(),
        'category_budgets': category_budgets,
        'expense_categories': exp_cat_list,
        'current_page_title': 'Ngân sách',
    }
    return render(request, 'tracker_app/budget.html', context)


@login_required_custom
def set_overall_budget_view(request):
    """Lưu hạn mức chi tiêu tổng cho cả tháng (FR-04)."""
    if request.method != 'POST':
        return redirect('budget')

    user = request.user
    raw_month = request.POST.get('month') or ''
    raw_amount = request.POST.get('amount')

    try:
        y, m = map(int, raw_month.split('-'))
        if len(raw_month) != 7 or not (1 <= m <= 12) or y < 2000:
            raise ValueError
        amount = Decimal(str(raw_amount).replace(',', ''))
        if not amount.is_finite() or amount <= 0 or amount > Decimal('9999999999999.99') or amount.as_tuple().exponent < -2:
            messages.error(request, 'Hạn mức phải lớn hơn 0 và có tối đa 2 chữ số thập phân.')
            return redirect(f'/budget/?month={raw_month}')
    except (ArithmeticError, TypeError, ValueError):
        messages.error(request, 'Thông tin ngân sách không hợp lệ.')
        return redirect('budget')

    budget, created = Budget.objects.update_or_create(
        user=user,
        category=None,
        month=m,
        year=y,
        defaults={'monthly_limit': amount}
    )

    log_system_action(user, 'SET_BUDGET', f"Cài đặt hạn mức ngân sách tổng tháng {m}/{y}: {amount:,.0f} đ.")
    messages.success(request, f"Đã lưu hạn mức ngân sách tổng tháng {m}/{y}: {amount:,.0f} đ.")

    # Kích hoạt kiểm tra cảnh báo ngay sau khi cập nhật ngân sách
    check_and_trigger_budget_alerts(user, date(y, m, 1))

    return redirect(f'/budget/?month={raw_month}')


@login_required_custom
def set_category_budget_view(request):
    """Lưu hạn mức chi tiêu cho từng danh mục riêng (FR-04)."""
    if request.method != 'POST':
        return redirect('budget')

    user = request.user
    raw_month = request.POST.get('month') or ''
    cat_id = request.POST.get('category')
    raw_amount = request.POST.get('amount')

    try:
        y, m = map(int, raw_month.split('-'))
        if len(raw_month) != 7 or not (1 <= m <= 12) or y < 2000:
            raise ValueError
        amount = Decimal(str(raw_amount).replace(',', ''))
        if not amount.is_finite() or amount <= 0 or amount > Decimal('9999999999999.99') or amount.as_tuple().exponent < -2:
            messages.error(request, 'Hạn mức phải lớn hơn 0 và có tối đa 2 chữ số thập phân.')
            return redirect(f'/budget/?month={raw_month}')
    except (ArithmeticError, TypeError, ValueError):
        messages.error(request, 'Thông tin không hợp lệ.')
        return redirect('budget')

    category = Category.objects.filter(
        category_id=cat_id,
        type='EXPENSE',
    ).filter(
        Q(is_default=True) | Q(user=user)
    ).first()
    if not category:
        messages.error(request, 'Vui lòng chọn danh mục chi tiêu hợp lệ.')
        return redirect(f'/budget/?month={raw_month}')

    Budget.objects.update_or_create(
        user=user,
        category=category,
        month=m,
        year=y,
        defaults={'monthly_limit': amount}
    )

    log_system_action(user, 'SET_BUDGET', f"Đặt hạn mức danh mục {category.category_name} tháng {m}/{y}: {amount:,.0f} đ.")
    messages.success(request, f"Đã lưu hạn mức cho '{category.category_name}' tháng {m}/{y}: {amount:,.0f} đ.")

    # Kích hoạt kiểm tra cảnh báo danh mục
    check_and_trigger_budget_alerts(user, date(y, m, 1), category)

    return redirect(f'/budget/?month={raw_month}')


@login_required_custom
def delete_category_budget_view(request, pk):
    """Xóa cài đặt ngân sách danh mục."""
    user = request.user
    budget = get_object_or_404(Budget, budget_id=pk, user=user)
    if request.method != 'POST':
        return redirect(f'/budget/?month={budget.year}-{budget.month:02d}')
    cat_name = budget.category.category_name if budget.category else "Tổng thể"
    m, y = budget.month, budget.year
    budget.delete()

    messages.info(request, f"Đã xóa hạn mức ngân sách của {cat_name}.")
    return redirect(f'/budget/?month={y}-{m:02d}')


# ==============================================================================
# 5. QUẢN LÝ DANH MỤC CÁ NHÂN & MẶC ĐỊNH (FR-03)
# ==============================================================================

@login_required_custom
def categories_view(request):
    """Màn hình Danh mục (FR-03): Danh mục tùy chỉnh cá nhân và danh mục mặc định hệ thống."""
    user = request.user

    custom_cats = Category.objects.filter(is_default=False, user=user).order_by('category_name')
    system_cats = Category.objects.filter(is_default=True).order_by('type', 'category_name')

    custom_categories = [{
        'id': c.category_id,
        'name': c.category_name,
        'type': c.type.lower(),
        'icon': c.icon,
        'icon_is_emoji': c.icon_is_emoji,
        'icon_css_class': c.icon_css_class,
        'description': 'Danh mục cá nhân của bạn'
    } for c in custom_cats]

    system_categories = [{
        'id': c.category_id,
        'name': c.category_name,
        'type': c.type.lower(),
        'icon': c.icon,
        'icon_is_emoji': c.icon_is_emoji,
        'icon_css_class': c.icon_css_class,
        'description': 'Danh mục chuẩn hệ thống'
    } for c in system_cats]

    # Common Font Awesome 6 icons for quick pick (same as admin)
    common_icons = [
        'fa-utensils', 'fa-house', 'fa-graduation-cap', 'fa-gamepad', 'fa-bus',
        'fa-shirt', 'fa-money-bill-wave', 'fa-hand-holding-dollar', 'fa-award', 'fa-briefcase',
        'fa-notes-medical', 'fa-receipt', 'fa-wallet', 'fa-trophy', 'fa-cart-shopping',
        'fa-plane', 'fa-car', 'fa-heart-pulse', 'fa-film', 'fa-coffee', 'fa-phone',
        'fa-wifi', 'fa-piggy-bank', 'fa-tags', 'fa-folder', 'fa-box', 'fa-sack-dollar',
        'fa-gift', 'fa-seedling', 'fa-book', 'fa-headphones', 'fa-music', 'fa-dumbbell',
        'fa-bicycle', 'fa-train', 'fa-gas-pump', 'fa-shopping-bag', 'fa-laptop', 'fa-mobile',
        'fa-camera', 'fa-video', 'fa-ticket', 'fa-medal', 'fa-certificate', 'fa-landmark'
    ]

    context = {
        'custom_categories': custom_categories,
        'system_categories': system_categories,
        'current_page_title': 'Danh mục',
        'common_icons': common_icons,
    }
    return render(request, 'tracker_app/categories.html', context)


@login_required_custom
def save_category_view(request):
    """Tạo mới hoặc Sửa danh mục tùy chỉnh cá nhân (FR-03)."""
    if request.method != 'POST':
        return redirect('categories')

    user = request.user
    cat_id = request.POST.get('category_id')
    name = request.POST.get('name', '').strip()
    raw_type = request.POST.get('type', 'expense').strip().upper()
    icon = request.POST.get('icon', 'fa-folder').strip()

    if not name:
        messages.error(request, 'Tên danh mục không được để trống.')
        return redirect('categories')

    if raw_type not in ['INCOME', 'EXPENSE']:
        raw_type = 'EXPENSE'

    if cat_id:
        category = get_object_or_404(Category, category_id=cat_id, user=user, is_default=False)
        category.category_name = name
        category.type = raw_type
        category.icon = icon
        category.save()
        messages.success(request, f"Đã cập nhật danh mục cá nhân '{name}'.")
    else:
        Category.objects.create(
            user=user,
            category_name=name,
            type=raw_type,
            icon=icon,
            is_default=False
        )
        messages.success(request, f"Đã thêm danh mục cá nhân mới '{name}'.")

    return redirect('categories')


@login_required_custom
def delete_category_view(request, pk):
    """Xóa danh mục tùy chỉnh cá nhân."""
    if request.method != 'POST':
        return redirect('categories')

    user = request.user
    category = get_object_or_404(Category, category_id=pk, user=user, is_default=False)
    name = category.category_name
    try:
        category.delete()
    except (ProtectedError, RestrictedError):
        messages.error(request, f"Không thể xóa danh mục '{name}' vì danh mục này đang được giao dịch sử dụng.")
        return redirect('categories')
    messages.success(request, f"Đã xóa danh mục cá nhân '{name}'.")
    return redirect('categories')


# ==============================================================================
# 6. THÔNG BÁO HỆ THỐNG & CẢNH BÁO (FR-05)
# ==============================================================================

@login_required_custom
def notifications_view(request):
    """Màn hình Thông báo & Cảnh báo (FR-05)."""
    user = request.user
    notifs = Notification.objects.filter(user=user).order_by('-created_at')
    unread_count = notifs.filter(is_read=False).count()

    # Thông báo cảnh báo ngân sách đang hoạt động (để hiển thị banner)
    from datetime import datetime
    now = datetime.now()
    active_budget_alert = Notification.objects.filter(
        user=user,
        created_at__year=now.year,
        created_at__month=now.month,
        is_read=False
    ).order_by('-created_at').first()

    context = {
        'notifications': notifs,
        'unread_count': unread_count,
        'active_budget_alert': active_budget_alert,
        'current_page_title': 'Thông báo',
    }
    return render(request, 'tracker_app/notifications.html', context)


@login_required_custom
def mark_notification_read_view(request, pk):
    """Đánh dấu một thông báo là đã đọc."""
    user = request.user
    notif = get_object_or_404(Notification, notification_id=pk, user=user)
    notif.is_read = True
    notif.save()
    return redirect('notifications')


@login_required_custom
def mark_all_notifications_read_view(request):
    """Đánh dấu tất cả thông báo là đã đọc."""
    if request.method == 'POST':
        user = request.user
        Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        messages.success(request, 'Đã đánh dấu đã đọc toàn bộ thông báo.')
    return redirect('notifications')


# ==============================================================================
# 8. THÔNG TIN CÁ NHÂN (PROFILE)
# ==============================================================================

@login_required_custom
def profile_view(request):
    """Trang thông tin cá nhân tài khoản."""
    user = request.user
    
    # Thống kê nhanh
    total_transactions = Transaction.objects.filter(user=user).count()
    total_income = Transaction.objects.filter(user=user, type='INCOME').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    total_expense = Transaction.objects.filter(user=user, type='EXPENSE').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    total_budgets = Budget.objects.filter(user=user).count()
    custom_categories_count = Category.objects.filter(user=user, is_default=False).count()
    
    context = {
        'user': user,
        'total_transactions': total_transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'total_budgets': total_budgets,
        'custom_categories_count': custom_categories_count,
        'current_page_title': 'Thông tin cá nhân',
    }
    return render(request, 'tracker_app/profile.html', context)


@login_required_custom
def update_profile_view(request):
    """Cập nhật thông tin cá nhân (họ tên, email)."""
    if request.method != 'POST':
        return redirect('profile')
    
    user = request.user
    full_name = request.POST.get('full_name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    
    if not full_name or not email:
        messages.error(request, 'Vui lòng điền đầy đủ thông tin.')
        return redirect('profile')
    
    # Kiểm tra email trùng (ngoại trừ email hiện tại)
    if User.objects.filter(email=email).exclude(user_id=user.user_id).exists():
        messages.error(request, 'Email này đã được sử dụng bởi tài khoản khác.')
        return redirect('profile')
    
    # Kiểm tra định dạng email
    import re
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, email):
        messages.error(request, 'Định dạng email không hợp lệ.')
        return redirect('profile')
    
    user.full_name = full_name
    user.email = email
    user.save()
    
    log_system_action(user, 'UPDATE_PROFILE', f"Cập nhật thông tin cá nhân: {full_name} ({email})")
    messages.success(request, 'Đã cập nhật thông tin cá nhân thành công.')
    return redirect('profile')


@login_required_custom
def change_password_view(request):
    """Đổi mật khẩu."""
    if request.method != 'POST':
        return redirect('profile')
    
    user = request.user
    current_password = request.POST.get('current_password', '')
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')
    
    if not current_password or not new_password or not confirm_password:
        messages.error(request, 'Vui lòng điền đầy đủ các trường.')
        return redirect('profile')
    
    if not user.check_password(current_password):
        messages.error(request, 'Mật khẩu hiện tại không chính xác.')
        return redirect('profile')
    
    if new_password != confirm_password:
        messages.error(request, 'Mật khẩu mới và xác nhận không khớp.')
        return redirect('profile')
    
    if len(new_password) < 8 or not re.search(r'\d', new_password) or not re.search(r'[a-zA-Z]', new_password):
        messages.error(request, 'Mật khẩu mới phải có tối thiểu 8 ký tự, bao gồm cả chữ và số.')
        return redirect('profile')
    
    user.set_password(new_password)
    user.save()
    
    log_system_action(user, 'CHANGE_PASSWORD', "Đổi mật khẩu tài khoản.")
    messages.success(request, 'Đã đổi mật khẩu thành công. Vui lòng đăng nhập lại.')
    return redirect('logout')


# ==============================================================================
# 7. PHÂN HỆ QUẢN TRỊ VIÊN (ADMIN - RBAC)
# ==============================================================================

@admin_required_custom
def admin_users_view(request):
    """Admin: Quản lý người dùng, khóa / mở khóa tài khoản (RBAC)."""
    users_qs = User.objects.all().order_by('-created_at')
    return render(request, 'tracker_app/admin_users.html', {'users': users_qs, 'current_page_title': 'Người dùng'})


@admin_required_custom
def toggle_user_status_view(request, pk):
    """Admin: Khóa hoặc Mở khóa tài khoản sinh viên (RBAC)."""
    if request.method == 'POST':
        user_to_toggle = get_object_or_404(User, user_id=pk)
        admin_user = request.user

        if user_to_toggle.user_id == admin_user.user_id:
            messages.error(request, 'Bạn không thể tự khóa tài khoản của chính mình.')
            return redirect('admin_users')

        if user_to_toggle.status == 'ACTIVE':
            user_to_toggle.status = 'LOCKED'
            user_to_toggle.save()
            log_system_action(admin_user, 'LOCK_USER', f"Admin {admin_user.email} đã khóa tài khoản của {user_to_toggle.email}.")
            messages.warning(request, f"Đã KHÓA tài khoản của {user_to_toggle.full_name} ({user_to_toggle.email}).")
        else:
            user_to_toggle.status = 'ACTIVE'
            user_to_toggle.save()
            log_system_action(admin_user, 'UNLOCK_USER', f"Admin {admin_user.email} đã mở khóa cho {user_to_toggle.email}.")
            messages.success(request, f"Đã MỞ KHÓA tài khoản cho {user_to_toggle.full_name} ({user_to_toggle.email}).")

    return redirect('admin_users')


@admin_required_custom
def admin_categories_view(request):
    """Admin: Quản lý danh mục mặc định của hệ thống."""
    sys_cats = Category.objects.filter(is_default=True).order_by('type', 'category_name')
    cats_data = [{
        'id': c.category_id,
        'name': c.category_name,
        'type': c.type.lower(),
        'icon': c.icon,
        'icon_is_emoji': c.icon_is_emoji,
        'icon_css_class': c.icon_css_class,
        'description': c.description,
    } for c in sys_cats]
    
    # Common Font Awesome 6 icons for quick pick
    common_icons = [
        'fa-utensils', 'fa-house', 'fa-graduation-cap', 'fa-gamepad', 'fa-bus',
        'fa-shirt', 'fa-money-bill-wave', 'fa-hand-holding-dollar', 'fa-award', 'fa-briefcase',
        'fa-notes-medical', 'fa-receipt', 'fa-wallet', 'fa-trophy', 'fa-cart-shopping',
        'fa-plane', 'fa-car', 'fa-heart-pulse', 'fa-film', 'fa-coffee', 'fa-phone',
        'fa-wifi', 'fa-piggy-bank', 'fa-tags', 'fa-folder', 'fa-box', 'fa-sack-dollar',
        'fa-gift', 'fa-seedling', 'fa-book', 'fa-headphones', 'fa-music', 'fa-dumbbell',
        'fa-bicycle', 'fa-train', 'fa-gas-pump', 'fa-shopping-bag', 'fa-laptop', 'fa-mobile',
        'fa-camera', 'fa-video', 'fa-ticket', 'fa-medal', 'fa-certificate', 'fa-landmark'
    ]
    
    return render(request, 'tracker_app/admin_categories.html', {
        'system_categories': cats_data, 
        'current_page_title': 'Danh mục hệ thống',
        'common_icons': common_icons
    })


@admin_required_custom
def admin_save_category_view(request):
    """Admin: Thêm mới hoặc chỉnh sửa danh mục mặc định hệ thống."""
    if request.method == 'POST':
        cat_id = request.POST.get('category_id')
        name = request.POST.get('name', '').strip()
        raw_type = request.POST.get('type', 'expense').strip().upper()
        icon = request.POST.get('icon', 'fa-folder').strip()

        if not name:
            messages.error(request, 'Tên danh mục không được để trống.')
            return redirect('admin_categories')

        if raw_type not in ['INCOME', 'EXPENSE']:
            raw_type = 'EXPENSE'

        if cat_id:
            cat = get_object_or_404(Category, category_id=cat_id, is_default=True)
            cat.category_name = name
            cat.type = raw_type
            cat.icon = icon
            cat.save()
            log_system_action(request.user, 'SYSTEM', f"Admin cập nhật danh mục hệ thống: {name}.")
            messages.success(request, f"Đã cập nhật danh mục hệ thống '{name}'.")
        else:
            Category.objects.create(
                category_name=name,
                type=raw_type,
                icon=icon,
                is_default=True,
                user=None
            )
            log_system_action(request.user, 'SYSTEM', f"Admin tạo mới danh mục hệ thống: {name}.")
            messages.success(request, f"Đã tạo danh mục hệ thống mới '{name}'.")

    return redirect('admin_categories')


@admin_required_custom
def admin_delete_category_view(request, pk):
    """Admin: Xóa danh mục hệ thống."""
    cat = get_object_or_404(Category, category_id=pk, is_default=True)
    name = cat.category_name
    cat.delete()
    log_system_action(request.user, 'SYSTEM', f"Admin xóa danh mục hệ thống: {name}.")
    messages.success(request, f"Đã xóa danh mục hệ thống '{name}'.")
    return redirect('admin_categories')


@admin_required_custom
def admin_logs_view(request):
    """Admin: Xem nhật ký hoạt động hệ thống (System Logs Viewer)."""
    selected_action = request.GET.get('action_type', '').strip()
    search_user = request.GET.get('search_user', '').strip()

    logs_qs = SystemLog.objects.all().select_related('user').order_by('-created_at')

    if selected_action:
        logs_qs = logs_qs.filter(action__icontains=selected_action)

    if search_user:
        logs_qs = logs_qs.filter(
            Q(user__email__icontains=search_user) |
            Q(user__full_name__icontains=search_user)
        )

    paginator = Paginator(logs_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'selected_action': selected_action,
        'search_user': search_user,
        'current_page_title': 'Nhật ký hệ thống',
    }
    return render(request, 'tracker_app/admin_logs.html', context)
