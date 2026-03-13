#!/bin/bash
set -e

mkdir -p /app/.streamlit

{
  printf 'OPENAI_API_KEY = "%s"\n\n' "$OPENAI_API_KEY"
  printf '%s\n' "$STREAMLIT_USERS_TOML"
} > /app/.streamlit/secrets.toml

echo "Generated /app/.streamlit/secrets.toml"
