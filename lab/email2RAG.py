import imaplib
import email
from email.header import decode_header
import ollama
import chromadb
from chromadb.config import Settings
import logging
from logging.handlers import RotatingFileHandler
import sys
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration du logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('email_rag.log', maxBytes=10000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Configuration de ChromaDB
try:
    chroma_client = chromadb.Client(Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory="./chroma_db"
    ))
    collection = chroma_client.get_or_create_collection(name="email_collection")
    logger.info("Connexion à ChromaDB établie avec succès")
except Exception as e:
    logger.error(f"Erreur lors de la connexion à ChromaDB: {str(e)}")
    sys.exit(1)

def lire_emails(imap_server, email, password):
    try:
        imap = imaplib.IMAP4_SSL(imap_server)
        imap.login(email, password)
        imap.select("INBOX")

        _, message_numbers = imap.search(None, "UNSEEN")

        for num in message_numbers[0].split():
            _, msg_data = imap.fetch(num, "(RFC822)")
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)

            sujet = decode_header(email_message["Subject"])[0][0]
            if isinstance(sujet, bytes):
                sujet = sujet.decode()

            contenu = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        contenu = part.get_payload(decode=True).decode()
            else:
                contenu = email_message.get_payload(decode=True).decode()

            yield sujet, contenu

        imap.close()
        imap.logout()
    except imaplib.IMAP4.error as e:
        logger.error(f"Erreur IMAP lors de la lecture des emails: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la lecture des emails: {str(e)}")
        logger.error(traceback.format_exc())

def envoyer_email(smtp_server, smtp_port, sender_email, sender_password, recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = f"Re: {subject}"

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        logger.info(f"Réponse envoyée avec succès à {recipient}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email à {recipient}: {str(e)}")
        logger.error(traceback.format_exc())

def stocker_exemple_positif(question, reponse, utilisateur_id):
    collection.add(
        documents=[f"Q: {question}\nR: {reponse}"],
        metadatas=[{"type": "exemple_positif", "user_id": utilisateur_id}],
        ids=[f"exemple_{hash(question)}_{utilisateur_id}"]
    )
    logger.info(f"Exemple positif stocké avec succès pour l'utilisateur {utilisateur_id}")

def stocker_exemple_negatif(question, utilisateur_id):
    collection.add(
        documents=[f"Q: {question}"],
        metadatas=[{"type": "exemple_negatif", "user_id": utilisateur_id}],
        ids=[f"erreur_{hash(question)}_{utilisateur_id}"]
    )
    logger.info(f"Exemple négatif stocké avec succès pour l'utilisateur {utilisateur_id}")

def generer_reponse(contenu, utilisateur_id):
    try:
        model_name = utilisateur_id  # Utilisation directe de utilisateur_id comme nom du modèle

        embedding = ollama.embeddings(model=model_name, prompt=contenu)["embedding"]

        exemples_positifs = collection.query(
            query_embeddings=[embedding],
            where={"type": "exemple_positif", "user_id": utilisateur_id},
            n_results=3
        )

        contexte_exemples = "\n".join(exemples_positifs['documents'][0])

        prompt = f"Exemples précédents:\n{contexte_exemples}\n\nEmail actuel:\n{contenu}\n\nRéponse:"
        response = ollama.chat(model=model_name, messages=[
            {
                'role': 'system',
                'content': 'Vous êtes un assistant email intelligent. Utilisez les exemples précédents et le contexte fourni pour générer une réponse pertinente.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ])

        return response['message']['content']
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la réponse pour l'utilisateur {utilisateur_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return "Désolé, une erreur s'est produite lors de la génération de la réponse."

def analyser_erreurs():
    try:
        erreurs = collection.query(
            query_embeddings=None,
            where={"type": "exemple_negatif"},
            n_results=100
        )

        # Ici, vous pourriez implémenter une logique pour analyser les erreurs communes
        # et ajuster votre modèle ou vos prompts en conséquence
        logger.info(f"Analyse de {len(erreurs['documents'])} erreurs effectuée")
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des erreurs: {str(e)}")
        logger.error(traceback.format_exc())

def traiter_emails_et_appliquer_rag(imap_server, email, password, smtp_server, smtp_port, utilisateur_id):
    emails_traites = 0
    try:
        for sujet, contenu in lire_emails(imap_server, email, password):
            logger.info(f"Traitement de l'email avec le sujet: {sujet}")

            expediteur = email.utils.parseaddr(email.message_from_string(contenu)['From'])[1]

            if contenu.strip().endswith("OK!"):
                reponse_generee = generer_reponse(contenu, utilisateur_id)
                stocker_exemple_positif(contenu, reponse_generee, utilisateur_id)
            elif contenu.strip().endswith("KO!"):
                stocker_exemple_negatif(contenu, utilisateur_id)
                reponse_generee = "Nous sommes désolés que notre réponse précédente n'ait pas été satisfaisante. Nous allons analyser votre demande pour améliorer notre service."
            else:
                reponse_generee = generer_reponse(contenu, utilisateur_id)

            envoyer_email(smtp_server, smtp_port, email, password, expediteur, sujet, reponse_generee)

            emails_traites += 1
            if emails_traites % 100 == 0:
                analyser_erreurs()

    except Exception as e:
        logger.error(f"Erreur générale dans le processus de traitement des emails: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        logger.info("Démarrage du processus de traitement des emails")

        # Charger les variables d'environnement depuis le fichier .env
        IMAP_SERVER = os.getenv("IMAP_SERVER")
        SMTP_SERVER = os.getenv("SMTP_SERVER")
        SMTP_PORT = int(os.getenv("SMTP_PORT"))
        EMAIL = os.getenv("EMAIL")
        PASSWORD = os.getenv("PASSWORD")
        UTILISATEUR_ID = sys.argv[1] if len(sys.argv) > 1 else "gwen2"

        traiter_emails_et_appliquer_rag(IMAP_SERVER, EMAIL, PASSWORD, SMTP_SERVER, SMTP_PORT, UTILISATEUR_ID)
        logger.info("Fin du processus de traitement des emails")
    except KeyboardInterrupt:
        logger.info("Processus interrompu par l'utilisateur")
    except Exception as e:
        logger.critical(f"Erreur critique: {str(e)}")
        logger.critical(traceback.format_exc())