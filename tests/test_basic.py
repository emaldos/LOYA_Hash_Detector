from contextlib import redirect_stdout
from io import StringIO
from json import loads
from pathlib import Path
from sys import path
from tempfile import TemporaryDirectory
path.insert(0,str(Path(__file__).resolve().parents[1]))
from hashdetector.core import detect
from hashdetector import LOGO,TITLE,VERSION
from hashdetector.cli import clean_path,direct_path,file_mode,log_event,menu,result,render_json,render_text,setup_logs
BCRYPT="$2b$12$abcdefghijklmnopqrstuuJr8oP9pL4gY3Yz7Q3QjzVvP6S7vO9fy"
MD5="ae11fd697ec92c7c98de3fac23aba525"
DJANGO="pbkdf2_sha256$20000$H0dPx8NeajVu$GiC4k5kqbbR9qWBlsRgDywNqC2vd9kqfk7zdorEnNas="
def names(h):
    return [hit["name"] for hit in detect(h)]
def capture(fn,*args):
    out=StringIO()
    with redirect_stdout(out):
        fn(*args)
    return out.getvalue()
def test_md5():
    assert "MD5" in names(MD5)
def test_version_metadata():
    assert VERSION == "1.0.0"
    assert TITLE == "LOYA Hash Detector 1.0.0"
    assert "HASH DETECTOR v1.0.0" in LOGO
def test_scores_sort_high_first():
    assert detect(BCRYPT)[0]["score"] == 99
def test_reasons_present():
    assert "regex=fullmatch" in detect(MD5)[0]["reasons"]
def test_mode_fields_present():
    hit=detect(BCRYPT)[0]
    assert hit["hashcat"] == "3200"
    assert hit["john"] == "bcrypt"
def test_top_limits_results():
    assert len(detect(MD5,top=5)) == 5
def test_wordpress():
    assert "MD5(Wordpress)" in names("$P$BiTOhOj3ukMgCci2juN0HRbCdDRqeh.")
def test_non_hex_rejected():
    assert detect("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz") == []
def test_bcrypt():
    assert "bcrypt" in names(BCRYPT)
def test_django_pbkdf2():
    assert "Django PBKDF2-SHA256" in names(DJANGO)
def test_argon2id():
    assert "Argon2id" in names("$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$YWJjZGVmZ2hpamtsbW5vcA")
def test_yescrypt():
    assert "yescrypt" in names("$y$j9T$abcdefghijklmnop$ABCDEFGHIJKLMNOPQRSTUV")
def test_pbkdf2_hmac_sha256():
    assert "PBKDF2-HMAC-SHA256" in names("sha256:1000:c2FsdA==:YWJjZGVm")
def test_laravel_bcrypt():
    assert "Laravel bcrypt" in names(BCRYPT)
def test_cisco_type_5():
    assert "Cisco-IOS type 5" in names("$1$abc12345$abcdefghijklmnopqrstuv")
def test_file_mode():
    with TemporaryDirectory() as d:
        p=Path(d)/"hashes.txt"
        p.write_text(f"{MD5}\n\nnot-a-known-format\n",encoding="utf-8")
        out=capture(file_mode,str(p))
    assert out.startswith(" _      ___")
    assert f"line 1: {MD5}" in out
    assert "line 3: not-a-known-format" in out
def test_direct_absolute_file_path():
    with TemporaryDirectory() as d:
        p=Path(d)/"hashes.txt"
        p.write_text(MD5,encoding="utf-8")
        assert direct_path(str(p)) == str(p)
        assert direct_path(f'"{p}"') == str(p)
    assert direct_path(MD5) is None
def test_interactive_menu_text():
    assert menu() == "1) HASH\n2) File Directory\n3) Exit"
    assert clean_path('"C:\\hashes.txt"') == "C:\\hashes.txt"
def test_result_json_shape():
    data=result(MD5)
    assert data["found"] is True
    assert {"id","name","score","hashcat","john","reasons"} <= set(data["matches"][0])
def test_result_top_and_strict():
    data=result(MD5,strict=True,top=1)
    assert len(data["matches"]) == 1
    assert data["matches"][0]["score"] >= 70
def test_file_mode_json():
    with TemporaryDirectory() as d:
        p=Path(d)/"hashes.txt"
        p.write_text(f"{MD5}\n\nnot-a-known-format\n",encoding="utf-8")
        data=loads(capture(file_mode,str(p),True))
    assert data[0]["line"] == 1
    assert data[1]["line"] == 3
def test_log_file():
    with TemporaryDirectory() as d:
        log=Path(d)/"loya.log"
        hashes=Path(d)/"hashes.txt"
        hashes.write_text(f"{MD5}\n",encoding="utf-8")
        setup_logs(str(log),False)
        capture(file_mode,str(hashes))
        log_event("unit_test",ok=True)
        setup_logs(None,False)
        rows=[loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert any(row["event"] == "file_mode" for row in rows)
    assert any(row["event"] == "unit_test" and row["ok"] is True for row in rows)
def test_render_helpers():
    data=result("not-a-known-format")
    assert loads(render_json(data))["found"] is False
    assert "Not Found" in render_text(data["input"],data["matches"])
def test_not_found():
    assert detect("not-a-known-format") == []
def run():
    tests=[v for k,v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")
if __name__=="__main__":
    run()
