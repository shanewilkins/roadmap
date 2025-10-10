# Roadmap CLI

A command line tool for creating and managing project roadmaps.

## Installation

### From PyPI (coming soon)

```bash
pip install roadmap
```

### From Source

1. Clone the repository:
```bash
git clone https://github.com/yourusername/roadmap.git
cd roadmap
```

2. Install with Poetry:
```bash
poetry install
```

3. Activate the virtual environment:
```bash
poetry shell
```

## Usage

### Initialize a new roadmap

```bash
roadmap init
```

### Add a milestone

```bash
roadmap add "Complete project setup"
```

### View roadmap status

```bash
roadmap status
```

### Mark milestone as complete

```bash
roadmap complete "Complete project setup"
```

### List all milestones

```bash
roadmap list
```

### Get help

```bash
roadmap --help
```

## Development

### Setup

1. Clone the repository
2. Install dependencies:
```bash
poetry install
```

3. Install pre-commit hooks:
```bash
poetry run pre-commit install
```

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black .
poetry run isort .
```

### Type Checking

```bash
poetry run mypy roadmap
```

### Building for Distribution

```bash
poetry build
```

### Publishing to PyPI

```bash
poetry publish
```

## Features

- 🗺️ Initialize project roadmaps
- ➕ Add milestones and tasks
- ✅ Track completion status
- 📊 Visual progress reporting
- 🎨 Rich terminal output
- 📝 YAML-based configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Changelog

### v0.1.0
- Initial release
- Basic CLI structure
- Core commands: init, add, complete, list, status