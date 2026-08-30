import requests
try:
    res = requests.get('http://localhost:11434/api/tags', timeout=3)
    print("Ollama tags:", res.json())
except Exception as e:
    print("Ollama connection error:", e)
