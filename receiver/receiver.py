from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/notify', methods=['POST'])
def receive_notification():
    data = request.json
    print("\n🔔 --- REAL-TIME UPDATE RECEIVED --- 🔔", flush=True)
    print(json.dumps(data, indent=2), flush=True)
    return "Notification received", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)