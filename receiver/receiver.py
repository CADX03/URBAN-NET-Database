from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Variable to store the most recent payload
latest_payload = {}

@app.route('/notify', methods=['POST'])
def receive_notification():
    global latest_payload
    latest_payload = request.json
    
    print("\n🔔 --- REAL-TIME UPDATE RECEIVED --- 🔔", flush=True)
    print(json.dumps(latest_payload, indent=2), flush=True)
    
    return "Notification received", 200

# NEW: Streamlit will call this to get the data
@app.route('/latest', methods=['GET'])
def get_latest():
    return jsonify(latest_payload), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)