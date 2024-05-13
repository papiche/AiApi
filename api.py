#!/usr/bin/env python
from fastapi import FastAPI
from fastapi import HTTPException
from typing import Optional
from bs4 import BeautifulSoup
import whisper
import subprocess
import requests


app = FastAPI()
model = whisper.load_model("base")

MAX_FILE_SIZE_KB = 20

@app.get("/tellme")
async def ai_question(cid: str):
    curl_data= {
      "model" : "mistral",
      "system" : "Vous comprenez et maitrisez parfaitement le français. Vous êtes un scribe. Vous êtes chargé de recevoir du contenu, qui peut être fourni  dans divers langues et formats texte, html, markdown, JSON. Vous devez comprendre ce que vous lisez et expliquer de quoi il s'agit. Vous devez toujours renvoyer la réponse dans le format demandé et en français.",
      "prompt" : "A partir de ceci (jusqu'à EOF) : {} EOF que tu traduis toujours en français d'abord. Raconte ce que tu comprends de son contenu. Rédige une réponse sous forme de chapitres si plusieurs sujets sont abordés. Formate la réponse en markdown. Si le fichier est en JSON, extrait la liste des titres, et descriptions, Ajoute les adresses emails et leur nombre d'ocurence si tu en trouve.",
      "stream" : False
    }

    # ~ # Verify if the file contains binary data in the first 200 bytes using ipfs cat -l
    # ~ cat_result = subprocess.run(["ipfs", "cat", "-l", "200", cid], capture_output=True, text=True, encoding='utf-8')

    # ~ if "x\x00" in cat_result.stdout:
        # ~ raise HTTPException(status_code=400, detail="File contains binary data. ERROR")

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
    tellme = r.json()['response']

    output = {"system" : curl_data['system'], "prompt" : curl_data['prompt'], "tellme" : tellme}
    return output


@app.get("/g1vlog")
async def ai_question(cid: str):
    print('G1VLOG')
    # Verify if the file contains "x264" in the first 200 bytes
    cat_result = subprocess.run(["ipfs", "cat", "-l", "200", cid], capture_output=True, text=True, encoding='utf-8')
    if "x264" not in cat_result.stdout:
        raise HTTPException(status_code=400, detail="File is not 'x264' format. ERROR")

    getlog = subprocess.run(["ipfs", "get", "-o", "vlog.mp4", cid], capture_output=True, text=True)
    print(getlog)

    ## SPEECH TO TEXT
    speech = model.transcribe("vlog.mp4")['text']
    subprocess.run(["rm", "-Rf", "vlog.mp4"])

    output = {"speech" : speech}
    return output


@app.get("/youtube")
async def ai_question(url: str):
    # Use yt-dlp to get video information, including duration
    video_info = subprocess.check_output(["yt-dlp", "--get-duration", url], text=True)

    # Convert duration from HH:MM:SS to seconds
    duration_seconds = sum(int(x) * 60 ** i for i, x in enumerate(reversed(video_info.strip().split(":"))))

    # Check if the video is less than 5 minutes (300 seconds)
    if duration_seconds > 300:
        return {"error": "Video is too long. Please provide a video shorter than 5 minutes."}

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

@app.get("/transactions")
async def get_transactions(pubkey: str, date: Optional[str] = None):
    # Validate date format
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Construct jaklis.py command
    command = [
        "/home/frd/.zen/Astroport.ONE/tools/jaklis/jaklis.py",
        "history",
        "-p", pubkey,
        "-j",
        "-n", "100"
    ]

    # Run jaklis.py command
    result = subprocess.run(command, capture_output=True, text=True)

    # Parse JSON output
    try:
        transactions = eval(result.stdout)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing jaklis.py output: {str(e)}")

    # Filter transactions based on date if provided
    if date:
        # Extract year and month from the provided date
        target_year, target_month, _ = date.split('-')
        transactions = [
            t for t in transactions
            if datetime.utcfromtimestamp(t['date']).strftime("%Y-%m") == f"{target_year}-{target_month}"
        ]

    # Format transactions into CSV
    csv_data = []
    total = 0.0  # Initialize total here
    for transaction in transactions:
        total += transaction["amount"]
        formatted_date = datetime.utcfromtimestamp(transaction["date"]).strftime('%d/%m/%Y (%H:%M)')
        csv_data.append([
            formatted_date,
            transaction["pubkey"],
            transaction["comment"],
            f"{transaction['amount']:.1f}" if transaction["amount"] < 0 else "0.0",
            f"{-transaction['amount']:.1f}" if transaction["amount"] > 0 else "0.0",
            f"{total:.1f}"
        ])

    # Generate CSV file in-memory
    csv_file = "\n".join([",".join(map(str, row)) for row in csv_data])

    return {"csv_data": csv_file}

# Store the OBS Studio recording process object
recording_process = None

@app.get("/rec")
def start_recording():
    global recording_process
    if recording_process:
        raise HTTPException(status_code=400, detail="Recording is already in progress.")

    # Start OBS Studio recording and store the process object
    getlog = subprocess.run(["obs-cmd", "--websocket", "obsws://127.0.0.1:4455/cUupyLMSTXuSEIpc", 'recording', 'start'], capture_output=True, text=True)
    print(getlog)
    recording_process = True

    return {"message": "Recording started successfully."}

@app.get("/stop")
def stop_recording():
    global recording_process
    if not recording_process:
        raise HTTPException(status_code=400, detail="No recording in progress to stop.")

    getlog = subprocess.run(["obs-cmd", "--websocket", "obsws://127.0.0.1:4455/cUupyLMSTXuSEIpc", 'recording', 'stop'], capture_output=True, text=True)
    print(getlog)
    recording_process = None

    return {"message": "Recording stopped successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
