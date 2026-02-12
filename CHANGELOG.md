# Changelog

All notable changes to Archive Downloader will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- [ ] Support for additional archive sites
- [ ] Download queue management
- [ ] Custom download location per link
- [ ] Export/import download history

## [1.0.0] - 2026-02-12

### Added
- ✨ Initial release of Archive Downloader
- 🌐 Support for Fapello and Picazor sites
- 🎨 Modern PySide6 (Qt6) graphical interface
- 📊 Real-time progress bar with percentage display
- 🎨 Light and dark theme support with smooth transitions
- 🖼️ Video thumbnail generation using OpenCV
- 🚀 Parallel downloading with optimized thread pools
- ⚡ Site-specific performance tuning:
  - Fapello: 3 threads, 512KB chunks
  - Picazor: 4 threads, 256KB chunks, 0.1s delay
- 📦 Configurable batch downloading for Picazor
- 💾 UI state persistence (theme, batch settings)
- 📝 Detailed logging system
- 🔄 Throttled UI updates (120ms) for better performance
- 🔒 Thread-safe network sessions with thread-local storage
- 📁 Automatic file organization by site and profile
- ⚡ Streaming downloads to handle large files efficiently
- 🛡️ Resilient filename handling for edge cases
- 🔁 Automatic retry logic for failed downloads
- 🧪 Comprehensive test suite with pytest
- 📚 Complete documentation (README, RELEASE guide)

### Technical Highlights
- Python 3.13+ support
- PySide6 for modern Qt6 interface
- requests with Retry adapter for reliable HTTP
- cloudscraper for sites with JavaScript challenges
- BeautifulSoup4 for HTML parsing
- opencv-python for video processing
- Modular architecture (core/ui/utils separation)
- Worker threads for async operations
- Event-driven progress tracking
- PyInstaller configuration for standalone executables

### Fixed
- Fixed filename preparation crashes on short URLs
- Fixed thread-unsafe HTTP session usage
- Fixed excessive Picazor scanning when no valid indices found
- Fixed progress bar display with integrated percentage text
- Fixed in-memory downloads causing memory issues with large files

### Developer Experience
- Created build automation script (build.ps1)
- Created PyInstaller spec file with optimizations
- Created comprehensive test suite (6 tests, 100% passing)
- Created release documentation (RELEASE.md)
- Added requirements-dev.txt for test dependencies
- Configured .gitignore for build artifacts

---

## Version Format

- **X.0.0**: Major version - Breaking changes, major new features
- **0.X.0**: Minor version - New features, backwards compatible
- **0.0.X**: Patch version - Bug fixes, small improvements

## Release Links

[Unreleased]: https://github.com/yourusername/Archive-Downloader/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/Archive-Downloader/releases/tag/v1.0.0
