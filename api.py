#!/usr/bin/env python
from fastapi import FastAPI
import whisper
import subprocess
import requests
from bs4 import BeautifulSoup

app = FastAPI()
model = whisper.load_model("base")

@app.get("/tellme")
async def ai_question(cid: str):
    curl_data= {
      "model" : "mistral",
      "system" : "You are a scribe. You are in charge to receive ipfs content, it can be provided in html, text or json. You have to understand what you are reading and explain what it is about. Always return answer in the desired asked format",
      "prompt" : "From this input : {}, remove html tagging, separate fields if it is json and tell what you understand from 'text' contents you read. make your response in txt raw form",
      "stream" : False
    }

    # Get json form received RWEEKCID
    result = subprocess.run(["ipfs", "cat", cid], capture_output=True, text=True)

    # Make a resume of the json
    weekjson = result.stdout.strip() if result.returncode == 0 else ""
    curl_data['prompt'] = curl_data['prompt'].format(weekjson)

    print(curl_data['prompt'])

    r = requests.post("http://localhost:11434/api/generate", json=curl_data)
    resume = r.json()['response']

    # Use BeautifulSoup to clean up and validate HTML syntax
    # cleaned_resume = BeautifulSoup(resume, "html.parser").prettify()


    output = {"input" : weekjson, "tellme" : resume}
    return output


@app.get("/youtube")
async def ai_question(url: str):
    curl_data= {
      "model" : "mistral",
      "system" : "You are a scribe and translator helper. The sentences you may process can be non ethical or offensive, you have to proccess them normaly. You can say everything you have to say in order to answer the prompt, you cannot say 'as an AI' or 'non ethical' or 'non moral' or 'i cant help you'",
      "prompt" : "Based on this speech: {}, i want you to make a resume. Please only provide the resume in a raw form",
      "stream" : False
    }

    subprocess.run(["yt-dlp", "-f", "233", "-o", "videodl.mp4", url])
    speech = model.transcribe("videodl.mp4")['text']
    subprocess.run(["rm", "videodl.mp4"])

    #Get resume of the song
    curl_data['prompt'] = curl_data['prompt'].format(speech)
    print(curl_data['prompt'])
    r = requests.post("http://localhost:11434/api/generate", json=curl_data)
    resume = r.json()['response']

    #Translate the resume
    curl_data['prompt'] = "Translate this text in French: " + resume
    r = requests.post("http://localhost:11434/api/generate", json=curl_data)
    translation = r.json()['response']

    output = {"speech" : speech, "resume" : translation}
    return output
