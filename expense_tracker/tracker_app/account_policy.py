"""Approved demo accounts for this single-workspace application."""

APPROVED_ACCOUNTS = (
    {
        'email': 'admin_system@ptit.edu.vn',
        'full_name': 'Quản Trị Viên Hệ Thống',
        'password': 'Admin@Ptit2026',
        'role': 'ADMIN',
    },
    {
        'email': 'sinhvien_test@ptit.edu.vn',
        'full_name': 'Nguyễn Văn Sinh Viên',
        'password': 'Student@2026',
        'role': 'STUDENT',
    },
    {
        'email': 'sinhvien2_test@ptit.edu.vn',
        'full_name': 'Trần Thị Sinh Viên',
        'password': 'Student2@2026',
        'role': 'STUDENT',
    },
)

APPROVED_LOGIN_EMAILS = frozenset(account['email'] for account in APPROVED_ACCOUNTS)


def approved_email_for_login(identifier):
    normalized_identifier = identifier.strip().lower()
    for email in APPROVED_LOGIN_EMAILS:
        if normalized_identifier == email or normalized_identifier == email.split('@', 1)[0]:
            return email
    return None


def is_approved_login_email(email):
    return bool(email) and email.strip().lower() in APPROVED_LOGIN_EMAILS
