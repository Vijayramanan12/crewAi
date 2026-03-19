# Frontend Digest

An AI-powered crew that discovers, analyzes, and documents cutting-edge frontend development techniques from websites across the web.

## Features

- **Web Scout**: Discovers 5 design-forward websites daily across different categories
- **Frontend Analyst**: Deep dives into frontend codebase, CSS techniques, and JavaScript patterns
- **Report Writer**: Generates beautifully structured markdown reports with insights and code snippets
- **Live Analyzer**: Real-time analysis of any website's frontend stack
- **Web Viewer**: Interactive dashboard to browse and search reports

## Setup

```bash
cd analzfrontend
uv sync
```

## Running

```bash
# Generate today's report
python -m analz_frontend.main

# Start the web viewer
python viewer/app.py
```

Open http://localhost:5001 to browse reports.

## Configuration

- **LLM**: Uses LM Studio locally (Ministral 3.3B)
- **Knowledge**: Reports stored in `knowledge/` folder
- **API**: Flask server at `http://localhost:5001`

## Project Structure

```
analzfrontend/
├── src/analz_frontend/       # CrewAI crew definition
│   ├── crew.py              # Main crew
│   ├── main.py              # Entry point
│   ├── config/              # Agent & task YAML configs
│   └── tools/               # Custom tools
├── viewer/                   # Flask web interface
│   ├── app.py               # Flask server
│   └── templates/           # Frontend HTML/CSS/JS
├── knowledge/               # Generated reports (markdown)
└── tests/                   # Test suite
```

## License

MIT
