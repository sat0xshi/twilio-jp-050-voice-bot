# Twilio Japan 050 voice demo

Public demo: buy a Japan **050 National** number on Twilio, answer one inbound call, place one outbound call, and append call-status callbacks to a JSONL file with phone numbers masked.

On an inbound call the bot must introduce itself by name before it asks how it can help. The name is `BOT_NAME` (default `Grok Phone Bot`).

Anyone who clones this repo can follow the steps below. The app is a small FastAPI server plus one outbound script. It does not record calls, and it does not set up SIP trunks or messaging.

## What you need

- Python 3.11 or newer
- A Twilio account
- A phone that can call the 050 number, and a destination for the outbound test
- [ngrok](https://ngrok.com/) or [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/) so Twilio can reach the app on your machine

Japan 050 numbers are IP-phone numbers. In Twilio they are **National** numbers and use the prefix **+8150**.

## 1. Buy a Japan 050 National number

Twilio will not sell the number until a **Regulatory Bundle** for Japan is approved. Document rules change. Use Twilio's page as the source of truth:

<https://www.twilio.com/en-us/guidelines/jp/regulatory>

Console path (menu labels drift; the order does not):

1. Sign in at <https://console.twilio.com>.
2. Open **Phone Numbers → Regulatory Compliance**.
3. Create a Regulatory Bundle.
   - Country: **Japan**
   - Number type: **National** (this is the 050 inventory, prefix +8150)
   - End-user type: whichever type the form offers for the person or business that will use the number
4. Fill in the end-user and address the form asks for, upload the documents it lists, and submit.
5. Wait until the bundle status is **Twilio Approved**. A purchase before that fails.
6. Open **Phone Numbers → Manage → Buy a number**.
7. Country: **Japan (+81)**. Enable **Voice**. In the number-type filter, choose **National**.
8. Search. Results look like `+8150…`. Buy one.
9. On the purchase screen, assign the approved Japan National bundle and the address the form requires, then confirm.
10. Copy the number in E.164 (`+8150` and 8 more digits). You will put it in `.env` in the next section. Do not commit it.

Leave the number's Voice webhook empty until the tunnel in section 4 is up. Section 5 points it at this app.

Trial accounts: Twilio plays a short trial notice before your greeting. Outbound calls from a trial account can only reach [verified caller IDs](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account). Enable Japan under **Voice → Settings → Geo permissions** before the outbound test.

## 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`. `.env.example` holds placeholders only. Real values stay in `.env`, which is gitignored.

| Variable | Where it comes from |
| --- | --- |
| `TWILIO_ACCOUNT_SID` | Console → Account → API keys & tokens. Starts with `AC`. |
| `TWILIO_AUTH_TOKEN` | Same page. The primary Auth Token, 32 hex characters. |
| `TWILIO_FROM_NUMBER` | The 050 number you bought, E.164, for example `+815012345678`. |
| `OUTBOUND_TO` | The phone that should ring for the outbound test, E.164. |
| `PUBLIC_BASE_URL` | The tunnel origin from section 4. `https://…`, no path, no trailing slash. |
| `TWILIO_VALIDATE_REQUESTS` | `auto` (default). Signatures are checked once `TWILIO_AUTH_TOKEN` is set. |
| `BOT_NAME` | Display name spoken on inbound calls. Default `Grok Phone Bot` when unset or blank. |
| `STATUS_LOG_PATH` | Default `logs/call_status.jsonl`. |

Restart the server after you change `.env`. The process reads it at startup.

`TWILIO_VALIDATE_REQUESTS=false` skips signature checks. Use that only to curl TwiML on localhost before you have a token. Turn it back to `auto` before a real call.

## 3. Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
chmod +x scripts/run_server.sh scripts/place_call.sh
./scripts/run_server.sh
```

The server listens on `127.0.0.1:8000` unless `HOST` and `PORT` in `.env` say otherwise. Check it:

```bash
curl -sS http://127.0.0.1:8000/health
```

`{"ok":true}` means the process is up.

On Windows, from the activated venv:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m app.outbound
```

## 4. Open a tunnel

Twilio's cloud must fetch your webhooks. Pick one tunnel. Both print an `https` URL. Put that origin in `PUBLIC_BASE_URL`, restart the server, and use the same origin in the console webhooks.

Quick-tunnel hostnames change every run. When the URL changes, update `PUBLIC_BASE_URL` and the number's webhooks together. Signature checks compare `PUBLIC_BASE_URL` plus the path with the URL Twilio requested.

### ngrok

```bash
ngrok http 8000
```

Use the `https://….ngrok-free.app` forwarding URL (no path).

### Cloudflare Tunnel

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Use the `https://….trycloudflare.com` URL it prints (no path).

## 5. Point the 050 number at the app

On the number's page in the console, under **Voice**:

| Setting | Value |
| --- | --- |
| A call comes in | Webhook, HTTP POST, `https://<your-public-host>/voice` |
| Call status changes | Webhook, HTTP POST, `https://<your-public-host>/status` |

Save. The outbound script sets its own status callback; you do not need a second console entry for that.

## 6. Inbound test

Required inbound behavior: when the call is answered, the bot speaks its own name first, then asks how it can help. It must not open with a generic greeting that leaves the name out.

`POST /voice` returns TwiML in this order:

1. Japanese self-introduction (`Polly.Mizuki`, `ja-JP`): `こんにちは、{BOT_NAME}です。`
2. Japanese request prompt: `ご用件をどうぞ。どのようにお手伝いできますか。`
3. English restatement that repeats the name and the offer to help.
4. Hang up.

`BOT_NAME` comes from the environment. If it is missing or blank, the spoken name is `Grok Phone Bot`. Change `BOT_NAME` in `.env` and restart the server to use another name. A placeholder name is enough for this demo.

Local XML check (validation off, or no auth token yet):

```bash
curl -sS -X POST http://127.0.0.1:8000/voice
```

The first `<Say>` text must contain `BOT_NAME`. The next `<Say>` asks for the caller's request.

Phone check, after the tunnel and the console webhook are in place:

1. Call your `+8150…` number.
2. You should hear `こんにちは、` plus the bot name, then the request prompt, then the English line.
3. Twilio hangs up.

A trial account inserts its own spoken notice before your bot speaks.

## 7. Outbound test

`PUBLIC_BASE_URL` must be the live tunnel. Twilio fetches `POST /outbound-twiml` when the destination answers. With the server still running:

```bash
./scripts/place_call.sh
```

The script calls the Twilio REST API once: `calls.create` from `TWILIO_FROM_NUMBER` to `OUTBOUND_TO`. The callee hears a different prompt ("outbound test call"). The call is capped at 30 seconds. Stdout prints the call SID and **masked** numbers, for example:

```text
call_sid=CA0123456789abcdef0123456789abcdef status=queued to=+81******0000 from=+81******0000
```

The Auth Token and the full phone numbers are not printed. On failure the script prints the HTTP status and Twilio error code only.

Trial accounts can only call verified numbers. If Twilio rejects the call, verify `OUTBOUND_TO` in the console and confirm Japan is enabled in Voice geo permissions.

## 8. Status log

Inbound and outbound status callbacks append one JSON object per line to `logs/call_status.jsonl` (gitignored):

```json
{"ts":"2026-01-01T00:00:00Z","call_sid":"CA0123456789abcdef0123456789abcdef","call_status":"completed","direction":"inbound","from":"+81******2222","to":"+81******1234","duration":"8"}
```

`from` and `to` keep a short country prefix and the last four digits. The subscriber number in the middle is replaced with `*`. The account SID is not stored. A value that still contains an E.164 number is redacted again at write time.

```bash
tail -f logs/call_status.jsonl
```

An invalid `X-Twilio-Signature` returns HTTP 403 and writes nothing.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

The tests cover masking, TwiML, the status JSONL line, signature accept/reject, and the outbound request shape. They do not call Twilio.

## Layout

```text
app/main.py            POST /voice, POST /outbound-twiml, POST /status
app/outbound.py        one REST call; python -m app.outbound
app/masking.py         phone masking
app/status_log.py      JSONL append
scripts/run_server.sh
scripts/place_call.sh
.env.example           placeholders only
```

## Security

- Do not commit `.env`, a real SID, a real Auth Token, or a real phone number.
- Leave `TWILIO_VALIDATE_REQUESTS` on `auto` when the token is set. `PUBLIC_BASE_URL` must match the `https` origin Twilio calls.
- This demo does not record audio. Do not log raw webhook bodies; the status file is masked on purpose.
- `logs/` is gitignored. Treat it as local operational data anyway.

## 日本語（概要）

公開デモです。Twilio で日本の 050（National、`+8150`）番号を買い、着信では最初にボット名を名乗ってから用件を尋ね、発信を 1 件行い、通話状態を番号マスク済みの JSONL に残します。

1. Console の **Phone Numbers → Regulatory Compliance** で、国 Japan・番号種別 **National** の規制バンドルを申請する。承認後に **Buy a number** から Voice 付きの National 番号（`+8150…`）を買う。必要書類は [Japan regulatory guidelines](https://www.twilio.com/en-us/guidelines/jp/regulatory) が正です。
2. `.env.example` を `.env` にコピーし、SID・Auth Token・050 番号・発信先・公開 URL を入れる。`.env` はコミットしない。
3. `python3 -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt` のあと `./scripts/run_server.sh` で起動する。
4. `ngrok http 8000` または `cloudflared tunnel --url http://127.0.0.1:8000` で HTTPS の入口を作る。`PUBLIC_BASE_URL` にそのオリジン（パスなし）を入れ、サーバーを再起動する。
5. 番号の Voice で、着信 Webhook を `POST https://<host>/voice`、通話状態を `POST https://<host>/status` にする。
6. 着信の必須動作: 最初の発話は「こんにちは、{BOT_NAME}です。」（未設定時は `Grok Phone Bot`）。その次に用件を尋ねる。名前のない汎用挨拶から始めない。050 番号へ電話して確認する。ローカルの XML 確認は `curl -sS -X POST http://127.0.0.1:8000/voice`。
7. `./scripts/place_call.sh` で `OUTBOUND_TO` へ 1 件発信する。トライアルアカウントは確認済み番号にしか発信できない。
8. `logs/call_status.jsonl` を見て、番号が末尾 4 桁以外マスクされていることを確認する。

手順の詳細は上の英語の節を参照してください。

## License

MIT. See [LICENSE](LICENSE).
