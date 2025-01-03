from flask import Blueprint, request, jsonify # type: ignore
from .utils import extract_text_from_pdf, evaluate_resume
import os
from werkzeug.utils import secure_filename

resume_bp = Blueprint('resume', __name__)

@resume_bp.route('/evaluate_resume', methods=['POST'])
def evaluate_resume_route():
    # Get the resume PDF file from the request
    pdf_file = request.files.get('resume')

    # Get the job description from the request
    job_description = request.form.get('job_description')

    # Validate input
    if not pdf_file or not job_description:
        return jsonify({"error": "Both resume and job description are required"}), 400

    if not pdf_file.filename.endswith('.pdf'):
        return jsonify({"error": "Invalid file format, only PDFs are allowed"}), 400

    # # Secure the filename to avoid security issues
    # filename = secure_filename(pdf_file.filename)
    # file_path = os.path.join('temp', filename)  # Store temporarily, you can customize the path

    try:
        # Save the PDF file temporarily
        # pdf_file.save(file_path)
        
        # Extract text from the PDF file
        resume_text = extract_text_from_pdf(pdf_file)
        
        # Perform the evaluation
        evaluation_results = evaluate_resume(resume_text, job_description)
        
        # Cleanup: Remove the temporary file after processing (optional, based on your needs)
        # os.remove(file_path)
        
        # Return the evaluation results
        return jsonify(evaluation_results), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500