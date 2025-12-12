import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import csv
import traceback
from pathlib import Path
from types import SimpleNamespace
from flask import (
    Flask, render_template, request, redirect, url_for, session,
    send_from_directory, abort, flash
)
from werkzeug.utils import secure_filename
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import pytesseract
import difflib
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
ANSWER_KEY_FOLDER = os.path.join(UPLOAD_FOLDER, "answer_keys")
STUDENT_ANS_FOLDER = os.path.join(UPLOAD_FOLDER, "student_answers")
QUESTION_PAPER_FOLDER = os.path.join(UPLOAD_FOLDER, "question_papers")

os.makedirs(ANSWER_KEY_FOLDER, exist_ok=True)
os.makedirs(STUDENT_ANS_FOLDER, exist_ok=True)
os.makedirs(QUESTION_PAPER_FOLDER, exist_ok=True)

RESULTS_FILE = "results.csv"
USERS_FILE = "users.csv"
EXAMS_FILE = "exams.csv"
ASSIGN_FILE = "assignments.csv"
SUBMISSIONS_FILE = "submissions.csv"


if os.name == "nt":
    tess_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if Path(tess_path).exists():
        pytesseract.pytesseract.tesseract_cmd = tess_path

def load_users():
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("username"):
                    continue
                users[row["username"]] = {
                    "password": row.get("password", ""),
                    "role": row.get("role", "")
                }
    return users

def save_user(username, password, role):
    file_exists = os.path.exists(USERS_FILE)
    with open(USERS_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ["username", "password", "role"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(USERS_FILE) == 0:
            writer.writeheader()
        writer.writerow({"username": username, "password": password, "role": role})

def load_exams():
    exams = []
    if os.path.exists(EXAMS_FILE):
        with open(EXAMS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                exams.append(row)
    return exams

def save_exam(exam_name, question_filename):
    file_exists = os.path.exists(EXAMS_FILE)
    next_id = 1
    if file_exists:
        with open(EXAMS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            ids = [int(r.get("id", 0)) for r in reader if r.get("id")]
            if ids:
                next_id = max(ids) + 1
    with open(EXAMS_FILE,'a', newline='', encoding='utf-8') as f:
        fieldnames = ["id","exam_name","question_file"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(EXAMS_FILE) == 0:
            writer.writeheader()
        writer.writerow({"id": next_id, "exam_name": exam_name, "question_file": question_filename})
    return str(next_id)

def load_assignments():
    assigns = []
    if os.path.exists(ASSIGN_FILE):
        with open(ASSIGN_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                assigns.append(row)
    return assigns

def assign_exam_to_student(exam_id, student_username):
    file_exists = os.path.exists(ASSIGN_FILE)
    with open(ASSIGN_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ["exam_id","student_username"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(ASSIGN_FILE)==0:
            writer.writeheader()
        writer.writerow({"exam_id": exam_id, "student_username": student_username})

def load_submissions():
    subs = []
    if os.path.exists(SUBMISSIONS_FILE):
        with open(SUBMISSIONS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                subs.append(row)
    return subs

def save_submission(exam_id, student_username, filename):
    file_exists = os.path.exists(SUBMISSIONS_FILE)
    next_id = 1
    if file_exists:
        with open(SUBMISSIONS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            ids = [int(r.get("id",0)) for r in reader if r.get("id")]
            if ids: next_id = max(ids)+1
    with open(SUBMISSIONS_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ["id","exam_id","student_username","filename","submitted_at","status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if (not file_exists) or os.path.getsize(SUBMISSIONS_FILE)==0:
            writer.writeheader()
        writer.writerow({
            "id": next_id,
            "exam_id": exam_id,
            "student_username": student_username,
            "filename": filename,
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "pending"
        })
    return str(next_id)

def mark_submission_status(submission_id, status):
    subs = load_submissions()
    updated = False
    with open(SUBMISSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["id","exam_id","student_username","filename","submitted_at","status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in subs:
            if row.get("id") == str(submission_id):
                row["status"] = status
                updated = True
            writer.writerow(row)
    return updated


def preprocess_image(image_path):
    img = Image.open(image_path).convert("L")
    avg = sum(img.getdata()) / (img.width * img.height)
    if avg < 127:
        img = ImageOps.invert(img)
    img = ImageEnhance.Contrast(img).enhance(2)
    img = img.filter(ImageFilter.MedianFilter())
    return img

def ocr_extract(image_path):
    try:
        img = preprocess_image(image_path)
        text = pytesseract.image_to_string(img, config='--psm 6').replace('\r', '\n').strip()
        if not text:
            text = pytesseract.image_to_string(Image.open(image_path), config='--psm 6').strip()
        return text if text else "No text detected"
    except Exception as e:
        print(f"OCR error: {e}")
        traceback.print_exc()
        return "OCR error"

def calculate_similarity(a, b):
    return difflib.SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio() if a is not None and b is not None else 0.0

def load_answer_key(file_path):
    key = []
    if not file_path or not os.path.exists(file_path):
        return key
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("question"):
                continue
            key.append({"question": row["question"], "answer": row.get("answer", "")})
    return key

def evaluate_answer(extracted_answers, answer_key):
    results = []
    total_marks = 0
    for q in answer_key:
        student_ans = extracted_answers.get(q["question"], "")
        sim = calculate_similarity(student_ans, q["answer"])
        marks = int(sim * 100)
        remarks = "Excellent" if marks > 80 else "Good" if marks > 60 else "Needs Improvement"
        results.append({
            "question": q["question"],
            "extracted": student_ans,
            "marks": marks,
            "similarity": round(sim * 100, 2),
            "remarks": remarks
        })
        total_marks += marks
    return results, total_marks

def save_student_results(student_name, evaluated_answers):
    student_id = 1
    existing_ids = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    existing_ids.append(int(row.get("id", 0)))
                except Exception:
                    pass
    if existing_ids:
        student_id = max(existing_ids) + 1

    file_exists = os.path.exists(RESULTS_FILE)
    with open(RESULTS_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ["id", "name", "question", "extracted", "marks", "similarity", "remarks"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if (not file_exists) or os.path.getsize(RESULTS_FILE) == 0:
            writer.writeheader()
        for ans in evaluated_answers:
            writer.writerow({
                "id": student_id,
                "name": student_name,
                "question": ans.get("question", ""),
                "extracted": ans.get("extracted", ""),
                "marks": ans.get("marks", ""),
                "similarity": ans.get("similarity", ""),
                "remarks": ans.get("remarks", "")
            })
    return student_id

def load_results():
    students = {}
    if not os.path.exists(RESULTS_FILE):
        return students
    with open(RESULTS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                sid = int(row.get("id", 0))
            except Exception:
                continue
            if sid not in students:
                students[sid] = {"name": row.get("name", ""), "answers": []}
            row_copy = dict(row)
            try:
                row_copy["marks"] = int(row_copy.get("marks", 0))
            except Exception:
                row_copy["marks"] = 0
            students[sid]["answers"].append(row_copy)
    return students

def _to_submission_objs(sub_rows):
    objs = []
    for r in sub_rows:
        # normalize keys
        sid = r.get("id")
        exam_id = r.get("exam_id")
        student_username = r.get("student_username") or r.get("student_name") or ""
        filename = r.get("filename", "")
        status = r.get("status", "")
        submitted_at = r.get("submitted_at", "")
        obj = SimpleNamespace(
            id=str(sid),
            exam_id=str(exam_id),
            student_username=student_username,
            student_name=student_username,  
            filename=filename,
            status=status,
            submitted_at=submitted_at
        )
        objs.append(obj)
    return objs


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "username" not in session:
                return redirect(url_for("index"))
            if role and session.get("role") != role:
                return "Access Denied"
            return f(*args, **kwargs)
        return wrapped
    return decorator



@app.route('/')
def index():
    return render_template("index.html")



@app.route('/signup/<role>', methods=['GET', 'POST'])
def signup(role):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users:
            return render_template("signup.html", role=role, action="signup", error="User already exists")
        save_user(username, password, role)
        return redirect(url_for('login', role=role))
    return render_template("signup.html", role=role, action="signup", error=None)

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        user = users.get(username)
        if user and user['role'] == role and user['password'] == password:
            session['username'] = username
            session['role'] = role
            if role == "admin":
                return redirect(url_for("admin_dashboard"))
            elif role == "evaluator":
                return redirect(url_for("evaluator_dashboard"))
            elif role == "student":
                return redirect(url_for("student_dashboard"))
        return render_template("login.html", role=role, action="login", error="Invalid credentials")
    return render_template("login.html", role=role, action="login", error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("index"))



@app.route('/admin/dashboard')
@login_required(role="admin")
def admin_dashboard():
    exams = load_exams()
    students = [u for u,info in load_users().items() if info.get("role")=="student"]
    answer_keys = os.listdir(ANSWER_KEY_FOLDER)
    return render_template("admin_dashboard.html", exams=exams, students=students, answer_keys=answer_keys)

@app.route('/admin/create_exam', methods=['GET','POST'])
@login_required(role="admin")
def create_exam():
    if request.method == 'POST':
        exam_name = request.form.get("exam_name")
        qfile = request.files.get("question_file")
        if not exam_name or not qfile:
            flash("All fields required")
            return redirect(url_for("create_exam"))
        filename = secure_filename(qfile.filename)
        save_path = os.path.join(QUESTION_PAPER_FOLDER, filename)
        qfile.save(save_path)
        save_exam(exam_name, filename)
        flash("Exam created and question paper uploaded")
        return redirect(url_for("admin_dashboard"))
    return render_template("create_exam.html")

@app.route('/admin/upload_answer_key', methods=["GET", "POST"])
@login_required(role="admin")
def upload_answer_key():
    exams = load_exams()
    if request.method == "POST":
        exam_id = request.form.get("exam_id")
        file = request.files.get("answer_key")
        if not exam_id or not file:
            flash("Please choose exam and file")
            return redirect(url_for("upload_answer_key"))
        filename = secure_filename(f"exam{exam_id}_" + file.filename)
        save_path = os.path.join(ANSWER_KEY_FOLDER, filename)
        file.save(save_path)
        flash(f"Answer key '{filename}' uploaded for exam {exam_id}")
        return redirect(url_for("admin_dashboard"))
    return render_template("upload_answer_key.html", exams=exams, success=None, keys=os.listdir(ANSWER_KEY_FOLDER), error=None)

@app.route('/admin/assign_exam', methods=["GET","POST"])
@login_required(role="admin")
def assign_exam():
    exams = load_exams()
    students = [u for u,info in load_users().items() if info.get("role")=="student"]
    if request.method == "POST":
        exam_id = request.form.get("exam_id")
        student_username = request.form.get("student_username")
        if not exam_id or not student_username:
            flash("Select exam and student")
            return redirect(url_for("assign_exam"))
        assign_exam_to_student(exam_id, student_username)
        flash("Exam assigned")
        return redirect(url_for("admin_dashboard"))
    return render_template("assign_exam.html", exams=exams, students=students)

@app.route('/admin_results')
@login_required(role="admin")
def admin_results():
    students = load_results() 
    submissions = load_submissions()
    

    for s in students.values():
        s['total_marks'] = sum(int(a.get('marks', 0)) for a in s.get('answers', []))

   
    marks_map = {s['name']: s['total_marks'] for s in students.values()}

    return render_template(
        "admin_results.html",
        submissions=submissions,
        marks_map=marks_map
    )




@app.route('/student/dashboard')
@login_required(role="student")
def student_dashboard():
    username = session.get("username")
    exams = load_exams()
    assigns = load_assignments()
    assigned_exam_ids = [a['exam_id'] for a in assigns if a['student_username']==username]
    assigned_exams = [e for e in exams if e['id'] in assigned_exam_ids]
    submissions_raw = [s for s in load_submissions() if s["student_username"]==username]
    submissions = _to_submission_objs(submissions_raw)
 
    results = load_results()
    personal_results = []
    for sid, s in results.items():
        if s.get("name") == username:
            personal_results.append(s)
    return render_template("student_dashboard.html", assigned_exams=assigned_exams, submissions=submissions, results=personal_results)

@app.route('/student/upload/<exam_id>', methods=["GET","POST"])
@login_required(role="student")
def student_upload_answer(exam_id):
    username = session.get("username")
   
    assigns = load_assignments()
    if not any(a['exam_id']==str(exam_id) and a['student_username']==username for a in assigns):
        return "Not assigned this exam", 403
    if request.method == "POST":
        f = request.files.get("answer_image")
        if not f:
            flash("Please upload file")
            return redirect(url_for("student_upload_answer", exam_id=exam_id))
        filename = secure_filename(f"{username}_exam{exam_id}_" + f.filename)
        save_path = os.path.join(STUDENT_ANS_FOLDER, filename)
        f.save(save_path)
        save_submission(exam_id, username, filename)
        flash("Uploaded successfully")
        return redirect(url_for("student_dashboard"))
    exam = next((e for e in load_exams() if e['id']==str(exam_id)), None)
    return render_template("student_upload.html", exam=exam)


@app.route('/evaluator/dashboard')
@login_required(role="evaluator")
def evaluator_dashboard():
    subs_raw = load_submissions()
   
    subs = _to_submission_objs(subs_raw)
    exams = {e['id']: e for e in load_exams()}
    answer_keys = os.listdir(ANSWER_KEY_FOLDER)
    return render_template("evaluator_dashboard.html", submissions=subs, exams=exams, answer_keys=answer_keys)

@app.route('/evaluator/submissions')
@login_required(role="evaluator")
def list_submissions():
    subs_raw = [s for s in load_submissions() if s.get("status") in ("pending", "uploaded")]
    subs = _to_submission_objs(subs_raw)
    exams = load_exams()
    return render_template("evaluator_submissions.html", submissions=subs, exams=exams)


@app.route('/evaluate_submission/<submission_id>', methods=["GET", "POST"])
@login_required(role="evaluator")
def evaluate_submission(submission_id):
    return evaluator_evaluate(submission_id)

@app.route('/evaluator/evaluate/<submission_id>', methods=["GET","POST"])
@login_required(role="evaluator")
def evaluator_evaluate(submission_id):
    subs_raw = load_submissions()
    submission_row = next((s for s in subs_raw if s.get("id") == str(submission_id)), None)
    if not submission_row:
        return "Submission not found", 404

   
    submission = _to_submission_objs([submission_row])[0]
  
    exam = next((e for e in load_exams() if e['id'] == submission.exam_id), None)

    if request.method == "POST":
        chosen_key = request.form.get("answer_key")
        saved_name = submission.filename
        ans_path = os.path.join(STUDENT_ANS_FOLDER, saved_name)

        if not os.path.exists(ans_path):
            flash("Student answer image not found on server.")
            return redirect(url_for("evaluator_dashboard"))

        key_path = os.path.join(ANSWER_KEY_FOLDER, chosen_key) if chosen_key else None
        extracted_text = ocr_extract(ans_path)
        lines = [line.strip() for line in extracted_text.split("\n") if line.strip()]
        answer_key = load_answer_key(key_path) if key_path else []
        extracted_answers = {}
        for i, q in enumerate(answer_key):
            extracted_answers[q["question"]] = lines[i] if i < len(lines) else ""
        evaluated, total_marks = evaluate_answer(extracted_answers, answer_key)

      
        return render_template(
            "review_evaluation.html",
            student_name=submission.student_username,
            evaluated=evaluated,
            total_marks=total_marks,
            image_file=submission.filename,
            submission_id=submission.id,
            exam=exam,
            chosen_key=chosen_key
        )

    keys = os.listdir(ANSWER_KEY_FOLDER)
    return render_template("evaluator_preview_submission.html", submission=submission, exam=exam, keys=keys)

@app.route('/evaluator/save_results', methods=["POST"])
@login_required(role="evaluator")
def save_results():
    try:
        student_name = request.form.get("student_name")
        submission_id = request.form.get("submission_id")  
        questions = request.form.getlist("question[]")
        extracted_list = request.form.getlist("extracted[]")
        marks_list = request.form.getlist("marks[]")
        similarity_list = request.form.getlist("similarity[]")
        remarks_list = request.form.getlist("remarks[]")

        evaluated = []
        for i, q in enumerate(questions):
            evaluated.append({
                "question": q,
                "extracted": extracted_list[i] if i < len(extracted_list) else "",
                "marks": int(marks_list[i]) if i < len(marks_list) and str(marks_list[i]).isdigit() else 0,
                "similarity": float(similarity_list[i]) if i < len(similarity_list) and similarity_list[i] else 0.0,
                "remarks": remarks_list[i] if i < len(remarks_list) else ""
            })

      
        save_student_results(student_name, evaluated)

        if submission_id:
            mark_submission_status(submission_id, "evaluated")
        else:
            subs = load_submissions()
            pending_for_student = [s for s in subs if s.get("student_username") == student_name and s.get("status") in ("pending", "uploaded")]
            if pending_for_student:
                try:
                    latest = sorted(pending_for_student, key=lambda x: int(x.get("id") or 0))[-1]
                    mark_submission_status(latest.get("id"), "evaluated")
                except Exception:
                    mark_submission_status(pending_for_student[0].get("id"), "evaluated")

        return redirect(url_for("evaluator_dashboard"))
    except Exception as e:
        traceback.print_exc()
        return f"Error saving results: {e}", 500


@app.route('/question_paper/<filename>')
@login_required()
def serve_question_paper(filename):
    filepath = os.path.join(QUESTION_PAPER_FOLDER, filename)
    if not os.path.exists(filepath):
        return "Not found", 404
    return send_from_directory(QUESTION_PAPER_FOLDER, filename)

@app.route('/student_images/<filename>')
@login_required()
def serve_student_image(filename):
    filepath = os.path.join(STUDENT_ANS_FOLDER, filename)
    if not os.path.exists(filepath):
        abort(404)
    return send_from_directory(STUDENT_ANS_FOLDER, filename)

@app.route('/preview_answer_key/<filename>')
@login_required()
def preview_answer_key(filename):
    filepath = os.path.join(ANSWER_KEY_FOLDER, filename)
    if not os.path.exists(filepath):
        return "Answer key not found", 404
    with open(filepath, "r", encoding='utf-8') as f:
        content = f.read()
    return render_template("preview_answer_key.html", filename=filename, content=content)


@app.route('/student/results')
@login_required(role="student")
def student_results():
    username = session.get("username")
    results = load_results()
    personal = []
    for sid, s in results.items():
        if s.get("name") == username:
            personal.append(s)
    return render_template("student_results.html", results=personal)


@app.route('/analytics')
def analytics():
    students = load_results()  
    labels = [s.get("name", "Unknown") for s in students.values()]
    marks  = [sum(int(a.get("marks", 0)) for a in s.get("answers", [])) for s in students.values()]

    
    plt.figure(figsize=(10,6))
    sns.barplot(x=labels, y=marks, palette="Blues_d")
    plt.ylabel("Total Marks")
    plt.xlabel("Students")
    plt.title("Student Performance")
    plt.xticks(rotation=45)

   
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_data = base64.b64encode(buf.getvalue()).decode()
    plt.close()

    return render_template("analytics_img.html", chart_data=chart_data)




@app.route('/list_exams')
def list_exams():
    exams = load_exams()
    return render_template("list_exams.html", exams=exams)

if __name__ == "__main__":
    app.run(debug=True)
