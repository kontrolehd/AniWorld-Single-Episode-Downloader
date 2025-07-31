# AniWorld Single Episode Downloader

A Python application to download single episodes from aniworld.to with a user-friendly PyQt6 GUI.

---

## Features

- Automatically parses streaming providers from aniworld episode pages.
- Supports multiple video providers with custom extraction logic.
- Downloads videos using the powerful `yt-dlp` tool.
- Real-time download progress displayed in the GUI.
- Simple and intuitive interface for easy use.

---

## Requirements

- Python 3.8 or higher
- The following Python packages (see `requirements.txt`):
  - requests
  - beautifulsoup4
  - yt-dlp
  - PyQt6

---

## Installation

1. Clone or download this repository.
2. Create a Python virtual environment (recommended):
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows:
     ```powershell
     .\venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

Run the GUI application:

```bash
python main.py
```

- Enter the full URL of the aniworld.to episode you want to download.
- Select the output directory where the video will be saved.
- Click "Start Download" to begin.
- Monitor download progress and logs in the GUI.

---

## Notes

- Ensure `yt-dlp` is installed and accessible in your environment.
- The downloader supports multiple providers; if a provider is not supported, an error will be shown.
- The output filename is automatically generated based on the episode URL.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Author

Your Name
