# SLA-Guard Project Contract & Troubleshooting History

This document serves as the central context file for the **SLA-Guard Compliance Control Room** project. It outlines the scope, architectures, technical details, and troubleshooting notes for developer references.

---

## 🔍 Project Overview & Architecture
SLA-Guard is a multi-agent consensus and grounding engine designed to audit and verify automated customer service responses. It prevents LLMs from making incorrect refund promises, quoting wrong SLAs, or allowing prompt injections.

### 1. Verification Council Components
*   **Llama-3-8B Generator (Text-to-SQL & Response Generator):** Drafts the initial support response based on the query and customer context.
*   **SQL Account Verifier (Structured SQLite Ledger):** Checks the database row for the customer's actual plan tier, SLA target, and max monthly refund cap.
*   **Mistral-7B Guardrail Inspector (Safety Auditor):** Runs a security audit to catch prompt injections, swear words, and calculate if the draft refund exceeds the SQL cap.
*   **Auto-Refinement Loop:** If consensus fails, feeds compiler errors back to Llama-3 for up to 3 self-healing iterations.

### 2. Deployment Architecture
*   **Frontend:** HTML5/CSS3/JavaScript operations panel with animated compliance gauges and tabbed logs.
*   **Backend:** FastAPI server serving REST APIs and mounting static files.
*   **Local Simulation Fallback:** If Hugging Face API keys are missing, the backend runs a rule-based simulation of the LLMs to ensure the dashboard remains 100% functional and interactive.

---

## 🛠️ Issues Faced & Solved

### 1. Large Model Storage vs. Local Space Constraint
*   **Issue:** Running Llama-3 and Mistral locally requires downloading 15+ GB of model weights, contradicting the user's goal of keeping minimal files on the Mac.
*   **Solution:** Built a serverless API connector that routes LLM calls to Hugging Face serverless endpoints. Additionally, created a local high-quality rule-based fallback simulator so the dashboard can run immediately upon cloning with zero local weights downloaded.

### 2. FastAPI Static Files Mount Conflicts
*   **Issue:** Mounting StaticFiles at root (`/`) can swallow specific subpaths like `/api/process-ticket` if not mounted in the correct order.
*   **Solution:** Declared all REST API endpoints (`/api/customers`, `/api/process-ticket`) *before* mounting `StaticFiles(directory=STATIC_DIR, html=True)` at `/`.

### 3. SVG Gauge Stroke-Dashoffset Calculations
*   **Issue:** Animating SVG stroke lines requires precise stroke-dasharray circumferences. For a radius of 40, the circumference is $2 \cdot \pi \cdot 40 \approx 251.2$.
*   **Solution:** Implemented the calculation dynamically in `app.js` using:
    $$\text{offset} = 251.2 - \left(251.2 \times \frac{\text{percentage}}{100}\right)$$
    and updated the `stroke-dashoffset` style property.
