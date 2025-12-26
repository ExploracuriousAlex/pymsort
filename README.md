# PyMSort - Python Media Sorter

A desktop application for organizing and converting media files (photos and videos) with automatic format detection, intelligent conversion, and metadata preservation.

## Features

- **Drag & Drop Interface** with background import and live progress
- **Automatic Organization** by camera model and capture date
- **Smart Video Conversion** with metadata preservation
- **17 Device Profiles** for Sony, Panasonic, Olympus, iPhone, DJI cameras
- **Live Photo Support** for Apple devices

### Supported Formats

- **Images**: JPEG, PNG, HEIC
- **Videos**: MOV, MP4, MTS (AVCHD)
- **Codecs**: AVC/HEVC video, AAC/AC-3/PCM audio

## Architecture

- **Models**: MediaFile, ConversionProfile
- **Services**: ExifTool, FFmpeg, MediaInfo integrations
- **Workers**: Background processing with Qt signals/slots
- **131 unit tests** with comprehensive coverage

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
- **Dependencies**: PySide6, pymediainfo, pyexiftool (installed automatically)

## Installation

```bash
# Clone repository
git clone https://github.com/ExploracuriousAlex/pymsort.git
cd pymsort

# Install external tools (macOS)
brew install exiftool ffmpeg

# Install Python dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
uv sync  # Install dependencies

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

Example:

```
Sony DSC-RX100/2024/01-January/photo.jpg
iPhone/2024/12-December/IMG_0001.mov
```

## Conversion Profiles

17 pre-configured profiles in `ConversionProfiles.json`:

- Sony DSC-RX100, Panasonic HD-SD600 (MTS to MP4)
- iPhone/iPad (AVC & HEVC, Live Photos)
- Olympus, DJI cameras

Profiles match on file extension, video/audio format, scan type, and Live Photo flag.

## Configuration

- **config.py**: Tool paths and temp directory
- **ConversionProfiles.json**: Video conversion profiles

## Development

```bash
# Run tests
uv run pytest -v

# Format code
uv run ruff format
```

## Troubleshooting

- **Tool not found**: Install ExifTool/FFmpeg and add to PATH
- **Slow import**: Network drives → copy locally first
- **Conversion fails**: Check FFmpeg libfdk_aac support, review logs
- **Organization issues**: Verify EXIF metadata with `exiftool file.jpg`
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

## License6)

- Initial Python release
- Complete feature parity with C# version
- 131 unit tests with 100% pass rate
- 17 conversion profiles
- Background import with progress
- Responsive UI during all operations
- Comprehensive error handling and logging
- Uses pyexiftool library for efficient ExifTool integration
- German locale support for month names
- Improved error reporting with processing summary
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
