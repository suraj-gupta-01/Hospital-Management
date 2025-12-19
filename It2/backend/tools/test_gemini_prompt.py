#!/usr/bin/env python3
"""Test script to exercise extract_structured_data and show error handling.
This script monkeypatches `genai` in `backend.server` to simulate a non-JSON response
so we can see the JSON parsing error path in the terminal.
"""
import os
import asyncio
import logging

# Ensure project root is on sys.path so `import backend` works when run directly
import sys
from pathlib import Path
# The project root is two levels up from this file: /<root>/backend/tools
ROOT = Path(__file__).resolve().parents[2]
# Fallback to current working directory if resolution fails
if not ROOT.exists():
    ROOT = Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import server

# Dummy genai that returns invalid JSON
class DummyResp:
    def __init__(self, text):
        self.text = text

class DummyGenai:
    def configure(self, api_key):
        self.api_key = api_key
    def generate_text(self, model, prompt):
        # Return an object with `text` attribute that's NOT JSON
        return DummyResp("Not a JSON response from Gemini: some text here")

# Replace server.genai with dummy
server.genai = DummyGenai()
# Ensure key is present so the code attempts to call genai
os.environ["GEMINI_API_KEY"] = "dummy_key"

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Running extract_structured_data with simulated invalid Gemini response...")
    result = await server.extract_structured_data("Dr. X\nPatient: Y\nPrescription: Drug 10mg")
    print("Result:", result)

if __name__ == '__main__':
    asyncio.run(main())
