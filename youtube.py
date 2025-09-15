import argparse
import logging
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import yt_dlp

# --- Defaults ---
DEFAULT_DOWNLOAD_PATH = 'downloads/%(channel)s/%(upload_date)s - %(title)s [%(id)s].%(ext)s'
DEFAULT_FILENAME_SUFFIX = "Processed"
DEFAULT_LOG_FILE = 'downloader.log'
DEFAULT_DOWNLOAD_ARCHIVE = 'downloaded.txt'
DEFAULT_PROCESSED_ARCHIVE = 'processed.txt'
MAX_CONCURRENT_PROCESSES = 2
DEFAULT_VIDEO_QUALITY = '1080'
DEFAULT_AUDIO_FORMAT = 'mp3'
DEFAULT_AUDIO_BITRATE = '192'
DEFAULT_SUB_LANGS = 'en'
DEFAULT_CRF = 18
DEFAULT_PRESET = 'slow'
DEFAULT_PROCESS_MODE = 'encode'
DEFAULT_AUDIO_CODEC_MODE = 'encode'


# --- Logging ---
def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


# --- Helpers ---
def sanitize_filename(name):
    """Remove invalid characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def sanitize_info(info):
    """Sanitize metadata fields before yt-dlp writes files."""
    for key in ["title", "channel", "playlist_title"]:
        if key in info and info[key]:
            info[key] = sanitize_filename(info[key])
    return info


# --- CLI Parser ---
def create_arg_parser():
    parser = argparse.ArgumentParser(
        description="Advanced YouTube Downloader and Processor",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('url_or_identifier', help="Channel URL, channel ID, or playlist URL.")
    
    group_path = parser.add_argument_group('Paths and Archive Options')
    group_path.add_argument('--output-path', '-o', default=DEFAULT_DOWNLOAD_PATH, help="Output path template.")
    group_path.add_argument('--archive-file', default=DEFAULT_DOWNLOAD_ARCHIVE, help="Download archive file.")
    group_path.add_argument('--processed-archive', default=DEFAULT_PROCESSED_ARCHIVE, help="Processed archive file.")
    group_path.add_argument('--log-file', default=DEFAULT_LOG_FILE, help="Log file.")

    group_quality = parser.add_argument_group('Quality and Format Options')
    group_quality.add_argument('--audio-only', '-a', action='store_true', help="Download audio only.")
    group_quality.add_argument('--audio-format', default=DEFAULT_AUDIO_FORMAT, help="Audio format (e.g., mp3, m4a, flac).")
    group_quality.add_argument('--audio-bitrate', default=DEFAULT_AUDIO_BITRATE, help="Audio bitrate in kbps (e.g., 128, 192, 320).")
    group_quality.add_argument('--quality', default=DEFAULT_VIDEO_QUALITY, help="Video quality (e.g., 1080, 720).")
    
    group_subs = parser.add_argument_group('Subtitle Options (video only)')
    group_subs.add_argument('--subtitles', '--subs', action='store_true', help="Embed subtitles.")
    group_subs.add_argument('--sub-langs', default=DEFAULT_SUB_LANGS, help="Subtitle languages list.")

    group_processing = parser.add_argument_group('Processing Options')
    group_processing.add_argument('--filename-suffix', default=DEFAULT_FILENAME_SUFFIX, help="Suffix to add after processing.")
    group_processing.add_argument('--skip-processing', action='store_true', help="Skip manual processing stage.")
    group_processing.add_argument('--process-mode', choices=['copy', 'encode'], default=DEFAULT_PROCESS_MODE, help="Video processing mode:\n- encode: re-encode video (default).\n- copy: fast copy without re-encoding.")
    group_processing.add_argument('--crf', type=int, default=DEFAULT_CRF, help=f"CRF value for x264 encoding (lower = better quality). Default: {DEFAULT_CRF}")
    group_processing.add_argument('--preset', choices=['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow'], default=DEFAULT_PRESET, help="x264 encoding speed preset.")
    group_processing.add_argument('--audio-codec', choices=['copy', 'encode'], default=DEFAULT_AUDIO_CODEC_MODE, help="Audio codec mode when processing video:\n- encode: re-encode audio (default).\n- copy: keep original audio.")
    group_processing.add_argument('--keep-original', action='store_true', help="Keep original file after processing.")
    group_processing.add_argument('--max-workers', type=int, default=MAX_CONCURRENT_PROCESSES, help="Max number of concurrent processing jobs.")
    
    return parser


# --- Main Class ---
class YoutubeDownloader:
    def __init__(self, args):
        self.args = args
        self.args.filename_suffix = sanitize_filename(self.args.filename_suffix)
        self.files_to_process = []
        self.tqdm_progress_bars = {}
        self.processed_archive = set()
        self._load_processed_archive()

    def _load_processed_archive(self):
        if os.path.exists(self.args.processed_archive):
            with open(self.args.processed_archive, "r", encoding="utf-8") as f:
                self.processed_archive = set(line.strip() for line in f if line.strip())

    def _save_to_processed_archive(self, filename):
        with open(self.args.processed_archive, "a", encoding="utf-8") as f:
            f.write(filename + "\n")
        self.processed_archive.add(filename)

    def _get_valid_url(self, identifier):
        if 'playlist?list=' in identifier or 'watch?v=' in identifier:
            return [identifier]

        if identifier.startswith('@'):
            return [
                f"https://www.youtube.com/{identifier}/videos",
                f"https://www.youtube.com/{identifier}/shorts"
            ]

        if identifier.startswith('UC'):
            return [
                f"https://www.youtube.com/channel/{identifier}/videos",
                f"https://www.youtube.com/channel/{identifier}/shorts"
            ]

        if identifier.startswith('https://'):
            return [identifier]

        logging.error("Invalid identifier or URL.")
        sys.exit(1)

    def _progress_hook(self, d):
        file_id = d.get('info_dict', {}).get('id') or os.path.basename(d.get('filename', ''))
        if not file_id: return

        if d['status'] == 'downloading':
            if file_id not in self.tqdm_progress_bars:
                title = d.get('info_dict', {}).get('title', 'Unknown')
                self.tqdm_progress_bars[file_id] = tqdm(
                    total=d.get('total_bytes') or d.get('total_bytes_estimate'),
                    unit='B', unit_scale=True, unit_divisor=1024,
                    desc=f"{title[:25]}...", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
                )
            pbar = self.tqdm_progress_bars[file_id]
            downloaded = d.get('downloaded_bytes', 0)
            pbar.update(downloaded - pbar.n)

        elif d['status'] == 'finished':
            if file_id in self.tqdm_progress_bars:
                self.tqdm_progress_bars[file_id].close()
                del self.tqdm_progress_bars[file_id]
            
            final_filepath = d.get('filename')
            if not final_filepath: return
            
            logging.info(f"Finished downloading: {os.path.basename(final_filepath)}")

            if not self.args.skip_processing:
                if final_filepath not in self.processed_archive:
                    self.files_to_process.append(final_filepath)
                else:
                    logging.info(f"Skipping processing (already processed): {os.path.basename(final_filepath)}")

    def download_content(self):
        target_urls = self._get_valid_url(self.args.url_or_identifier)
        logging.info(f"Starting download from: {target_urls}")
        
        ydl_opts = {
            'outtmpl': self.args.output_path,
            'download_archive': self.args.archive_file,
            'ignoreerrors': True,
            'retries': 10,
            'fragment_retries': 10,
            'restrictfilenames': True,
            'progress_hooks': [self._progress_hook],
            'quiet': True,
            'no_warnings': True,
            'sanitize_info': sanitize_info,  # custom sanitizer
        }

        if self.args.audio_only:
            logging.info(f"Audio-only mode -> {self.args.audio_format} @ {self.args.audio_bitrate}k")
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': self.args.audio_format}]
            ydl_opts['postprocessor_args'] = ['-b:a', f"{self.args.audio_bitrate}k"]
        else:
            logging.info(f"Video mode -> up to {self.args.quality}p")
            quality_filter = self.args.quality.replace('p', '')
            # اجبار yt-dlp على دمج الفيديو والصوت
            ydl_opts['format'] = f"bestvideo[height<={quality_filter}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            ydl_opts['merge_output_format'] = 'mp4'
            if self.args.subtitles:
                logging.info(f"Embedding subtitles: {self.args.sub_langs}")
                ydl_opts['writesubtitles'] = True
                ydl_opts['subtitleslangs'] = self.args.sub_langs.split(',')
                ydl_opts['embedsubtitles'] = True

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(target_urls)
        except Exception as e:
            logging.error(f"Fatal download error: {e}")

    def process_videos_concurrently(self):
        if not self.files_to_process:
            logging.info("No new videos to process.")
            return

        logging.info(f"Processing {len(self.files_to_process)} videos in '{self.args.process_mode}' mode...")
        
        with ThreadPoolExecutor(max_workers=self.args.max_workers) as executor:
            with tqdm(total=len(self.files_to_process), desc="Processing videos") as pbar:
                futures = {executor.submit(self.process_single_video, f): f for f in self.files_to_process}
                for future in as_completed(futures):
                    result = future.result()
                    if result: logging.info(result)
                    pbar.update(1)

    def process_single_video(self, filename):
        if self.args.audio_only: return None

        base, _ = os.path.splitext(filename)
        if base.endswith(self.args.filename_suffix):
            logging.warning(f"File '{os.path.basename(filename)}' seems already processed. Skipping.")
            return None
            
        output_file = f"{base}_{self.args.filename_suffix}.mp4"

        audio_cmd = ["-c:a", "copy"] if self.args.audio_codec == 'copy' else ["-c:a", "aac", "-b:a", f"{self.args.audio_bitrate}k"]
        video_cmd = ["-c:v", "copy"] if self.args.process_mode == 'copy' else ["-c:v", "libx264", "-preset", self.args.preset, "-crf", str(self.args.crf)]
        
        cmd = ["ffmpeg", "-y", "-i", filename] + video_cmd + audio_cmd + [output_file]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                if not self.args.keep_original:
                    os.remove(filename)
                self._save_to_processed_archive(output_file)
                return f"Processed and saved: {os.path.basename(output_file)}"
            else:
                return f"Processing failed for: {os.path.basename(filename)}. Original kept."

        except subprocess.CalledProcessError as e:
            return f"FFmpeg error while processing {os.path.basename(filename)}: {e}"
        except Exception as e:
            return f"Unexpected error while processing {os.path.basename(filename)}: {e}"

    def process_audio_files_concurrently(self):
        if not self.files_to_process:
            logging.info("No new audio files to process.")
            return
        
        logging.info(f"Processing {len(self.files_to_process)} audio files (rename only)...")
        for filepath in tqdm(self.files_to_process, desc="Processing audio"):
            base, ext = os.path.splitext(filepath)
            if not base.endswith(self.args.filename_suffix):
                new_filepath = f"{base}_{self.args.filename_suffix}{ext}"
                try:
                    os.rename(filepath, new_filepath)
                    self._save_to_processed_archive(new_filepath)
                    logging.info(f"Renamed: {os.path.basename(new_filepath)}")
                except OSError as e:
                    logging.error(f"Failed to rename {os.path.basename(filepath)}: {e}")


# --- Main ---
def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    
    if args.audio_only and args.subtitles:
        logging.warning("Subtitles cannot be used with --audio-only. Ignoring subtitles.")
        args.subtitles = False

    setup_logging(args.log_file)
    
    downloader = YoutubeDownloader(args)
    downloader.download_content()
    
    if not args.skip_processing:
        if args.audio_only:
            downloader.process_audio_files_concurrently()
        else:
            downloader.process_videos_concurrently()
    
    logging.info("All operations completed successfully.")


if __name__ == '__main__':
    main()
