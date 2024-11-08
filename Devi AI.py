from fastapi import FastAPI, Request
import openai
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from telegram import Bot
from typing import Dict

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("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")
TELEGRAM_TOKEN = os.getenv("6302989361:AAFAZgFf7_gGFB5fErpeCTxpVeRQxaTDfIo")
bot = Bot(token=TELEGRAM_TOKEN)

# Initialize FastAPI app
app = FastAPI()

# Initialize memory storage and request counter
chat_memory: Dict[int, list] = {}  # Dictionary to store memory by chat ID
request_count = 0
REQUEST_LIMIT = 5000  # Daily request limit
reset_time = datetime.now() + timedelta(days=1)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    global request_count, reset_time

    # Handle daily request limit
    if datetime.now() >= reset_time:
        request_count = 0
        reset_time = datetime.now() + timedelta(days=1)

    if request_count >= REQUEST_LIMIT:
        return {"status": "Request limit reached. Please try again tomorrow."}

    # Parse incoming Telegram message
    data = await request.json()
    chat_id = data['message']['chat']['id']
    user_message = data['message']['text']
    user_name = data['message']['from'].get('username', 'User')  # Fallback to 'User' if no username
    user_phone = data['message']['from'].get('phone_number', None)

    # Create user identifier for response personalization
    user_identifier = user_name if user_name else (user_phone if user_phone else "User")

    # Maintain chat memory for the specific chat ID
    if chat_id not in chat_memory:
        chat_memory[chat_id] = []
    chat_memory[chat_id].append({"user": f"{user_identifier}: {user_message}"})
    
    # Generate response from OpenAI
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=generate_memory_prompt(chat_id, user_identifier, user_message),
            max_tokens=150
        )
        bot_response = response.choices[0].text.strip()
        
        # Save bot response to memory and increase request count
        chat_memory[chat_id].append({"bot": bot_response})
        request_count += 1
        
        # Send the response back to the user in the chat
        bot.send_message(chat_id=chat_id, text=f"{user_identifier}, {bot_response}")
        
    except Exception as e:
        # Handle exceptions and send error message
        bot.send_message(chat_id=chat_id, text="Sorry, an error occurred.")
        print("Error:", e)
    
    return {"status": "Message processed"}

def generate_memory_prompt(chat_id: int, user_identifier: str, user_message: str) -> str:
    # Generate a prompt with memory context for ChatGPT, limited to the last 5 messages
    memory_context = ""
    for msg in chat_memory[chat_id][-5:]:  # Limit to last 5 messages for context
        memory_context += f"{msg.get('user', '')}\nBot: {msg.get('bot', '')}\n"
    
    return f"{memory_context}{user_identifier}: {user_message}\nBot:"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    