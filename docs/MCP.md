# MCP server (`reviewer mcp`)

Plug and Play Reviewer ships a built-in MCP-compatible server. It exposes three
tools over **newline-delimited JSON-RPC on stdio**. There is no HTTP or SSE
transport.

Because the server uses stdio, it always runs **locally** on the same machine
as the runner. Your source, diffs, and model key never leave that machine. A
remote MCP transport is not needed and is not provided.

## Start the server

```sh
reviewer mcp
```

The process reads one JSON object per line from stdin and writes one JSON object
per line to stdout. It exits with code `0` when stdin closes or when `--help` is
printed. Protocol-level errors are returned as JSON payloads. They do not change
the exit code while the loop is alive.

## Protocol

Supported methods:

| Method | Purpose |
|---|---|
| `tools/list` | Return the three tool definitions and their input schemas. |
| `tools/call` | Run a tool by name with arguments. |

Unknown methods return a JSON-RPC error with code `-32602`.

### List tools

Request:

```json
{"jsonrpc":"2.0","id":"tools-1","method":"tools/list","params":{}}
```

Response shape:

```json
{
  "jsonrpc": "2.0",
  "id": "tools-1",
  "result": {
    "tools": [
      {
        "name": "review_pull_request",
        "description": "Start a PR review and return the review, findings and remediation prompts.",
        "input_schema": { "...": "..." }
      },
      {
        "name": "list_findings",
        "description": "List findings for a review id.",
        "input_schema": { "...": "..." }
      },
      {
        "name": "list_remediation_prompts",
        "description": "List remediation prompts for a review id.",
        "input_schema": { "...": "..." }
      }
    ]
  }
}
```

### Call a tool

Request:

```json
{
  "jsonrpc": "2.0",
  "id": "call-1",
  "method": "tools/call",
  "params": {
    "name": "review_pull_request",
    "arguments": {
      "owner": "acme",
      "repository": "widgets",
      "pull_request": 12
    }
  }
}
```

`review_pull_request` arguments:

| Field | Required | Notes |
|---|---|---|
| `owner` | yes | GitHub owner. |
| `repository` | yes | Repository name. |
| `pull_request` | yes | PR number, integer greater than 0. |
| `model` | no | Override model id. |

`list_findings` and `list_remediation_prompts` require:

| Field | Required |
|---|---|
| `review_id` | yes, non-empty string from a prior review |

## Tool result shapes

Every `tools/call` result uses one of three statuses inside `result`:

Success:

```json
{
  "jsonrpc": "2.0",
  "id": "call-1",
  "result": {
    "status": "ok",
    "result": { "... review or list payload ..." }
  }
}
```

Refusal:

```json
{
  "jsonrpc": "2.0",
  "id": "call-1",
  "result": {
    "status": "refused",
    "refusal": {
      "code": "github_not_connected",
      "message": "GitHub is not connected. Connect GitHub before requesting a review.",
      "action": "Connect GitHub, then retry the request."
    }
  }
}
```

Failure:

```json
{
  "jsonrpc": "2.0",
  "id": "call-1",
  "result": {
    "status": "error",
    "error": {
      "code": "unexpected_error",
      "message": "Review failed unexpectedly.",
      "action": "Check the local logs, fix the cause, then retry the request."
    }
  }
}
```

Stable refusal and error codes match [AGENT_CONTRACT.md](AGENT_CONTRACT.md).

## Client configuration example

Add this to a Claude Desktop or Cursor MCP config on the **same machine** as
the runner:

```json
{
  "mcpServers": {
    "plug-and-play-reviewer": {
      "command": "reviewer",
      "args": ["mcp"]
    }
  }
}
```

The client spawns `reviewer mcp` as a child process and speaks JSON-RPC over
stdin and stdout. No network port is opened.

## Prerequisites

Before `tools/call` can succeed:

1. GitHub is connected (`reviewer` or `reviewer login` in a terminal).
2. A model key is stored (`reviewer setup --hosted-origin https://reviewer.niresh.tech`).
3. The runner can reach the hosted control plane at the origin you paired with.

## Related surfaces

The same review backend also supports:

- `reviewer review owner/repo#pr --json` (CLI)
- `reviewer a2a` (A2A JSON-RPC on stdio)
- `reviewer acp` (ACP messages on stdio)

See [AGENT_CONTRACT.md](AGENT_CONTRACT.md) for exit codes and full JSON shapes.
