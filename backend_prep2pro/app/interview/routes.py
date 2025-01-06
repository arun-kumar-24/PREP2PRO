from flask import Blueprint, request, jsonify  # type: ignore
from app.supabase_client import supabase_client
from .utils import extract_text_from_pdf, problems_DS, problems_SDE
import google.generativeai as genai  # type: ignore
import os
from dotenv import load_dotenv  # type: ignore
from app.redis_client import redis_client
import json
from langchain_google_genai import GoogleGenerativeAIEmbeddings # type: ignore
import pandas as pd
from langchain_core.documents import Document  # type: ignore
from langchain_community.vectorstores import FAISS # type: ignore
import io
from datetime import datetime

interview_bp = Blueprint('interview', __name__)

@interview_bp.route('/initialize', methods=['POST'])
def initialize_interview():
    # Initialize an interview session.
    data = request.form
    domain = data.get('domain').strip()
    interview_type = data.get('type').strip()
    resume = request.files.get('resume')
    
    # Check for missing required fields
    if not domain or not interview_type or not resume:
        return jsonify({"error": "Missing required fields"}), 400

    # Check for valid file format
    if not resume.filename.endswith('.pdf'):
        return jsonify({"error": "Invalid file format, only PDFs are allowed"}), 400
    
    resume_text = extract_text_from_pdf(resume)

    # Query domain ID
    response = supabase_client.table("domains").select("id").eq("name", domain).execute()

    if not response.data:
        return jsonify({"error": f"No domain found for {domain}"}), 404
    domain_id = response.data[0]["id"]

    # Query round ID
    response = supabase_client.table("rounds").select("id").eq("name", interview_type).execute()
    if not response.data:
        return jsonify({"error": f"No round found for {interview_type}"}), 404
    round_id = response.data[0]["id"]
    
    # Query interview rules
    response = supabase_client.table("interview_rules").select("rule_content").eq("domain_id", domain_id).eq("round_id", round_id).execute()
    if not response.data:
        return jsonify({"error": "No rules found for the selected domain and type"}), 404

    interview_rules = response.data[0]

    # Create session state (In-Memory, Redis, or DB)
    session_id = f"{domain}_{interview_type}_{resume.filename.split('.')[0]}"

    #Problems retrieval from database
    if interview_type == "TECHNICAL_1":
        problems = problems_SDE()
    if domain == "DS" and interview_type == "TECHNICAL":
        problems = problems_DS()

    session_data = {
        "domain": domain,
        "type": interview_type,
        "resume": resume_text,
        "rules": interview_rules,
        "chat_history": [
            {"role": "system", "content": "Hi I am Alice. I am your interviewer today. Could you please introduce yourself?"}
        ],
        "start_time": datetime.now().isoformat()  # Add start time
    }
    if 'problems' in locals() and problems:  # Check if problems is defined and not empty
        session_data["problems"] = problems 
    # Serialize session_data before storing it in Redis
    session_data_str = json.dumps(session_data)

    # Now store the serialized session_data in Redis
    redis_client.hset(session_id, "session_data", session_data_str)

    # For now, we'll return it as a response.
    return jsonify({"session_id": session_id, "interviewer_response": session_data["chat_history"]}), 200

@interview_bp.route('/next_question', methods=['POST'])
def next_question():
    data = request.form
    session_id = data.get('session_id')
    user_answer = data.get('user_answer')
    st = datetime.now().isoformat()

    if not session_id or not user_answer:
        return jsonify({"error": "Missing session ID or user answer"}), 400

    # Debugging to check the Redis key type
    redis_key_type = redis_client.type(session_id)

    if redis_key_type != 'hash':
        return jsonify({"error": "Invalid Redis key type. Expected hash."}), 400

    # Retrieve session data from Redis using HGET
    session_data_str = redis_client.hget(session_id, 'session_data')

    print("redis get")
    print((datetime.now() - datetime.fromisoformat(st)).total_seconds() / 60)

    if session_data_str is None:
        return jsonify({"error": "Invalid session ID or missing session data"}), 404

    # Decode the data if stored as bytes
    if isinstance(session_data_str, bytes):
        session_data_str = session_data_str.decode('utf-8')

    # Deserialize session data (assuming it's stored as JSON)
    try:
        session_data = json.loads(session_data_str)
    except json.JSONDecodeError:
        return jsonify({"error": "Error decoding session data"}), 500

    print("decode fom redis")
    print((datetime.now() - datetime.fromisoformat(st)).total_seconds() / 60)

    # Update chat history
    session_data["chat_history"].append({"role": "user", "content": user_answer})
    start_time = session_data.get('start_time')
    elapsed_time = (datetime.now() - datetime.fromisoformat(start_time)).total_seconds() / 60
    # if elapsed_time > 50:
    #     conclusion_message = "Thank you so much for taking the time to talk with us today. We really enjoyed learning more about your background and the skills you bring to the role. We'll review everything and be in touch soon about the next steps. If you have any questions in the meantime, feel free to reach out. Have a great day!"
    #     return jsonify({"message": conclusion_message, "status_code": 408, "session_id": session_id}), 408

    # Generate a prompt for Gemini API
    interview_info = session_data["rules"]
    chat_history = session_data["chat_history"]
    resume_text = session_data["resume"]
    if "problems" in session_data:
        problems = session_data["problems"]
    else:
        problems = None
    #Best practices code
    try:
        best_practices_file = supabase_client.storage.from_('ragfiles').download('answers_followup_questions.csv')
        best_practices_file = io.BytesIO(best_practices_file)
    except Exception as e:
        print('Error:', e)
    print("rag file retrie")
    print((datetime.now() - datetime.fromisoformat(st)).total_seconds() / 60)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"D://Hackathons//CODERED'25//PREP2PRO//backend_prep2pro//gcpserviceacckey.json"
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    df = pd.read_csv(best_practices_file)
    texts = df[['Answer', 'Follow-Up Question']].agg(' '.join, axis=1).tolist()
    documents = [Document(page_content=text) for text in texts]
    db = FAISS.from_documents(documents, embeddings)

    def retrieve_info(query):
        similar_response = db.similarity_search(query, k=3)
        page_contents_array = [doc.page_content for doc in similar_response]
        return page_contents_array

    best_practice = retrieve_info(user_answer)
    print("best practice")
    print((datetime.now() - datetime.fromisoformat(st)).total_seconds() / 60)
    # Load GEMINI_KEY from environment variables
    load_dotenv()
    GEMINI_KEY = os.getenv('GEMINI_KEY')
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = f'''
    You are a world-class interviewer with expertise in various technical domains. Your task is to frame a highly specific technical follow-up question based on the provided resources and context.
    
    Context:
    Interview Structure and Rules: {interview_info}
    Best Practices for Question Framing: {best_practice}
    Ensure questions align with the formal style provided, keeping them concise yet detailed where necessary.
    Chat History of the Interview So Far: {chat_history}
    This is the user's answer to your previous question : {user_answer}
    This is the user' resume :{resume_text}
    Current duration of the interview : {elapsed_time}
    If the user's response is a self-introduction and some clarification can be asked in that, feel free to ask that too but don't ask unnecessary questions.
    Pay particular attention to the user's answer to the last question when framing the follow-up.

    Instructions:
    Note: Restrict yourself from asking multiple questions at a time.
    Only ask follow up questions when you need clarification in user's response.
    Don't generate follow up questions with the current question, assess the user's response before asking a follow up.
    Assess the rules and resources carefully.
    Ensure the follow-up question is medium level technical, specific, and conceptually connected to the user's last response in the chat history.
    Maintain a formal tone and structure consistent with the provided best practices.
    The Questions should be short precise and difficulty should be medium level.
    The response from you should not start with "Given your " instead you various vocabulary.
    The response must consists of the response to the user's previous answer and then follow up or new question thats it.
    Don't add any headings or something. Just plain text.
    If you have met all the criteria to end the meeting based on the interview_rules  and the elapsed_time is greater than 30 then just respond "conclude"
    '''
    if problems != None:
        prompt += f'''Here are the problems use should be including in this session{problems}'''
    try:
        response = gemini_model.generate_content(prompt)
        print("response")
        print((datetime.now() - datetime.fromisoformat(st)).total_seconds() / 60)
    except Exception as e:
        print(f"Error occurred while fetching follow-up: {e}")
        return jsonify({"error": "No follow-up available"}), 500

    # Update chat history with generated question
    question = response.text

    if "conclude" in question:
        conclusion_message = "Thank you so much for taking the time to talk with us today. We really enjoyed learning more about your background and the skills you bring to the role. We'll review everything and be in touch soon about the next steps. If you have any questions in the meantime, feel free to reach out. Have a great day!"
        return jsonify({"message": conclusion_message, "status_code": 408, "session_id": session_id}), 408
    
    session_data["chat_history"].append({"role": "interviewer", "content": question})

    # Serialize session data back to JSON
    session_data_str = json.dumps(session_data)

    # Save updated session data back to Redis using HSET
    redis_client.hset(session_id, 'session_data', session_data_str)

    return jsonify({"question": question}), 200

@interview_bp.route('/improvements', methods=['POST'])
def generate_improvements():
    data = request.form
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({"error": "Missing session ID"}), 400

    session_data_str = redis_client.hget(session_id, 'session_data')

    if session_data_str is None:
        return jsonify({"error": "Invalid session ID or missing session data"}), 404

    # Decode the data if stored as bytes
    if isinstance(session_data_str, bytes):
        session_data_str = session_data_str.decode('utf-8')

    # Deserialize session data (assuming it's stored as JSON)
    try:
        session_data = json.loads(session_data_str)
    except json.JSONDecodeError:
        return jsonify({"error": "Error decoding session data"}), 500

    # Generate improvements using Gemini
    chat_history = session_data["chat_history"]
    load_dotenv()
    GEMINI_KEY = os.getenv('GEMINI_KEY')
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f'''
    You are an expert interviewer. Based on the following chat history, provide detailed and constructive improvement suggestions for the user in bullet points:
    {chat_history}
    '''
    try:
        response = gemini_model.generate_content(prompt)
        improvements = response.text
    except Exception as e:
        print(f"Error occurred while generating improvements: {e}")
        return jsonify({"error": "Could not generate improvements"}), 500

    # Clear the session data
    redis_client.delete(session_id)

    return jsonify({"improvements": improvements}), 200