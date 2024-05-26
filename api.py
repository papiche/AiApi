#!/usr/bin/python3
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from typing import Optional
from bs4 import BeautifulSoup
from datetime import datetime
import whisper
import subprocess
import requests
import os
import magic

app = FastAPI()
model = whisper.load_model("small")

MAX_FILE_SIZE_KB = 20

# HTML form for file upload
html_form = """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Upload to Astroport</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
        }

        #upload-container {
            background-color: #ffffff;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            max-width: 400px;
            width: 100%;
        }

        h1 {
            color: #333333;
        }

        form {
            margin-top: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        input[type="file"] {
            margin-bottom: 10px;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }

        input[type="button"] {
            background-color: #4caf50;
            color: white;
            border: none;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            cursor: pointer;
            border-radius: 4px;
        }

        input[type="button"]:hover {
            background-color: #45a049;
        }

        #result-container, #text-option, #video-option {
            margin-top: 20px;
            display: none;
        }

        #loading-indicator {
            display: none;
            margin-top: 20px;
        }

        .error {
            color: red;
        }

        .success {
            color: green;
        }
    </style>
</head>

<body>
    <div id="upload-container">
        <h1>Upload file to Astroport</h1>
        <form id="upload-form" enctype="multipart/form-data" method="post">
            <input type="file" id="file" accept="video/*,audio/*,text/*,.txt" required>
            <input type="button" value="Upload" onclick="uploadFile()">
            <div id="loading-indicator">Loading...</div>
        </form>

        <div id="result-container" class="success"></div>
        <div id="text-option"><a id="text-option-link" href="#">Process Text File</a></div>
        <div id="video-option"><a id="video-option-link" href="#">Process Video File</a></div>
        <div id="error-message" class="error"></div>
    </div>

    <script>
        async function uploadFile() {
            const fileInput = document.getElementById('file');
            const file = fileInput.files[0];
            const resultContainer = document.getElementById('result-container');
            const errorMessage = document.getElementById('error-message');
            const loadingIndicator = document.getElementById('loading-indicator');
            const textOption = document.getElementById('text-option');
            const videoOption = document.getElementById('video-option');
            const maxSizeKB = 100 * 1024; // 100 MB

            // Reset previous states
            resultContainer.style.display = 'none';
            errorMessage.style.display = 'none';
            textOption.style.display = 'none';
            videoOption.style.display = 'none';
            loadingIndicator.style.display = 'block';

            // Check file size
            if (file.size / 1024 > maxSizeKB) {
                errorMessage.textContent = 'File size exceeds the limit of 100MB';
                errorMessage.style.display = 'block';
                loadingIndicator.style.display = 'none';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('Failed to upload file');
                }

                const result = await response.json();
                resultContainer.textContent = `File uploaded successfully. CID: ${result.cid}`;
                resultContainer.style.display = 'block';

                if (result.file_type === 'text') {
                    textOption.style.display = 'block';
                    document.getElementById('text-option-link').href = `/tellme?cid=${encodeURIComponent(result.cid)}`;
                } else if (result.file_type === 'video') {
                    videoOption.style.display = 'block';
                    document.getElementById('video-option-link').href = `/g1vlog?cid=${encodeURIComponent(result.cid)}`;
                } else {
                    errorMessage.textContent = 'Unsupported file type. Please upload a text or video file.';
                    errorMessage.style.display = 'block';
                }
            } catch (error) {
                errorMessage.textContent = `Error uploading file: ${error.message}`;
                errorMessage.style.display = 'block';
            } finally {
                loadingIndicator.style.display = 'none';
            }
        }
    </script>
</body>

</html>
"""

@app.get("/")
async def read_root():
    return HTMLResponse(content=html_form, status_code=200)

def get_mime_type(file: UploadFile):
    mime = magic.Magic()
    mime_type = mime.from_buffer(file.file.read(1024))
    return mime_type

@app.post("/upload")
async def create_upload_file(file: UploadFile = File(...)):
        
    # Check the file type
    mime_type = get_mime_type(file)
    print(f"Detected MIME type: {mime_type}")
    # Determine the file type based on MIME type
    file_type = (
        "text" if mime_type.startswith("text/") 
        else "video" if mime_type.startswith("video/") or "MP4" in mime_type
        else "audio" if mime_type.startswith("Audio") or "MP3" in mime_type
        else "unknown"
    )
    # Save the uploaded file to a temporary location
    temp_file_path = f"/tmp/{file.filename}"
    with open(temp_file_path, "wb") as f:
        f.write(file.file.read())

    # Validate file size
    max_file_size = 100 * 1024 * 1024  # 100MB
    if file.file.__sizeof__() > max_file_size:
        raise HTTPException(status_code=400, detail="File size exceeds the limit of 100MB")

    # Add the file to IPFS 
    result = subprocess.run(["ipfs", "add", "-wq", temp_file_path], capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail="Error adding file to IPFS")

    # Extract CID from the command output
    cid = result.stdout.strip().split('\n')[-1]

    # Remove the temporary file
    os.remove(temp_file_path)
    finish = subprocess.run(["ipfs", "pin", "rm", cid], capture_output=True, text=True)
    isok = finish.stdout.strip()
    print(f"{isok}/{file.filename}")

    # Construct the response data
    output = {"cid": cid, "file": file.filename, "file_type": file_type, "mime_type": mime_type, "isok": isok }

    return output
    
@app.get("/tellme")
async def ai_question(cid: str):
    curl_data= {
      "model" : "phi3",
      "system" : "Vous comprenez et maitrisez parfaitement le français. Vous êtes un scribe. Vous êtes chargé de recevoir du contenu, qui peut être fourni  dans divers langues et formats texte, html, markdown, JSON. Vous devez comprendre ce que vous lisez et expliquer de quoi il s'agit. Vous devez toujours renvoyer la réponse dans le format demandé et en français.",
      "prompt" : "A partir de ceci (jusqu'à EOF) : {} EOF que tu traduis toujours en français d'abord. Raconte ce que tu comprends de son contenu. Rédige un résumé sous forme de chapitres si plusieurs sujets sont abordés.",
      "stream" : False
    }

    # Verify if the file contains binary data in the first 200 bytes using ipfs cat -l
    # cat_result = subprocess.run(["ipfs", "cat", "-l", "200", cid], capture_output=True, text=True, encoding='utf-8')

    # if "x\x00" in cat_result.stdout:
    #     raise HTTPException(status_code=400, detail="File contains binary data. ERROR")

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
    cat_result = subprocess.run(["ipfs", "cat", "-l", "200", cid], capture_output=True, text=True, encoding='latin-1')
    if "x264" not in cat_result.stdout:
        raise HTTPException(status_code=400, detail="File is not 'x264' format. ERROR")

    getlog = subprocess.run(["ipfs", "get", "-o", "vlog.mp4", cid], capture_output=True, text=True)
    print(getlog)

    ## SPEECH TO TEXT
    speech = model.transcribe("vlog.mp4", language="fr")['text']
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
      "model" : "phi3",
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
