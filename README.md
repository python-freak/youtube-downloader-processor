# Advanced YouTube Downloader & Processor

A powerful and flexible command-line tool for downloading and processing video/audio content from YouTube.  
Built with **Python**, **yt-dlp**, and **ffmpeg**, it gives you fine-grained control over quality, formats, and post-processing, while ensuring efficiency with archiving and concurrent processing.

---

## Features

- **Multiple Content Sources**: Download from channels (`@name` or `UC...` ID), videos, and playlists.
- **Video & Audio Modes**: Download full videos or audio-only tracks.
- **Quality Control**: Choose video resolution (e.g., `1080p`, `720p`) and audio bitrate.
- **Flexible Processing**:
  - **Video**: Re-encode with `x264` for optimized size/quality or perform a fast, lossless `copy`.
  - **Audio**: Save directly as `mp3`, `m4a`, `flac`, etc.
- **Subtitle Support**: Download and embed subtitles automatically.
- **Efficient & Resumable**:
  - Download archive skips already-downloaded files.
  - Processed archive skips already-processed files.
- **Concurrent Processing**: Run multiple `ffmpeg` jobs in parallel.
- **Safe & Robust**:
  - Filenames are sanitized to prevent errors.
  - Original files deleted only if processing succeeds.
- **Customizable**: Control everything: `crf`, `preset`, audio codec, suffix, and more.

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
   ```

2. **Install dependencies**:
   ```bash
   pip install yt-dlp tqdm
   ```

3. **Install FFmpeg**:
   - [Download here](https://ffmpeg.org/download.html)  
   - Ensure `ffmpeg` is available in your system PATH.

---

## Usage

```bash
python downloader.py [URL_OR_IDENTIFIER] [OPTIONS]
```

---

## Examples

- **Download all videos/shorts from a channel (default: 1080p, re-encode):**
  ```bash
  python downloader.py @MrBeast
  ```

- **Download a playlist as audio-only MP3:**
  ```bash
  python downloader.py "https://www.youtube.com/playlist?list=PL..." --audio-only --audio-format mp3
  ```

- **Download in 720p with subtitles (English + Arabic):**
  ```bash
  python downloader.py @MKBHD --quality 720 --subtitles --sub-langs en,ar
  ```

- **Lossless copy (no re-encode):**
  ```bash
  python downloader.py "https://www.youtube.com/watch?v=..." --process-mode copy
  ```

- **High compression re-encode (smaller, slower):**
  ```bash
  python downloader.py "https://www.youtube.com/watch?v=..." --preset veryslow --crf 24
  ```

- **Re-encode video but keep original audio:**
  ```bash
  python downloader.py "https://www.youtube.com/watch?v=..." --audio-codec copy
  ```

- **Keep original file after processing:**
  ```bash
  python downloader.py @SomeChannel --keep-original
  ```

---

## Command-Line Options

Run:
```bash
python youtube.py --help
```

### Main Argument
| Argument            | Description                                                |
|---------------------|------------------------------------------------------------|
| `url_or_identifier` | URL or channel/playlist identifier                         |

### Paths & Archive
| Option                | Default          | Description                           |
|-----------------------|------------------|---------------------------------------|
| `--output-path, -o`   | `downloads/...`  | Output path template                  |
| `--archive-file`      | `downloaded.txt` | Tracks downloaded items               |
| `--processed-archive` | `processed.txt`  | Tracks processed items                |
| `--log-file`          | `downloader.log` | Log file                              |

### Quality & Format
| Option             | Default | Description                                       |
|--------------------|---------|---------------------------------------------------|
| `--audio-only, -a` | `False` | Download audio only                               |
| `--audio-format`   | `mp3`   | Audio format (`mp3`, `m4a`, `flac`)               |
| `--audio-bitrate`  | `192`   | Audio bitrate (kbps)                              |
| `--quality`        | `1080`  | Max video resolution                              |

### Subtitles (video only)
| Option                | Default | Description                                    |
|-----------------------|---------|------------------------------------------------|
| `--subtitles, --subs` | `False` | Download & embed subtitles                     |
| `--sub-langs`         | `en`    | Comma-separated list of subtitle languages     |

### Processing
| Option              | Default     | Description                                  |
|---------------------|-------------|----------------------------------------------|
| `--filename-suffix` | `Processed` | Suffix for processed files                   |
| `--skip-processing` | `False`     | Skip manual processing                       |
| `--process-mode`    | `encode`    | Video: `encode` (re-encode) or `copy` (fast) |
| `--crf`             | `18`        | Video CRF (x264, lower = higher quality)     |
| `--preset`          | `slow`      | Video encoding preset                        |
| `--audio-codec`     | `encode`    | Audio: `encode` (AAC) or `copy`              |
| `--keep-original`   | `False`     | Keep original file after processing          |
| `--max-workers`     | `2`         | Number of parallel jobs                      |

---

## License

This project is licensed under the **MIT License**.  
You are free to use, modify, and distribute it.

---
