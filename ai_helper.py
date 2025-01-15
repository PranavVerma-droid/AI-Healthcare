from ollama import Client # type: ignore
import json
import sys

class AIHelper:
    def __init__(self):
        self.client = Client(host='http://localhost:11434')
        self.model = "qwen2.5:3b"
        self.db = None

    def set_database(self, db):
        self.db = db

    def get_response(self, user_input):
        try:
            # Get recent chat context
            messages = []
            if self.db:
                try:
                    recent_chats = self.db.get_recent_chats(3)
                    for _, msg, resp in recent_chats[::-1]:
                        if not msg.startswith('/'):
                            messages.extend([
                                {"role": "user", "content": msg},
                                {"role": "assistant", "content": resp}
                            ])
                except Exception as e:
                    print(f"Warning: Could not get chat history: {e}")

            # Add current message
            messages.append({
                "role": "system",
                "content": """You are Stacy, a friendly and empathetic emotional AI Healthcare Assistant.
                Guidelines:
                - Keep responses conversational and appropriate to the context
                - Only mention crisis resources (988) if the user expresses serious distress
                - For casual greetings and conversations, respond naturally
                - Keep responses concise and friendly"""
            })
            messages.append({"role": "user", "content": user_input})

            # Get response using official client
            response = self.client.chat(
                model=self.model,
                messages=messages
            )

            # Extract content from response dictionary
            if isinstance(response, dict) and 'message' in response:
                return response['message'].get('content', 'No response content')
            else:
                return str(response)

        except Exception as e:
            return f"Error: Unable to get response. Please ensure Ollama is running. ({str(e)})"
