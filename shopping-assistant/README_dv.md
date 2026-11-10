# How to run app
Will need two terminals running, one for the backend and one the frontend
- ## First-time setup
   - Move into each directory and pip install requirements.txt for first time set up
   - Get your own google gemini API key
   - Create a .env file with GEMINI_API_KEY= and store key here (dont push to github)
   - pip install --upgrade google-genai python-dotenv
- ## Every-other time
   - In frontend terminal run python -m streamlit run app.py
   - In backend terminal run python -m uvicorn main:app --
                               
   
