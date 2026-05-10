import zipfile, os, datetime as dt
from pathlib import Path

stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
out = Path("backups") / f"preEODHD_{stamp}.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for base in ("backend", "frontend"):
        for p in Path(base).rglob("*"):
            sp = p.as_posix()
            if p.is_file() and "__pycache__" not in sp and not sp.startswith("backend/_cache"):
                z.write(p, p)
print("backup:", out, out.stat().st_size, "bytes")
