# Podcast Transcription and Summarization

This project automates the process of transcribing and summarizing podcast episodes using the Podcast Index API, Whisper, and the Claude API. It retrieves the latest episodes from specified podcast feeds, downloads the audio files, transcribes them using Whisper, and generates summaries using the Claude API. The summaries are then sent via email.

## Prerequisites

Before running the code, make sure you have the following:

1. Python 3.x installed on your system.
2. An API key and secret from the Podcast Index API. Register at [https://podcastindex.org](https://podcastindex.org) to obtain the necessary credentials.
3. Whisper installed on your system. Follow the installation instructions at [https://github.com/openai/whisper](https://github.com/openai/whisper).
4. FFmpeg installed on your system. It is used for audio file conversion.
5. An API key for the Claude API from Anthropic. Sign up at [https://www.anthropic.com](https://www.anthropic.com) to get your API key.

## Installation

1. Clone this repository to your local machine:
   ```
   git clone https://github.com/jschulman/ai-podcast.git
   ```

2. Navigate to the project directory:
   ```
   cd ai-podcast
   ```

3. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

4. Update the configuration variables in the code:
   - Set the `SMTP_SERVER`, `SMTP_PORT`, and `RECIPIENT_EMAIL` variables with your email server details and recipient email address.
   - Replace the placeholders for `api_key` and `api_secret` with your Podcast Index API credentials.
   - Update the `api_key` variable with your Claude API key.

## Usage

1. Prepare a text file named `podcasts.txt` and add the feed IDs of the podcasts you want to process, with each feed ID on a separate line.  If you just want to download specific episodes, put the episode IDs in the episodes.txt file.

2. Edit the text file named `prompt.txt` and modify the prompt you want to use for generating summaries. The prompt will be appended to the transcription before sending it to the Claude API.

3. Run the script for Podcast Series:
   ```
   python series.py
   ```

or run the script for Podcast Episodes:
   ```
   python episode.py
   ```

   The series script will retrieve the latest episodes for each feed ID specified in `podcasts.txt`, download the audio files, transcribe them using Whisper, generate summaries using the Claude API, and send the summaries via email.  The episode script will only download, transcribe and summarize the episodes desired.

4. Check the console output for progress and any error messages.

5. The transcriptions will be saved as text files in the `transcripts` directory.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgements

- [Podcast Index API](https://podcastindex.org) for providing access to podcast data.
- [Whisper](https://github.com/openai/whisper) for the audio transcription functionality.
- [Claude API](https://www.anthropic.com) for generating summaries.
- [FFmpeg](https://ffmpeg.org) for audio file conversion.

```
