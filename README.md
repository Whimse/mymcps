
# Install

poetry install

# Environment Setip

CREDS_PATH=../credentials # Modify this
MODEL=$CREDS_PATH/llm_apis/google-gemini-2.5-flash.json

# Run

Server:

  API_KEYS=$CREDS_PATH/api_keys.yaml
  poetry run mymcp-server --verbose --model $MODEL -s tests/samples -k $API_KEYS

Client:
  MODEL=$CREDS_PATH/llm_apis/openai.gpt-4o.json
  poetry run mygent --model $MODEL

# Testing

  MODEL=$CREDS_PATH/llm_apis/openai.gpt-4o.json
  poetry run python3 tests/regression.py --model $MODEL

