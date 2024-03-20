# YouTube Downloader Script

This Python script allows you to download YouTube videos and playlists with various resolution options, including 4K, 1080p, 720p, 480p, or just the audio. It uses `pytube` to fetch video details and download streams, and `ffmpeg` to merge video and audio streams into a single file when necessary. Progress tracking is implemented via `tqdm` for a visually appealing and informative download progress bar.

## Features

- Download individual YouTube videos or entire playlists.
- Choose between different video resolutions or download only the audio.
- Progress bars for each download.
- Automatic merging of video and audio streams for the best quality.
- Filename sanitization to avoid issues with incompatible characters.

## Dependencies

To run this script, you need Python 3 and the following packages:
- `pytube`: For fetching YouTube video details and downloading.
- `tqdm`: For displaying download progress bars.
- `ffmpeg`: Required for merging video and audio streams (must be installed separately).

Install Python dependencies using pip:

Ensure `ffmpeg` is installed and accessible in your system's PATH.

## Usage

1. Clone this repository or copy the script into a local file.
2. Install the required Python dependencies.
3. Run the script in your terminal or command prompt:


4. Follow the on-screen prompts to enter a YouTube video or playlist URL and choose the desired resolution.

## License

This script is provided "as is", without warranty of any kind, express or implied. Feel free to use and modify it for your personal use.

## Contributions

Contributions are welcome! If you have suggestions for improvements or bug fixes, please open an issue or a pull request.

## Disclaimer

This script is for educational purposes only. Please ensure you have the right to download content from YouTube and use it in compliance with YouTube's Terms of Service.



