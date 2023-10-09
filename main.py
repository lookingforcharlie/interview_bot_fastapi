import json
import os

import openai
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse

app = FastAPI()

load_dotenv()
# Load your API key from an environment variable or secret management service
openai.api_key = os.getenv("OPEN_AI_KEY")
openai.org = os.getenv("OPEN_AI_ORG")
elevenlabs_key = os.getenv("ELEVENLABS_KEY")


@app.get("/")
async def root():
    return {"message": "Hello Bot"}


# 1. Send in audio, and have it transcribed - using openAI - whisper-1
@app.post("/talk")
async def post_audio(file: UploadFile):
    user_message = transcribe_audio(file)
    chat_response = get_chat_response(user_message)
    # Using elevenlabs to convert GPT returned text to realistic speech, and store in an variable
    audio_output = text_to_speech(chat_response)

    # https://fastapi.tiangolo.com/advanced/custom-response/?h=streamingresponse#using-streamingresponse-with-file-like-objects
    def iterfile():
        yield audio_output

    return StreamingResponse(iterfile(), media_type="audio/mpeg")


# function: to have the audio file transcribed
def transcribe_audio(file):
    # convert audio to text, 'rb' means 'read bytes'
    audio_file = open(file.filename, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    # Hard-coded for testing, not gonna use the token over and over
    # transcript = {"role": "user", "content": "Who won the world series in 2020?"}
    print(transcript)
    # transcript looks like: {"text": "Hi, hi, hi, Charlie, how are you doing?"}
    # We need to turn the format like: {"role": "user", "content": "hello I am Charlie..."}
    # https://platform.openai.com/docs/guides/gpt/chat-completions-api
    # Now we return the format that ChatGPT can recognize
    return {"role": "user", "content": transcript["text"]}


# 3. We want to save that chat history to send back and forth for context - chatJeopardy doesn't have memory, how it works with chatJeopardy is that every time you talk to ChatJeopardy you send the entire context of conversation. In this moment, we gonna create a file to store the history of the chat
def get_chat_response(user_message):
    # 1st: load the history of the chat
    messages = load_message()
    # 2nd: append the newly asked prompt, now we get the entire context of conversation
    messages.append(user_message)
    # # TODO 3. We want to send it to chatgpt and get a response
    gpt_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=messages
    )
    print(user_message)
    print("-------------- divider ---------------")
    print(gpt_response)
    # parse the raw response
    parsed_gpt_response = gpt_response["choices"][0]["message"]
    # 4th: save messages
    print("-------------- parsed_gpt_response ---------------")
    print(parsed_gpt_response)
    # This is the format of 'parsed_gpt_response'
    # {
    #   "role": "assistant",
    #   "content": "Glad we're on the same page! Now, let's dive into the front-end. What JavaScript frameworks or libraries are you familiar with?"
    # }
    save_messages(user_message, parsed_gpt_response)

    # return a string of content
    return parsed_gpt_response["content"]


# function: to load the data from database.json
def load_message():
    messages = []
    file = "database.json"
    empty = os.stat(file).st_size == 0

    # If file not empty, loop through history and add to messages
    # If file is empty we need to add the context
    if not empty:
        with open(file, "r") as db_f:
            data = json.load(db_f)
            for item in data:
                messages.append(item)
    else:
        # if the chat is empty, this message will be the first thing in the chat history always
        messages.append(
            {
                "role": "system",
                "content": "You are interviewing a Full Stack Software Engineer. Please ask short questions that are relevant to this position. Keep responses under 30 words and be funny sometimes",
            },
        )
    print(messages)
    return messages


# function
def save_messages(user_message, gpt_response):
    file = "database.json"
    messages = load_message()
    messages.append(user_message)
    messages.append(gpt_response)
    with open(file, "w") as f:
        # dumping messages as JSON into database.json represented by object f
        json.dump(messages, f)


# Function: to get a realistic voice from elevenlabs, we gonna call another api in the backend
def text_to_speech(text: str):
    body = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0,
            "similarity_boost": 0,
            "style": 0,
            "use_speaker_boost": True,
        },
    }
    headers = {
        "Content-type": "application/json",
        "accept": "audio/mpeg",
        "xi-api-key": elevenlabs_key,
    }

    # you can find all voice id by 'https://api.elevenlabs.io/v1/voices', search for charlie if you like it
    charlie = "IKne3meq5aSn9XLyUdCD"
    adam = "pNInz6obpgDQGcFmaJgB"

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{charlie}"

    try:
        response = requests.post(url, json=body, headers=headers)
        if response.status_code == 200:
            print("---------- Type of response from 11-labs -----------")
            print(type(response.content))
            return response.content
        else:
            print("Something went wrong.")
    except Exception as e:
        print(e)
