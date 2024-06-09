# FastAPI File Upload and Processing Application

Cette application FastAPI permet de télécharger, traiter et analyser des fichiers texte, audio et vidéo. Elle utilise IPFS pour le stockage des fichiers, Whisper pour la transcription audio, et diverses commandes shell pour l'interaction avec les systèmes externes.

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

1. Démarrez l'application FastAPI :

    ```bash
    uvicorn main:app --reload
    ```

2. Ouvrez votre navigateur et accédez à `http://127.0.0.1:8000` pour voir le formulaire de téléchargement de fichiers.

### Endpoints

- **GET /** : Affiche le formulaire HTML pour le téléchargement de fichiers.
- **POST /upload** : Télécharge un fichier, détermine son type, et l'ajoute à IPFS.
- **GET /tellme** : Analyse le contenu d'un fichier texte à partir de son CID sur IPFS, le résume et le traduit en français.
- **GET /g1vlog** : Vérifie si un fichier vidéo est au format x264, le télécharge, et utilise Whisper pour transcrire le contenu audio en texte.
- **GET /youtube** : Télécharge une vidéo YouTube, vérifie sa durée, la transcrit, et traduit le résumé en français.
- **GET /transactions** : Récupère l'historique des transactions d'une clé publique donnée et les formate en CSV.
- **GET /rec** : Démarre l'enregistrement vidéo avec OBS Studio.
- **GET /stop** : Arrête l'enregistrement vidéo avec OBS Studio.

### Exemple de Téléchargement de Fichier

1. Sélectionnez un fichier à télécharger (texte, audio ou vidéo).
2. Cliquez sur le bouton "Upload".
3. Une fois le fichier téléchargé, un CID sera affiché.
4. Utilisez les boutons "Process Text" ou "Process Video" pour analyser le fichier.

### Exemple de Traitement de Vidéo YouTube

1. Accédez à l'endpoint `/youtube` avec l'URL de la vidéo YouTube en paramètre.
2. La vidéo sera téléchargée, transcrite et résumée.

## Développement

Pour contribuer à ce projet, veuillez suivre les étapes ci-dessous :

1. Forkez le dépôt.
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/ma-fonctionnalite`).
3. Commitez vos modifications (`git commit -am 'Ajoute une nouvelle fonctionnalité'`).
4. Poussez votre branche (`git push origin feature/ma-fonctionnalite`).
5. Créez une Pull Request.

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
