# How to Run the Math OCR Service

## Prerequisites
- Python 3.12+ installed
- All dependencies from `requirements.txt`

## Project Structure

```
math-ocr-service/
├── app/
│   ├── __init__.py
│   └── main.py            # FastAPI app + OCR pipeline
├── requirements.txt
└── README.md
```

## Installation Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** Some packages (like `tokenizers`) may require Rust. If you encounter issues:
- Install Rust from https://rustup.rs/
- Or use pre-built wheels: `pip install tokenizers --only-binary :all:`

### 2. Run the Server

**Option A: Direct Python execution**
```bash
python app/main.py
```

**Option B: Using uvicorn directly**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8501
```

**Option C: Using Python module**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8501
```

## Server Information
- **Host:** 0.0.0.0 (accessible from all network interfaces)
- **Port:** 8501
- **Health Check:** http://localhost:8501/health
- **API Docs:** http://localhost:8501/docs (Swagger UI)
- **Alternative Docs:** http://localhost:8501/redoc

## API Endpoints

### Health Check
```bash
GET http://localhost:8501/health
```

### OCR Endpoint
```bash
POST http://localhost:8501/ocr
Content-Type: multipart/form-data

Parameters:
- file: Image file (required)
- strategy: "hybrid" | "text_only" | "formula_only" | "auto" (default: "hybrid")
- language: Language code (default: "en")
```

## Example Usage

### Using curl:
```bash
curl -X POST "http://localhost:8501/ocr" \
  -F "file=@your_image.png" \
  -F "strategy=hybrid"
```

### Using Python requests:
```python
import requests

url = "http://localhost:8501/ocr"
files = {"file": open("math_problem.png", "rb")}
data = {"strategy": "hybrid"}

response = requests.post(url, files=files, data=data)
print(response.json())
```

## Troubleshooting

1. **ModuleNotFoundError**: Install missing dependencies with `pip install <package-name>`
2. **Port already in use**: Change the port in `app/main.py` or use: `uvicorn app.main:app --port 8502`
3. **Model loading errors**: First run may download model files - wait for completion
4. **Memory issues**: Some OCR models are large - ensure sufficient RAM

