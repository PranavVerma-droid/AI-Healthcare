from ollama import Client # type: ignore
import json
from datetime import datetime
from config import OLLAMA_HOST, AI_MODEL

class AIHelper:
    def __init__(self):
        self.client = Client(host=OLLAMA_HOST)
        self.model = AI_MODEL
        self.db = None

    # Set the database.
    def set_database(self, db):
        self.db = db

    def get_response(self, user_input):
        try:
            todays_activities = []
            if self.db:
                try:
                    activities = self.db.get_todays_activities()
                    if activities:
                        by_category = {}
                        for name, category, points, notes, timestamp in activities:
                            if category not in by_category:
                                by_category[category] = []
                            time_str = datetime.fromisoformat(timestamp).strftime('%I:%M %p')
                            activity_str = f"{name} ({points}pts at {time_str})"
                            if notes:
                                activity_str += f" - Note: {notes}"
                            by_category[category].append(activity_str)
                        
                        for category, acts in by_category.items():
                            todays_activities.append(f"{category.title()}: {', '.join(acts)}")
                except Exception as e:
                    print(f"Warning: Could not get today's activities: {e}")

            daily_context = "\nToday's Activities:"
            if todays_activities:
                daily_context += "\n• " + "\n• ".join(todays_activities)
            else:
                daily_context += "\nNo activities completed today yet."

            completed_activities = []
            total_points = 0
            if self.db:
                try:
                    recommendations, recent = self.db.get_activity_recommendations(0.5) 
                    completed_activities = recent
                    total_points = self.db.get_total_points()
                except Exception as e:
                    print(f"Warning: Could not get activity history: {e}")

            activity_context = ""
            if completed_activities:
                activity_context = f"\nUser's recent activities: {', '.join(completed_activities)}"
                activity_context += f"\nTotal points earned: {total_points}"

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

            # Add current message with enhanced context
            messages.append({
                "role": "system",
                "content": f"""You are Stacy, a friendly and empathetic emotional AI Healthcare Assistant created by Pranav Verma.
                {daily_context}
                {activity_context}
                Guidelines:
                - Be very specific about today's completed activities when asked
                - Include timing information for activities when available
                - If activities were completed today, acknowledge them positively
                - If no activities were completed today, encourage starting with a simple one
                - Keep responses conversational and natural
                - Only mention crisis resources (988) if user expresses serious distress
                """
            })
            messages.append({"role": "user", "content": user_input})

            # Get response using ollama
            response = self.client.chat(
                model=self.model,
                messages=messages
            )

            # Extract content
            if isinstance(response, dict) and 'message' in response:
                return response['message'].get('content', 'No response content')
            else:
                return str(response)

        except Exception as e:
            return f"Error: Unable to get response. Please ensure Ollama is running. ({str(e)})"

    def generate_activities(self, mood_score, recent_activities=None):
        try:
            mood_type = "low" if mood_score < 0.3 else "neutral" if mood_score < 0.7 else "positive"
            recent = ""
            if recent_activities and isinstance(recent_activities, (list, tuple)):
                recent = "\nRecently completed activities: " + ", ".join(str(act) for act in recent_activities)

            # Activity Generation Template
            messages = [{
                "role": "system",
                "content": """You are an AI assistant that generates mental health activities. 
                Respond ONLY with a JSON array containing exactly 3 activities.
                Each activity must be a JSON object with these exact keys:
                - "name": string
                - "description": string
                - "points": integer between 5 and 30
                - "category": string, one of ["mindfulness", "exercise", "reflection", "social", "creative"]
                
                Example response format:
                [
                    {
                        "name": "Nature Walk",
                        "description": "Take a 10-minute walk outside and observe nature",
                        "points": 20,
                        "category": "exercise"
                    },
                    {
                        "name": "Gratitude List",
                        "description": "Write down three things you're grateful for",
                        "points": 15,
                        "category": "reflection"
                    },
                    {
                        "name": "Deep Breathing",
                        "description": "Practice deep breathing for 5 minutes",
                        "points": 10,
                        "category": "mindfulness"
                    }
                ]"""
            }, {
                "role": "user",
                "content": f"""Generate 3 unique activities for {mood_type} mood (score: {mood_score:.2f}).{recent}
                Make them specific, achievable within 30 minutes, and appropriate for the current mood."""
            }]

            response = self.client.chat(
                model=self.model,
                messages=messages
            )

            try:
                # Extract JSON content from response
                content = response['message']['content']
                # Find the JSON array in the response
                start = content.find('[')
                end = content.rfind(']') + 1
                if start != -1 and end != -1:
                    activities_json = content[start:end]
                    # Parse JSON safely
                    activities = json.loads(activities_json)
                    
                    # Validate activities format
                    for activity in activities:
                        if not all(k in activity for k in ('name', 'description', 'points', 'category')):
                            raise ValueError("Invalid activity format")
                        if not isinstance(activity['points'], int):
                            activity['points'] = int(float(activity['points']))
                    
                    return activities
                else:
                    raise ValueError("No JSON array found in response")

            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing activities: {e}")
                print(f"Raw response: {content}")
                return self._get_fallback_activities(mood_type)

        except Exception as e:
            print(f"Error generating activities: {e}")
            return self._get_fallback_activities(mood_type)

    def parse_custom_activity(self, description: str):
        try:
            # User's Custom Activity Generator
            messages = [{
                "role": "system",
                "content": """You are an AI that categorizes and scores mental health activities.
                Convert the user's activity description into a structured format.
                Respond ONLY with a JSON object containing:
                - "name": A concise 2-4 word title for the activity
                - "description": A clear, brief description
                - "points": integer between 5-30 based on effort/impact
                - "category": one of ["mindfulness", "exercise", "reflection", "social", "creative"]
                
                Example: "went on a long walk in the park" becomes:
                {
                    "name": "Park Walk",
                    "description": "Took an extended walk in the park",
                    "points": 20,
                    "category": "exercise"
                }"""
            }, {
                "role": "user",
                "content": f"Parse this activity: {description}"
            }]

            response = self.client.chat(
                model=self.model,
                messages=messages
            )

            content = response['message']['content']
            # Find the JSON object in the response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                activity = json.loads(content[start:end])
                
                # Validate format
                if not all(k in activity for k in ('name', 'description', 'points', 'category')):
                    raise ValueError("Invalid activity format")
                if not isinstance(activity['points'], int):
                    activity['points'] = int(float(activity['points']))
                
                return activity
            else:
                raise ValueError("No valid activity format found in response")

        except Exception as e:
            print(f"Error parsing custom activity: {e}")
            return None

    # Fallback activities (default incase the AI does not work)
    def _get_fallback_activities(self, mood_type):
        """Provide fallback activities if AI generation fails"""
        fallbacks = {
            "low": [
                {"name": "Gentle Breathing", "description": "Take 10 deep breaths", "points": 10, "category": "mindfulness"},
                {"name": "Comfort Music", "description": "Listen to your favorite calm song", "points": 15, "category": "mindfulness"},
                {"name": "Mood Journal", "description": "Write down your current feelings", "points": 20, "category": "reflection"}
            ],
            "neutral": [
                {"name": "Quick Walk", "description": "Take a 5-minute walk", "points": 15, "category": "exercise"},
                {"name": "Gratitude", "description": "List 3 good things about today", "points": 10, "category": "reflection"},
                {"name": "Stretch Break", "description": "Do some basic stretches", "points": 10, "category": "exercise"}
            ],
            "positive": [
                {"name": "Share Joy", "description": "Send a positive message to someone", "points": 20, "category": "social"},
                {"name": "Creative Time", "description": "Draw or doodle for 5 minutes", "points": 15, "category": "creative"},
                {"name": "Achievement List", "description": "Write down 3 recent accomplishments", "points": 15, "category": "reflection"}
            ]
        }
        return fallbacks.get(mood_type, fallbacks["neutral"])
