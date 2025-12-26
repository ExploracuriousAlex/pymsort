# PyMSort - Python Media Sorter

A desktop application for organizing and converting media files (photos and videos) from various cameras and devices with automatic format detection, intelligent conversion, and metadata preservation.

## Overview

PyMSort is a complete Python reimplementation of a C# media sorting application. It automatically organizes photos and videos into a structured folder hierarchy based on camera model and capture date, while intelligently converting video formats when needed.

## Features

### Core Functionality

- **Drag & Drop Interface**: Simply drag media files or folders into the application
- **Output Folder Selection**: Choose where to save organized files via Browse button
- **Background Import**: Files are imported in a background thread with live progress updates
- **Automatic Organization**: Files organized by camera model and capture date
- **Smart Video Conversion**: Automatically converts videos to optimized formats
- **Metadata Preservation**: All EXIF data is preserved during conversion and copying
- **Live Photo Support**: Detects and handles Apple Live Photos correctly
- **17 Device Profiles**: Pre-configured conversion profiles for common cameras
- **Progress Tracking**: Real-time progress bar and detailed processing log
- **Responsive UI**: Non-blocking interface stays responsive during long operations

### Supported Devices & Formats

**Cameras:**

- Sony DSC-RX100 (Progressive & Interlaced)
- Panasonic HD-SD600
- Olympus STYLUS TG-830
- iPhone/iPad (Legacy AVC & Modern HEVC)
- DJI Mimo App

**Formats:**

- Images: JPEG, PNG, and other common formats
- Videos: MOV, MP4, MTS (AVCHD), and more
- Container formats: QuickTime, MPEG-4, AVCHD
- Video codecs: AVC (H.264), HEVC (H.265)
- Audio codecs: AAC, AC-3, PCM

## Architecture

PyMSort follows a clean, layered architecture for maintainability and testability:

```text
src/pymsort/
├── models/              # Data models (MediaFile, ConversionProfile)
├── services/            # External tool integrations
│   ├── exiftool_service.py     # Metadata extraction/manipulation
│   ├── ffmpeg_service.py       # Video conversion
│   └── mediainfo_service.py    # Media analysis
├── workers/             # Background processing
│   ├── import_worker.py        # File import with progress
│   └── process_worker.py       # Conversion & organization
├── utils/               # Configuration and utilities
├── mainwindow.py        # Main UI window
├── mediafiles_tablemodel.py    # Table data model
└── mediafiles_tableview.py     # Table view widget
```

### Design Principles

- **Separation of Concerns**: Clear boundaries between UI, business logic, and services
- **Dependency Injection**: Services are passed to workers, not created internally
- **Thread Safety**: Qt signals/slots for all cross-thread communication
- **Type Safety**: Comprehensive type hints throughout
- **Testability**: 135 unit tests with 100% pass rate

## Requirements

### External Tools

PyMSort requires these command-line tools installed and available in your system PATH or placed in the application directory:

#### 1. ExifTool (Required)

For metadata extraction and manipulation.

- **Download**: [ExifTool](https://exiftool.org/)
- **Verify**: `exiftool -ver`
- **Features used**:
  - Batch metadata extraction with JSON output
  - Metadata restoration
  - File date setting
  - UTF-8 filename support
  - Large file support (>2GB)

#### 2. FFmpeg (Required)

For video conversion, preferably with libfdk_aac encoder.

- **Download**: [FFmpeg](https://ffmpeg.org/)
- **Verify**: `ffmpeg -version`
- **libfdk_aac check**: `ffmpeg -encoders | grep libfdk_aac`
- **Note**: libfdk_aac provides better audio quality than native AAC encoder

#### 3. MediaInfo Library

For media file analysis (installed automatically via Python package).

### Python Requirements

- **Python**: 3.13 or higher
- **OS**: Windows, macOS, or Linux

**Dependencies** (installed automatically):

- PySide6 >= 6.8.1 (Qt for Python)
- pymediainfo >= 6.1.0
- pywin32 >= 308 (Windows only, for creation time preservation)

**Development Dependencies**:

- pytest >= 9.0.0
- pytest-qt >= 4.5.0
- pytest-cov >= 6.0.0

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/pymsort.git
cd pymsort
```

### 2. Install External Tools

**Windows:**

- Download ExifTool and FFmpeg executables
- Add their directories to PATH or place executables in the application directory

**macOS:**

```bash
brew install exiftool ffmpeg
```

**Linux:**

```bash
sudo apt-get install exiftool ffmpeg
# or
sudo yum install perl-Image-ExifTool ffmpeg
```

### 3. Install Python Package

```bash
# Install in development mode
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
# Run tests to verify everything works
python -m pytest tests/
```

## Usage

### Starting the Application

```bash
python main.py
```

### First Run

On startup, PyMSort will:

1. Search for ExifTool and FFmpeg in system PATH
2. Verify tool versions and availability
3. Check for FFmpeg libfdk_aac encoder support
4. Create temporary directory (default: `~/.pymsort/temp`)
5. Load conversion profiles from configuration
6. Display any warnings about missing tools

### Processing Workflow

#### 1. Import Files

- **Drag & Drop**: Drag one or more files or folders into the table
- **Progress**: Watch import progress: "Importing 15/100: photo.jpg"
- **Live Updates**: Files appear in table as they're imported
- **Background Processing**: UI remains responsive during import

#### 2. Review Detected Files

The table shows:

- Source file path
- MIME type (image/jpeg, video/mp4, etc.)
- Container format (MPEG-4, QuickTime, etc.)
- Video format (AVC, HEVC)
- Video scan type (Progressive, Interlaced)
- Audio format (AAC, AC-3, PCM)
- Live Photo flag
- Processing state

#### 3. Select Output Folder

- Use the **"Browse..."** button to select where files should be saved
- Or type/paste the path directly into the text field
- Default: `~/.pymsort/temp`
- Folder will be created automatically if it doesn't exist

#### 4. Convert & Sort

- Click **"Convert & Sort"** button
- Watch progress: "Processing 5/42: Converting video.mov"
- Monitor detailed log messages
- Processing runs in background thread

#### 5. Results

Files are organized in your selected output folder:

```text
/destination/
├── Sony DSC-RX100/
│   ├── 2024/
│   │   ├── 01-January/
│   │   │   ├── photo1.jpg
│   │   │   └── photo2.jpg
│   │   └── 02-February/
│   │       └── video.mp4
├── iPhone/
│   └── 2024/
│       └── 12-December/
│           ├── IMG_0001.mov
│           └── IMG_0001.jpg (Live Photo pair)
```

### File Organization Rules

**Folder Structure:**

```text
{CameraModel}/{Year}/{Month-MonthName}/filename
```

**Date Priority** (first available used):

1. `CreationDate` (QuickTime with timezone)
2. `DateTimeOriginal` (EXIF)
3. `CreateDate` (EXIF)
4. `FileModifyDate` (filesystem)

**Camera Model Detection:**

- Extracted from EXIF `Model` field
- Special handling for Apple devices (iPhone, iPad)
- Falls back to "Unknown Camera" if not detected

**Duplicate Handling:**

- Automatic numbering: `photo.jpg`, `photo_2.jpg`, `photo_3.jpg`
- Based on filename comparison in destination folder

## Conversion Profiles

PyMSort includes 17 pre-configured conversion profiles for optimal output quality:

### Sony & Panasonic Cameras

```json
{
  "UseCase": "Sony DSC-RX100, Panasonic HD-SD600",
  "OriginalFileExtension": ".mts",
  "VideoFormat": "AVC",
  "VideoScanType": "Progressive",
  "AudioFormat": "AC-3",
  "FfmpegExecutionString": "ffmpeg -i %s -c:v copy -c:a libfdk_aac -vbr 5 -f mp4 %s",
  "NewFileExtension": ".mp4"
}
```

### iPhone/iPad Profiles

- Legacy (AVC): 4 profiles (no audio, PCM, AAC audio)
- Modern (HEVC): 6 profiles (no audio, PCM, AAC audio)
- Live Photos and Special Captures supported

### Profile Matching

Files are matched based on:

1. Original file extension (.mov, .mts, .mp4)
2. Video format (AVC, HEVC)
3. Video scan type (Progressive, Interlaced, or empty)
4. Audio format (AAC, AC-3, PCM, or empty)
5. Live Photo video flag

**Empty FfmpegExecutionString** = Copy only, no conversion

## Processing States

Files progress through these states:

- **NoState**: Initial state
- **Pending**: File added, ready to process
- **InProgress**: Currently being processed (blue)
- **Success**: Processing completed successfully (green)
- **Warning**: Completed with warnings (yellow)
- **Error**: Processing failed (red)

## Configuration

### config.py

```python
exiftool_path = "exiftool"  # or full path
ffmpeg_path = "ffmpeg"      # or full path
temp_dir = Path.home() / ".pymsort" / "temp"
```

### ConversionProfiles.json

Located at `src/pymsort/ConversionProfiles.json`

Format:

```json
[
  {
    "UseCase": "Description",
    "OriginalFileExtension": ".mov",
    "VideoFormat": "AVC",
    "VideoScanType": "Progressive",
    "AudioFormat": "AAC",
    "IsLivePhotoVideo": false,
    "FfmpegExecutionString": "ffmpeg command template",
    "NewFileExtension": ".mp4"
  }
]
```

## Development

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_import_worker.py -v

# With coverage
python -m pytest tests/ --cov=pymsort --cov-report=html
```

### Test Coverage

- **135 unit tests** covering all major components
- Services: ExifTool, FFmpeg, MediaInfo
- Workers: ProcessWorker, ImportWorker
- Models: MediaFile, ConversionProfile
- UI Models: MediaFilesTableModel

### Code Quality

- **Type hints** throughout codebase
- **Docstrings** for all public methods
- **Logging** at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- **Error handling** with detailed messages

### Adding New Profiles

1. Edit `src/pymsort/ConversionProfiles.json`
2. Add new profile with required fields
3. Ensure unique combination of matching fields
4. Test with sample files from the camera

## Troubleshooting

### "ExifTool not found"

- Install ExifTool from [ExifTool](https://exiftool.org/)
- Add to system PATH or place in application directory

### "FFmpeg not found" or "libfdk_aac not available"

- Install FFmpeg with libfdk_aac support
- Or use FFmpeg with native AAC encoder (lower quality)
- Add to system PATH or place in application directory

### "Import is slow"

- Check disk I/O performance
- For network drives, copy to local disk first
- MediaInfo analysis of videos is CPU-intensive

### "Videos not converting"

- Check FFmpeg installation and libfdk_aac support
- Review log for detailed error messages
- Verify conversion profile matches file format
- Check temp directory has sufficient space

### "Files not organized correctly"

- Verify EXIF metadata is present (`exiftool file.jpg`)
- Check camera model is detected in EXIF
- Review log for organization errors

## Technical Details

### Thread Safety

- **ImportWorker**: Runs in QThreadPool, emits signals for UI updates
- **ProcessWorker**: Runs in QThreadPool, uses signals for progress
- **All UI updates**: Via Qt signals/slots mechanism
- **No direct UI access** from worker threads

### Memory Management

- Batch metadata extraction minimizes subprocess overhead
- Temporary files cleaned up after processing
- Large file support (>2GB) via ExifTool API flag

### Cross-Platform Compatibility

- Uses `pathlib.Path` for all path operations
- Platform-specific features (Windows creation time) are optional
- UTF-8 encoding enforced throughout
- No hardcoded path separators

### Performance Optimizations

- Batch ExifTool metadata extraction (one subprocess call for all files)
- Background import prevents UI freezing
- Progress updates limited to prevent signal flooding
- Lazy video analysis (only for video files)

## License

This project is licensed under the terms specified in the LICENSE file.

## Credits

- Original C# implementation concept
- Python reimplementation by Alexander
- Built with PySide6 (Qt for Python)
- Uses ExifTool by Phil Harvey
- Uses FFmpeg project
- Uses MediaInfo library

## Version History

### v1.0.0 (2025-12-25)

- Initial Python release
- Complete feature parity with C# version
- 135 unit tests with 100% pass rate
- 17 conversion profiles
- Background import with progress
- Responsive UI during all operations
- Comprehensive error handling and logging
