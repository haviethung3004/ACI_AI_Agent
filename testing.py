import json
import os

def load_urls(file_path='urls.json'):
    if not os.path.exists(file_path):
        return {"error": f"URLs file '{file_path}' not found."}
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Return the list of dictionaries directly
        print(data) 
        return data
        
    except Exception as e:
        return {"error": f"Error loading URLs: {str(e)}"}

load_urls()