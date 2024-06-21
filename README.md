# FastAPI File Upload and Processing Application

Cette application FastAPI permet de télécharger, traiter et analyser des fichiers texte,
audio et vidéo. Elle utilise IPFS pour le stockage des fichiers,
Whisper pour la transcription audio, et diverses commandes shell pour
l'interaction avec les systèmes externes.

## Prérequis

- Python 3.7 ou supérieur
- FastAPI
- Uvicorn
- Whisper
- IPFS
- yt-dlp
- OBS Studio avec WebSocket

## Installation

1. Clonez le dépôt :

    ```bash
    git clone https://github.com/papiche/AiApi
    cd AiApi
    ```

2. Créez un environnement virtuel et activez-le :

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Installez les dépendances :

    ```bash
    pip install fastapi uvicorn beautifulsoup4 whisper magic requests
    ```

4. Assurez-vous que IPFS, yt-dlp et OBS Studio sont installés et configurés sur votre système.

## Configuration

1. Démarrez le démon IPFS :

    ```bash
    ipfs daemon
    ```

2. Configurez OBS Studio pour accepter les commandes WebSocket.

## Utilisation

1. Lancez l'application :
    ```bash
    uvicorn api:app --host 0.0.0.0 --port 8000
    ```
ou `./api.py`


2. Accédez à l'API via `http://localhost:8000`.

## Endpoints

### `/g1vlog`
Transcrit une vidéo récupérée depuis IPFS.

- **Méthode** : `GET`
- **Paramètres** :
  - `cid` : CID du fichier IPFS
  - `file` : Nom du fichier
- **Réponse** :
  - `speech` : Transcription du fichier vidéo

### `/youtube`
Analyse une vidéo YouTube pour en extraire la durée et la convertir en secondes.

- **Méthode** : `GET`
- **Paramètres** :
  - `url` : URL de la vidéo YouTube
  - `pubkey` : Clé publique
- **Réponse** :
  - `logs` : Logs de l'opération
  - `error` : Message d'erreur (si applicable)

### `/tellme`
Utilise un modèle d'IA pour traiter et traduire du texte récupéré depuis IPFS.

- **Méthode** : `GET`
- **Paramètres** :
  - `cid` : CID du fichier IPFS
- **Réponse** :
  - `system` : Système utilisé
  - `prompt` : Invite utilisée
  - `tellme` : Résultat de l'IA

### `/upload`
Télécharge un fichier, vérifie son type et sa taille, puis l'ajoute à IPFS.

- **Méthode** : `POST`
- **Paramètres** :
  - `file` : Fichier à télécharger
- **Réponse** :
  - `cid` : CID du fichier ajouté à IPFS
  - `file` : Nom du fichier
  - `file_type` : Type de fichier
  - `mime_type` : Type MIME du fichier

### `/transactions`
Récupère et filtre des transactions basées sur une clé publique et une date optionnelle.

- **Méthode** : `GET`
- **Paramètres** :
  - `pubkey` : Clé publique
  - `date` : Date optionnelle (format YYYY-MM-DD)
- **Réponse** :
  - `csv_data` : Transactions formatées en CSV

### `/rec`
Démarre l'enregistrement vidéo via OBS Studio.

- **Méthode** : `GET`
- **Réponse** :
  - `message` : Message de confirmation

### `/stop`
Arrête l'enregistrement vidéo via OBS Studio.

- **Méthode** : `GET`
- **Réponse** :
  - `message` : Message de confirmation


# UI `templates/index.html`


L'interface utilisateur (UI) est définie dans un fichier HTML avec du JavaScript pour gérer les interactions avec l'API. Voici une description des principales fonctionnalités de l'UI :

### Structure HTML

- **Container Principal** : Contient les formulaires et les résultats.
- **Formulaire YouTube** : Permet à l'utilisateur d'entrer une URL de vidéo YouTube et une clé publique pour traiter la vidéo.
- **Formulaire de Téléchargement** : Permet à l'utilisateur de télécharger un fichier (texte, audio ou vidéo) pour le traitement.
- **Indicateurs de Chargement** : Affichent des spinners pour indiquer que des opérations sont en cours.
- **Containers de Résultats** : Affichent les résultats des opérations et les messages d'erreur.

### JavaScript

Le JavaScript gère les interactions utilisateur et les appels API. Voici les principales fonctions :

#### `uploadFile()`

Cette fonction gère le téléchargement de fichiers et leur traitement :

1. **Récupération du Fichier** : Récupère le fichier sélectionné par l'utilisateur.
2. **Validation de la Taille** : Vérifie que la taille du fichier ne dépasse pas 100 MB.
3. **Envoi du Fichier** : Envoie le fichier à l'endpoint `/upload` de l'API.
4. **Traitement du Résultat** :
   - Si le fichier est de type texte, affiche un bouton pour traiter le texte via l'endpoint `/tellme`.
   - Si le fichier est de type vidéo, affiche un bouton pour traiter la vidéo via l'endpoint `/g1vlog`.
5. **Gestion des Erreurs** : Affiche les messages d'erreur en cas de problème.

#### `processYouTube()`

Cette fonction gère le traitement des vidéos YouTube :

1. **Récupération des Entrées** : Récupère l'URL de la vidéo YouTube et la clé publique entrées par l'utilisateur.
2. **Envoi de la Requête** : Envoie une requête à l'endpoint `/youtube` de l'API.
3. **Traitement du Résultat** :
   - Affiche un bouton pour transcrire la vidéo via l'endpoint `/g1vlog`.
4. **Gestion des Erreurs** : Affiche les messages d'erreur en cas de problème.


## Développement

Pour contribuer à ce projet, veuillez suivre les étapes ci-dessous :

1. Forkez le dépôt.
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/ma-fonctionnalite`).
3. Commitez vos modifications (`git commit -am 'Ajoute une nouvelle fonctionnalité'`).
4. Poussez votre branche (`git push origin feature/ma-fonctionnalite`).
5. Créez une Pull Request.

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
