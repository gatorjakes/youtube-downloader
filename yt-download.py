import pytube
import os
import subprocess
import re
import time
from tqdm import tqdm
from threading import Thread, Semaphore, Lock

# Global variables to track playlist progress
total_videos = 1
current_video_number = 1

class ProgressBarManager:
    def __init__(self):
        self.bars = {}
        self.lock = Lock()

    def create_bar(self, key, total_size, title):
        with self.lock:
            self.bars[key] = tqdm(total=total_size, unit='B', unit_scale=True, desc=title, leave=True)

    def update_bar(self, key, progress):
        with self.lock:
            if key in self.bars:
                self.bars[key].n = progress
                self.bars[key].refresh()

    def close_bar(self, key):
        with self.lock:
            if key in self.bars:
                self.bars[key].close()
                del self.bars[key]

progress_manager = ProgressBarManager()

def on_progress(stream, chunk, bytes_remaining):
    global total_videos
    global current_video_number
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining

    if stream.title not in progress_manager.bars:
        progress_manager.create_bar(stream.title, total_size, f'{stream.title} ({current_video_number}/{total_videos})')

    progress_manager.update_bar(stream.title, bytes_downloaded)

    if bytes_remaining == 0:
        progress_manager.close_bar(stream.title)
        current_video_number += 1

def fetch_streams(youtube):
    video_streams = youtube.streams.filter(adaptive=True, only_video=True).order_by('resolution')
    audio_stream = youtube.streams.filter(only_audio=True).order_by('abr').desc().first()
    
    return video_streams, audio_stream

def deduplicate_streams(streams):
    unique_resolutions = {}
    for stream in streams:
        if stream.resolution not in unique_resolutions:
            unique_resolutions[stream.resolution] = stream
    return list(unique_resolutions.values())

def find_best_available_resolution(video_streams, preferred_resolution):
    available_resolutions = [stream.resolution for stream in video_streams]
    if preferred_resolution in available_resolutions:
        return preferred_resolution
    else:
        sorted_resolutions = sorted(available_resolutions, key=lambda x: int(x[:-1]), reverse=True)
        return sorted_resolutions[0] if sorted_resolutions else None

def select_stream(video_streams, audio_stream, resolution_choice):
    unique_streams = deduplicate_streams(video_streams)
    resolution_map = {1: '2160p', 2: '1080p', 3: '720p', 4: '480p', 5: 'audio'}

    if resolution_choice in resolution_map:
        if resolution_choice == 5:
            return None, audio_stream
        else:
            preferred_resolution = resolution_map[resolution_choice]
            best_resolution = find_best_available_resolution(unique_streams, preferred_resolution)
            for stream in unique_streams:
                if stream.resolution == best_resolution:
                    return stream, audio_stream

    highest_resolution_stream = max(unique_streams, key=lambda x: int(x.resolution[:-1]))
    return highest_resolution_stream, audio_stream

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def download_and_merge_streams(video_stream, audio_stream, path='.', file_suffix=''):
    global progress_manager
    
    sanitized_title = sanitize_filename(video_stream.title if video_stream else audio_stream.title)
    final_path = ''  # Initialize final_path to ensure it has a value

    if video_stream is None:
        # Audio-only download
        audio_path = audio_stream.download(output_path=path, filename_prefix="audio_")
        final_audio_filename = f"{sanitized_title}_{file_suffix}.mp3"
        final_path = os.path.join(path, final_audio_filename)

        # Convert to mp3 using ffmpeg
        ffmpeg_command = ['ffmpeg', '-i', audio_path, '-vn', '-ab', '128k', '-ar', '44100', '-y', '-c:a', 'libmp3lame', final_path]
        process = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Optional: Print ffmpeg output for troubleshooting
        print("ffmpeg stdout:", process.stdout.decode())
        print("ffmpeg stderr:", process.stderr.decode())

        os.remove(audio_path)  # Cleanup original download
    else:
        # Video and audio download
        video_path = video_stream.download(output_path=path, filename_prefix="video_")
        audio_path = audio_stream.download(output_path=path, filename_prefix="audio_")
        final_filename = f"{sanitized_title}_{file_suffix}.mp4"
        final_path = os.path.join(path, final_filename)

        # Use ffmpeg to merge video and audio
        ffmpeg_command = ['ffmpeg', '-i', video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', final_path]
        subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        os.remove(video_path)
        os.remove(audio_path)

    return final_path

def download_youtube_video(url, path='.', index=None, resolution_choice=None):
    global current_video_number
    try:
        youtube = pytube.YouTube(url, on_progress_callback=on_progress)
        video_streams, audio_stream = fetch_streams(youtube)

        if not video_streams and not audio_stream:
            print("No downloadable streams found.")
            return None

        selected_video_stream, selected_audio_stream = select_stream(video_streams, audio_stream, resolution_choice)

        file_suffix = str(int(time.time())) if index is None else str(index)
        final_video_path = download_and_merge_streams(selected_video_stream, selected_audio_stream, path, file_suffix)
        print(f"\nDownloaded video to '{final_video_path}' successfully.")

    except pytube.exceptions.PytubeError as e:
        print(f"An error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def download_youtube_playlist(playlist_url, path='.', resolution_choice=None, max_threads=5):
    global total_videos
    global current_video_number
    playlist = pytube.Playlist(playlist_url)
    total_videos = len(playlist.video_urls)
    current_video_number = 1
    print(f"Found {total_videos} videos in the playlist.")

    semaphore = Semaphore(max_threads)
    threads = []

    for index, url in enumerate(playlist.video_urls):
        semaphore.acquire()
        thread = Thread(target=threaded_download, args=(url, path, index, resolution_choice, semaphore))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

def threaded_download(url, path, index, resolution_choice, semaphore):
    try:
        download_youtube_video(url, path, index, resolution_choice=resolution_choice)
    finally:
        semaphore.release()

if __name__ == "__main__":
    while True:
        url = input("Enter the YouTube video or playlist URL (or type 'exit' to quit): ")
        if url.lower() in ['exit', 'quit']:
            print("Exiting program.")
            break

        print("Select the resolution:")
        print("1: 2160p (4K)")
        print("2: 1080p")
        print("3: 720p")
        print("4: 480p")
        print("5: Audio Only")
        try:
            resolution_choice = int(input("Enter your choice (1-5): "))
            if resolution_choice not in range(1, 6):
                print("Invalid choice. Please enter a number between 1 and 5.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 5.")
            continue

        if "playlist" in url:
            download_youtube_playlist(url, resolution_choice=resolution_choice)
        else:
            total_videos = 1
            current_video_number = 1
            download_youtube_video(url, resolution_choice=resolution_choice)

        print("\nDownload completed. Ready for the next download.")
