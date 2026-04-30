# ZH-35 - GenAI Advanced Auth Registration API

## Ticket Purpose

ZH-35 adds a service-token-authenticated registration endpoint for GenAI user provisioning. The endpoint is intentionally limited to accepting a `user_id` and returning an idempotent provisioning response until the export-control entitlement rules are approved.

## Generated Files and Code Changes

`zh-35-transfer.py` creates or updates:

- `app_users/register_genai.py` — **not** under `app_users/views/`, because many backends ship `app_users/views.py` as a single module. In that layout `app_users.views` is not a Python package, so `from app_users.views.register_genai import ...` raises *"is not a package"*.
- `app_users/urls.py` — imports `from app_users.register_genai import RegisterGenAIView`.

The script also writes `tests/app_users/test_register_genai.py` (force-added by the transfer script).

## Reasoning, Choices, and Justification

The implementation creates a minimal DRF `APIView` guarded by `APIKeyAuthentication`. This is the safest first step because the business process needs a registration surface, but auto-entitlement through X-Class and US-person claims is explicitly blocked pending Global Trade sign-off.

Rejected alternatives:

- Auto-provisioning roles and folders immediately: blocked by governance and export-control review.
- Public or user-session auth: wrong trust boundary for service-to-service registration.
- Building a broad entitlement engine in this ticket: too much policy risk before George/Dave/Global Trade approval.

## Code Breakdown

- `RegisterGenAIView`: validates `user_id`, uses API-key auth, and returns an idempotent placeholder response.
- URL patch: adds `/api/users/register-genai/` to `app_users/urls.py`.
- TODO comments: preserve the governance gate and future implementation points for GenAI role, folder, and assistant access.

## Runtime Setup and Test Playbook

Run from the backend repository root on the runtime machine, where `manage.py` lives unless the ticket says otherwise.

```cmd
cd C:\path\to\ENCHS-PW-GenAI-Backend
py -3 C:\path\to\rag_eval\evals\phase-2\zh-35-transfer.py
```

On macOS/Linux:

```bash
cd /path/to/ENCHS-PW-GenAI-Backend
python3 /path/to/rag_eval/evals/phase-2/zh-35-transfer.py
```


Run Django checks:

```cmd
uv sync --group dev
uv run python manage.py check
```

Manual API smoke test after configuring a valid API key. The backend is async (ASGI), so start it with `uvicorn` — not `manage.py runserver`:

```cmd
uvicorn app.wsgi:application --lifespan --host=0.0.0.0 --port=8000 --workers 1
```

Then in another shell:

```cmd
curl -X POST http://localhost:8000/api/users/register-genai/ -H "Content-Type: application/json" -H "Authorization: Api-Key <token>" -d "{\"user_id\":\"sample.user\"}"
```

Expected response:

```json
{"status":"provisioned","user_id":"sample.user"}
```

## Git Add and Commit Guidance

Use `git add -f` for the generated test file if your repo ignores `tests/`.

```cmd
git add app_users/register_genai.py app_users/urls.py
git add -f tests/app_users/test_register_genai.py
git commit -m "ZH-35: add RegisterGenAI registration endpoint"
```
