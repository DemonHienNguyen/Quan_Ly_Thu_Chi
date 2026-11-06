import datetime
from functools import wraps
import jwt
import bcrypt
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponseForbidden, JsonResponse
from .models import User, AnonymousUser


def hash_password(password: str) -> str:
    """Băm mật khẩu bằng thuật toán bcrypt an toàn."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Xác thực mật khẩu đã băm."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def generate_jwt_token(user: User, days: int = 30) -> str:
    """Tạo chuỗi xác thực JWT có thời hạn 30 ngày theo đặc tả đề tài."""
    payload = {
        'user_id': user.user_id,
        'email': user.email,
        'role': user.role,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days),
        'iat': datetime.datetime.now(datetime.timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def decode_jwt_token(token: str) -> dict:
    """Giải mã và xác minh tính toàn vẹn của chuỗi JWT."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def login_required_custom(view_func):
    """Decorator yêu cầu đăng nhập đối với sinh viên và admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return JsonResponse({'error': 'Vui lòng đăng nhập để tiếp tục.'}, status=401)
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required_custom(view_func):
    """Decorator kiểm tra phân quyền RBAC: Chỉ cho phép Quản trị viên (ADMIN)."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'ADMIN' and not request.user.is_superuser:
            return HttpResponseForbidden("Bạn không có quyền truy cập trang quản trị này (RBAC: Admin Only).")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
