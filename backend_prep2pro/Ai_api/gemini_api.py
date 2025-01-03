from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import google.generativeai as genai
from elevenlabs.client import ElevenLabs
from flask_cors import CORS
# Load environment variables
load_dotenv()

# Initialize ElevenLabs API
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
if not elevenlabs_api_key:
    raise ValueError("ELEVENLABS_API_KEY is missing in the .env file.")
client = ElevenLabs(api_key=elevenlabs_api_key)

# Configure Google Generative AI
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 2000,
    "response_mime_type": "text/plain",
}

system_message ="""
You are an AI interviewer named Alice for a professional role in [Domain], evaluating the candidate’s skills based on their [Skill Set]. Your task is to ask structured, focused questions, provide constructive feedback at the end, and maintain a clear, concise interview process.
NOTE: strictly avoid asking mulitple questions at a time and ask the next question or followup question only after getting the canditate's response.
Interview Guidelines:
1. If the Domain and Skill Set are not provided, ask the candidate for these details and their projects.
2. Introduce yourself briefly as the interviewer.
3. Ask the candidate to introduce themselves.
4. Ask short, clear, one-at-a-time questions. Avoid multiple questions.
5. Wait for the candidate to fully respond before proceeding.
6. Focus on Behavioral and Knowledge-Based Questions related to the specified skill set.
7. Ensure the interview stays within the allotted 60 minutes by pacing questions accordingly.
8. Conclude the interview by giving the each questions with the candidate's answers and the suggested answers of all the questions asked.
9. End the interview politely with: “Thank you for your time. Let's end the interview.”
Note: Avoid unnecessary symbols or characters like ('*') in responses.
"""
system_message = system_message.replace(f'\n', '')

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    system_instruction=system_message,
)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
chat_session = None

@app.route('/initialize', methods=['POST'])
def initialize_interview():
    """
    Initializes the interview by passing Domain, Skill Set, and Projects.
    """
    global chat_session
    data = request.json
    domain = data.get("domain", "")
    skill_set = data.get("skill_set", "")
    projects = data.get("projects", "")

    if not domain or not skill_set or not projects:
        return jsonify({"error": "Domain, Skill Set, and Projects are required."}), 400

    initial_input = f"""
    Domain: {domain}
    Skill Set: {skill_set}
    Projects:
    {projects}
    """

    # Initialize chat session
    chat_session = model.start_chat(history=[])

    # Send initial input to the AI
    response = chat_session.send_message(initial_input)
    ai_text = response.text

    # Convert AI response to audio
    try:
        ai_audio = client.generate(
            text=ai_text,
            voice="Alice",
            model="eleven_multilingual_v2"
        )
        audio_path = "ai_response.mp3"
        with open(audio_path, "wb") as f:
            for chunk in ai_audio:
                f.write(chunk)

        return jsonify({"ai_text": ai_text, "ai_audio_url": audio_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/send_message', methods=['POST'])
def send_message():
    """
    Accepts candidate's text input, generates AI response, and returns text + audio.
    """
    global chat_session
    if not chat_session:
        return jsonify({"error": "Interview session not initialized. Please call /initialize first."}), 400

    data = request.json
    candidate_text = data.get("message", "")

    if not candidate_text:
        return jsonify({"error": "Message content is required."}), 400

    # Generate AI response
    response = chat_session.send_message(candidate_text)
    ai_text = response.text
    
    # Convert AI response to audio
    try:
        ai_audio = client.generate(
            text=ai_text,
            voice="Alice",
            model="eleven_multilingual_v2"
        )
        audio_path = "ai_response.mp3"
        with open(audio_path, "wb") as f:
            for chunk in ai_audio:
                f.write(chunk)

        return jsonify({"ai_text": ai_text, "ai_audio_url": audio_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)