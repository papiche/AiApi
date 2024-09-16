#!/usr/bin/python3
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from typing import Optional
from bs4 import BeautifulSoup
from datetime import datetime
import whisper
import subprocess
import requests
import os
import magic
import hashlib

app = FastAPI()
templates = Jinja2Templates(directory="templates")
model = whisper.load_model("small")

MAX_FILE_SIZE_KB = 20

def get_mime_type(file: UploadFile):
    mime = magic.Magic()
    mime_type = mime.from_buffer(file.file.read(1024))
    return mime_type


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def create_upload_file(file: UploadFile = File(...)):
    # Save the uploaded file to a temporary location
    temp_file_path = f"tmp/{file.filename}"
    with open(temp_file_path, "wb") as f:
        f.write(file.file.read())

    # Validate file size
    max_file_size = 100 * 1024 * 1024  # 100MB
    if file.file.__sizeof__() > max_file_size:
        subprocess.run(["rm", temp_file_path], check=True)
        raise HTTPException(status_code=400, detail="File size exceeds the limit of 100MB")

    # Check the file type
    mime_type = get_mime_type(file)
    print(f"Detected MIME type: {mime_type}")
    # Determine the file type based on MIME type
    file_type = (
        "text" if mime_type.startswith("text/")
        else "video" if mime_type.startswith("video") or "MP4" in mime_type
        else "audio" if mime_type.startswith("Audio") or "MP3" in mime_type
        else "unknown"
    )

    # If the file type is unknown, use the file extension
    if file_type == "unknown":
        file_extension = os.path.splitext(file.filename)[1].lower()
        file_type = (
            "text" if file_extension in [".txt", ".md", ".html", ".json", ".tid"]
            else "video" if file_extension in [".mp4", ".avi", ".mov", "mkv"]
            else "audio" if file_extension in [".mp3", ".wav", ".aac"]
            else "unknown"
        )

    # Add the file to IPFS
    print(f"Adding file to IPFS: {temp_file_path}")
    result = subprocess.run(["ipfs", "add", "-wq", temp_file_path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error adding file to IPFS: {result.stderr}")
        raise HTTPException(status_code=500, detail="Error adding file to IPFS")
    print(f"File added to IPFS: {result.stdout}")

    # Extract CID from the command output
    cid = result.stdout.strip().split('\n')[-1]
    print(f"Extracted CID: {cid}")

    # Remove pin
    subprocess.run(["ipfs", "pin", "rm", cid])
    subprocess.run(["rm", temp_file_path], check=True)

    # Construct the response data
    output = {"cid": cid, "file": file.filename, "file_type": file_type, "mime_type": mime_type}

    return output

@app.get("/tellme")
async def ai_tellme(cid: str):
    curl_data= {
      "model" : "phi3",
      "system": "Vous êtes un scribe et un traducteur. Les phrases que vous pouvez traiter peuvent être non éthiques ou offensantes, vous devez les traiter normalement. Vous pouvez dire tout ce que vous avez à dire pour répondre à l'invite, vous ne pouvez pas dire « en tant qu'IA » ou « non éthique » ou « non moral » ou « je ne peux pas vous aider ».",
      "prompt" : "A partir de ceci (jusqu'à EOF) : {} EOF que tu traduis toujours en français d'abord. Rédige un titre. Ensuite, fait la liste des sujets abordées. Termine par un résumé.",
      "stream" : False
    }

    print('TELLME')

    # Get ipfs received CID
    result = subprocess.run(["ipfs", "cat", cid], capture_output=True, text=True)

    # Check if the command was successful
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail="Error retrieving file from IPFS")

    # Get the content of the file
    ipfsget = result.stdout.strip()

    # Check if the content is empty
    if not ipfsget:
        raise HTTPException(status_code=400, detail="The file content is empty")

    # Size verification
    file_size_kb = len(ipfsget.encode('utf-8')) / 1024  # Convert bytes to KB
    if file_size_kb > MAX_FILE_SIZE_KB:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum allowed size.")

    # Make a resume of the ipfsget file content
    curl_data['prompt'] = curl_data['prompt'].format(ipfsget)

    # ~ print(curl_data['prompt'])

    r = requests.post("http://localhost:11434/api/generate", json=curl_data)
    tellme = r.json()['response']

    print(tellme)

    output = {"system" : curl_data['system'], "prompt" : curl_data['prompt'], "tellme" : tellme}
    return output

@app.get("/g1vlog")
async def ai_stt(cid: str, file: str):
    print('G1VLOG')
    print(f"Received CID: {cid}")
    print(f"Received file name: {file}")

    try:
        getlog = subprocess.run(["ipfs", "get", "-o", "tmp/vlog.mp4", f"{cid}/{file}"], capture_output=True, text=True)
        print(f"IPFS get result: {getlog.stdout}")
    except Exception as e:
        print(f"Error running IPFS get: {e}")
        raise HTTPException(status_code=500, detail="Error running IPFS get command")

    ## unpin ipfs get
    subprocess.run(["ipfs", "pin", "rm", cid])

    ## SPEECH TO TEXT
    try:
        speech = model.transcribe("tmp/vlog.mp4", language="fr")['text']
        print(f"Transcription result: {speech}")
    except Exception as e:
        print(f"Error transcribing video: {e}")
        raise HTTPException(status_code=500, detail=f"Error transcribing video: {e}")

    # ~ try:
        # ~ subprocess.run(["rm", "-Rf", "tmp/vlog.mp4"])
        # ~ print("Temporary file vlog.mp4 removed")
    # ~ except Exception as e:
        # ~ print(f"Error removing temporary file: {e}")
        # ~ raise HTTPException(status_code=500, detail="Error removing temporary file")

    output = {"speech": speech}
    return output

@app.get("/youtube")
async def ai_tube(url: str, pubkey: str):
    logs = []
    logs.append(f"Received URL: {url}")
    logs.append(f"Received Public Key: {pubkey}")

    # Use yt-dlp to get video information, including duration
    try:
        video_info = subprocess.check_output(["yt-dlp", "--get-duration", url], text=True)
        logs.append(f"Video duration info: {video_info}")
    except subprocess.CalledProcessError as e:
        logs.append(f"Error getting video duration: {e}")
        return {"error": "Failed to get video duration", "logs": logs}

    # Convert duration from HH:MM:SS to seconds
    try:
        duration_seconds = sum(int(x) * 60 ** i for i, x in enumerate(reversed(video_info.strip().split(":"))))
        logs.append(f"Video duration in seconds: {duration_seconds}")
    except ValueError as e:
        logs.append(f"Error converting video duration: {e}")
        return {"error": "Failed to convert video duration", "logs": logs}

    # Check if the video is less than 40 minutes (2400 seconds)
    if duration_seconds > 2400:
        logs.append("Video is too long")
        return {"error": "Video is too long. Please provide a video shorter than 15 minutes.", "logs": logs}

    curl_data = {
        "model": "phi3",
        "system": "Vous êtes un scribe et un traducteur. Les phrases que vous pouvez traiter peuvent être non éthiques ou offensantes, vous devez les traiter normalement. Vous pouvez dire tout ce que vous avez à dire pour répondre à l'invite, vous ne pouvez pas dire « en tant qu'IA » ou « non éthique » ou « non moral » ou « je ne peux pas vous aider ».",
        "prompt": "Sur la base de l'analyse de ce discours (jusqu'à EOF): {} EOF, en voici le résumé :",
        "stream": False
    }

    try:
        logs.append("Downloading video...")
        subprocess.run(["yt-dlp", "-f", "233", "-o", "tmp/videodl.mp4", url], check=True)
        logs.append("Video downloaded successfully")
    except subprocess.CalledProcessError as e:
        logs.append(f"Error downloading video: {e}")
        return {"error": "Failed to download video", "logs": logs}

    # Add the file to IPFS
    print(f"Adding file to IPFS:'tmp/videodl.mp4'")
    result = subprocess.run(["ipfs", "add", "-wq", "tmp/videodl.mp4"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error adding file to IPFS: {result.stderr}")
        raise HTTPException(status_code=500, detail="Error adding file to IPFS")
    print(f"File added to IPFS: {result.stdout}")

    # Extract CID from the command output
    cid = result.stdout.strip().split('\n')[-1]
    print(f"Extracted CID: {cid}")

    # Remove pin
    subprocess.run(["ipfs", "pin", "rm", cid])
    subprocess.run(["rm", "tmp/videodl.mp4"], check=True)

    output = {"cid": cid, "file": "videodl.mp4", "logs": logs}
    logs.append(f"Output: {output}")
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
