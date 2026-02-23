import json
import requests

def send_data_to_broker(file_path):
    # The URL from your curl command
    url = 'http://orion:1026/ngsi-ld/v1/entities'
    
    # The headers from your curl command
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        # 1. Read the JSON file
        with open(file_path, 'r') as file:
            payload = json.load(file)
            
        # 2. Send the POST request
        # Using the json parameter automatically formats the payload correctly
        response = requests.post(url, headers=headers, json=payload)
        
        # 3. Check the response
        if response.status_code == 201:
            print(f"Success! Entity created. Status Code: {response.status_code}")
        else:
            print(f"Failed to create entity. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' does not contain valid JSON.")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the server: {e}")

if __name__ == "__main__":
    # Run the function pointing to your JSON file
    send_data_to_broker('./../data/data.json')