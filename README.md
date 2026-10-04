# EDXSO — AI Interview Accelerator

A working AI-powered interview preparation prototype built for Assignment 3.

## What it implements

- JD paste/upload: PDF, DOCX, TXT
- Resume paste/upload: PDF, DOCX, TXT
- Role analysis
- Candidate-vs-JD analysis
- Transparent Job Fit score
- Three interview levels:
  - Screening
  - Competency
  - Deep-Dive
- Personalized questions using the supplied JD and resume
- Adaptive follow-up questions based on the previous answer
- Browser voice input using Web Speech API
- Text-to-speech for interviewer questions
- Answer evaluation
- Overall interview score
- Competency scores
- Question-level feedback
- Strengths
- Weaknesses
- Preparation gaps
- Interview readiness assessment
- JSON report download

## Architecture

```text
                 ┌─────────────────────┐
                 │ JD + Resume Input   │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Document Extraction │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Role/Candidate AI   │
                 │ Analysis             │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Job Fit Engine      │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Adaptive Interview  │
                 │ Planner              │
                 └──────────┬──────────┘
                            ↓
          ┌─────────────────┴──────────────────┐
          ↓                                    ↓
   Browser TTS                         Browser Speech-to-Text
   AI question                          Candidate answer
          └─────────────────┬──────────────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Answer Evaluator    │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Next Question       │
                 │ / Follow-up         │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Performance Report  │
                 └─────────────────────┘
```

## AI modes

### Demo mode
No API key required. The app uses deterministic analysis/evaluation so the complete product can be demonstrated locally.

### Gemini mode
Set:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```

### Ollama mode
Install Ollama and pull a local model, then set:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```

## Run locally

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local Streamlit URL.

## Voice

The prototype uses the browser's Web Speech API for speech recognition and SpeechSynthesis for interviewer audio. Chrome/Edge are recommended. A normal text field remains available as a reliable fallback.

## Deployment

The easiest deployment target is Streamlit Community Cloud.

1. Push this folder to GitHub.
2. Create a Streamlit deployment.
3. Set the main file to `app.py`.
4. Add `GEMINI_API_KEY` and `LLM_PROVIDER=gemini` as secrets if using Gemini.
5. Deploy.

## Demo flow

For the recorded demo:

1. Open the application.
2. Paste/upload an AI Engineer Intern JD.
3. Upload/paste the candidate resume.
4. Run analysis.
5. Show role requirements.
6. Show Job Fit and candidate gaps.
7. Start the interview.
8. Use the microphone for an answer.
9. Show the transcript.
10. Submit a weak/vague answer once to demonstrate adaptive follow-up.
11. Complete the three levels.
12. Show the final competency report.
13. Show preparation gaps and readiness.
14. Download the JSON report.

## Important implementation note

The Job Fit heuristic in Demo mode is intentionally transparent: matched identified JD skills divided by identified JD skills. When an LLM provider is configured, semantic comparison and evaluation are handled by the LLM prompts. This keeps the demo functional without an API key while allowing a richer AI experience for deployment.
