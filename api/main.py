from flask import Flask, jsonify, make_response
import re
import requests
import json
import random
import time
import os
import base64
from urllib.parse import urlparse

app = Flask(__name__)
app.config['ENV'] = os.environ.get('FLASK_ENV', 'production')
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

cache = {'html': None, 'timestamp': 0}
validated_url_cache = {}


def _make_svg_placeholder(text='Image unavailable', width=640, height=360):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ddd"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="20" fill="#666">{text}</text>
</svg>'''
    b64 = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    return f"data:image/svg+xml;base64,{b64}"


PLACEHOLDER_DATA_URI = _make_svg_placeholder()


def _is_remote_url(url):
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https'):
        return True
    return False


def _url_exists(url, timeout=5):
    if not url or url.startswith('data:'):
        return True
    if not _is_remote_url(url):
        return True
    if url in validated_url_cache:
        return validated_url_cache[url]
    try:
        resp = requests.head(url, allow_redirects=True, timeout=timeout, verify=False)
        exists = resp.status_code < 400
        if not exists:
            resp = requests.get(url, stream=True, timeout=timeout, verify=False)
            exists = resp.status_code < 400
    except Exception:
        exists = False
    validated_url_cache[url] = exists
    return exists


def _process_images_in_html(html):
    def replace_img(match):
        prefix = match.group(1)
        quote = match.group(2)
        src = match.group(3)
        new_src = src
        if not _url_exists(src):
            new_src = PLACEHOLDER_DATA_URI
        replacement = f"{prefix}{quote}{new_src}{quote}"
        return replacement

    html = re.sub(r'(<img\b[^>]*\bsrc\s*=\s*)(["\'])(.*?)\2', replace_img, html, flags=re.IGNORECASE | re.DOTALL)

    def add_onerror(match):
        tag = match.group(0)
        if re.search(r'onerror\s*=\s*', tag, flags=re.IGNORECASE):
            return tag
        insert_at = -1
        onerror_attr = f" onerror=\"this.onerror=null;this.src='{PLACEHOLDER_DATA_URI}';\""
        new_tag = tag[:-1] + onerror_attr + tag[-1]
        return new_tag

    html = re.sub(r'<img\b[^>]*>', add_onerror, html, flags=re.IGNORECASE)
    def replace_css_url(match):
        quote = match.group(1) or ''
        url = match.group(2).strip()
        if not _url_exists(url):
            return f"url('{PLACEHOLDER_DATA_URI}')"
        return f"url({quote}{url}{quote})"

    html = re.sub(r'url\(\s*([\'\"]?)(.*?)\1\s*\)', replace_css_url, html, flags=re.IGNORECASE)

    return html
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    return response

def call_ai(prompt, system_prompt=None, is_code=False):
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    if is_code:
        temperature = 0.95
    else:
        temperature = 0.8
    try:
        response = requests.post(
            'https://ai.hackclub.com/chat/completions',
            headers={'Content-Type': 'application/json'},
            json={
                'messages': messages,
                'temperature': temperature,
                'include_reasoning': True
            },
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.SSLError:
        time.sleep(1)
        try:
            response = requests.post(
                'https://ai.hackclub.com/chat/completions',
                headers={'Content-Type': 'application/json'},
                json={
                    'messages': messages,
                    'temperature': temperature,
                    'include_reasoning': True
                },
                verify=False,
                timeout=60
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"Error generating content: {str(e)}"
    except Exception as e:
        return f"Error generating content: {str(e)}"

@app.route('/', methods=['GET'])
def generate_random_website():
    if cache['html'] and (time.time() - cache['timestamp'] < 10 * 60):
        return cache['html']
    
    ideas_system = "You are a creative web design historian who specializes in pre-2000 internet culture and website concepts. Generate diverse, authentic retro website ideas that capture the spirit of different eras from the 1980s to 1999."
    ideas_prompt = "Generate exactly 10 unique retro website concepts from before the year 2000. Each should represent different eras, purposes, and design styles from the 1980s-1990s. Return ONLY a valid JSON array with objects containing: id, era, type, purpose, target_audience, and brief_description. Make each concept historically authentic and diverse."
    
    try:
        ideas_response = call_ai(ideas_prompt, ideas_system)
        ideas_json = re.sub(r'^```json\s*', '', ideas_response)
        ideas_json = re.sub(r'\s*```$', '', ideas_json)
        ideas_list = json.loads(ideas_json)
        selected_idea = random.choice(ideas_list)
    except:
        selected_idea = {"era": "1990s", "type": "BBS", "purpose": "Community Forum", "target_audience": "Tech enthusiasts", "brief_description": "Early bulletin board system for sharing software and discussions"}
    
    step1_system = "You are a creative web designer who comes up with unique, interesting, and diverse website concepts. Be imaginative and think outside the box. Explain your ideas in plain text, medium-short paragraphs, and include all necessary details for a complete website concept. Do not use any tools which require additional setup. You like retro, please use retro styles (but make the design really impressive, you can even describe animations). Make sure that even if the content is retro, doesn't mean that the content needs to be retro. For example it can be a early stage retro netflix copy. It doesn't need to be around time traveling. Please imagine that you are in that year as the website. Just write the plain text as answer, nothing more (no styling, etc.). So you don't write no * or ** and simular symbols, just plain text."
    step1_prompt = f"Based on this retro concept: {json.dumps(selected_idea)}, generate a detailed website specification with specific requirements. Include: website type/purpose, target audience, key features needed, color scheme suggestions, typography, layout structure, animations, and overall design style that authentically represents the {selected_idea.get('era', '1990s')} era. Be unique, engaging, and historically accurate. Just write the plain text as answer, nothing more (no styling, etc.). So you don't write no * or ** and simular symbols, just plain text."
    website_requirements = call_ai(step1_prompt, step1_system)

    step2_system = "You are a skilled content writer who creates engaging, creative website copy that captures visitors' attention. We are in 2025. Please make everything fun, playful, creative, funny. It doesn't need to be a retro content. Play along as you be in the time of the website. If the site is retro don't include the word 'retro' so make it authentic."
    step2_prompt = f"Based on these website requirements: {str(website_requirements)}, create complete website content including: site name, tagline, main heading, navigation menu items, 2-3 paragraphs of engaging content, features/services list, and a call-to-action button text. Make it creative and engaging. Just write the plain text as answer, nothing more (no styling, etc.). So you don't write no * or ** and simular symbols, just plain text."
    website_content = call_ai(step2_prompt, step2_system)

    step3_system = (
        "You are an expert frontend developer who creates beautiful websites with HTML, CSS, and JavaScript. "
        "You always return complete, working HTML code (without comments). Requirements: Style is pre-specified in requirements; try matching the vibe of the page as closely as possible. "
        "Do NOT reference or link to any external assets (no external images, fonts, or scripts). If the design requires graphics, icons, or pictures, embed them directly using inline SVG markup or data-URI images only. "
        "Prefer raw inline <svg> elements placed in the HTML where needed, or data:image/svg+xml;base64 URIs for backgrounds—do not output <img src=\"http...\"> to external URLs. "
        "Return ONLY the HTML code with embedded CSS and any needed JavaScript. Make every element functional on the page. Ensure the result is a single-file program with no external dependencies. "
        "Do not hallucinate assets because there aren't any. For the page footer, always add: SiteSuprise by Barnabás (MasterBros Developers)"
    )
    step3_prompt = f"Based on these requirements: {str(website_requirements)} and this content: {str(website_content)}, generate complete HTML code."

    html_code = call_ai(step3_prompt, step3_system)
    sanitized = re.sub(r'^```\w*', '', html_code)
    sanitized = re.sub(r'```$', '', sanitized)
    sanitized = sanitized.strip()
    try:
        sanitized = _process_images_in_html(sanitized)
    except Exception:
        pass
    cache['html'] = sanitized
    cache['timestamp'] = time.time()
    return sanitized

application = app

if __name__ == '__main__':
    from wsgiref.simple_server import make_server

    server = make_server('0.0.0.0', 39641, application)
    server.serve_forever()