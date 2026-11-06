from django.contrib import admin
from .models import User, Category, Transaction, Budget, Notification, SystemLog


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'full_name', 'email', 'role', 'status', 'created_at')
    list_filter = ('role', 'status', 'created_at')
    search_fields = ('full_name', 'email')
    ordering = ('-created_at',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'category_name', 'type', 'icon', 'is_default', 'user')
    list_filter = ('type', 'is_default')
    search_fields = ('category_name',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'category', 'amount', 'type', 'transaction_date', 'created_at')
    list_filter = ('type', 'transaction_date', 'category')
    search_fields = ('user__full_name', 'user__email', 'category__category_name', 'note')
    ordering = ('-transaction_date', '-created_at')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('budget_id', 'user', 'category', 'monthly_limit', 'month', 'year')
    list_filter = ('month', 'year')
    search_fields = ('user__full_name', 'user__email')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('notification_id', 'user', 'threshold_type', 'is_read', 'created_at')
    list_filter = ('threshold_type', 'is_read')
    search_fields = ('user__full_name', 'message')


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('log_id', 'user', 'action', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__email', 'action', 'details')
    ordering = ('-created_at',)
