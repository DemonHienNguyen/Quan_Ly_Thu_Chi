from .models import User, AnonymousUser
from .auth_utils import decode_jwt_token
from .account_policy import is_approved_login_email


class JWTAuthenticationMiddleware:
    """
    Middleware trích xuất và xác thực JWT token từ:
    1. Header HTTP: Authorization: Bearer <token>
    2. Cookie bảo mật: jwt_token
    3. Django Session: jwt_token
    Đảm bảo tính độc lập dữ liệu cá nhân (RBAC) và bảo mật theo yêu cầu đồ án.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = None

        # 1. Kiểm tra header Authorization
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1].strip()

        # 2. Kiểm tra Cookie
        if not token:
            token = request.COOKIES.get('jwt_token')

        # 3. Kiểm tra Session
        if not token:
            token = request.session.get('jwt_token')

        # Xác thực Token
        user = None
        if token:
            payload = decode_jwt_token(token)
            if payload and 'user_id' in payload:
                try:
                    db_user = User.objects.get(user_id=payload['user_id'])
                    if db_user.status == 'ACTIVE' and is_approved_login_email(db_user.email):
                        user = db_user
                except User.DoesNotExist:
                    user = None

        request.user = user if user else AnonymousUser()

        response = self.get_response(request)
        return response
