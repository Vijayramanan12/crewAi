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
# generate today's report
python -m analz_frontend.main

# start the web viewer
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
├── src/analz_frontend/       # crewAI crew definition
│   ├── crew.py              # main crew
│   ├── main.py              # entry point
│   ├── config/              # agent & task YAML configs
│   └── tools/               # custom tools
├── viewer/                   # flask web interface
│   ├── app.py               # flask server
│   └── templates/           # frontend HTML/CSS/JS
├── knowledge/               # generated reports (markdown)
└── tests/                   # test suite
```

## License

MIT
