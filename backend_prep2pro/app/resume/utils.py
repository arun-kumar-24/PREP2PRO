import PyPDF2 # type: ignore
from sentence_transformers import SentenceTransformer # type: ignore
import language_tool_python # type: ignore
import google.generativeai as genai # type: ignore
from sklearn.metrics.pairwise import cosine_similarity # type: ignore
import os
from dotenv import load_dotenv # type: ignore

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_file):
    try:
        # Initialize PDF reader
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        # Loop through all pages and extract text
        for page in reader.pages:
            text += page.extract_text()
        
        return text

    except Exception as e:
        # Handle errors, such as file issues or empty content
        return f"Error in PDF extraction: {str(e)}"

# Function to check grammatical correctness
def grammar_check(text):
    tool = language_tool_python.LanguageTool('en-US')  # Use English language

    matches = tool.check(text)
    errors = len(matches)  # Number of grammar issues
    total_words = len(text.split())
    error_ratio = errors / total_words if total_words > 0 else 0  # Error ratio
    grammar_score = max(0, 30 * (1 - error_ratio))  # Scale to 30%
    return grammar_score

# Function to check and grade the overall layout
def layout_check(resume_text):
    layout_score = 0

    # Check for consistent use of bullet points
    bullet_points = ['-', '*', '•']
    bullet_count = sum(1 for line in resume_text.splitlines() if line.strip().startswith(tuple(bullet_points)))
    if bullet_count > 5:  # Assume a good resume has at least 5 bullet points
        layout_score += 7  # Allocate 7 points for bullet usage

    # Check for spacing consistency (at least one blank line between sections)
    lines = resume_text.splitlines()
    blank_line_count = sum(1 for i in range(1, len(lines)) if lines[i].strip() == "" and lines[i - 1].strip() != "")
    if blank_line_count >= 4:  # Assume 4+ blank lines indicate good spacing
        layout_score += 7  # Allocate 7 points for spacing

    # Check for presence of contact details
    contact_keywords = ['email', 'phone', 'contact', '@']
    if any(keyword in resume_text.lower() for keyword in contact_keywords):
        layout_score += 6  # Allocate 6 points for contact details

    return layout_score  

# Function to score the keyword matching between resume and job description
def keyword_similarity(job_desc,resume_text):
    # Load pre-trained SBERT model
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

    # Encode both the job description and the resume
    job_vec = model.encode([job_desc])
    resume_vec = model.encode([resume_text])

    # Calculate cosine similarity
    similarity_score = cosine_similarity(job_vec, resume_vec)[0][0]

    return similarity_score

# Function to provide potential improvements from gemini api
def improvement_suggestions_gemini(job_desc, resume_text):
    # Load environment variables from the .env file
    load_dotenv()

    # Access the GEMINI_KEY from the environment variables
    GEMINI_KEY = os.getenv('GEMINI_KEY')
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f'''Please review the following resume text ({resume_text}) in reference to the job description ({job_desc}). The review
should follow an interview-like feedback style, with everything based on the given resume text. Focus on the following key areas:

Bullet Points Usage:

Review: Check if bullet points are used in the resume to highlight achievements, responsibilities, or key skills. If they are used 
effectively, acknowledge the formatting. If not, suggest using bullet points for better readability and clarity.
Example (if no bullet points are used):
Experience:
Led a team to develop a full-stack web application. Worked with various stakeholders to design and implement features. Coordinated 
testing and deployment.
Suggested Change: Provide examples from the given resume text if suggesting changes.
Experience:
- Led a team to develop a full-stack web application.
- Worked with stakeholders to design and implement features.
- Coordinated testing and deployment.

Formal Writing Review:

Review: Assess the tone of the resume. It should be formal and professional. If the language is too casual, provide suggestions to 
make it more formal.
Example (if casual language is found in the resume text):
I really like working with teams and get things done quickly.
Suggested Change: Provide examples from the given resume text if suggesting changes.
Collaborated effectively with teams to deliver projects within deadlines.

Keyword Similarity:

Review: Compare the keywords in the resume text with the job description. Identify any missing keywords or areas where the resume 
could better match the job description.
Example: If the job description emphasizes "project management" and the resume text lacks it:
Job Description: "Looking for a candidate with strong project management skills."
Resume Text: "Managed a team to deliver software solutions."
Suggested Change: Provide examples from the given resume text if suggesting changes.
Resume Text: "Led and managed projects from conception to delivery, ensuring timely and successful completion."

Grammatical Errors:

Review: Identify any grammatical errors in the resume text. Correct the errors and suggest improvements.
Example (if grammatical errors are found in the resume text):
I am expert in JavaScript, Python, and Java.
Suggested Change: Provide examples from the given resume text if suggesting changes.
I am an expert in JavaScript, Python, and Java.

Metrics in Contributions:

Review: Check if there are any measurable metrics that demonstrate the candidate's contribution to previous roles (e.g., improved 
sales by 20%, reduced response time by 30%). If not, suggest adding such metrics where applicable.
Example (if no metrics are present in the resume text):
Led a project team and delivered a product.
Suggested Change: Provide examples from the given resume text if suggesting changes.
Led a project team of 10 members and delivered the product 15% ahead of schedule.

Contact Information:

Review: Ensure that the resume includes contact details (e.g., phone number, email). If no contact details are present, suggest
adding them.
Example (if contact info is missing in the resume text):
(No contact information present)
Suggested Change: Provide examples from the given resume text if suggesting changes.
Please include your contact details, such as:
- Phone number
- Email address

Additional Sections:

Review: Check if necessary sections like "Skills", "Projects", and "Education" are present. If not, suggest adding these headings.
Example (if sections are missing in the resume text):
Experience:
- Developed software applications using Python.
Suggested Change: Provide examples from the given resume text if suggesting changes.
Skills:
- Python, JavaScript, React

Just dont give response in headings or conversation just respond in sentences thats it.
Conclusion: Finally, based on the review of the provided resume text and job description, suggest any necessary changes to improve 
the resume and ensure it aligns well with the job description. Always base your suggestions and examples on the provided resume text,
 and provide clear and actionable feedback.'''

    try:
        # Using the correct method, likely 'generate_content' instead of 'Completion.create'
        response = gemini_model.generate_content(prompt)
        
        # Extracting the generated suggestions
        suggestions = response.text.strip() if hasattr(response, 'text') else "No suggestions available."

        # Split the suggestions into sentences and return them as a list
        suggestions_list = suggestions.split('. ')
        suggestions_list = [sentence.strip() + '.' for sentence in suggestions_list if sentence]  # Ensuring proper punctuation
        
        return suggestions_list
    except Exception as e:
        print(f"Error occurred while fetching suggestions: {e}")
        return ["No suggestions available."]
    
# Function to evaluate resumes based on extracted text    
def evaluate_resume(resume_text, job_description):
    # Calculate cosine similarity
    keyword_score = keyword_similarity(job_description,resume_text)

    # Grammar score
    grammar_score_percentage = grammar_check(resume_text)

    # Layout score
    layout_score = layout_check(resume_text)
    
    total_ats_score = str((keyword_score * 50) + grammar_score_percentage + layout_score)


    suggestions = improvement_suggestions_gemini(job_description, resume_text)
    
    response = {
        "ats-score" : total_ats_score,
        "ats-score-breakdown" : {
            "keyword-score" : str(keyword_score),
            "grammar-score" : grammar_score_percentage,
            "layout-score" : layout_score
        },
        "suggestions" : suggestions,

    }
    return response