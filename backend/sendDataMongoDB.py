import json
import requests

def send_data_to_broker(file_path):
    url = 'http://orion:1026/ngsi-ld/v1/entityOperations/upsert'
    
    try:
        with open(file_path, 'r') as file:
            raw_payload = json.load(file)
            
        # 1. Determine if the payload contains @context
        # We check the first item in the list (assuming it's a batch array)
        has_context = False
        if isinstance(raw_payload, list) and len(raw_payload) > 0:
            has_context = '@context' in raw_payload[0]
        elif isinstance(raw_payload, dict):
            has_context = '@context' in raw_payload

        # 2. Dynamically assign the correct Content-Type header
        headers = {}
        if has_context:
            headers['Content-Type'] = 'application/ld+json'
            print(f"Sending {file_path} as application/ld+json (Context found)")
        else:
            headers['Content-Type'] = 'application/json'
            print(f"Sending {file_path} as application/json (No context found)")

        # 3. Send the request
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
    # Now you can safely call this on both files!
    send_data_to_broker('./../output/traffic_data_ngsild.json')
    #send_data_to_broker('./../data/weatherPortoRealTime_NGSILD.json')