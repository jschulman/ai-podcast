import requests
import time
import hashlib
import sqlite3
import subprocess
import os
import smtplib
import re
import json
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import mistune
import anthropic

SMTP_SERVER = 'mail.server'
SMTP_PORT = 25
RECIPIENT_EMAIL = 'email@domain.com'
markdown = mistune.create_markdown()

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

def write_to_file(data, name):
    """
    Write data to a file with a cleaned-up name.

    Args:
        data (str): The data to write to the file.
        name (str): The name to use for the file.
    """
    cleaned_name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    cleaned_name = re.sub(r'\s+', '_', cleaned_name)
    filename = f"/directory/transcripts/{cleaned_name}.txt"
    with open(filename, 'w') as file:
        file.write(str(data))

def send_email(html_content, source):
    """
    Send an email with the provided HTML content.

    Args:
        html_content (str): The HTML content of the email.
        source (str): The source of the email content.
    """
    image_path = '/directory/header.png'
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
    client = anthropic.Anthropic(api_key="sk-ant-key")
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def get_latest_episode_data_by_feed_id(api_key, api_secret, feed_id):
    """
    Get the latest episode data for a given feed ID.

    Args:
        api_key (str): The API key.
        api_secret (str): The API secret.
        feed_id (str): The feed ID.

    Returns:
        dict: The latest episode data, including episode_id, audio_url, title, and url.
    """
    headers = generate_headers(api_key, api_secret)
    lookup_url = f'https://api.podcastindex.org/api/1.0/episodes/byfeedid?id={feed_id}&max=1'
    response = requests.get(lookup_url, headers=headers)
    if response.status_code == 200:
        lookup_results = response.json()
        if 'items' in lookup_results and lookup_results['items']:
            latest_episode = lookup_results['items'][0]
            episode_id = latest_episode.get('id')
            enclosure_url = latest_episode.get('enclosureUrl')
            title = latest_episode.get('title')
            if episode_id and enclosure_url:
                return {'episode_id': episode_id, 'audio_url': enclosure_url, 'title': title, 'url': lookup_url}
    else:
        print(f"API call failed with status code {response.status_code} for feed_id {feed_id}")
    return None

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
        subprocess.run(["ffmpeg", "-loglevel", "quiet", "-i", mp3_file, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_file], check=True)
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

# Initialize the SQLite database and table
conn = sqlite3.connect('/directory/podcasts.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS podcast_episodes (
    feed_id INTEGER,
    episode_id INTEGER,
    PRIMARY KEY (feed_id, episode_id)
)
''')
conn.commit()

api_key = 'key'  # Podcast Indexer Key
api_secret = 'key'  # Podcast Indexer Secret

# Create a directory to store the downloaded audio files
audio_directory = '/directory/podcast_audio'
os.makedirs(audio_directory, exist_ok=True)

with open(f"/directory/prompt.txt", 'r') as file:
    prompt = file.read().strip()

with open('/directory/podcasts.txt', 'r') as podcasts_file, open('/directory/podcast-links.txt', 'w') as podcast_links_file:
    for feed_id in podcasts_file:
        feed_id = feed_id.strip()
        print(f"Searching for feed ID: {feed_id}")
        episode_data = get_latest_episode_data_by_feed_id(api_key, api_secret, feed_id)
        if episode_data:
            title = episode_data['title']
            print(f"Title: {episode_data['title']}")
            print(f"URL: {episode_data['url']}")
            cursor.execute('SELECT episode_id FROM podcast_episodes WHERE feed_id = ?', (feed_id,))
            db_episode_id = cursor.fetchone()
            if db_episode_id is None or db_episode_id[0] != episode_data['episode_id']:
                if db_episode_id is None:
                    cursor.execute('INSERT INTO podcast_episodes (feed_id, episode_id) VALUES (?, ?)', (feed_id, episode_data['episode_id']))
                else:
                    cursor.execute('UPDATE podcast_episodes SET episode_id = ? WHERE feed_id = ?', (episode_data['episode_id'], feed_id))
                conn.commit()

                podcast_links_file.write(f"{episode_data['audio_url']}\n")
                print(f"New episode found for feed ID: {feed_id}")

                audio_url = episode_data['audio_url']
                mp3_filename = os.path.join(audio_directory, f"{feed_id}_{episode_data['episode_id']}.mp3")
                response = requests.get(audio_url)
                if response.status_code == 200:
                    with open(mp3_filename, 'wb') as audio_file:
                        audio_file.write(response.content)
                    print(f"Audio file downloaded: {mp3_filename}")

                wav_filename = os.path.join(audio_directory, f"{feed_id}_{episode_data['episode_id']}.wav")
                if convert_audio_to_wav(mp3_filename, wav_filename):
                    print(f"Audio file converted to WAV: {wav_filename}")

                    transcript = transcribe_audio_with_whisper(wav_filename)
                    if transcript:
                        write_to_file(transcript, title)
                        summary = prompt + "\n\n" + transcript + "\n</transcript>"
                        content = query_claude(summary)
                        content_email = markdown(content)
                        send_email(content_email, title)
                    else:
                        print(f"Failed to transcribe audio file: {wav_filename}")
                else:
                    print(f"Failed to convert audio file to WAV: {mp3_filename}")
            else:
                print(f"Failed to download audio file for feed ID: {feed_id}")

print("Finished checking for new episodes and downloading audio files.")
