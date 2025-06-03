import os

from framework import Agent, MCPToolkit

GMAIL_KEYS_DIR = os.environ["GMAIL_KEYS_DIR"]
NPM_CACHE_DIR = os.environ["NPM_CACHE_DIR"]

cmd = [
    "docker",
    "run",
    "-i",
    "--rm",
    "--entrypoint",
    "/usr/local/bin/npm",
    "--mount",
    f"type=bind,source={GMAIL_KEYS_DIR},target=/keys",
    "--mount",
    f"type=bind,source={NPM_CACHE_DIR},target=/root/.npm",
    "-v",
    "mcp-gmail:/gmail-server",
    "-e",
    "GMAIL_OAUTH_PATH=/keys/gcp-oauth.keys.json",
    "-e",
    "GMAIL_CREDENTIALS_PATH=/keys/credentials.json",
    "-p",
    "3000:3000",
    "node:24",
    "exec",
    "@gongrzhe/server-gmail-autoauth-mcp",
]

gmail = Agent(
    name="Gmail",
    system_prompt=(
        "You are Gmail assistant."
        "Try bringing at least 100 results when searching for emails."
        "Get confirmation before performing any actions that modify data."
        f"When access token is not valid, instruct user to authenticate by running `{' '.join(cmd)} auth` command."
    ),
    toolkit=MCPToolkit(command=cmd[0], args=cmd[1:]),
)
