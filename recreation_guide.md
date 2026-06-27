# SLA-Guard - Local Reconstruction Guide

This guide describes how to run and deploy the **SLA-Guard Compliance Control Room** locally on your Mac.

---

## 🛠️ Step-by-Step Instructions

### Step 1: Clone the Codebase
If recreating, clone the codebase to your local workspace:
```bash
git clone https://github.com/Saeed0296/sla_guard.git
cd sla_guard
```

### Step 2: Set Up Virtual Environment & Install Dependencies
Isolate Python requirements:
```bash
# Create environment
python3 -m venv jupyter_env
source jupyter_env/bin/activate

# Install requirements
pip install --upgrade pip
pip install fastapi uvicorn pillow
```

### Step 3: Initialize the Database (Optional)
The database is already located under `data/customer_accounts.db`. If you need to re-initialize it:
```bash
python data/setup_database.py
```

### Step 4: Configure API Tokens (Optional)
If you want to use live Hugging Face Serverless APIs instead of the local simulator:
```bash
export HF_API_TOKEN="your_huggingface_write_token_here"
```

### Step 5: Launch the API Server & Dashboard
Run the FastAPI application from the project root:
```bash
bash run_server.sh
```
Uvicorn will spin up a local development server at: **`http://127.0.0.1:8080`**

Open **`http://127.0.0.1:8080`** in your web browser to access the control room dashboard.
