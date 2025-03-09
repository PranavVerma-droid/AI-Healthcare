# The Config for the app.

# Change this to http://localhost:11434 if you want to run Ollama Locally.
# (Make sure that ollama is actually running before chaning!)
OLLAMA_HOST = 'https://ollama-h2.pranavv.co.in'

# The model to use.
# (Warning: It will show an error incase this model is not present on your machine. Please pull it before running this app.)
# If you are using the hosted version, then it is fine, else run this command:
# ollama pull qwen2.5:3b
# OR (Incase you want a lighter model):
# ollama pull qwen2.5:1.5b
AI_MODEL = 'qwen2.5:3b'
