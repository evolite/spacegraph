import io
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = sorted(p for d in ("src", "tests", "docs") for p in (ROOT / d).rglob("*.py"))


def test_no_comments():
    found = []
    for path in SOURCES:
        for tok in tokenize.generate_tokens(io.StringIO(path.read_text()).readline):
            if tok.type == tokenize.COMMENT:
                found.append(f"{path.relative_to(ROOT)}:{tok.start[0]}: {tok.string}")
    assert not found, "comments are not allowed:\n" + "\n".join(found)
