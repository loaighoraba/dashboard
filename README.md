# Dashboard

A small [FastAPI](https://fastapi.tiangolo.com/) web app that handles my technical needs, deployed on [FastAPI Cloud](https://fastapicloud.com/).

It currently has one feature: a webhook that GitHub Actions calls on a schedule. The webhook checks a shared secret and reports success. It doesn't do any work yet; scheduled tasks will be added to it.

## Tech stack

- Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- FastAPI (`fastapi[standard]`)
- pytest for tests
- FastAPI Cloud for hosting
- GitHub Actions to trigger the scheduled webhook

## Project structure

```
app/
  main.py              # FastAPI app; includes the routers
  security.py          # verify_cron_secret: checks the X-Cron-Secret header
  routers/
    webhooks.py        # POST /webhooks/cron
tests/
  test_cron_webhook.py
.github/workflows/
  cron.yml             # Scheduled workflow that calls the webhook
pyproject.toml         # Dependencies and the FastAPI entrypoint (app.main:app)
```

## Local development

Install the dependencies:

```bash
uv sync
```

Run the dev server with auto-reload:

```bash
CRON_SECRET_TOKEN=local-secret uv run fastapi dev
```

The interactive API docs are at http://localhost:8000/docs. To call protected endpoints from there, click **Authorize** and enter the value of `CRON_SECRET_TOKEN`.

Run the tests:

```bash
uv run pytest
```

## Configuration

| Environment variable | Required | Description                                                       |
| -------------------- | -------- | ----------------------------------------------------------------- |
| `CRON_SECRET_TOKEN`  | Yes      | The shared secret that callers must send in the `X-Cron-Secret` header. |

If `CRON_SECRET_TOKEN` is not set, the webhook rejects every request with a `500`, so a missing setting never lets requests through.

## API

### `POST /webhooks/cron`

The webhook that GitHub Actions calls on a schedule. It is authenticated with the `X-Cron-Secret` header.

```bash
curl -X POST -H "X-Cron-Secret: $CRON_SECRET_TOKEN" http://localhost:8000/webhooks/cron
```

| Status | Meaning                                                                 |
| ------ | ----------------------------------------------------------------------- |
| `200`  | `{"message": "Cron job completed successfully"}`                        |
| `401`  | The `X-Cron-Secret` header is missing or wrong                          |
| `500`  | `CRON_SECRET_TOKEN` is not configured on the server                     |

## Deployment (FastAPI Cloud)

1. Log in and deploy from the repo root. The entrypoint is read from `[tool.fastapi]` in `pyproject.toml`.

   ```bash
   uv run fastapi login
   uv run fastapi deploy
   ```

2. In the FastAPI Cloud dashboard, set the `CRON_SECRET_TOKEN` environment variable for the app and mark it as a secret.

### Generating the secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This produces 256 random bits in URL-safe characters, so the value never needs quoting in headers or YAML. Use the same value in FastAPI Cloud and in GitHub (see below).

## Scheduled job (GitHub Actions)

[`.github/workflows/cron.yml`](.github/workflows/cron.yml) calls `POST /webhooks/cron` every day at 06:00 UTC. To run it at a different time, change the `cron` expression in that file. You can also start it by hand from the **Actions** tab (`workflow_dispatch`).

The workflow needs two settings in **Settings → Secrets and variables → Actions**:

| Kind     | Name                | Value                                                        |
| -------- | ------------------- | ------------------------------------------------------------ |
| Secret   | `CRON_SECRET_TOKEN` | The same value as in FastAPI Cloud                           |
| Variable | `APP_URL`           | The deployed app's base URL, e.g. `https://<app>.fastapicloud.dev` |

The call retries up to 3 times. If the webhook still returns an error, the workflow run fails and GitHub notifies you.

GitHub only runs scheduled workflows from the default branch, and scheduled runs can start several minutes late.

### Rotating the secret

1. Generate a new token.
2. Update `CRON_SECRET_TOKEN` in FastAPI Cloud.
3. Update the `CRON_SECRET_TOKEN` secret in GitHub.

Any run that happens between steps 2 and 3 gets a `401`.
