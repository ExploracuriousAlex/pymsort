# PyMSort - Python Media Sorter

A desktop application for organizing and converting media files (photos and videos) with automatic format detection, intelligent conversion, and metadata preservation.

## Features

- **Drag & Drop Interface** with background import and live progress
- **Automatic Organization** by camera model and capture date
- **Video Conversion** with metadata preservation
- **Device Profiles** for Sony, Panasonic, Olympus, iPhone, DJI cameras
- **Live Photo Support** for Apple devices

### Supported Formats

- **Images**: JPEG, PNG, HEIC
- **Videos**: MOV, MP4, MTS (AVCHD)
- **Codecs**: AVC/HEVC video, AAC/AC-3/PCM audio

## Architecture

- **Models**: MediaFile, ConversionProfile
- **Services**: ExifTool, FFmpeg, MediaInfo integrations
- **Workers**: Background processing with Qt signals/slot

## Requirements

### External Tools

#### 1. ExifTool (Required)

- **Download**: [ExifTool](https://exiftool.org/)
- **Verify**: `exiftool -ver`

#### 2. FFmpeg (Required)

- **Download**: [FFmpeg](https://ffmpeg.org/)
- **Verify**: `ffmpeg -version`
- **Recommended**: Build with libfdk_aac for better audio quality

#### 3. MediaInfo

- Installed automatically via Python package

### Python Requirements

- **Python**: 3.13+
- **Package Manager**: [uv](https://docs.astral.sh/uv/) (recommended) or pip
- **Dependencies**: PySide6, pymediainfo (installed automatically)

## Installation

```bash
# Clone repository
git clone https://github.com/ExploracuriousAlex/pymsort.git
cd pymsort

# Verify
uv run pytest
```

## Usage

```bash
# Start application
uv run python main.py
```

### Workflow

1. **Import**: Drag files/folders into the application
2. **Review**: Check detected formats in table
3. **Select Output**: Choose destination folder
4. **Process**: Click "Convert & Sort"

### File Organization

Files are organized as: `{CameraModel}/{Year}/{Month-MonthName}/filename`
The month's name will be in German.

Example:

```
Sony DSC-RX100/2024/01-Januar/photo.jpg
iPhone/2024/12-Dezember/IMG_0001.mov
```

## Conversion Profiles

Pre-configured profiles in `src/ConversionProfiles.json`:

- Sony DSC-RX100, Panasonic HD-SD600 (MTS to MP4)
- iPhone/iPad (AVC & HEVC, Live Photos)
- Olympus, DJI cameras
- ...

Profiles match on file extension, video/audio format, scan type, and Live Photo flag.

## Development

```bash
# Sort imports
uv run ruff check --select I --fix

# Fix lint errors
uv run ruff check --fix

# Format code
uv run ruff format

# Run tests
uv run pytest -v
```

## Troubleshooting

- **Tool not found**: Install ExifTool/FFmpeg and add to PATH
- **Slow import**: Network drives → copy locally first
- **Conversion fails**: Check FFmpeg libfdk_aac support, review logs
- **Organization issues**: Verify EXIF metadata with `exiftool file.jpg`

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

## Version History

### v0.1.0 (2025-12-25)

- Initial Python release

### v0.1.1 (2025-12-27)

- Removed pyexiftool
