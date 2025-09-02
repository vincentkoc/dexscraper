# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python WebSocket client that scrapes real-time cryptocurrency trading data from DexScreener's public API. The application connects to DexScreener's WebSocket endpoint, decodes binary protocol messages, and outputs structured JSON data about Solana trading pairs.

## Commands

### Running the Application
```bash
python dex.py
```

### Testing
```bash
python -m pytest tests/
```
Note: pytest may need to be installed first with `pip install pytest`

### Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Core Components

**Main Module (`dex.py`)**:
- Single-file application with all functionality
- WebSocket connection management with automatic reconnection
- Binary protocol decoder for DexScreener's proprietary format
- Data sanitization and validation utilities

**Key Functions**:
- `connect_to_dexscreener()`: Main WebSocket connection handler with retry logic
- `decode_pair(data)`: Binary decoder for individual trading pair data
- `decode_metrics(data, start_pos)`: Numeric data extractor using struct unpacking
- `clean_string(s)`: String sanitization for malformed/garbage data
- `handle_double(value)`: NaN/Infinity validation for numeric values

### Data Flow
1. WebSocket connects to DexScreener with specific query parameters for Solana trending pairs
2. Binary messages are received and validated (must start with version header)
3. Messages are parsed in 512-byte chunks to extract individual trading pairs
4. Each pair undergoes field extraction (strings) followed by 8-byte aligned numeric data
5. Clean, validated JSON is output to stdout

### Binary Protocol Details
- String fields are length-prefixed (1 byte length + UTF-8 data)
- Numeric metrics are packed as 8 consecutive doubles (64 bytes total)
- Data must be 8-byte aligned before reading doubles
- Protocol includes built-in validation against unreasonable string lengths (>100 chars)

### Testing Strategy
Tests focus on edge cases in data parsing:
- String cleaning and sanitization (`test_decode_pair.py`)
- Malformed binary data handling
- Invalid length field scenarios

### Configuration
- `DEBUG = True/False`: Controls logging verbosity
- Query parameters target Solana pairs ranked by 6-hour trending score
- WebSocket headers mimic Firefox browser for compatibility

### Error Handling Philosophy
Multiple layers of defensive programming:
- Connection-level: Auto-reconnect on failures
- Message-level: Skip malformed messages, continue processing
- Data-level: Validate and sanitize all input, handle NaN/Inf gracefully