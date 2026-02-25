import json
import requests

def send_data_to_broker(file_path):
    url = 'http://orion:1026/ngsi-ld/v1/entityOperations/upsert'
    
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        with open(file_path, 'r') as file:
            raw_payload = json.load(file)
            
        # Clean the payload before sending
        #ngsild_payload = clean_payload_for_ngsi_ld(raw_payload)
            
        response = requests.post(url, headers=headers, json=raw_payload)
        
        if response.status_code == 201:
            print("Success! Entity created.")
        elif response.status_code == 207:
            print("Batch operation returned 207 (Multi-Status).")
            print(f"Broker Response:\n{json.dumps(response.json(), indent=2)}")
        else:
            print(f"Failed. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    send_data_to_broker('./../data/weatherPortoRealTime_NGSILD.json')