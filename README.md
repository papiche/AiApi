# AiApi
AiApi provide whisper video/audio 2 speech transcription and mistral AI interactions

## collaborative Pad

https://pad.p2p.legal/gpu_ynov

### Usage:
Running the API:
```
uvicorn api:app --host 0.0.0.0
```

### Api endpoints:
```
http://<host>/tellme
```

Request type : GET
Params: cid : string
Returns: [{“system” : system, "prompt" : prompt , “tellme” : resume_of_cid_content }]

```
http://<host>/youtube
```

Request type : GET
Params: url : string
Returns: [{“speech” : video_speech, “resume” : a_resume_of_the_speech}]

### Technical details

* Le script fait appel à l’outil yt-dlp pour télécharger la vidéo à partir du lien fourni en paramètre de la requête GET
* La librairie Whisper est utilisée pour récupérer le texte associé à l’audio de la vidéo
* Le texte est ajouté en prompt à un modèle (voir script) pour obtenir un résumé en anglais de ce texte
* Le résumé est traduis en français par un deuxième appel à un LLM

### Notes importantes

* la vidéo ne doit pas dépasser 3 minutes. (Dépends de la RAM / GPU)
* l’API Whisper gére mieux les paroles anglais que français.
* La traduction du résumé des paroles peut être partiellement incorrect selon le modèle utilisé

https://gist.github.com/mberman84/ea207e7d9e5f8c5f6a3252883ef16df3
https://microsoft.github.io/autogen/
