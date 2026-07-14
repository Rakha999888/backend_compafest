# Compafest Backend API

Backend project template powered by **Python 3.12**, **FastAPI**, **Pydantic v2**, and **Docker**.

## Project Structure

```text
backend/
│
├── app/
│   ├── main.py        # Entrypoint for FastAPI
│   ├── routes/        # Route controllers
│   ├── services/      # Business logic services
│   ├── schemas/       # Pydantic schemas (request/response validation)
│   ├── data/          # Databases, migrations, or local storage
│   ├── utils/         # Helper functions and utilities
│   └── config/        # Environment configurations and settings
│
├── requirements.txt   # Python dependency list
├── Dockerfile         # App Docker file
├── docker-compose.yml # Dev/production orchestration file
└── README.md          # Project guide
```

## Setup & Running Locally

### Prerequisites

Ensure you have Python 3.12 installed.

### 1. Manual Setup (Without Docker)

From the `backend/` directory:

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   - **Windows (CMD):** `.\venv\Scripts\activate.bat`
   - **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
   - **Linux/macOS:** `source venv/bin/activate`

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run development server:**
   ```bash
   uvicorn app.main:app --reload
   ```

5. Access Swagger API documentation at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Running with Docker Compose

1. **Start the containers:**
   ```bash
   docker compose up
   ```
   *(Use `docker compose up --build` if you have changed configuration dependencies or need to rebuild the image).*

2. Access the server at [http://localhost:8000/](http://localhost:8000/) and Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## Available Endpoints

- **Root API Address**: [http://localhost:8000/](http://localhost:8000/)
- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: `GET /health` - Checks the API status and details.
- **Dataset Catalog**: `GET /demo/list` - Lists available dataset names and IDs.
- **Get Dataset Log**: `GET /demo/{dataset_id}` - Fetches transaction records from a specific dataset (`small`, `medium`, `large`).
- **Get Recommendations**: `POST /recommend` - Evaluates the dataset and generates optimized warehouse slotting suggestions and picking paths.

