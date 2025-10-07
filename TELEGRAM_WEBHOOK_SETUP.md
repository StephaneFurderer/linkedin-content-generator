# 🤖 Telegram Bot Webhook Setup

## Overview

The Telegram bot now uses **webhooks** instead of polling for production reliability. This eliminates the "409 Conflict" error when multiple instances try to run simultaneously.

## Environment Variables Required

Add these to your Railway environment variables:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_WEBHOOK_URL=https://your-app.railway.app
```

⚠️ **Important:** `TELEGRAM_WEBHOOK_URL` should be your Railway app URL **without** any path (no `/telegram/webhook` at the end)

## How It Works

1. **On App Startup:** The server automatically calls Telegram API to register the webhook at `https://your-app.railway.app/telegram/webhook`

2. **Telegram Sends Updates:** When users send messages, Telegram POSTs them to your webhook endpoint

3. **Bot Processes:** Your bot handlers process the updates and respond

## Setup Steps

### 1. Get Your Railway URL

In Railway dashboard:
- Click on your service
- Copy the public domain (e.g., `https://linkedin-content-generator-production.up.railway.app`)

### 2. Set Environment Variables

In Railway dashboard → Variables:
```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_URL=https://linkedin-content-generator-production.up.railway.app
```

### 3. Deploy

Push your code:
```bash
git add .
git commit -m "Switch Telegram bot to webhooks"
git push origin main
```

Railway will auto-deploy.

### 4. Verify Webhook

After deployment, check webhook status:
```bash
curl https://your-app.railway.app/telegram/webhook-info
```

You should see:
```json
{
  "url": "https://your-app.railway.app/telegram/webhook",
  "pending_update_count": 0,
  "last_error_message": null
}
```

### 5. Test the Bot

Send `/help` to your Telegram bot. It should respond instantly!

## Troubleshooting

### Bot Not Responding

**Check webhook status:**
```bash
curl https://your-app.railway.app/telegram/webhook-info
```

**Manually setup webhook:**
```bash
curl -X POST https://your-app.railway.app/telegram/setup-webhook \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://your-app.railway.app"}'
```

### Still Getting 409 Errors

- Make sure only ONE Railway instance is running (check Replicas = 1)
- Remove any old polling-based deployments
- The webhook approach prevents conflicts automatically

### Webhook Not Receiving Updates

- Check Railway logs for startup messages
- Verify `TELEGRAM_WEBHOOK_URL` doesn't have trailing slash
- Ensure your Railway app is publicly accessible

## API Endpoints

### `POST /telegram/webhook`
Receives updates from Telegram (called by Telegram, not by you)

### `GET /telegram/webhook-info`
Get current webhook information

### `POST /telegram/setup-webhook`
Manually trigger webhook setup (useful for troubleshooting)

## Benefits of Webhooks vs Polling

✅ **No 409 Conflicts:** Only one webhook URL, no multiple instances fighting  
✅ **Faster Response:** Instant delivery instead of polling every few seconds  
✅ **Lower Resources:** No background thread constantly checking for updates  
✅ **Railway-Friendly:** Works perfectly with container restarts  
✅ **Production-Ready:** Industry standard for Telegram bots  

## Commands Available

All your bot commands work the same:
- `/help` - Show help message
- `/ideas <readwise_url>` - Generate 12 content ideas
- `/select <conversation_id> <idea_number>` - Generate article from idea
- `/create_post <url> <notes>` - Quick post generation
- `/post` - Advanced YAML post generation

## Local Development

For local development, webhooks won't work (Telegram can't reach localhost). The code automatically skips webhook setup if `TELEGRAM_WEBHOOK_URL` is not set.

To test locally, you can temporarily use polling or use a tool like ngrok to expose localhost.

