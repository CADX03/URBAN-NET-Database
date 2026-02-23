import json
import requests

def send_notification_to_quantumleap(file_path):
    # The QuantumLeap notify endpoint from your curl command
    url = 'http://quantumleap:8668/v2/notify'
    
    # The headers ensuring the payload is treated as JSON
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        # 1. Read the JSON file
        with open(file_path, 'r') as file:
            payload = json.load(file)
            
        # 2. Send the POST request to QuantumLeap
        response = requests.post(url, headers=headers, json=payload)
        
        # 3. Check the response
        # QuantumLeap usually returns 200 OK or 201 Created on success
        if response.status_code in [200, 201]:
            print(f"Success! Data sent to QuantumLeap/TimescaleDB. Status Code: {response.status_code}")
        else:
            print(f"Failed to send data. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' does not contain valid JSON.")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to QuantumLeap: {e}")

if __name__ == "__main__":
    # Point the function to your newly created JSON file
    send_notification_to_quantumleap('./../data/notification_data.json')