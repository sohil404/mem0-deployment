#!/usr/bin/env python3
import requests
import json
import sys

# Replace with your Railway deployment URL
API_URL = "YOUR_RAILWAY_DEPLOYMENT_URL"

def create_memory(user_id, message_content):
    """Create a new memory in Mem0."""
    url = f"{API_URL}/memories"
    payload = {
        "messages": [
            {"role": "user", "content": message_content}
        ],
        "user_id": user_id
    }
    
    response = requests.post(url, json=payload)
    return response.json()

def search_memories(user_id, query):
    """Search for memories in Mem0."""
    url = f"{API_URL}/search"
    payload = {
        "query": query,
        "user_id": user_id
    }
    
    response = requests.post(url, json=payload)
    return response.json()

def get_all_memories(user_id):
    """Get all memories for a user."""
    url = f"{API_URL}/memories"
    params = {"user_id": user_id}
    
    response = requests.get(url, params=params)
    return response.json()

def print_usage():
    print("Usage:")
    print(f"  {sys.argv[0]} create <user_id> <message>   - Create a new memory")
    print(f"  {sys.argv[0]} search <user_id> <query>     - Search memories")
    print(f"  {sys.argv[0]} list <user_id>               - List all memories")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    user_id = sys.argv[2]
    
    if command == "create" and len(sys.argv) >= 4:
        message = sys.argv[3]
        result = create_memory(user_id, message)
        print(json.dumps(result, indent=2))
    
    elif command == "search" and len(sys.argv) >= 4:
        query = sys.argv[3]
        result = search_memories(user_id, query)
        print(json.dumps(result, indent=2))
    
    elif command == "list":
        result = get_all_memories(user_id)
        print(json.dumps(result, indent=2))
    
    else:
        print_usage()
        sys.exit(1) 