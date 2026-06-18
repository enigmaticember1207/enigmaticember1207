"""
script_generator.py
3 content types (English):
  horoscope  - Daily horoscope (12 signs rotation)
  love       - Love reading for today
  encourage  - Encouragement / self-love message
"""

import anthropic
import json
import random
import re
import logging
from datetime import datetime

client = anthropic.Anthropic()
log = logging.getLogger(__name__)

CONTENT_TYPES = ["horoscope", "love", "encourage"]

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

def today_zodiac_index() -> int:
    return datetime.now().timetuple().tm_yday % 12

SYSTEM_PROMPT = """You are a scriptwriter for short-form video content (TikTok/YouTube Shorts).

TARGET AUDIENCE:
- People feeling lonely, hurt, or overwhelmed
- Those struggling with relationships or heartbreak
- Anyone who needs a gentle push or reassurance
- People who feel unseen or misunderstood

NARRATION STYLE:
- Speak directly to "you" — warm, intimate, like a close friend
- Simple, everyday English — no jargon or complex words
- Short sentences (under 15 words each)
- Slow, calming tone — use commas and periods generously for natural pauses
- Flow: Empathy → Validation → Gentle encouragement
- Length: 320–350 characters (approx. 65–70 seconds when read aloud at calm pace)

STRICT RULES:
- NO mystical/spiritual jargon (universe, manifestation, vibration, soul, energy)
- NO empty guarantees ("everything will be fine", "you'll definitely succeed")
- NO preachy or lecture-like tone
- Title and narration MUST match the same theme
- Reply in JSON format ONLY — no preamble or explanation"""


def generate_script(content_type: str, performance_data: dict = None) -> dict:
    today = datetime.now()
    date_str = today.strftime("%B %d")
    idx = today_zodiac_index()
    zodiac = ZODIAC_SIGNS[idx]

    perf_hint = ""
    if performance_data and performance_data.get("top_theme"):
        perf_hint = f"\nNote: Last week's top performer was '{performance_data['top_theme']}'"

    prompts = {

        "horoscope": f"""Create a {zodiac} horoscope script for {date_str}.{perf_hint}

Theme: Speak ONLY to {zodiac} — today's energy, what to watch out for, and one lucky action.
Keep it personal and specific to {zodiac}'s traits. Do NOT mix in other signs.

Narration rules:
- 320–350 characters
- Calm, spoken English — not written English
- Start with "{zodiac}..." or "Hey {zodiac}..."

Reply in this JSON format only:
{{"hook":"Opening line to grab attention (under 15 words)",
"narration":"Full narration 320–350 characters. Calm spoken English. Short sentences with pauses.",
"captions":["{zodiac}","Today's energy","Watch out for this","Lucky action","A reminder","You've got this"],
"tiktok_caption":"TikTok caption + hashtags (#horoscope #{zodiac.lower()} #zodiac #dailyhoroscope)",
"youtube_title":"{zodiac} Horoscope | {date_str}",
"thumbnail_text":"{zodiac} Today"}}""",

        "love": f"""Create a love reading script for {date_str}.{perf_hint}

Theme: Speak to someone with a crush or unrequited love — the nervousness, the hope, what to do next.
Focus on ONE person: someone silently in love. Do NOT address people in relationships.

Narration rules:
- 320–350 characters
- Warm and gentle spoken English
- Start with empathy: "You like someone, don't you..." or similar

Reply in this JSON format only:
{{"hook":"Opening line (under 15 words, speaks to having a crush)",
"narration":"Full narration 320–350 characters. Empathy → validation → one gentle nudge.",
"captions":["You like someone","It's okay to feel this","Take your time","Be yourself","Don't overthink","You deserve love"],
"tiktok_caption":"TikTok caption + hashtags (#loveadvice #crush #lovereading #selflove)",
"youtube_title":"Love Reading for {date_str} | If You Have a Crush",
"thumbnail_text":"You Like Someone"}}""",

        "encourage": f"""Create an encouragement script for {date_str}.{perf_hint}

Pick ONE theme from this list (do NOT mix themes):
- For anyone who's been too hard on themselves
- For anyone exhausted by other people's opinions
- For anyone who feels like they're falling behind
- For anyone who hasn't heard "you're doing great" lately
- For anyone who keeps giving but never receives
- For anyone who's been crying alone

Use the chosen theme as the title. Narration must match exactly.

Narration rules:
- 320–350 characters
- Quiet, intimate spoken English — like a late-night message from a friend
- Start by naming the feeling: "You've been really hard on yourself lately..." or similar

Reply in this JSON format only:
{{"hook":"Opening line that names the feeling (under 15 words)",
"narration":"Full narration 320–350 characters. Empathy → you are not alone → one small truth.",
"captions":["It's okay","You're not alone","You're doing enough","Be gentle with yourself","You matter","Keep going"],
"tiktok_caption":"TikTok caption + hashtags (#mentalhealth #selfcare #selflove #youmatter)",
"youtube_title":"Chosen theme title (under 60 characters)",
"thumbnail_text":"Short thumbnail text (under 6 words)"}}"""
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompts[content_type]}]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    script = json.loads(raw)

    # Warn if narration is too short
    narration = script.get("narration", "")
    if len(narration) < 280:
        log.warning(f"Narration too short: {len(narration)} chars")

    return script
