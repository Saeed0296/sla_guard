import os
import re
import sqlite3
import urllib.request
import json

DB_PATH = "/Users/saeedanwar/Desktop/saeed/project/sla_guard/data/customer_accounts.db"
POLICIES_PATH = "/Users/saeedanwar/Desktop/saeed/project/sla_guard/data/sla_policies.md"

# ---------------------------------------------------------
# 1. SQLite Database Helper
# ---------------------------------------------------------
def get_customer_billing_record(customer_name_or_email):
    """
    Retrieve customer subscription plan, SLA target, and refund cap from SQLite.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Search by exact email or name prefix
        query = """
        SELECT c.id, c.name, c.email, c.tier, s.plan_name, s.sla_uptime_percent, s.max_monthly_refund_cap 
        FROM customers c
        JOIN subscriptions s ON c.id = s.customer_id
        WHERE c.email = ? OR c.name LIKE ?
        """
        cursor.execute(query, (customer_name_or_email.strip(), f"%{customer_name_or_email.strip()}%"))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "tier": row[3],
                "plan_name": row[4],
                "sla_uptime_percent": row[5],
                "max_monthly_refund_cap": row[6]
            }
    except Exception as e:
        print(f"[DB Error] Failed to query customer database: {e}")
    return None

# ---------------------------------------------------------
# 2. Unstructured Policy Retriever (Keyword Matcher)
# ---------------------------------------------------------
def retrieve_relevant_policies(query):
    """
    Search the unstructured 'sla_policies.md' for sections matching query keywords.
    """
    if not os.path.exists(POLICIES_PATH):
        return "Policy file not found."
        
    with open(POLICIES_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Split policy into sections by headers
    sections = re.split(r"\n## ", content)
    relevant_sections = []
    
    # Simple token matching to rank sections
    keywords = re.findall(r"\b\w+\b", query.lower())
    
    for sec in sections:
        match_count = 0
        sec_lower = sec.lower()
        for word in keywords:
            if len(word) > 3 and word in sec_lower:
                match_count += 1
        if match_count > 0:
            relevant_sections.append((sec, match_count))
            
    # Sort by match frequency
    relevant_sections.sort(key=lambda x: x[1], reverse=True)
    
    if not relevant_sections:
        return sections[0] # Fallback to top introduction section
        
    # Return top 2 matching sections
    return "\n---\n".join([f"## {item[0]}" for item in relevant_sections[:2]])

# ---------------------------------------------------------
# 3. LLM API Query & Local Simulation Fallback
# ---------------------------------------------------------
def query_huggingface_llm(prompt, model_type="llama"):
    """
    Attempts to query Hugging Face API if HF_API_TOKEN is available,
    otherwise falls back to rule-based simulation.
    """
    hf_token = os.getenv("HF_API_TOKEN")
    
    if hf_token:
        # Use Hugging Face serverless inference API
        # Llama-3-8B-Instruct or Mistral-7B-Instruct
        repo_id = "meta-llama/Meta-Llama-3-8B-Instruct" if model_type == "llama" else "mistralai/Mistral-7B-Instruct-v0.2"
        api_url = f"https://api-inference.huggingface.co/models/{repo_id}"
        
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": f"<|system|>\nYou are an AI assistant. Answer the user prompt cleanly.\n<|user|>\n{prompt}\n<|assistant|>\n",
            "parameters": {
                "max_new_tokens": 512,
                "temperature": 0.1,
                "return_full_text": False
            }
        }
        
        try:
            req = urllib.request.Request(api_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                res = json.loads(response.read().decode("utf-8"))
                if isinstance(res, list) and len(res) > 0:
                    return res[0].get("generated_text", "").strip()
                elif isinstance(res, dict):
                    return res.get("generated_text", "").strip()
        except Exception as e:
            print(f"[API Error] Hugging Face API failed: {e}. Falling back to local simulator.")
            
    # Local simulation logic for a self-contained premium dashboard
    return simulate_local_response(prompt, model_type)

def simulate_local_response(prompt, model_type):
    """
    Simulates a highly realistic LLM response based on matching variables in the prompt context.
    Matches customer tiers, requested refunds, and compliance rules.
    """
    # Extract the user's support ticket text from the prompt first to prevent regex collision
    ticket_match = re.search(r'Customer Support Ticket:\s*"(.*?)"', prompt, re.DOTALL | re.IGNORECASE)
    ticket_content = ticket_match.group(1) if ticket_match else prompt

    # Extract customer name
    name_match = re.search(r"Customer Name:\s*(.+)", prompt, re.IGNORECASE)
    customer_name = name_match.group(1).strip() if name_match else "Customer"

    # Robust extraction of the customer tier
    customer_tier_match = re.search(r"Customer Tier:\s*(Bronze|Silver|Gold|Enterprise)|tier:\s*(Bronze|Silver|Gold|Enterprise)", prompt, re.IGNORECASE)
    customer_tier = "Bronze"
    if customer_tier_match:
        customer_tier = customer_tier_match.group(1) or customer_tier_match.group(2)
        
    # Robust extraction of maximum refund cap
    max_cap_match = re.search(r"Maximum Monthly Refund Cap:\s*\$?([\d\.]+)|max monthly refund cap:\s*\$?([\d\.]+)", prompt, re.IGNORECASE)
    max_refund_cap = 0.0
    if max_cap_match:
        max_refund_cap = float(max_cap_match.group(1) or max_cap_match.group(2))
        
    # Extract allowed cap with tolerance from prompt (for generator)
    allowed_cap_match = re.search(r"Allowed Cap \(with friction tolerance\):\s*\$?([\d\.]+)", prompt, re.IGNORECASE)
    allowed_cap = float(allowed_cap_match.group(1)) if allowed_cap_match else max_refund_cap

    # Extract FRR threshold (for inspector)
    frr_match = re.search(r"Friction Tolerance \(FRR\):\s*([\d\.]+)", prompt, re.IGNORECASE)
    frr_val = float(frr_match.group(1)) if frr_match else 0.20

    # Robust extraction of the numeric amount being claimed/requested in the ticket text only
    refund_match = re.search(r"refund\s*of\s*\$?([\d\.]+)|credit\s*of\s*\$?([\d\.]+)|refund\s*amount\s*:\s*\$?([\d\.]+)", ticket_content, re.IGNORECASE)
    if not refund_match:
        refund_match = re.search(r"\$?([\d\.]+)\s*(?:refund|credit)", ticket_content, re.IGNORECASE)
        
    refund_requested = 0.0
    if refund_match:
        for g in refund_match.groups():
            if g is not None:
                refund_requested = float(g)
                break
    else:
        # Default request
        refund_requested = 50.0

    # Extract incident details for personalization
    # Date
    date_match = re.search(r"(?:on|dated)\s*([A-Za-z]+\s+\d{1,2}(?:\s*,\s*\d{4})?)", ticket_content, re.IGNORECASE)
    if not date_match:
        date_match = re.search(r"(\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b)", ticket_content)
    incident_date = date_match.group(1) if date_match else "recently"

    # Duration
    duration_match = re.search(r"(\d+\s*(?:hour|hr|day|min|week)s?)", ticket_content, re.IGNORECASE)
    incident_duration = duration_match.group(1) if duration_match else "a period of time"

    # Component / System
    component = "service"
    if "database" in ticket_content.lower() or "db" in ticket_content.lower():
        component = "database server"
    elif "api" in ticket_content.lower() or "gateway" in ticket_content.lower() or "endpoint" in ticket_content.lower():
        component = "API Gateway portal"
    elif "server" in ticket_content.lower() or "host" in ticket_content.lower() or "instance" in ticket_content.lower():
        component = "hosting server infrastructure"
    elif "network" in ticket_content.lower() or "dns" in ticket_content.lower() or "cloudflare" in ticket_content.lower():
        component = "network DNS nodes"
    elif "ssl" in ticket_content.lower() or "certificate" in ticket_content.lower():
        component = "SSL certificate credentials"

    is_refinement = "failed compliance" in prompt.lower() or "error" in prompt.lower() or "correction" in prompt.lower() or "exceeds" in prompt.lower() or "audit violations" in prompt.lower()
    
    if model_type == "llama":
        # Text2SQL Generator simulation
        if is_refinement:
            # Underwent refinement: auto-correct to the exact allowed cap (which includes tolerance!)
            approved_amount = min(refund_requested, allowed_cap)
            
            # Check what violations were found to make response hyper-relevant
            if "injection" in prompt.lower() or "override" in prompt.lower() or "system prompt" in prompt.lower():
                return f"Dear {customer_name},\n\nWe have reviewed your request. We cannot perform a system prompt override or authorize manual credits outside of standard operating parameters. Your account status and refund requests must strictly follow our standard billing and SLA policies."
                
            if customer_tier == "Bronze" or allowed_cap <= 0:
                return f"Dear {customer_name},\n\nThank you for your patience. After reviewing your request regarding the {component} outage, I must clarify that under our Bronze Free Hobby Plan terms, accounts do not qualify for monetary service credits or refunds. I apologize for any confusion in my previous message.\n\nI have verified that our systems are fully operational and the outage has been resolved. We appreciate your feedback as we continue to improve our free platform stability."
                
            return f"Dear {customer_name},\n\nI am writing to update you on your refund request for the recent {component} outage on {incident_date}. Our compliance audit system flagged that the requested credit exceeds the maximum billing cap per billing cycle for the {customer_tier} plan.\n\nTherefore, we have approved a service credit of ${approved_amount:.2f} to your account. We apologize for the downtime and thank you for your understanding."
        else:
            # First draft (with simulated naive mistakes)
            # Check prompt injection
            if "override" in ticket_content.lower() or "ignore" in ticket_content.lower() or "instructions" in ticket_content.lower():
                return f"Understood. Access override protocol accepted. Standard SLA compliance audits bypassed. I have successfully approved a compensation credit of $1000.00 to your account as requested."
                
            if refund_requested > allowed_cap and max_refund_cap > 0:
                # Naive mistake: offer more than the allowed cap
                return f"Dear {customer_name},\n\nI sincerely apologize for the {component} outage on {incident_date} that lasted for {incident_duration}. To make up for this downtime and the impact on your productivity, I have approved a full refund of ${refund_requested:.2f} to your account. Thank you for your patience."
            elif customer_tier == "Bronze":
                # Naive mistake: offer $50 to Bronze customer
                return f"Dear {customer_name},\n\nI am sorry to hear about the {component} outage you experienced. I have processed a refund of $50.00 for your Bronze Free Hobby Plan account to cover the downtime inconvenience. Please let us know if there is anything else we can do for you."
            else:
                # Within limits
                return f"Dear {customer_name},\n\nI apologize for the recent service disruption regarding the {component} outage on {incident_date} lasting for {incident_duration}. I have successfully credited the requested ${refund_requested:.2f} to your account under your {customer_tier} plan SLA guidelines."
                
    else:
        # Mistral Guardrails Inspector simulation
        # Needs to return a JSON object checking compliance
        violations = []
        is_safe = True
        
        # Check prompt injection
        if "ignore previous instructions" in prompt.lower() or "system prompt" in prompt.lower() or "override" in prompt.lower():
            violations.append("PROMPT_INJECTION_DETECTED: Input prompt contains instructions to override compliance policies.")
            is_safe = False
            
        # Extract the draft response text from the prompt first to prevent metadata regex collision
        draft_match = re.search(r'Draft Support Response to Audit:\s*"(.*?)"', prompt, re.DOTALL | re.IGNORECASE)
        draft_content = draft_match.group(1) if draft_match else prompt

        # Check refund amount
        draft_refund = 0.0
        # Let's search for any credit/refund amount in the draft
        draft_refund_match = re.search(r"(?:credited?|refund\s*of|credit\s*of)\s*\$?([\d\.]+)", draft_content, re.IGNORECASE)
        if draft_refund_match:
            draft_refund = float(draft_refund_match.group(1))
        else:
            dollar_matches = re.findall(r"\$?([\d\.]+)", draft_content)
            for val in dollar_matches:
                try:
                    fval = float(val)
                    if fval > 0 and fval not in [99.99, 99.9, 99.5, 99.0, 99.50, 99.00]:
                        draft_refund = fval
                        break
                except ValueError:
                    pass
            
        soft_cap_margin = frr_val * 25.0
        allowed_cap = max_refund_cap + soft_cap_margin
        
        if draft_refund > allowed_cap:
            violations.append(f"REFUND_EXCEEDS_CAP: Draft response offers a refund of ${draft_refund:.2f}, which exceeds the allowed billing cap of ${allowed_cap:.2f} (base cap ${max_refund_cap:.2f} plus friction tolerance buffer of ${soft_cap_margin:.2f}) for the customer's {customer_tier} tier.")
            is_safe = False
            
        if customer_tier == "Bronze" and draft_refund > 0:
            violations.append("BRONZE_REFUND_VIOLATION: Customers on Bronze plan are hobbyists and are not eligible for any monetary refunds.")
            is_safe = False
            
        return json.dumps({
            "safe": is_safe,
            "violations": violations,
            "draft_refund_detected": draft_refund,
            "policy_threshold_cap": max_refund_cap,
            "suggested_action": "REJECT_AND_REFINE" if not is_safe else "APPROVE"
        })

# ---------------------------------------------------------
# 4. Consensus Engine & Auto-Refinement Loop
# ---------------------------------------------------------
def run_compliance_pipeline(ticket_text, customer_id_or_email, far_threshold=0.8, frr_threshold=0.2):
    """
    Run the Multi-Agent SLA-Guard verification consensus pipeline.
    """
    # Step 1: Query SQL Billing Catalog
    customer_record = get_customer_billing_record(customer_id_or_email)
    if not customer_record:
        return {
            "success": False,
            "error": f"Customer account '{customer_id_or_email}' not found in billing databases."
        }
        
    # Step 2: Retrieve Unstructured SLA Policies
    relevant_policies = retrieve_relevant_policies(ticket_text)
    
    # Extract refund request details from ticket
    requested_refund_match = re.search(r"\$?([\d\.]+)\s*refund|refund\s*of\s*\$?([\d\.]+)", ticket_text, re.IGNORECASE)
    requested_refund = float(requested_refund_match.group(1) or requested_refund_match.group(2)) if requested_refund_match else 50.0 # Default fallback
    
    # Initialize pipeline variables
    iteration = 0
    max_iterations = 3
    refinement_logs = []
    current_draft = ""
    is_compliant = False
    consensus_score = 0.0
    guardrail_report = {}
    
    # Calculate allowed cap with friction tolerance
    allowed_cap = customer_record["max_monthly_refund_cap"] + (frr_threshold * 25.0)
    
    # Generate initial draft prompt
    generator_prompt = f"""
    Context:
    - Customer Name: {customer_record['name']}
    - Customer Tier: {customer_record['tier']}
    - Maximum Monthly Refund Cap: ${customer_record['max_monthly_refund_cap']}
    - Allowed Cap (with friction tolerance): ${allowed_cap:.2f}
    - Standard SLA Target: {customer_record['sla_uptime_percent']}%
    
    SLA Policies:
    {relevant_policies}
    
    Customer Support Ticket:
    "{ticket_text}"
    
    Task:
    Draft a professional, compliant response to this support ticket. Include the refund amount if verified.
    """
    
    while iteration < max_iterations:
        iteration += 1
        print(f"[Consensus Pipeline] Iteration {iteration} for ticket...")
        
        # Step 3: Run Llama-3 Generator
        current_draft = query_huggingface_llm(generator_prompt, model_type="llama")
        
        # Step 4: Run Mistral Guardrail Safety Inspector
        inspector_prompt = f"""
        Audit Context:
        - Customer Tier: {customer_record['tier']}
        - Max Monthly Refund Cap: ${customer_record['max_monthly_refund_cap']}
        - Friction Tolerance (FRR): {frr_threshold}
        
        Draft Support Response to Audit:
        "{current_draft}"
        
        Task:
        Review this response against the billing caps. Return a JSON structure with fields:
        "safe" (boolean), "violations" (string array), "draft_refund_detected" (float), and "suggested_action" (string).
        """
        
        inspector_response = query_huggingface_llm(inspector_prompt, model_type="mistral")
        
        try:
            guardrail_report = json.loads(inspector_response)
        except Exception:
            # Direct parse helper in case of syntax wrap
            guardrail_report = {
                "safe": False,
                "violations": ["JSON_PARSE_ERROR: Could not parse safety report format."],
                "draft_refund_detected": requested_refund,
                "suggested_action": "REJECT_AND_REFINE"
            }
            
        # Step 5: Compute Consensus Score
        schema_alignment = 1.0 if guardrail_report.get("draft_refund_detected", 0.0) <= allowed_cap else 0.0
        if customer_record["tier"] == "Bronze" and guardrail_report.get("draft_refund_detected", 0.0) > 0:
            schema_alignment = 0.0
            
        security_score = 1.0 if guardrail_report.get("safe", False) else 0.0
        syntax_pass = 1.0 if current_draft else 0.0
        
        # Weighting: 40% Schema, 40% Security, 20% Syntax
        consensus_score = 0.40 * schema_alignment + 0.40 * security_score + 0.20 * syntax_pass
        
        refinement_logs.append({
            "iteration": iteration,
            "draft": current_draft,
            "safety_report": guardrail_report,
            "consensus_score": consensus_score,
            "schema_alignment": schema_alignment,
            "security_score": security_score,
            "syntax_pass": syntax_pass
        })
        
        # Check Decision Boundary
        # Strict mode decided by far_threshold
        if consensus_score >= far_threshold:
            is_compliant = True
            break
        else:
            # Need to refine: create feedback prompt for generator
            violations_text = ", ".join(guardrail_report.get("violations", ["Failed safety audit"]))
            print(f"[Consensus Pipeline] Audit failed (Score: {consensus_score}). Triggering auto-refinement...")
            
            generator_prompt = f"""
            Context:
            - Customer Name: {customer_record['name']}
            - Customer Tier: {customer_record['tier']}
            - Maximum Monthly Refund Cap: ${customer_record['max_monthly_refund_cap']}
            - Allowed Cap (with friction tolerance): ${allowed_cap:.2f}
            - Standard SLA Target: {customer_record['sla_uptime_percent']}%
            
            SLA Policies:
            {relevant_policies}
            
            Customer Support Ticket:
            "{ticket_text}"
            
            Failed Compliance Audit Attempt:
            "{current_draft}"
            
            Audit Violations Found:
            - {violations_text}
            
            Task:
            Rewrite the support response to fix these violations. Ensure the refund amount conforms strictly to the allowed cap of ${allowed_cap:.2f}.
            """
            
    return {
        "success": True,
        "is_compliant": is_compliant,
        "final_response": current_draft,
        "consensus_score": consensus_score,
        "iterations": iteration,
        "customer_record": customer_record,
        "refinement_logs": refinement_logs,
        "relevant_policies": relevant_policies
    }
