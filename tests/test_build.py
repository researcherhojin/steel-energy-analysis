import importlib.util
import json

from steelenergy import config, export


def _build_module():
    spec = importlib.util.spec_from_file_location("build", config.ROOT / "web" / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_templates_render_with_strict_undefined(payload, tmp_path):
    data = export.write(payload, tmp_path / "analysis.json")
    for page in _build_module().render(data, tmp_path / "build"):
        html = page.read_text(encoding="utf-8")
        assert html.startswith("<title>")
        embedded = html.split('<script id="data" type="application/json">')[1].split("</script>")[0]
        assert json.loads(embedded)["schema_version"] == export.SCHEMA_VERSION


def test_notebook_prose_builds_from_payload(payload, tmp_path):
    spec = importlib.util.spec_from_file_location("nb", config.ROOT / "notebooks" / "build_notebook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    nb = module.build(export.write(payload, tmp_path / "analysis.json"))
    prose = "".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown")
    assert f"{payload['kpi']['weekday_daytime']['kwh_share'] * 100:.0f}%" in prose


def test_korean_particles_follow_the_number():
    spec = importlib.util.spec_from_file_location("nb", config.ROOT / "notebooks" / "build_notebook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fix = module.fix_josa
    assert fix("역률이 0.73다.") == "역률이 0.73이다."
    assert fix("0.863로 가장") == "0.863으로 가장"
    assert fix("0.99이 나왔다") == "0.99가 나왔다"
    assert fix("0.97로 거의") == "0.97로 거의"
    assert fix("10%를 옮기면") == "10%를 옮기면"


def test_pages_wrap_fragments_as_full_documents(payload, tmp_path):
    data = export.write(payload, tmp_path / "analysis.json")
    _build_module().render(data, tmp_path / "build")
    spec = importlib.util.spec_from_file_location("pages", config.ROOT / "web" / "pages.py")
    pages = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pages)
    for page in pages.write(tmp_path / "build", data, tmp_path / "site"):
        html = page.read_text(encoding="utf-8")
        assert html.startswith("<!doctype html>") and '<meta charset="utf-8">' in html
        assert html.rstrip().endswith("</html>")
