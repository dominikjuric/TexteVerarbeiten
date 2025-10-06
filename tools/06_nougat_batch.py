#!/usr/bin/env python3
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from typing import Tuple

RAW_DIRS = [Path("raw/Paper"), Path("raw/Bücher")]
OUT_DIR = Path("processed/nougat_md")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def run_nougat(pdf: Path) -> Tuple[str, bool, str]:
    # Nougat schreibt je nach Version .mmd (Math-Markdown) oder .md
    out_mmd = OUT_DIR / (pdf.stem + ".mmd")
    out_md = OUT_DIR / (pdf.stem + ".md")
    if out_mmd.exists() or out_md.exists():
        return (pdf.name, True, "skip (exists)")

    # Bevorzuge MPS (Apple GPU) – Fallback auf CPU erlauben
    env = {
        **os.environ,
        "PYTORCH_ENABLE_MPS_FALLBACK": "1",
        # Hinweis: TORCH_DEVICE ist keine offizielle Torch-Env-Var,
        # Nougat wählt den Device intern. Dieser Eintrag schadet aber nicht.
        "TORCH_DEVICE": "mps",
        # optional: weniger Tokenizer-Warnungen
        "TOKENIZERS_PARALLELISM": "false",
    }
    cmd = ["nougat", str(pdf), "--out", str(OUT_DIR)]
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, check=True, env=env, timeout=900
        )
        msg = (res.stderr or res.stdout or "ok").strip()
        return (pdf.name, True, msg)
    except subprocess.TimeoutExpired as e:
        return (pdf.name, False, f"timeout after {e.timeout}s")
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or str(e))[-500:]
        return (pdf.name, False, msg)
    except Exception as e:
        return (pdf.name, False, str(e))

def main():
    pdfs = []
    for d in RAW_DIRS:
        if d.exists():
            pdfs.extend(sorted(d.glob("*.pdf")))
    print(f"Nougat Batch: {len(pdfs)} PDFs")

    ok = 0
    fail = 0
    errors = []

    # M1: 1–2 Threads sind sinnvoll; nougat CLI startet intern eigene Prozesse
    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {ex.submit(run_nougat, p): p for p in pdfs}
        for fut in as_completed(futures):
            name, success, msg = fut.result()
            if success:
                ok += 1
                print(f"[OK ] {name}")
            else:
                fail += 1
                last_line = (msg.splitlines()[-1] if msg else "").strip()
                print(f"[ERR] {name} :: {last_line}")
                errors.append((name, msg))

    print(f"Fertig: {ok} OK, {fail} Fehler. Output: {OUT_DIR}")
    if errors:
        (OUT_DIR / "_errors.log").write_text(
            "\n\n".join([f"{n}\n{m}" for n, m in errors]), encoding="utf-8"
        )
        print(f"Details: {OUT_DIR / '_errors.log'}")

if __name__ == "__main__":
    main()