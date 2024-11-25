# app/services/chat_service.py
from typing import Dict, List
import openai
from flask import current_app
from app.models.chat import Chat
from app import db
import json

from app.services.vector_store_service import VectorStoreService

class ChatService:
    def __init__(self, vector_store_service: VectorStoreService):
        self.vector_store = vector_store_service

    def generate_response(self, user_id: int, syllabus_id: int, message: str) -> Dict:
        """Generate a response using GPT and relevant context."""
        try:
            # Get relevant context from vector store
            context = self.vector_store.get_relevant_context(syllabus_id, message)
            
            # Prepare messages for ChatGPT
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions about course syllabi. "
                              "Use the provided context to answer questions accurately. "
                              "If you're not sure about something, say so."
                },
                {
                    "role": "user",
                    "content": f"Context from syllabus:\n{json.dumps([c['text'] for c in context])}\n\n"
                              f"Question: {message}"
                }
            ]

            # Generate response using ChatGPT
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            # Extract the response text
            response_text = response['choices'][0]['message']['content']

            # Save the chat interaction
            chat = Chat(
                user_id=user_id,
                syllabus_id=syllabus_id,
                message=message,
                response=response_text
            )
            db.session.add(chat)
            db.session.commit()

            return {
                'response': response_text,
                'context': context
            }

        except Exception as e:
            current_app.logger.error(f"Error generating response: {str(e)}")
            raise