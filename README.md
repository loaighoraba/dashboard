# Dashboard

A small [FastAPI](https://fastapi.tiangolo.com/) web app that handles my technical needs, deployed on [Railway](https://railway.com/).

It currently has one feature: a webhook that GitHub Actions calls on a schedule. The webhook checks a shared secret and reports success. It doesn't do any work yet; scheduled tasks will be added to it.

## Tech stack

- Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- FastAPI (`fastapi[standard]`)
- pytest for tests
- Railway for hosting (built with Railpack)
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
  ci.yml               # Runs the tests on pushes and pull requests
  cron.yml             # Scheduled workflow that calls the webhook
pyproject.toml         # Dependencies and the FastAPI entrypoint (app.main:app)
railway.json           # Railway build and deploy settings
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

## Deployment (Railway)

Railway deploys every push to `main` through its GitHub integration. Railway waits for the [`CI`](.github/workflows/ci.yml) workflow to pass before it deploys, so a failing test blocks the deploy.

Railway builds the app with [Railpack](https://railpack.com/), which detects the uv project from `pyproject.toml`, `uv.lock` and `.python-version`. [`railway.json`](railway.json) sets the rest:

- **Start command:** `fastapi run --host 0.0.0.0 --port $PORT`. `fastapi run` reads the entrypoint from `[tool.fastapi]` in `pyproject.toml`, and Railway sets `PORT`.
- **Healthcheck:** `GET /` must return `200` before Railway routes traffic to a new deployment.
- **Restart policy:** Railway restarts the app if it crashes.

### First-time setup

1. In Railway, create a project with **Deploy from GitHub repo**, pick this repository, and set the branch to `main`.
2. In the service's **Settings**, turn on **Wait for CI**.
3. In the service's **Variables**, add `CRON_SECRET_TOKEN`.
4. In **Settings → Networking**, click **Generate Domain**. Use this URL as the `APP_URL` variable in GitHub (see below).

### Generating the secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This produces 256 random bits in URL-safe characters, so the value never needs quoting in headers or YAML. Use the same value in Railway and in GitHub (see below).

## Scheduled job (GitHub Actions)

[`.github/workflows/cron.yml`](.github/workflows/cron.yml) calls `POST /webhooks/cron` every day at 06:00 UTC. To run it at a different time, change the `cron` expression in that file. You can also start it by hand from the **Actions** tab (`workflow_dispatch`).

The workflow needs two settings in **Settings → Secrets and variables → Actions**:

| Kind     | Name                | Value                                                        |
| -------- | ------------------- | ------------------------------------------------------------ |
| Secret   | `CRON_SECRET_TOKEN` | The same value as in Railway                                 |
| Variable | `APP_URL`           | The deployed app's base URL, e.g. `https://<app>.up.railway.app` |

The call retries up to 3 times. If the webhook still returns an error, the workflow run fails and GitHub notifies you.

GitHub only runs scheduled workflows from the default branch, and scheduled runs can start several minutes late.

### Rotating the secret

1. Generate a new token.
2. Update `CRON_SECRET_TOKEN` in Railway. Railway redeploys the service when a variable changes.
3. Update the `CRON_SECRET_TOKEN` secret in GitHub.

Any run that happens between steps 2 and 3 gets a `401`.
