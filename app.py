import os
from flask import Flask, request, jsonify, render_template
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure Google Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    prompt_text = data.get('prompt')
    
    if not prompt_text:
        return jsonify({"error": "No prompt provided"}), 400
        
    if not API_KEY:
         return jsonify({"error": "API Key is missing. Please set GEMINI_API_KEY in the .env file."}), 500

    try:
        # Initialize client with the new google-genai SDK
        client = genai.Client(api_key=API_KEY)
        
        # Using gemini-2.5-flash which is the standard fast model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_text,
        )
        
        return jsonify({"result": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
