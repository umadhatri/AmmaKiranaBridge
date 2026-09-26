import cgi
import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sarvamai import SarvamAI


ROOT = Path(__file__).parent
LANGUAGE_CODES = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Telugu": "te-IN",
    "Tamil": "ta-IN",
    "Kannada": "kn-IN",
}
SPOKEN_INTROS = {
    "English": "Your shopping list.",
    "Hindi": "आपकी खरीदारी की सूची।",
    "Telugu": "మీ కొనుగోలు జాబితా.",
    "Tamil": "உங்கள் மளிகைப் பட்டியல்.",
    "Kannada": "ನಿಮ್ಮ ದಿನಸಿ ಪಟ್ಟಿ.",
}
GROCERY_LIST_SCHEMA = {
    "name": "telugu_grocery_list",
    "description": "A precise grocery list extracted from Telugu speech.",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["telugu_name", "quantity", "unit", "uncertain"],
                    "properties": {
                        "telugu_name": {"type": "string"},
                        "quantity": {"type": ["number", "null"]},
                        "unit": {"type": ["string", "null"]},
                        "uncertain": {"type": "boolean"},
                    },
                },
            }
        },
    },
}
SHOPKEEPER_LABEL_SCHEMA = {
    "name": "shopkeeper_grocery_labels",
    "description": "Semantic grocery labels in the shopkeeper's selected language.",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["telugu_name", "shopkeeper_name"],
                    "properties": {
                        "telugu_name": {"type": "string"},
                        "shopkeeper_name": {"type": "string"},
                    },
                },
            }
        },
    },
}


def load_key():
    for line in (ROOT / ".env").read_text().splitlines():
        key, _, value = line.partition("=")
        if key == "SARVAM_API_KEY" and value.strip():
            return value.strip()
    raise RuntimeError("Set SARVAM_API_KEY in .env before starting the app.")


def client():
    return SarvamAI(api_subscription_key=load_key())


def structured_list(prompt):
    response = client().chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": prompt}],
        reasoning_effort="low",
        response_format={"type": "json_schema", "json_schema": GROCERY_LIST_SCHEMA},
    )
    return json.loads(response.choices[0].message.content)


def extract_items(transcript):
    prompt = f"""Extract a Telugu household grocery list from this transcript: {transcript!r}

For every item, telugu_name must contain only the grocery noun in Telugu — never quantity words, numbers,
or units. Put the amount in quantity as a number and the unit separately using kg, g, litre, ml, count,
packet, or dozen. Mark uncertain true only when the source itself is ambiguous.

Examples:
- "అరకిలో ఉల్లి" becomes telugu_name "ఉల్లి", quantity 0.5, unit "kg".
- "ఒక లీటర్ నూనె" becomes telugu_name "నూనె", quantity 1, unit "litre".
- "ఆరు ఉల్లిపాయలు" becomes telugu_name "ఉల్లిపాయలు", quantity 6, unit "count".
Do not add any item that was not said."""
    candidate = structured_list(prompt)
    repair_prompt = f"""Validate and repair this grocery extraction using the original Telugu transcript.
Transcript: {transcript!r}
Candidate: {json.dumps(candidate, ensure_ascii=False)}

Return corrected data only. Re-read every amount from the transcript; do not trust the candidate blindly.
Each telugu_name must be only the Telugu food or product noun; move all amount words (such as అర, పావు,
కిలో, లీటర్, ఒక) into numeric quantity and unit. Preserve kg and litre when they were spoken — for example,
"ఒక కిలో ఉల్లిపాయలు" is quantity 1 and unit "kg", not count. Never send a phrase like "అరకిలో ఉల్లి"
to translation — it must be "ఉల్లి", 0.5, "kg"."""
    return structured_list(repair_prompt)


def canonical_english_labels(items):
    names = [item["telugu_name"] for item in items]
    prompt = f"""Create a canonical English grocery label for each Telugu grocery item below.
Items: {json.dumps(names, ensure_ascii=False)}

Translate meaning, not pronunciation. Use a concise, familiar English or Indian-English grocery term of one
to four words. Do not add parentheses, definitions, categories, or any explanation. Use a specific standard
dal name when needed to distinguish similar dals. Never return romanized Telugu.
Return every source item exactly once, with its source Telugu name unchanged."""
    response = client().chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": prompt}],
        reasoning_effort="low",
        response_format={"type": "json_schema", "json_schema": SHOPKEEPER_LABEL_SCHEMA},
    )
    labels = json.loads(response.choices[0].message.content)["items"]
    return {item["telugu_name"]: item["shopkeeper_name"] for item in labels}


def make_list(transcript, target_language):
    shopping_list = extract_items(transcript)
    target_code = LANGUAGE_CODES[target_language]
    labels = canonical_english_labels(shopping_list["items"]) if target_code != "te-IN" else {}
    for item in shopping_list.get("items", []):
        name = item.get("telugu_name", "").strip()
        if target_code == "te-IN":
            item["shopkeeper_name"] = name
            continue
        canonical_name = labels.get(name, name)
        if target_code == "en-IN":
            item["shopkeeper_name"] = canonical_name
            continue
        translation = client().text.translate(
            input=canonical_name,
            source_language_code="en-IN",
            target_language_code=target_code,
            model="sarvam-translate:v1",
            numerals_format="international",
        )
        item["shopkeeper_name"] = translation.translated_text
    return shopping_list


def make_audio(shopping_list, target_language):
    spoken_items = []
    for item in shopping_list["items"]:
        amount = " ".join(str(value) for value in (item["quantity"], item["unit"]) if value is not None)
        spoken_items.append(f"{item['shopkeeper_name']}: {amount}.")
    speech = client().text_to_speech.convert(
        text=" ".join([SPOKEN_INTROS[target_language], *spoken_items]),
        language_code=LANGUAGE_CODES[target_language],
        model="bulbul:v3",
        speaker="shubh",
        pace=0.9,
        output_audio_codec="mp3",
    )
    return speech.audios[0]


class App(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/list":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", "")},
            )
            target_language = form.getfirst("target_language", "English")
            transcript = form.getfirst("transcript", "").strip()
            if not transcript and "audio" in form and getattr(form["audio"], "file", None):
                speech = client().speech_to_text.transcribe(
                    file=form["audio"].file,
                    model="saaras:v4",
                    mode="transcribe",
                    language_code="te-IN",
                    keyterms=["మినపప్పు", "కందిపప్పు", "పెసరపప్పు", "బియ్యం", "నూనె"],
                )
                transcript = speech.transcript
            if not transcript:
                raise ValueError("Record a note or type the Telugu list first.")
            shopping_list = make_list(transcript, target_language)
            response = {"transcript": transcript, "list": shopping_list}
            try:
                response["audio"] = make_audio(shopping_list, target_language)
            except Exception:
                response["audio_error"] = "The list is ready, but its audio could not be generated."
            self.respond(response)
        except Exception as error:
            self.respond({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def respond(self, body, status=HTTPStatus.OK):
        payload = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"Open http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), App).serve_forever()
