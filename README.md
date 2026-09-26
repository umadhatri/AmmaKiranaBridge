# Amma's Kirana Bridge

Turn a short grocery note into a clear list for a shopkeeper.

Run it locally:

```bash
python3 app.py
```

Then open http://127.0.0.1:8000. Choose the language you will speak (English, Telugu, Hindi, Tamil, or Kannada), record a short note (up to 30 seconds), choose the shopkeeper's language, and make the list. The app also generates a Sarvam Bulbul audio version in that language for the shopkeeper to play.

The Sarvam API key stays in `.env` and is used only by the local Python server.

## Deploy on Vercel

The repository includes a Vercel Python Function at `/api/list`. In the Vercel project settings, add
`SARVAM_API_KEY` as an environment variable for Production (and Preview if needed), then redeploy. Do not
commit or upload `.env`.
