# Amma's Kirana Bridge

Turn a grocery voice note into a clear, translated shopping list for a shopkeeper.

**Live app:** [amma-kirana-bridge.vercel.app](https://amma-kirana-bridge.vercel.app/)

Amma's Kirana Bridge helps families share a grocery list across languages. Speak a list in English, Telugu,
Hindi, Tamil, or Kannada; choose the shopkeeper's preferred language; then show or play the translated list.

## How it works

1. Choose the language you will speak and record a short grocery note.
2. Choose the shopkeeper's language.
3. Sarvam AI transcribes the note, identifies items and quantities, translates the grocery names, and generates
   audio for the shopkeeper.

The app uses Sarvam Speech-to-Text, Sarvam Chat, Sarvam Translate, and Bulbul Text-to-Speech.

## Run locally

```bash
python3 app.py
```

Then open http://127.0.0.1:8000. Choose the language you will speak (English, Telugu, Hindi, Tamil, or Kannada), record a short note (up to 30 seconds), choose the shopkeeper's language, and make the list. The app also generates a Sarvam Bulbul audio version in that language for the shopkeeper to play.

Create a `.env` file containing `SARVAM_API_KEY=...`. The key stays on the server and must never be
committed.

## Deploy on Vercel

The repository includes a Vercel Python Function at `/api/list`. In the Vercel project settings, add
`SARVAM_API_KEY` as an environment variable for Production (and Preview if needed), then redeploy. Do not
commit or upload `.env`.
