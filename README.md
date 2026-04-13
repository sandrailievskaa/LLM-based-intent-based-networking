# LLM Intent-Based Networking Simulator

A small Python simulator that maps natural-language network intents to allow/block rules on a simple topology. It runs locally without Mininet or Ryu, so you can show intent → flow table → connectivity in a few commands.

## Tech stack

- Python 3
- NetworkX (topology graph)
- Matplotlib (topology view)
- OpenAI Python SDK (optional; for LLM-backed parsing)

## Key features

- Three hosts (`h1`, `h2`, `h3`) on one switch; simulated `ping` respects directed flow rules
- Natural-language intents such as “Block h1 from accessing h3” or “Allow h2 to h3”
- Interactive REPL: `ping`, `status`, `clear`, `show`, `quit`
- One-shot demo mode for quick runs and demos

## Highlights

- **SDN-style split:** northbound intents → controller → southbound flow table → data-plane checks
- **Two parsers:** regex patterns by default; if `OPENAI_API_KEY` is set and you pass `--llm`, the same pipeline can use `gpt-4o-mini` with JSON-shaped output
- **Directed rules:** a block on `h2 → h1` does not imply `h1 → h2`
- **Topology plot:** `show` draws the star topology and lists active rules

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Run**

```bash
python intent_simulator.py --demo
```

Interactive session:

```bash
python intent_simulator.py
```

Optional LLM parsing (requires API key in the environment):

```bash
python intent_simulator.py --llm
```
