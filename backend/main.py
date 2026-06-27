import os
import sqlite3
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from compliance_engine import run_compliance_pipeline, DB_PATH

app = FastAPI(
    title="SLA-Guard Compliance API",
    description="FastAPI backend for automated service level agreement compliance auditing and multi-agent consensus."
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.get("/api/customers")
def get_customers():
    """
    Fetch all customer records with subscription tiers to populate dashboard controls.
    """
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database file not found.")
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, c.email, c.tier, s.plan_name, s.sla_uptime_percent, s.max_monthly_refund_cap 
            FROM customers c
            JOIN subscriptions s ON c.id = s.customer_id
        """)
        rows = cursor.fetchall()
        conn.close()
        
        customers = []
        for row in rows:
            customers.append({
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "tier": row[3],
                "plan_name": row[4],
                "sla_uptime_percent": row[5],
                "max_monthly_refund_cap": row[6]
            })
        return customers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

@app.get("/api/customer-history/{customer_id}")
def get_customer_history(customer_id: int):
    """
    Fetch previous ticket history and refund approvals for a customer.
    """
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database file not found.")
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT issue_type, requested_refund, approved_refund, date 
            FROM tickets_history 
            WHERE customer_id = ?
        """, (customer_id,))
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                "issue_type": row[0],
                "requested_refund": row[1],
                "approved_refund": row[2],
                "date": row[3]
            })
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query ticket history: {str(e)}")

@app.post("/api/process-ticket")
def process_ticket(
    payload: dict = Body(...)
):
    """
    Process a customer support ticket through the multi-agent consensus verification pipeline.
    """
    ticket_text = payload.get("ticket_text")
    customer_id_or_email = payload.get("customer_id_or_email")
    far_threshold = float(payload.get("far_threshold", 0.8))
    frr_threshold = float(payload.get("frr_threshold", 0.2))
    
    if not ticket_text or not customer_id_or_email:
        raise HTTPException(status_code=400, detail="Missing required parameters: ticket_text and customer_id_or_email.")
        
    # Run the consensus auditing pipeline
    pipeline_result = run_compliance_pipeline(
        ticket_text=ticket_text,
        customer_id_or_email=customer_id_or_email,
        far_threshold=far_threshold,
        frr_threshold=frr_threshold
    )
    
    if not pipeline_result["success"]:
        raise HTTPException(status_code=500, detail=pipeline_result["error"])
        
    return pipeline_result

# ---------------------------------------------------------
# Static File Mounts
# ---------------------------------------------------------
STATIC_DIR = "/Users/saeedanwar/Desktop/saeed/project/sla_guard/static"
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount the static directory to serve HTML/CSS/JS at root (/)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Launch uvicorn on port 8080 as requested
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"Launching SLA-Guard Compliance API on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
