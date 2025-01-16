from textblob import TextBlob # type: ignore
import nltk
from typing import Tuple
from ollama import Client # type: ignore
from config import OLLAMA_HOST, AI_MODEL

class SentimentAnalyzer:
    def __init__(self):
        try:
            nltk.data.find('vader_lexicon')
        except LookupError:
            nltk.download('vader_lexicon')
        self.client = Client(host=OLLAMA_HOST)
        self.model = AI_MODEL

    def analyze_sentiment(self, text: str) -> Tuple[float, str, float]:

        messages = [{
            "role": "system",
            "content": """Analyze the emotional state in this message. 
            Respond ONLY with a JSON object containing:
            - score: float between 0-1 (0 = very negative, 1 = very positive)
            - mood: string (low/neutral/positive)
            - impact: float between -0.05 and 0.05 (how much this should affect overall mood)
            Example: {"score": 0.2, "mood": "low", "impact": -0.03}"""
        }, {
            "role": "user",
            "content": text
        }]

        try:
            response = self.client.chat(model=self.model, messages=messages)
            content = response['message']['content']
            
            import json
            import re
            
            json_match = re.search(r'{.*}', content)
            if json_match:
                analysis = json.loads(json_match.group())
                return (
                    float(analysis['score']),
                    str(analysis['mood']),
                    float(analysis['impact'])
                )
        except Exception as e:
            print(f"AI analysis failed: {e}")
        
        # Fallback to TextBlob if AI fails
        analysis = TextBlob(text)
        base_score = (analysis.sentiment.polarity + 1) / 2
        
        if base_score < 0.3:
            mood = "low"
            mood_impact = -0.03
        elif base_score < 0.7:
            mood = "neutral"
            mood_impact = 0.01
        else:
            mood = "positive"
            mood_impact = 0.03
            
        return base_score, mood, mood_impact
