from .server import ROOT, create_app

app = create_app(ROOT / "docs")
