import pathlib
root = pathlib.Path('d:/QuanLyThuChi')
b = root / 'expense_tracker/tracker_app/templates/tracker_app/base.html'
s = b.read_text(encoding='utf-8')
print('nav open:', s.count('<nav'), '| nav close:', s.count('</nav>'))
print('con Secondary:', 'Secondary' in s)
print('con admin_users lan:', s.count("url 'admin_users'"))
for name in ['ptit-base.css', 'ptit-pages.css']:
    hits = [str(p) for p in root.rglob('*') if p.is_file() and p.suffix in ('.html', '.py')
            and name in p.read_text(encoding='utf-8', errors='ignore')]
    print(name, '->', hits or 'KHONG AI THAM CHIEU')
junk = sorted(root.glob('tmp_*.py')) + sorted(root.glob('z_*.py')) + [root / '_cleanup_once.py']
junk += [root / 'expense_tracker/tracker_app/templates/tracker_app/z_part1.html',
         root / 'expense_tracker/static/css/ptit-base.css',
         root / 'expense_tracker/static/css/ptit-pages.css']
for p in junk:
    print(('DEL ' if p.exists() else 'SKIP ') + str(p.relative_to(root)))
    if p.exists():
        p.unlink()
print('DONE-CLEAN')
