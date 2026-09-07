from pathlib import Path

path = Path("tests/test_rq1c_preread_diagnostic.py")
text = path.read_text(encoding="utf-8")
old = 'https://secret.example/unknown-negative'
new = 'https://secret.example/other-negative'
if text.count(old) != 1:
    raise SystemExit(f"expected one reader stub test URL, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
