# SensibleForms Frontend (Example)

This is a minimal Vite + React UI that demonstrates how the three domain endpoints
communicate with the backend.

## Run (end-to-end)

### 1) Backend (FastAPI)

From the repo root:

1. Create/activate a Python virtual environment.
2. Install backend dependencies:
    - `pip install -r requirements.txt`
3. (Optional) Configure LLM provider(s):
    - Create a `.env` file in the repo root.
    - Add **one** of the following, depending on which provider you want to use:
       - `OPENAI_API_KEY=...` (for OpenAI-compatible endpoints -- including OwlChat API, which can provide Gemini models...)
       - `GOOGLE_API_KEY=...` (for Gemini models accessed directly through Google AI Studio.)
       - (You may set both if your backend is configured to support multiple providers.)
4. Optional: enable Google Forms API calls. 
  - Place `client_secrets.json` into backend directory
5. Start the API (pick one):
  - From repo root: `uvicorn app.main:app --app-dir backend --reload`
  - From `backend/`: `uvicorn app.main:app --reload`

### 2) Frontend (Vite + React)

1. `cd frontend`
2. Install deps: `npm install`
3. Start dev server: `npm run dev`

By default, the frontend calls the backend at `http://localhost:8000`.
To override the backend URL, set `VITE_API_BASE_URL` in an environmental file in the frontend.

Windows note: if `npm install` is blocked by PowerShell execution policy, you can allow scripts for the current session:

- `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

## What this is

- A simple, intentionally non-production single-page-app example of the data flow.
- Chat-style interfaces for Question Generation and Analysis Assistant.
- Form Deployment is upload-first and then chat-based for status/feedback.

## Endpoints this UI calls

- `POST /analysis/`
- `POST /question-generation/`
- `POST /form-deployment/deploy`
- `POST /form-deployment/chat`
- `GET /form-deployment/retrieve?formId=${formId}`
