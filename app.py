import os
import sqlite3
import pytesseract
import traceback
from flask import Flask, render_template, request, redirect, url_for
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from pathlib import Path
import difflib
import textwrap

# =====================================
# BASIC FLASK SETUP
# =====================================
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =====================================
# TESSERACT PATH (Windows Fix)
# =====================================
if os.name == "nt":  # Only for Windows
    tess_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if Path(tess_path).exists():
        pytesseract.pytesseract.tesseract_cmd = tess_path
    else:
        tess_env = os.environ.get("TESSERACT_CMD")
        if tess_env and Path(tess_env).exists():
            pytesseract.pytesseract.tesseract_cmd = tess_env
        else:
            print("⚠️ Warning: Tesseract not found! Install it or update tess_path variable.")

# =====================================
# DATABASE SETUP
# =====================================
DB_PATH = 'class_results.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    marks INTEGER,
    remarks TEXT
)
''')
conn.commit()
conn.close()

# =====================================
# IMAGE PREPROCESSING FOR OCR
# =====================================
def preprocess_image_for_ocr(image_path):
    try:
        img = Image.open(image_path)
        img = img.convert("L")  # grayscale
        img = ImageOps.invert(img)
        img = ImageEnhance.Contrast(img).enhance(2)
        img = img.filter(ImageFilter.MedianFilter())
        # Optional resize for small images
        # img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        return img
    except Exception as e:
        print(f"[ERROR] Preprocessing failed for {image_path}: {e}")
        traceback.print_exc()
        raise

# =====================================
# OCR EXTRACTION FUNCTION
# =====================================
def ocr_extract(image_path):
    """
    Extract text from an image using pytesseract with preprocessing.
    Returns a readable string. Logs errors for debugging.
    """
    try:
        img = preprocess_image_for_ocr(image_path)
        text = pytesseract.image_to_string(img, config='--psm 6')
        text = text.replace('\r', '\n').strip()

        if not text:
            # Try fallback on raw image
            try:
                raw = Image.open(image_path)
                text = pytesseract.image_to_string(raw, config='--psm 6').strip()
            except Exception as e2:
                print(f"[OCR Fallback Failed] {e2}")
                traceback.print_exc()
                return "OCR error"

        if not text:
            return "No text detected"

        return text
    except Exception as e:
        print(f"[OCR ERROR] File: {image_path}")
        print("Exception:", str(e))
        traceback.print_exc()
        return "OCR error"

# =====================================
# SIMPLE TEXT SIMILARITY FUNCTION
# =====================================
def calculate_similarity(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

# =====================================
# GRADING / EVALUATION LOGIC
# =====================================
def evaluate_answer(answer_text, answer_key_text):
    similarity = calculate_similarity(answer_text, answer_key_text)
    marks = int(similarity * 100)
    remarks = "Excellent" if marks > 80 else "Good" if marks > 60 else "Needs Improvement"
    return marks, remarks

# =====================================
# ROUTES
# =====================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        # Get uploaded files
        answer_key_file = request.files['answer_key']
        answer_image = request.files['answer_image']

        if not answer_key_file or not answer_image:
            return "Both files required!"

        # Save files
        key_path = Path(app.config['UPLOAD_FOLDER']) / answer_key_file.filename
        ans_path = Path(app.config['UPLOAD_FOLDER']) / answer_image.filename
        answer_key_file.save(str(key_path))
        answer_image.save(str(ans_path))

        # Extract OCR text
        print(f"[DEBUG] Starting OCR for {ans_path}")
        extracted = ocr_extract(str(ans_path))
        print(f"[DEBUG] Extracted Text (first 200 chars): {repr(extracted[:200])}")

        # Read answer key
        with open(key_path, 'r', encoding='utf-8', errors='ignore') as f:
            key_text = f.read().strip()

        # Evaluate
        marks, remarks = evaluate_answer(extracted, key_text)
        print(f"[DEBUG] Marks: {marks}, Remarks: {remarks}")

        # Save to DB
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO results (name, marks, remarks) VALUES (?, ?, ?)", 
                    (answer_image.filename, marks, remarks))
        conn.commit()
        conn.close()

        return render_template('result.html', 
                               name=answer_image.filename, 
                               marks=marks, 
                               remarks=remarks,
                               extracted=textwrap.shorten(extracted, width=400))

    except Exception as e:
        print("[ERROR] Upload failed:", e)
        traceback.print_exc()
        return f"Error during upload: {str(e)}"

@app.route('/analytics')
def analytics():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM results")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No records yet."

    total = len(rows)
    avg = sum([r[2] for r in rows]) / total
    top = max(rows, key=lambda r: r[2])
    return render_template('analytics.html', rows=rows, avg=avg, top=top)

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM results WHERE id=?", (student_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return "Student not found."
    return render_template('student.html', student=row)

# =====================================
# MAIN RUN
# =====================================
if __name__ == '__main__':
    app.run(debug=True)
