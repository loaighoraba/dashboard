# Dashboard

A small [FastAPI](https://fastapi.tiangolo.com/) web app that handles my technical needs, deployed on [DigitalOcean App Platform](https://www.digitalocean.com/products/app-platform).

It currently has one feature: a webhook that GitHub Actions calls on a schedule. The webhook checks a shared secret and reports success. It doesn't do any work yet; scheduled tasks will be added to it.

## Tech stack

- Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- FastAPI (`fastapi[standard]`)
- pytest for tests
- DigitalOcean App Platform for hosting (built from the `Dockerfile`)
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
  ci.yml               # Runs the tests; deploys to App Platform on pushes to main
  cron.yml             # Scheduled workflow that calls the webhook
pyproject.toml         # Dependencies and the FastAPI entrypoint (app.main:app)
Dockerfile             # Production image (uv + fastapi run on port 8080)
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

## Deployment (DigitalOcean App Platform)

The app is created and configured in the DigitalOcean dashboard. Every push to `main` runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml), which runs the test suite first and only deploys if the tests pass. The deploy job uses [`digitalocean/app_action`](https://github.com/digitalocean/app_action) to redeploy the app named `dashboard` with its current dashboard settings. It waits for the deployment to finish, so a failed deployment fails the workflow run. Pull requests only run the tests.

App Platform builds the image from the [`Dockerfile`](Dockerfile), which installs the locked dependencies with uv and starts the app with `fastapi run` on port 8080. `fastapi run` reads the entrypoint from `[tool.fastapi]` in `pyproject.toml`.

To try the production image locally:

```bash
docker build -t dashboard .
docker run --rm -p 8080:8080 -e CRON_SECRET_TOKEN=local-secret dashboard
```

### First-time setup

1. In the DigitalOcean dashboard, go to **Apps → Create App**, choose GitHub as the source, and pick this repository and the `main` branch. **Turn off Autodeploy**, because GitHub Actions deploys after the tests pass.
2. App Platform detects the `Dockerfile`. Set the HTTP port to `8080` and the health check path to `/`.
3. Add the environment variable `CRON_SECRET_TOKEN` and tick **Encrypt**.
4. Name the app `dashboard`. The deploy job finds the app by this name; if you pick a different name, change `app_name` in `ci.yml`.
5. Create a personal access token under **API → Tokens** with read and write access to Apps. In GitHub, add it as the repository secret `DIGITALOCEAN_ACCESS_TOKEN`.
6. Use the app's URL (`https://<app>.ondigitalocean.app`) as the `APP_URL` variable in GitHub (see below).

The deploy job runs in a GitHub environment called `production`, which GitHub creates on the first run. You can add protection rules to it, such as requiring approval before a deploy.

### Generating the secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This produces 256 random bits in URL-safe characters, so the value never needs quoting in headers or YAML. Use the same value in DigitalOcean and in GitHub (see below).

## Scheduled job (GitHub Actions)

[`.github/workflows/cron.yml`](.github/workflows/cron.yml) calls `POST /webhooks/cron` every day at 06:00 UTC. To run it at a different time, change the `cron` expression in that file. You can also start it by hand from the **Actions** tab (`workflow_dispatch`).

The workflow needs two settings in **Settings → Secrets and variables → Actions**:

| Kind     | Name                | Value                                                        |
| -------- | ------------------- | ------------------------------------------------------------ |
| Secret   | `CRON_SECRET_TOKEN` | The same value as in DigitalOcean                            |
| Variable | `APP_URL`           | The deployed app's base URL, e.g. `https://<app>.ondigitalocean.app` |

The call retries up to 3 times. If the webhook still returns an error, the workflow run fails and GitHub notifies you.

GitHub only runs scheduled workflows from the default branch, and scheduled runs can start several minutes late.

### Rotating the secret

1. Generate a new token.
2. Update `CRON_SECRET_TOKEN` in the app's settings in DigitalOcean. App Platform redeploys the app when a variable changes.
3. Update the `CRON_SECRET_TOKEN` secret in GitHub.

Any run that happens between steps 2 and 3 gets a `401`.
