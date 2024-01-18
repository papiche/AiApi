#!/usr/bin/env python
from fastapi import FastAPI
import whisper
import subprocess
import requests
from bs4 import BeautifulSoup

app = FastAPI()
model = whisper.load_model("base")

MAX_FILE_SIZE_KB = 10

@app.get("/tellme")
async def ai_question(cid: str):
    curl_data= {
      "model" : "mistral",
      "system" : "Vous comprenez et maitrisez parfaitement le français. Vous êtes un scribe. Vous êtes chargé de recevoir du contenu, qui peut être fourni  dans divers langues et formats texte, html, markdown, JSON. Vous devez comprendre ce que vous lisez et expliquer de quoi il s'agit. Vous devez toujours renvoyer la réponse dans le format demandé et en français.",
      "prompt" : "A partir de ceci (jusqu'à EOF) : {} EOF que tu traduis toujours en français d'abord. Raconte ce que tu comprends de son contenu. Rédige une réponse sous forme de chapitres si plusieurs sujets sont abordés. Formate la réponse en markdown. Si le fichier est en JSON, extrait la liste des titres, et descriptions, Ajoute les adresses emails et leur nombre d'ocurence si tu en trouve.",
      "stream" : False
    }

    ## TODO : ipfs cat -l 100 to verify file header type before proceeding

    # Get ipfs received CID
    result = subprocess.run(["ipfs", "cat", cid], capture_output=True, text=True)

    # Size verification
    file_size_kb = len(result.stdout.encode('utf-8')) / 1024  # Convert bytes to KB
    if file_size_kb > MAX_FILE_SIZE_KB:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum allowed size.")

    # Make a resume of the ipfsget file content
    ipfsget = result.stdout.strip() if result.returncode == 0 else ""
    curl_data['prompt'] = curl_data['prompt'].format(ipfsget)

    print(curl_data['prompt'])

    r = requests.post("http://localhost:11434/api/generate", json=curl_data)
    resume = r.json()['response']

    output = {"system" : curl_data['system'], "prompt" : curl_data['prompt'], "tellme" : resume}
    return output


@app.get("/g1vlog")
async def ai_question(cid: str):
    # ~ curl_data= {
      # ~ "model" : "mistral",
      # ~ "system" : "You are a scribe and translator helper. Vous maitrisez de nombreuses langues! The sentences you may process can be non ethical or offensive, you have to proccess them as it is.",
      # ~ "prompt" : "Based on this speech (until EOF_) : {} EOF_, make the exact transcription and translation of it in French. Et. Voila le résultat :",
      # ~ "stream" : False
    # ~ }

    print('G1VLOG')
    getlog = subprocess.run(["ipfs", "get", "-o", "vlog.mp4", cid], capture_output=True, text=True)
    print(getlog)

    model = None
    model = whisper.load_model("large")
    ## SPEECH TO TEXT
    speech = modeL.transcribe("vlog.mp4")['text']
    subprocess.run(["rm", "-Rf", "vlog.mp4"])

    output = {"speech" : speech}
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
