import os

from framework import Agent, MCPToolkit

GMAIL_KEYS_DIR = os.environ["GMAIL_KEYS_DIR"]
NPM_CACHE_DIR = os.environ["NPM_CACHE_DIR"]

docker_command = [
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
]
port_binding = ["-p", "3000:3000"]  # required to open this port for auth callback during auth command
image_command = ["node:24", "exec", "@gongrzhe/server-gmail-autoauth-mcp"]

auth_command = docker_command + port_binding + image_command
mcp_command = docker_command + image_command

gmail = Agent(
    name="Gmail",
    system_prompt=(
        "You are Gmail assistant."
        "Try bringing at least 100 results when searching for emails."
        "Get confirmation before performing any actions that modify data."
        f"When access token is not valid, instruct user to authenticate by running `{' '.join(auth_command)} auth` command."
    ),
    toolkit=MCPToolkit.from_config(command=mcp_command[0], args=mcp_command[1:]),
)
