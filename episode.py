import requests
import time
import hashlib
import sqlite3
import subprocess
import os
import re
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import mistune
import anthropic

SMTP_SERVER = 'mail.server'
SMTP_PORT = 25
RECIPIENT_EMAIL = 'email@domain.com'
SENDER_EMAIL = 'sender@domain.com'
markdown = mistune.create_markdown()
api_key = 'key'  # Podcast Indexer Key
api_secret = 'key'  # Podcast Indexer Secret

def generate_headers(api_key, api_secret):
    """
    Generate the authorization headers for the Podcast Index API.

    Args:
        api_key (str): The API key.
        api_secret (str): The API secret.

    Returns:
        dict: The authorization headers.
    """
    current_time = str(int(time.time()))
    data = api_key + api_secret + current_time
    sha1_hash = hashlib.sha1(data.encode()).hexdigest()
    headers = {
        'X-Auth-Date': current_time,
        'X-Auth-Key': api_key,
        'Authorization': sha1_hash,
        'User-Agent': 'PodcastJay'
    }
    return headers

def get_episode_data_by_episode_id(api_key, api_secret, episode_id):
    """
    Get the episode data for a given episode ID.

    Args:
        api_key (str): The API key.
        api_secret (str): The API secret.
        episode_id (str): The episode ID.

    Returns:
        dict: The episode data, including audio_url, title, and url.
    """
    headers = generate_headers(api_key, api_secret)
    lookup_url = f'https://api.podcastindex.org/api/1.0/episodes/byid?id={episode_id}'
    response = requests.get(lookup_url, headers=headers)
    if response.status_code == 200:
        episode_data = response.json()
        if 'episode' in episode_data:
            episode = episode_data['episode']
            enclosure_url = episode.get('enclosureUrl')
            title = episode.get('title')
            if enclosure_url:
                return {'audio_url': enclosure_url, 'title': title, 'url': lookup_url}
    else:
        print(f"API call failed with status code {response.status_code} for episode_id {episode_id}")
    return None

def write_to_file(data, name):
    """
    Write data to a file with the specified name.

    Args:
        data (str): The data to write to the file.
        name (str): The name of the file.
    """
    filename = f"transcripts/{name}.txt"
    with open(filename, 'w') as file:
        file.write(str(data))

def send_email(html_content, source):
    """
    Send an email with the provided HTML content.

    Args:
        html_content (str): The HTML content of the email.
        source (str): The source of the email content.
    """
    image_path = 'header.png'
    msg = MIMEMultipart('related')
    msg['Subject'] = f"Podcast Summary: {source}."
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.preamble = 'This is a multi-part message in MIME format.'
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    html_content_with_header_image = f"""\
    <html>
      <head></head>
      <body>
        <img src="cid:header_image" style="width: 600px; height: auto;">
        {html_content}
      </body>
    </html>
    """
    msg_html = MIMEText(html_content_with_header_image, 'html')
    msg_alternative.attach(msg_html)
    with open(image_path, 'rb') as image_file:
        msg_image = MIMEImage(image_file.read())
    msg_image.add_header('Content-ID', '<header_image>')
    msg.attach(msg_image)
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.sendmail(f"Podcast Summary <{SENDER_EMAIL}>", RECIPIENT_EMAIL, msg.as_string())

def query_claude(prompt):
    """
    Query the Claude API with the provided prompt.

    Args:
        prompt (str): The prompt to send to the Claude API.

    Returns:
        str: The response from the Claude API.
    """
    client = anthropic.Anthropic(api_key="sk-ant-api03-key")
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def convert_audio_to_wav(mp3_file, wav_file):
    """
    Convert an MP3 audio file to WAV format.

    Args:
        mp3_file (str): The path to the MP3 file.
        wav_file (str): The path to save the WAV file.

    Returns:
        bool: True if the conversion was successful, False otherwise.
    """
    try:
        subprocess.run(["ffmpeg", "-i", mp3_file, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_file], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during audio conversion: {e}")
        return False

def transcribe_audio_with_whisper(audio_file):
    """
    Transcribe an audio file using a local Whisper model.

    Args:
        audio_file (str): The path to the audio file.

    Returns:
        str: The transcription of the audio file, or None if an error occurred.
    """
    if not os.path.isfile(audio_file):
        print(f"Error: Audio file '{audio_file}' does not exist.")
        return None

    try:
        whisper_command = [
            "/usr/bin/whisper",
            "--model", "medium",
            "--output_format", "txt",
            " ", audio_file
        ]
        result = subprocess.run(whisper_command, capture_output=True, text=True)
        if result.returncode == 0:
            transcript = result.stdout.strip()
            return transcript
        else:
            print(f"Error during transcription. Return code: {result.returncode}")
            print(f"Error message: {result.stderr}")
            return None
    except FileNotFoundError:
        print("Error: Whisper command not found. Make sure Whisper is installed and accessible.")
        return None

# Create a directory to store the downloaded audio files
audio_directory = 'podcast_audio'
os.makedirs(audio_directory, exist_ok=True)

with open(f"prompt.txt", 'r') as file:
    prompt = file.read().strip()

with open('episodes.txt', 'r') as episodes_file:
    for episode_url in episodes_file:
        episode_url = episode_url.strip()
        print(f"Processing episode URL: {episode_url}")

        # Extract the episode ID from the URL
        episode_id = episode_url.split('/')[-1].split('?')[0]

        # Get the episode data using the episode ID
        episode_data = get_episode_data_by_episode_id(api_key, api_secret, episode_id)
        if episode_data:
            audio_url = episode_data['audio_url']
            title = episode_data['title']

            # Clean up the filename by removing query parameters
            filename = os.path.basename(audio_url)
            cleaned_filename = re.sub(r'\?.*', '', filename)

            # Download the audio file
            mp3_filename = os.path.join(audio_directory, cleaned_filename)
            response = requests.get(audio_url)
            if response.status_code == 200:
                with open(mp3_filename, 'wb') as audio_file:
                    audio_file.write(response.content)
                print(f"Audio file downloaded: {mp3_filename}")

                wav_filename = os.path.join(audio_directory, f"{os.path.splitext(cleaned_filename)[0]}.wav")
                if convert_audio_to_wav(mp3_filename, wav_filename):
                    print(f"Audio file converted to WAV: {wav_filename}")

                    transcript = transcribe_audio_with_whisper(wav_filename)
                    if transcript:
                        write_to_file(transcript, os.path.splitext(cleaned_filename)[0])
                        summary = prompt + "\n\n" + transcript
                        content = query_claude(summary)
                        content_email = markdown(content)
                        send_email(content_email, title)
                    else:
                        print(f"Failed to transcribe audio file: {wav_filename}")
                else:
                    print(f"Failed to convert audio file to WAV: {mp3_filename}")
            else:
                print(f"Failed to download audio file: {audio_url}")
        else:
            print(f"Failed to retrieve episode data for episode ID: {episode_id}")

print("Finished processing episodes.")
