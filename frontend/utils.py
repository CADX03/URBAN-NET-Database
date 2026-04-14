import tempfile
import json
import requests

def save_uploaded_file(uploaded_file, suffix=".json"):
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    return None

def load_json_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def check_health_db():
    results = {}
    # Changed QuantumLeap URL to /version
    for name, url in [("Orion-LD", "http://orion:1026/ngsi-ld/v1/types"),
                      ("QuantumLeap", "http://quantumleap:8668/version")]: 
        try:
            r = requests.get(url, timeout=3)
            # Optional: added the status code to the error for easier debugging
            results[name] = "🟢 Reachable" if r.ok else f"🔴 {r.status_code}"
        except Exception:
            results[name] = "🔴 Unreachable"
    return results