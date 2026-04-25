# <img src="frontend/src/assets/sensible-forms-icon.png" height=100> Sensible Forms

<br/>
<div align="center">
  <img src="https://img.shields.io/badge/Generative_AI-Lab-blueviolet?style=for-the-badge&logo=openai&logoColor=white" alt="Generative AI Lab" />
  <img src="https://img.shields.io/badge/OpenAI--Compatible_API-Supported-royalblue?style=for-the-badge&logo=&logoColor=white" alt="OpenAI-Compatible API Supported" />
  <img src="https://img.shields.io/badge/Gemini_API-Supported-royalblue?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Gemini API Supported" />
  <img src="https://img.shields.io/badge/MIT-License-darkgreen?style=for-the-badge" alt="License" />
</div>

---

## Overview

Sensible Forms is a generative AI system for academic researchers that streamlines the survey process. The system as deployed on the website does not require any specialized technical knowledge to use and will step the user through the process of creating, deploying, and analyzing a survey through Google Forms.

Sensible Forms uses Google Gemini via OwlChat OpenWebUI (an OpenAI-compatible API) with three customized bots: question generation, form deployment, and analysis assistance. All three bots are delivered through a website and they can be used together or separately. Users deploying their own version of Sensible Forms also have the option to use a Google Gemini API key if desired.

### Backend

  <img src="https://img.shields.io/badge/Python_3.14-midnightblue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.14" />
  <img src="https://img.shields.io/badge/FastAPI-midnightblue?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Pydantic-midnightblue?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic" />
  <img src="https://img.shields.io/badge/LangChain-midnightblue?style=for-the-badge&logo=langchain&logoColor=white" alt="LangChain" />
  <img src="https://img.shields.io/badge/pip-midnightblue?style=for-the-badge&logo=pip&logoColor=white" alt="pip" />


### Frontend

  <img src="https://img.shields.io/badge/React-maroon?style=for-the-badge&logo=react&logoColor=white" alt="React" />
  <img src="https://img.shields.io/badge/JavaScript-maroon?style=for-the-badge&logo=javascript&logoColor=white" alt="JavaScript" />
  <img src="https://img.shields.io/badge/HTML-maroon?style=for-the-badge&logo=html&logoColor=white" alt="HTML" />
  <img src="https://img.shields.io/badge/CSS-maroon?style=for-the-badge&logo=css&logoColor=white" alt="CSS" />
  <img src="https://img.shields.io/badge/npm-maroon?style=for-the-badge&logo=npm&logoColor=white" alt="npm" />

## Current Capabilities
### Question Generation
* Provide advice and recommendations for survey and interview questions
* Display questions in CSV format when requested
* Download a CSV with the requested questions

### Form Deployment
* Deploy a form on Google Forms from an uploaded CSV
* Provide the ID, Publisher link, and Responder link for the deployed Google Form
* Retrieve Google Forms responses from a Form ID (provided as a downloaded CSV)
* Explain the appropriate CSV format and how to correct any issues with an uploaded CSV

### Analysis Assistant
* Develop a data profile based on a CSV of uploaded responses
* Provide recommendations for analysis based on data provided
* Generate basic statistical insights

## Installation

### Configuration 
Sensible Forms can be configured using environment variables. We have included a .env_example file with an example of how to structure that.

A .env file will automatically be loaded from the working directory.

To allow for deployment on Google Forms, you must set up a client_secrets.json file with the appropriate information from Google to use OAuth. For more information, see Google's documentation: 
* [Using OAuth 2.0 to Access Google API](https://developers.google.com/identity/protocols/oauth2)
* [Using OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)


### How to Run

#### Backend
1. Create or activate a virtual environment.
```bash
.venv/Scripts/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Add the client_secrets.json file to the backend folder 
4. Start the API from the repo root:

```bash
uvicorn app.main:app --app-dir backend --reload
```

#### Frontend
Note: This must be in a new command line interface window.

1. Navigate to the frontend folder.
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the dev server:
```bash
npm run dev
```

4. Ensure backend is running on:
```bash
http://localhost:8000
```
or
```bash
http://127.0.0.1:8000
```

Alternatively, you can override the local hosts using the following environment variable:
```bash
VITE_API_BASE_URL
```

#### [Example Data Flow](./docs/example-data-flow.md)