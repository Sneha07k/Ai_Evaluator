The AI-Evaluator is an AI-driven system designed to automate the assessment of structured written responses, supporting both objective and subjective questions.
It reduces manual review effort by integrating Optical Character Recognition (OCR) and advanced text-processing techniques to evaluate content submitted in handwritten or typed form.

The system extracts text using OCR and compares responses against predefined reference answers and marking schemes.
Objective responses are evaluated through direct matching, while subjective answers are graded using keyword detection and semantic similarity–based analysis. A scoring and grading module calculates overall performance and generates detailed reports.

This project provides a complete, modular, and scalable architecture suitable for assignments, worksheets, practice sets, and other text-based evaluations.

-> System Architecture Overview

1. Input & User Management

  a. Role-based access (Admin / Teacher / Student)
  b. Secure upload of:
  c. Answer documents
  d. Reference keys
  e. Question-wise marking rules

2. Preprocessing & OCR

  a. Image enhancement and cleanup
  b. Support for JPG and common image formats
  c.OCR extraction (Tesseract as fallback engine)
  d.Automatic separation of responses by question

3. Evaluation Engine
   
  a. Objective Responses
  b. Direct string or option matching
  c. Suitable for MCQs, one-word answers, short responses
  d. Subjective Responses
  e. Hybrid scoring strategy:
  f. 60% keyword relevance
  g. 40% semantic similarity
  h. Adjustable correctness threshold (60–70%)
  i. Generates structured, easy-to-understand feedback

4. Scoring & Grading

  a. Configurable scoring rules
  b. Support for:
     Weightages
     Negative marking (optional)
     Total score and percentage calculation
     Grade mapping (A, B, C, etc.)

5. Reporting & Analytics

  a. Export results to Excel
  b. Visual analytics for:
      Score distribution
      Question-wise insights
      Performance summaries
  
-> Tech Stack

Python
Flask
OCR tools (e.g., Tesseract)
Text processing & similarity libraries
HTML/CSS frontend
Excel/CSV utilities for output reports

-> Key Highlights

Automates evaluation for assignments, worksheets, quizzes, and other written tasks

Reduces manual checking effort

Consistent scoring with transparent criteria

Modular design for easy customization

Works both with handwritten and typed submissions


-> Screenshots

1. Index and Login/Signup:
   
     <img width="959" height="472" alt="index" src="https://github.com/user-attachments/assets/2c659346-8464-4bf1-ba52-c09d234057e3" />

     <img width="960" height="470" alt="Login-signup" src="https://github.com/user-attachments/assets/5b67eda0-4c69-4305-ad99-c394d8b6fb30" />

2. Admin Dashboard:
   
     <img width="960" height="469" alt="Admin_dashboard" src="https://github.com/user-attachments/assets/6c2262af-8f96-4e05-9d55-69578a8d99b2" />

     <img width="958" height="464" alt="submissions" src="https://github.com/user-attachments/assets/df9b3c4b-88b2-478b-8aae-e38c567c121b" />

     <img width="537" height="317" alt="analytics" src="https://github.com/user-attachments/assets/9fc32fd0-9c35-4834-8455-f5dd86bea4a9" />

3. Evaluator Dashboard:

     <img width="960" height="475" alt="evaluator_dashboard" src="https://github.com/user-attachments/assets/d19578d0-1771-4801-a99d-89332b66d0b5" />

     <img width="960" height="474" alt="Auto-Evaluation" src="https://github.com/user-attachments/assets/fc5cf27e-2620-4398-be1f-e85cd5469275" />

     <img width="960" height="470" alt="review_auto_evaluation" src="https://github.com/user-attachments/assets/ba4900a6-3f21-42ca-bb44-50f31879a000" />

4. Student Dashboard:

      <img width="960" height="471" alt="student_dashboard" src="https://github.com/user-attachments/assets/b561a51b-e6df-4774-bbfd-6759eeadb033" />






     
