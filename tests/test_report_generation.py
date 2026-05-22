import os
import subprocess
from docx import Document

def test_report_script_exists():
    assert os.path.exists("scripts/generate_report.py")

def test_generated_file_exists_and_valid():
    # Execute script
    res = subprocess.run(["python", "scripts/generate_report.py"], capture_output=True, text=True)
    assert res.returncode == 0
    assert os.path.exists("AI_Travel_Optimizer_Architecture_Report.docx")
    
    # Read docx
    doc = Document("AI_Travel_Optimizer_Architecture_Report.docx")
    text = "".join([p.text for p in doc.paragraphs])
    assert "Nghiên cứu Khối Mobile App" in text
    assert "Nghiên cứu Khối Gateway" in text
    assert "Nghiên cứu Khối Routing Engine" in text
    assert "Nghiên cứu Khối Data/Infrastructure" in text
    assert "Tổng hợp và kết luận" in text
