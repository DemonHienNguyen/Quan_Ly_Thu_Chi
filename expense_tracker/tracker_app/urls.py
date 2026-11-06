from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Tổng quan
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard_alt'),

    # Xác thực người dùng
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Quản lý giao dịch thu/chi
    path('transactions/', views.transactions_view, name='transactions'),
    path('transactions/save/', views.save_transaction_view, name='save_transaction'),
    path('transactions/delete/<int:pk>/', views.delete_transaction_view, name='delete_transaction'),

    # Thiết lập ngân sách
    path('budget/', views.budget_view, name='budget'),
    path('budget/set-overall/', views.set_overall_budget_view, name='set_overall_budget'),
    path('budget/set-category/', views.set_category_budget_view, name='set_category_budget'),
    path('budget/delete/<int:pk>/', views.delete_category_budget_view, name='delete_category_budget'),

    # Quản lý danh mục cá nhân
    path('categories/', views.categories_view, name='categories'),
    path('categories/save/', views.save_category_view, name='save_category'),
    path('categories/delete/<int:pk>/', views.delete_category_view, name='delete_category'),

    # Thông báo & Cảnh báo thông minh
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/read/<int:pk>/', views.mark_notification_read_view, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read_view, name='mark_all_notifications_read'),

    # Thông tin cá nhân
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),

    # Phân hệ Quản trị viên (Admin Portal - RBAC)
    path('admin-portal/users/', views.admin_users_view, name='admin_users'),
    path('admin-portal/users/<int:pk>/toggle/', views.toggle_user_status_view, name='toggle_user_status'),
    path('admin-portal/categories/', views.admin_categories_view, name='admin_categories'),
    path('admin-portal/categories/save/', views.admin_save_category_view, name='admin_save_category'),
    path('admin-portal/categories/delete/<int:pk>/', views.admin_delete_category_view, name='admin_delete_category'),
    path('admin-portal/logs/', views.admin_logs_view, name='admin_logs'),
]
