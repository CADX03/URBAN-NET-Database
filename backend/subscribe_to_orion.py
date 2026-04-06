import requests
import json

def create_subscription(entity_type, entity_type_context, receiver_url):
    url = 'http://orion:1026/ngsi-ld/v1/subscriptions'
    #url = 'http://localhost:1026/ngsi-ld/v1/subscriptions'
    
    # The NGSI-LD Subscription Payload
    payload = {
        "description": f"Real-time subscription for {entity_type}",
        "type": "Subscription",
        "entities": [
            {
                "type": entity_type
            }
        ],
        "notification": {
            "endpoint": {
                "uri": receiver_url,
                "accept": "application/json"
            }
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            entity_type_context
        ]
    }

    headers = {
        'Content-Type': 'application/ld+json'
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            print("Success! Subscription created.")
            return True, f"Success! Subscription ID: {response.headers.get('Location')}"
        elif response.status_code == 409:
            print("Subscription already exists for this endpoint and entity type.")
            return False, "Subscription already exists for this endpoint and entity type."
        else:
            print(f"Failed. Status Code: {response.status_code}. Response: {response.text}")
            return False, f"Failed. Status Code: {response.status_code}. Response: {response.text}"
            
    except Exception as e:
        print(f"Connection error occurred: {e}")
        return False, f"Connection error occurred: {e}"

if __name__ == "__main__":
    # 1. The type of data you want to listen to (Check your JSON file for the exact "type")
    # Example: 'TrafficFlowObserved' or 'WeatherObserved'
    TARGET_ENTITY_TYPE = "TrafficFlowObserved" 
    
    # 2. The URL of your Flask receiver. 
    # IMPORTANT: Change 'host.docker.internal' to your machine's actual IP 
    # if Orion is in a Docker container and your Flask app is running locally.
    RECEIVER_ENDPOINT = "http://receiver:5000/notify"
    
    create_subscription(TARGET_ENTITY_TYPE, RECEIVER_ENDPOINT)