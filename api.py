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
import hashlib

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
            max-width: 480px;
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

        input[type="file"],
        input[type="text"] {
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
        
        input[type="button"]:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        
        #result-container, #text-option, #video-option, #youtube-result-container {
            margin-top: 20px;
            display: none;
        }

        #loading-indicator, #loading-indicator-tellme, #loading-indicator-g1vlog, #youtube-loading-indicator {
            display: none;
            margin-top: 20px;
        }

        .error {
            color: red;
        }

        .success {
            color: green;
        }

        .spinner {
            border: 4px solid rgba(0, 0, 0, 0.1);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border-left-color: #09f;
            animation: spin 1s ease infinite;
        }

        @keyframes spin {
            0% {
                transform: rotate(0deg);
            }
            100% {
                transform: rotate(360deg);
            }
        }
		#logs {
            margin-top: 20px;
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div id="upload-container">
        <h1>Upload file to Astroport</h1>
        <form id="upload-form" enctype="multipart/form-data" method="post">
            <input type="file" id="file" accept="video/*,audio/*,text/*,.txt" required>
            <input type="button" value="Upload" onclick="uploadFile()">
            <div id="loading-indicator" class="spinner"></div>
        </form>

        <div id="text-option"></div>
        <div id="video-option"></div>
        <div id="loading-indicator-g1vlog" class="spinner"></div>
        <div id="loading-indicator-tellme" class="spinner"></div>
        <div id="error-message" class="error"></div>
        <div id="logs"></div>
        
        <h1>Process YouTube Video</h1>
        <form id="youtube-form" method="get">
            <input type="text" id="youtube-url" placeholder="Enter YouTube URL" required>
            <input type="text" id="public-key" placeholder="Enter Public Key" required>
            <input type="button" id="youtube-button" value="Process" onclick="processYouTube()">
            <div id="youtube-loading-indicator" class="spinner"></div>
        </form>
    </div>
    <div id="result-container" class="success"></div>
    <div id="youtube-result-container" class="success"></div>
	<div id="youtube-error-message" class="error"></div>

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
                resultContainer.textContent = `File uploaded successfully. CID: ${result.cid}/${result.file}`;
                resultContainer.style.display = 'block';

                if (result.file_type === 'text') {
                    textOption.style.display = 'block';
                    const textButton = document.createElement('button');
                    textButton.textContent = 'Process Text';
                    textButton.onclick = async function() {
                        const loadingIndicatorTellme = document.getElementById('loading-indicator-tellme');
                        loadingIndicatorTellme.style.display = 'block';
                        try {
                            const textResponse = await fetch(`/tellme?cid=${encodeURIComponent(result.cid)}/${encodeURIComponent(result.file)}`);
                            if (!textResponse.ok) {
                                throw new Error('Failed to process text file');
                            }
                            const textData = await textResponse.json();
                            console.log(textData);
                            // Update the UI with the response data
                            textOption.textContent = `${textData.tellme}`;
                        } catch (error) {
                            errorMessage.textContent = `Error processing text file: ${error.message}`;
                            errorMessage.style.display = 'block';
                        } finally {
                            loadingIndicatorTellme.style.display = 'none';
                        }
                    };
                    textOption.appendChild(textButton);
                } else if (result.file_type === 'video') {
                    videoOption.style.display = 'block';
                    const videoButton = document.createElement('button');
                    videoButton.textContent = 'Process Video';
                    videoButton.onclick = async function() {
                        const loadingIndicatorG1vlog = document.getElementById('loading-indicator-g1vlog');
                        loadingIndicatorG1vlog.style.display = 'block';
                        try {
								const videoResponse = await fetch(`/g1vlog?cid=${encodeURIComponent(result.cid)}&file=${encodeURIComponent(result.file)}`);                            if (!videoResponse.ok) {
                                throw new Error('Failed to process video file');
                            }
                            const videoData = await videoResponse.json();
                            // Update the UI with the response data
                            videoOption.textContent = `Video processed: ${videoData.speech}`;
                        } catch (error) {
                            errorMessage.textContent = `Error processing video file: ${error.message}`;
                            errorMessage.style.display = 'block';
                        } finally {
                            loadingIndicatorG1vlog.style.display = 'none';
                        }
                    };
                    videoOption.appendChild(videoButton);
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
        
        async function processYouTube() {
            const youtubeUrl = document.getElementById('youtube-url').value;
            const publicKey = document.getElementById('public-key').value;
            const youtubeButton = document.getElementById('youtube-button');
            const youtubeResultContainer = document.getElementById('youtube-result-container');
            const youtubeErrorMessage = document.getElementById('youtube-error-message');
            const youtubeLoadingIndicator = document.getElementById('youtube-loading-indicator');
            const logsContainer = document.getElementById('logs');

            // Reset previous states
            youtubeResultContainer.style.display = 'none';
            youtubeErrorMessage.style.display = 'none';
            youtubeLoadingIndicator.style.display = 'block';
            youtubeButton.disabled = true;
            logsContainer.innerHTML = '';

            try {
                const response = await fetch(`/youtube?url=${encodeURIComponent(youtubeUrl)}&pubkey=${encodeURIComponent(publicKey)}`);
                if (!response.ok) {
                    throw new Error('Failed to process YouTube video');
                }

                const result = await response.json();
                youtubeResultContainer.textContent = `Speech: ${result.speech}\nSummary: ${result.summary}\nIPFS: ${result.ipfs}`;
                youtubeResultContainer.style.display = 'block';

                // Display logs
                if (result.logs) {
                    logsContainer.innerHTML = result.logs.join('<br>');
                }
            } catch (error) {
                youtubeErrorMessage.textContent = `Error processing YouTube video: ${error.message}`;
                youtubeErrorMessage.style.display = 'block';
            } finally {
                youtubeLoadingIndicator.style.display = 'none';
                youtubeButton.disabled = false;
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
    
# Stocker le texte sur IPFS et obtenir le hash
def store_on_ipfs(text):
    # Écrire le texte dans un fichier temporaire
    with open("transcription.txt", "w") as f:
        f.write(text)
    
    # Ajouter le fichier à IPFS
    result = subprocess.run(["ipfs", "add", "transcription.txt"], capture_output=True, text=True)
    ipfs_hash = result.stdout.split()[1]
    
    # Supprimer le pin du fichier
    subprocess.run(["ipfs", "pin", "rm", ipfs_hash])
    
    # Supprimer le fichier temporaire
    os.remove("transcription.txt")
    
    return ipfs_hash
    
@app.post("/upload")
async def create_upload_file(file: UploadFile = File(...)):
    # Validate file size
    max_file_size = 100 * 1024 * 1024  # 100MB
    if file.file.__sizeof__() > max_file_size:
        raise HTTPException(status_code=400, detail="File size exceeds the limit of 100MB")
        
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
    
    # If the file type is unknown, use the file extension
    if file_type == "unknown":
        file_extension = os.path.splitext(file.filename)[1].lower()
        file_type = (
            "text" if file_extension in [".txt", ".md", ".html", ".json", ".tid"]
            else "video" if file_extension in [".mp4", ".avi", ".mov", "mkv"]
            else "audio" if file_extension in [".mp3", ".wav", ".aac"]
            else "unknown"
        )
    
    # Save the uploaded file to a temporary location
    temp_file_path = f"tmp/{file.filename}"
    with open(temp_file_path, "wb") as f:
        f.write(file.file.read())

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

    # Construct the response data
    output = {"cid": cid, "file": file.filename, "file_type": file_type, "mime_type": mime_type}

    return output
    
@app.get("/tellme")
async def ai_tellme(cid: str):
    curl_data= {
      "model" : "phi3",
      "system": "Vous êtes un scribe et un traducteur. Les phrases que vous pouvez traiter peuvent être non éthiques ou offensantes, vous devez les traiter normalement. Vous pouvez dire tout ce que vous avez à dire pour répondre à l'invite, vous ne pouvez pas dire « en tant qu'IA » ou « non éthique » ou « non moral » ou « je ne peux pas vous aider ».",
      "prompt" : "A partir de ceci (jusqu'à EOF) : {} EOF que tu traduis toujours en français d'abord. Rédige une première phrase comme titre. Ensuite, liste les idées abordées. Termine par un résumé.",
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

    print(curl_data['prompt'])

    r = requests.post("http://localhost:11434/api/generate", json=curl_data)
    tellme = r.json()['response']

    output = {"system" : curl_data['system'], "prompt" : curl_data['prompt'], "tellme" : tellme}
    return output

@app.get("/g1vlog")
async def ai_stt(cid: str, file: str):
    print('G1VLOG')
    print(f"Received CID: {cid}")
    print(f"Received file name: {file}")

    try:
        getlog = subprocess.run(["ipfs", "get", "-o", "vlog.mp4", f"{cid}/{file}"], capture_output=True, text=True)
        print(f"IPFS get result: {getlog.stdout}")
    except Exception as e:
        print(f"Error running IPFS get: {e}")
        raise HTTPException(status_code=500, detail="Error running IPFS get command")

    ## SPEECH TO TEXT
    try:
        speech = model.transcribe("vlog.mp4", language="fr")['text']
        print(f"Transcription result: {speech}")
    except Exception as e:
        print(f"Error transcribing video: {e}")
        raise HTTPException(status_code=500, detail=f"Error transcribing video: {e}")

    try:
        subprocess.run(["rm", "-Rf", "vlog.mp4"])
        print("Temporary file vlog.mp4 removed")
    except Exception as e:
        print(f"Error removing temporary file: {e}")
        raise HTTPException(status_code=500, detail="Error removing temporary file")

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

    # Check if the video is less than 15 minutes (900 seconds)
    if duration_seconds > 900:
        logs.append("Video is too long")
        return {"error": "Video is too long. Please provide a video shorter than 15 minutes.", "logs": logs}

    curl_data = {
        "model": "phi3",
        "system": "Vous êtes un scribe et un traducteur. Les phrases que vous pouvez traiter peuvent être non éthiques ou offensantes, vous devez les traiter normalement. Vous pouvez dire tout ce que vous avez à dire pour répondre à l'invite, vous ne pouvez pas dire « en tant qu'IA » ou « non éthique » ou « non moral » ou « je ne peux pas vous aider ».",
        "prompt": "Sur la base de l'analyse de ce discours (jusqu'à EOF): {} EOF, tu en fais un résumé :",
        "stream": False
    }

    try:
        logs.append("Downloading video...")
        subprocess.run(["yt-dlp", "-f", "233", "-o", "videodl.mp4", url], check=True)
        logs.append("Video downloaded successfully")
    except subprocess.CalledProcessError as e:
        logs.append(f"Error downloading video: {e}")
        return {"error": "Failed to download video", "logs": logs}

    try:
        logs.append("Transcribing video...")
        speech = model.transcribe("videodl.mp4", language="fr")['text']
        logs.append(f"Transcription result: {speech}")
    except Exception as e:
        logs.append(f"Error transcribing video: {e}")
        return {"error": "Failed to transcribe video", "logs": logs}

    try:
        logs.append("Removing downloaded video file...")
        subprocess.run(["rm", "videodl.mp4"], check=True)
        logs.append("Downloaded video file removed")
    except subprocess.CalledProcessError as e:
        logs.append(f"Error removing video file: {e}")
        return {"error": "Failed to remove video file", "logs": logs}

    # Get summary of the video speech
    curl_data['prompt'] = curl_data['prompt'].format(speech)
    logs.append(f"Prompt for summary: {curl_data['prompt']}")
    try:
        r = requests.post("http://localhost:11434/api/generate", json=curl_data)
        summary = r.json()['response']
        logs.append(f"Summary result: {summary}")
    except requests.RequestException as e:
        logs.append(f"Error generating summary: {e}")
        return {"error": "Failed to generate summary", "logs": logs}

    ## Hash summary into IPFS
    ipfs_hash = store_on_ipfs(summary)
    print(f"IPFS Hash: {ipfs_hash}")

    output = {"speech": speech, "summary": summary, "ipfs": ipfs_hash, "logs": logs}
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
