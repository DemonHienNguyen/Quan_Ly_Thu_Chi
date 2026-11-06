#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import socket
import sys
import threading
from pathlib import Path


def run_desktop():
    """Launch Django in a local WebView window instead of a browser tab."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')

    if getattr(sys, 'frozen', False):
        data_dir = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        os.environ['EXPENSE_TRACKER_DATA_DIR'] = str(data_dir / 'PTITExpenseTracker')

    from django.core.management import call_command
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    from django.core.wsgi import get_wsgi_application
    import django
    import webview
    from wsgiref.simple_server import make_server

    django.setup()
    call_command('migrate', interactive=False, verbosity=0)
    call_command('seed_data', defaults_only=True, verbosity=0)

    server = make_server('127.0.0.1', 0, StaticFilesHandler(get_wsgi_application()))
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        webview.create_window(
            'Quản lý chi tiêu sinh viên PTIT',
            f'http://127.0.0.1:{server.server_port}/',
            width=1200,
            height=820,
            min_size=(860, 600),
        )
        webview.start()
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    if '--desktop' in sys.argv or getattr(sys, 'frozen', False):
        if '--desktop' in sys.argv:
            sys.argv.remove('--desktop')
        try:
            run_desktop()
        except Exception as exc:
            if not getattr(sys, 'frozen', False):
                raise
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                f'Không thể khởi động ứng dụng PTIT.\n\n{exc}',
                'Lỗi khởi động',
                0x10,
            )
            raise
    else:
        main()
