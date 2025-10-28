import json
import subprocess
import sys
from pathlib import Path

def test_cli_outputs_valid_json(tmp_path):
    # Geçici ikili giriş dosyası oluştur
    input_file = tmp_path / "input.bin"
    input_file.write_bytes(b'\x00\xff\x01\x02\x03\x04' * 10)
    output_file = tmp_path / "report.json"

    # CLI'yı modül olarak çalıştır
    completed = subprocess.run(
        [sys.executable, "-m", "patternanalyzer.cli", "analyze", str(input_file), "-o", str(output_file)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Çıktı dosyasının oluşturulduğunu doğrula
    assert output_file.exists(), f"Expected output file {output_file} to exist; stdout: {completed.stdout.decode()}; stderr: {completed.stderr.decode()}"

    # JSON'u yükle ve şema için temel anahtarları kontrol et
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "results" in data and "scorecard" in data
    assert isinstance(data["results"], list)
    assert isinstance(data["scorecard"], dict)

    # Ek temel kontroller
    assert "total_tests" in data["scorecard"] or "failed_tests" in data["scorecard"]
    if data["results"]:
        assert isinstance(data["results"][0], dict)

def test_cli_accepts_default_visuals_and_artefact_dir(tmp_path):
    input_file = tmp_path / "input2.bin"
    input_file.write_bytes(b'\x00\x01\x02' * 10)
    output_file = tmp_path / "report2.json"
    artefacts = tmp_path / "artefacts"
    default_visuals = '{"fft_placeholder": {"mime": "image/svg+xml"}}'

    completed = subprocess.run(
        [sys.executable, "-m", "patternanalyzer.cli", "analyze", str(input_file), "-o", str(output_file),
         "--default-visuals", default_visuals, "--artefact-dir", str(artefacts)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert output_file.exists(), f"Expected output file {output_file} to exist; stdout: {completed.stdout.decode()}; stderr: {completed.stderr.decode()}"
    assert artefacts.exists() and artefacts.is_dir(), f"Expected artefact dir {artefacts} to be created"

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # If visuals present in results, ensure each visual entry has either inline data or a file path
    for r in data.get("results", []):
        if isinstance(r, dict) and "visuals" in r:
            for v in r["visuals"].values():
                assert "mime" in v and ("data_base64" in v or "path" in v)


def test_cli_writes_html_report(tmp_path):
    input_file = tmp_path / "input3.bin"
    input_file.write_bytes(b'\x00\xff\x01\x02\x03' * 10)
    output_file = tmp_path / "report3.json"
    html_file = tmp_path / "report.html"

    completed = subprocess.run(
        [sys.executable, "-m", "patternanalyzer.cli", "analyze", str(input_file), "-o", str(output_file),
         "--html-report", str(html_file)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert output_file.exists(), f"Expected output file {output_file} to exist; stdout: {completed.stdout.decode()}; stderr: {completed.stderr.decode()}"
    assert html_file.exists(), f"Expected html report {html_file} to exist; stdout: {completed.stdout.decode()}; stderr: {completed.stderr.decode()}"

    html_text = html_file.read_text(encoding="utf-8")
    assert "<h1>Pattern Analyzer Report" in html_text
    assert "Summary" in html_text and "Results" in html_text
def test_cli_artefact_dir_writes_files_and_html_refs(tmp_path):
    input_file = tmp_path / "input4.bin"
    input_file.write_bytes(b'\x00\x01\x02' * 10)
    output_file = tmp_path / "report4.json"
    artefacts = tmp_path / "artefacts2"
    html_file = tmp_path / "report2.html"
    default_visuals = '{"fft_placeholder": {"mime": "image/svg+xml"}}'

    completed = subprocess.run(
        [sys.executable, "-m", "patternanalyzer.cli", "analyze", str(input_file), "-o", str(output_file),
         "--default-visuals", default_visuals, "--artefact-dir", str(artefacts), "--html-report", str(html_file)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert output_file.exists(), f"Expected output file {output_file} to exist; stdout: {completed.stdout.decode()}; stderr: {completed.stderr.decode()}"
    assert artefacts.exists() and artefacts.is_dir(), f"Expected artefact dir {artefacts} to be created"
    assert html_file.exists(), f"Expected html report {html_file} to exist; stdout: {completed.stdout.decode()}; stderr: {completed.stderr.decode()}"

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict)

    # Check that at least one visual entry used a file path and the file exists
    found_path = False
    for r in data.get("results", []):
        if isinstance(r, dict) and "visuals" in r:
            for v in r["visuals"].values():
                assert "mime" in v and ("data_base64" in v or "path" in v)
                if "path" in v:
                    found_path = True
                    assert Path(v["path"]).exists(), f"Expected artefact file {v['path']} to exist"

    assert found_path, "Expected at least one visual entry with 'path' in JSON when --artefact-dir is provided"

    # HTML should reference image by path (not data URI)
    html_text = html_file.read_text(encoding="utf-8")
    assert "<img" in html_text
    assert "data:" not in html_text, "HTML should not embed visuals as data URIs when artefact-dir is provided"
    assert str(artefacts.name) in html_text or str(artefacts) in html_text