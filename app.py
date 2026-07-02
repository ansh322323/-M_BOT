import os
import base64
import time
import sqlite3
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "*"}})

app.secret_key = "m_performance_matrix_secure_771"
DB_PATH = os.path.join(BASE_DIR, "m_memory_matrix.db")

# Initialize database
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_db()

# Establish Gemini Engine initialization safely using official google-genai SDK
gemini_client = None
def verify_and_get_client():
    global gemini_client
    if gemini_client is not None:
        return gemini_client
    
    # Retrieves the API key securely from your environment variables
    api_key_check = os.environ.get("GEMINI_API_KEY")
    if not api_key_check:
        print("[-] Gemini API Key is missing from Environment Variables.")
        return None
    try:
        gemini_client = genai.Client(api_key=api_key_check)
        return gemini_client
    except Exception as e:
        print(f"[-] Client initialization error: {e}")
        return None

def query_gemini(prompt, system_instruction="", context_history=None):
    client = verify_and_get_client()
    if not client:
        return "[Gemini Setup Error: Configuration key missing on Cloud server. Set GEMINI_API_KEY]"
        
    if context_history is None:
        context_history = []
        
    max_retries = 3
    delay = 2
    
    # Build context message timeline cleanly matching the new standard formats
    contents = []
    for msg in context_history:
        contents.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )
    # Append the newest message input
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
    )
    
    # Configure system instructions structural limits
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.7,
        max_output_tokens=1024
    )
    
    for attempt in range(max_retries):
        try:
            # Utilizing gemini-2.5-flash for lighting-fast performance metrics
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=config,
            )
            return response.text.strip() if response.text else "[Gemini Error: Empty response structural data]"
            
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e).toUpperCase():
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
            return f"[Gemini Resource Quota Exhausted: {e}]"

@app.route("/check_status", methods=["GET"])
def check_status_endpoint():
    client_status = verify_and_get_client()
    return jsonify({"gemini_active": client_status is not None, "tracking_active": False})

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    data = request.json or {}
    prompt = data.get("prompt", "").strip()
    mode = data.get("mode", "default")
    provider = data.get("provider", "gemini") 
    session_id = "ansh_session_core"
    
    if not prompt:
        return jsonify({"response": "Send a message to initialize."})

    image_keywords = ["generate image", "generate img", "create image", "create img", "make image", "make img", "draw an image", "draw a picture", "genrate img", "genrate image", "genrerate"]
    is_image_request = any(keyword in prompt.lower() for keyword in image_keywords)
    
    image_uri = None
    reply = ""

    if is_image_request:
        reply = "[Notice: Image Generation features require active Imagen access on this pipeline node. Text queries are fully active.]"
    else:
        context_history = []
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY id DESC LIMIT 10", (session_id,))
                rows = cursor.fetchall()
                for row in reversed(rows):
                    if not row[1] or any(err in row[1] for err in ["Error", "UNAVAILABLE", "404", "429", "Exception"]):
                        continue
                    # Match standard structural roles
                    mapped_role = "user" if row[0] in ["user", "user-bubble"] else "model"
                    context_history.append({"role": mapped_role, "content": row[1]})
        except Exception as db_err:
            print(f"DB Read Error: {db_err}")

        system_instruction = "You are an advanced assistant named M-BOT. Keep replies precise, perfectly engineered, and completely natural."
        if mode == "mm-mode":
            system_instruction += " Focus on high-octane performance metrics and engineering layout rules."

        # Route all requests securely into the fixed Gemini query module
        reply = query_gemini(prompt, system_instruction, context_history)

    if not isinstance(reply, str) or not reply.strip():
        reply = "[No response could be generated. Please try again.]"

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)", (session_id, "user", prompt))
            cursor.execute("INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)", (session_id, "model", reply))
            conn.commit()
    except Exception as db_write_err:
        print(f"DB Write Error: {db_write_err}")

    return jsonify({"response": reply, "image_uri": image_uri})

@app.route("/clear_memory", methods=["POST"])
def clear_memory_endpoint():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history")
            conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return render_template_string(VIBE_INTERFACE_LAYOUT)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'logo.png', mimetype='image/png')


VIBE_INTERFACE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>///M-BOT Universal</title>
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon.ico">
    <meta name="theme-color" content="#131314">
    
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js" crossorigin="anonymous"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    
    <style>
        :root {
            --bg-color: #131314;
            --sidebar-color: #1e1e1f;
            --text-color: #e3e3e3;
            --accent-blue: #0055ff;
            --accent-red: #ff2e2e;
            --accent-green: #00ff66;
            --accent-purple: #a12eff;
            --modal-overlay: rgba(0, 0, 0, 0.6);
            --modal-bg: #202124;
            --header-height: 56px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body {
            height: 100dvh; width: 100vw; overflow: hidden;
            color: var(--text-color);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; user-select: none;
            transition: background 0.4s ease-in-out;
        }
        body:not(.performance-active) {
            background: radial-gradient(circle at 60% 80%, #1a233a 0%, #0e0f12 60%) !important;
        }
        body.performance-active {
            background-image: 
                radial-gradient(circle at center, rgba(0, 0, 0, 0.2) 20%, rgba(0, 0, 0, 0.9) 75%, #000000 100%),
                url('/static/bmw.jpeg') !important;
            background-size: cover !important; 
            background-position: center !important; 
            background-repeat: no-repeat !important;
            background-color: #000000 !important;       
        }
        .app-container { display: flex; width: 100vw; height: 100dvh; position: relative; overflow: hidden; }
        
        .global-app-header {
            display: none; position: fixed; top: 0; left: 0; height: var(--header-height); width: 100%; 
            background-color: var(--sidebar-color); border-bottom: 1px solid rgba(255, 255, 255, 0.05); 
            align-items: center; padding: 0 16px; justify-content: space-between; z-index: 9999;
        }
        .hamburger-trigger-icon {
            background: transparent; border: none; color: var(--text-color); cursor: pointer;
            display: flex; align-items: center; justify-content: center; width: 40px; height: 40px;
            border-radius: 8px; transition: background 0.2s;
        }
        .hamburger-trigger-icon:hover { background: rgba(255, 255, 255, 0.05); }
        .hamburger-trigger-icon svg { width: 24px; height: 24px; stroke: currentColor; }

        .sidebar { 
            width: 290px; max-width: 100%; background-color: var(--sidebar-color); display: flex; flex-direction: column; 
            justify-content: space-between; padding: 16px; height: 100%; flex-shrink: 0; 
            border-right: 1px solid rgba(255, 255, 255, 0.03); z-index: 10000; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .sidebar-backdrop {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.5); z-index: 9998; display: none;
            opacity: 0; transition: opacity 0.3s ease; backdrop-filter: blur(2px);
        }

        .brand-logo-container { display: inline-flex; align-items: center; font-size: 24px; font-weight: 900; letter-spacing: -0.5px; gap: 12px; }
        .custom-app-logo-vector { width: 42px; height: 42px; background-image: url('/favicon.ico'); background-size: contain; background-position: center; background-repeat: no-repeat; display: inline-block; mix-blend-mode: lighten; }
        .welcome-center-logo { width: 110px; height: 110px; margin: 0 auto 16px auto; background-image: url('/favicon.ico'); background-size: contain; background-position: center; background-repeat: no-repeat; mix-blend-mode: lighten; }
        .brand-slashes-wrap span { margin-right: -4px; }
        .sl-cyan { color: #00A6FF; } .sl-blue { color: #0033FF; } .sl-red   { color: #FF2E2E; }
        .menu-label { font-size: 11px; color: #808185; text-transform: uppercase; font-weight: 700; letter-spacing: 1px; margin: 25px 8px 8px 8px; }
        .menu-links { display: flex; flex-direction: column; gap: 4px; }
        .nav-item { display: flex; align-items: center; gap: 14px; padding: 12px 14px; color: #e3e3e3; font-size: 14px; font-weight: 500; border-radius: 8px; cursor: pointer; transition: background 0.3s; }
        .nav-item:hover { background-color: rgba(255, 255, 255, 0.06); }
        
        .nav-item.engine-active { background-color: rgba(0, 85, 255, 0.15) !important; color: #ffffff !important; font-weight: 600; }
        body.performance-active .nav-item.engine-active { background-color: rgba(255, 0, 85, 0.15) !important; }
        .nav-item.sc-active { background-color: rgba(0, 255, 102, 0.12) !important; color: #ffffff !important; font-weight: 600; }
        .nav-item.debate-active { background-color: rgba(161, 46, 255, 0.15) !important; color: #ffffff !important; font-weight: 600; }
        
        .nav-item svg { width: 20px; height: 20px; color: #c4c7c5; flex-shrink: 0; }
        .nav-item.engine-active svg { color: #0055ff !important; }
        .nav-item.sc-active svg { color: var(--accent-green) !important; }
        .nav-item.debate-active svg { color: var(--accent-purple) !important; }
        
        .active-tools-indicator-box { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 12px; margin-top: 8px; }
        .active-tools-indicator-box span { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #b0b3b8; margin-bottom: 6px; }
        .active-tools-indicator-box span::before { content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #808185; }
        .active-tools-indicator-box span.status-live::before { background: #00ff66 !important; }
        .active-tools-indicator-box span.status-dead::before { background: #ff2e2e !important; }
        .logout-box { padding: 8px; }
        .logout-box button { background: transparent; border: none; color: #808185; font-size: 13px; cursor: pointer; }
        
        .main-content { flex: 1; display: flex; flex-direction: column; height: 100%; overflow: hidden; position: relative; }
        .chat-container-scroll-wrapper { flex: 1; overflow-y: auto; overflow-x: hidden; width: 100%; position: relative; scroll-behavior: smooth; }
        .chat-container { padding: 30px 25px; display: flex; flex-direction: column; gap: 24px; width: 100%; max-width: 950px; margin: 0 auto; min-height: min-content; }
        .welcome-vibe { margin: auto; text-align: center; max-width: 600px; padding-top: 20px; }
        .welcome-vibe h1 { font-size: 26px; font-weight: 500; margin-bottom: 12px; color: #ffffff; }
        
        .phone-camera-viewport-container {
            width: 100%; max-width: 240px; margin: 15px auto; border-radius: 12px;
            border: 2px solid rgba(255, 255, 255, 0.1); overflow: hidden;
            background: #000; display: none; aspect-ratio: 4/3; position: relative;
        }
        .phone-camera-viewport-container video { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
        
        .ui-gesture-tracking-cursor {
            position: fixed; width: 28px; height: 28px; background-color: var(--accent-green);
            border: 3px solid #ffffff; border-radius: 50%; pointer-events: none;
            z-index: 2000000; display: none; transform: translate(-50%, -50%);
            box-shadow: 0 0 20px rgba(0, 255, 102, 0.9), inset 0 0 8px rgba(0,0,0,0.3); 
            top: 50%; left: 50%;
        }
        .ui-gesture-tracking-cursor.clicking-state {
            background-color: var(--accent-red) !important;
            transform: translate(-50%, -50%) scale(0.75);
            box-shadow: 0 0 25px rgba(255, 46, 46, 1);
        }

        .bubble { max-width: 100%; padding: 14px 20px; border-radius: 18px; line-height: 1.6; font-size: 16px; word-wrap: break-word; user-select: text; }
        .user-bubble { background: #2b2c2f; color: #ffffff; align-self: flex-end; border-bottom-right-radius: 4px; white-space: pre-wrap; max-width: 80%; display: flex; flex-direction: column; gap: 10px; }
        .bot-bubble { background: transparent; color: #e3e3e3; align-self: flex-start; padding-left: 0; width: 100%; }
        
        .loader-bubble { align-self: flex-start; background: rgba(255, 255, 255, 0.05); padding: 15px 25px; border-radius: 18px; display: flex; align-items: center; gap: 12px; }
        .loader-dots-flex { display: flex; align-items: center; gap: 6px; }
        .loader-dot { width: 8px; height: 8px; background-color: #e3e3e3; border-radius: 50%; animation: pulseDots 1.4s infinite ease-in-out both; }
        
        .stop-generation-action-btn {
            background: #2b2c2f; border: 1px solid rgba(255,255,255,0.15); color: #ff6b6b;
            font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 12px;
            cursor: pointer; display: flex; align-items: center; gap: 4px; transition: background 0.2s;
        }
        .stop-generation-action-btn:hover { background: rgba(255, 46, 46, 0.15); }
        
        @keyframes pulseDots { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }
        
        .input-area { padding: 12px 20px 24px 20px; width: 100%; max-width: 950px; margin: 0 auto; display: flex; flex-direction: column; gap: 10px; background: transparent; flex-shrink: 0; z-index: 10; }
        .input-box-wrapper { display: flex; align-items: center; background-color: #202124; border-radius: 32px; padding: 6px 14px 6px 16px; width: 100%; border: 1px solid rgba(255,255,255,0.05); gap: 10px; transition: opacity 0.2s ease; }
        .input-box-wrapper input { flex: 1; background: transparent; border: none; outline: none; color: #ffffff; font-size: 16px; height: 44px; min-width: 50px; }
        .input-box-wrapper input:disabled { cursor: not-allowed; opacity: 0.5; }
        
        .inline-model-selector-wrapper { position: relative; display: flex; align-items: center; flex-shrink: 0; }
        .inline-model-selector-wrapper select {
            background-color: #2b2c2f; color: #e3e3e3; font-size: 13px; font-weight: 600;
            padding: 6px 24px 6px 12px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08);
            outline: none; cursor: pointer; appearance: none; -webkit-appearance: none;
        }
        .inline-model-selector-wrapper::after {
            content: "▼"; font-size: 9px; color: #b0b3b8; position: absolute; right: 10px; top: 50%;
            transform: translateY(-50%); pointer-events: none;
        }
        
        .mic-btn {
            background: transparent; border: none; color: #808185; font-size: 20px; cursor: pointer;
            padding: 4px 8px; display: flex; align-items: center; justify-content: center;
            transition: all 0.2s; border-radius: 50%;
        }
        .mic-btn:hover { color: var(--accent-red); background: rgba(255,255,255,0.05); }
        .mic-btn.recording-active { color: #fff; background: var(--accent-red); animation: micPulse 1.5s infinite; }
        
        @keyframes micPulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .send-btn { background-color: #303134; color: #808185; border: none; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .send-btn.active-input { background-color: var(--accent-blue); color: white; }
        .send-btn:disabled { cursor: not-allowed !important; opacity: 0.4; }

        .app-custom-modal-backdrop {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background-color: var(--modal-overlay); display: flex; align-items: center;
            justify-content: center; z-index: 999999; visibility: hidden; opacity: 0;
            transition: opacity 0.25s ease, visibility 0.25s ease; backdrop-filter: blur(4px);
        }
        .app-custom-modal-backdrop.modal-open { visibility: visible; opacity: 1; }
        .app-custom-modal-window { background-color: var(--modal-bg); border: 1px solid rgba(255, 255, 255, 0.08); width: 440px; max-width: 92%; border-radius: 16px; padding: 24px; }
        
        .modal-headline { font-size: 18px; font-weight: 700; color: #ffffff; margin-bottom: 10px; }
        .modal-message-body { font-size: 14px; color: #b0b3b8; margin-bottom: 24px; }
        .modal-actions-layout { display: flex; justify-content: flex-end; gap: 10px; }
        .modal-btn { padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; }
        .modal-btn-cancel { background: #2f3033; color: #e3e3e3; }
        .modal-btn-primary { background: var(--accent-blue); color: #ffffff; }

        @media screen and (max-width: 991px) {
            .app-container { flex-direction: column; height: 100dvh; padding-top: var(--header-height); }
            .global-app-header { display: flex; }
            .sidebar {
                position: fixed; top: 0; left: 0; height: 100dvh; width: 280px;
                transform: translateX(-100%); box-shadow: 12px 0 40px rgba(0,0,0,0.6);
            }
            .sidebar.drawer-open { transform: translateX(0); }
            .sidebar-backdrop.drawer-open { display: block; opacity: 1; }
            .chat-container { padding: 20px 16px; }
            .input-area { padding: 8px 12px 16px 12px; }
            .welcome-center-logo { width: 80px; height: 80px; margin-bottom: 12px; }
            .welcome-vibe h1 { font-size: 20px; }
        }
    </style>
</head>
<body>

    <div class="ui-gesture-tracking-cursor" id="virtualCursor"></div>

    <div class="global-app-header">
        <button class="hamburger-trigger-icon" onclick="toggleMobileSidebarSystem(true)" title="Open Menu">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2.5" stroke-linecap="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
        </button>
        <div class="brand-logo-container" style="font-size: 20px;">
            <span class="brand-slashes-wrap"><span class="sl-cyan">/</span><span class="sl-blue">/</span><span class="sl-red">/</span></span>
            <span style="color:#fff;">M-BOT</span>
        </div>
        <div style="width: 40px;"></div>
    </div>

    <div class="sidebar-backdrop" id="mobileSidebarDismissalLayer" onclick="toggleMobileSidebarSystem(false)"></div>

    <div class="app-container">
        <div class="sidebar" id="appSidebarNode">
            <div>
                <div style="padding: 4px 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div class="brand-logo-container">
                        <div class="custom-app-logo-vector"></div>
                        <span class="brand-slashes-wrap"><span class="sl-cyan">/</span><span class="sl-blue">/</span><span class="sl-red">/</span></span>
                        <span style="color:#fff;">M-BOT</span>
                    </div>
                </div>
                <input type="hidden" id="executionMode" value="default">
                <div class="menu-links">
                    <div class="nav-item" id="btn-new-chat" onclick="triggerImmediateWorkspaceWipe();">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                        <span>New Chat Matrix</span>
                    </div>
                    <div class="nav-item engine-active" id="btn-mode-default" onclick="requestModeChangeSequence('default', 'Default Mode Stack');">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/></svg>
                        <span>Default Mode Stack</span>
                    </div>
                    <div class="nav-item" id="btn-mode-mm" onclick="requestModeChangeSequence('mm-mode', '///M Performance Mode');">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
                        <span>///M Performance Mode</span>
                    </div>
                    <div class="nav-item" id="btn-mode-debate" onclick="requestModeChangeSequence('debate', 'Debating Core Engine');">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        <span>Debating Core Engine</span>
                    </div>
                    <div class="nav-item" id="btn-mode-sc" onclick="changeEngineTargetDirectly('screen-control');">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                        <span>Universal Screen Control</span>
                    </div>
                </div>
                <div class="menu-label">Active Tool Baseline</div>
                <div class="active-tools-indicator-box">
                    <span class="status-live">Memory Matrix Active</span>
                    <span id="indicator-gemini" class="status-dead">Processor Nodes</span>
                    <span id="indicator-tracking" class="status-dead">Camera Tracking</span>
                </div>
            </div>
            <div class="logout-box">
                <button onclick="triggerPurgeLogsModal();">Clear Logs Matrix</button>
            </div>
        </div>
        
        <div class="main-content" id="mainContentWrapper">
            <div class="chat-container-scroll-wrapper" id="mainWorkspaceScrollNode">
                <div class="chat-container" id="chatDisplay">
                    <div class="welcome-vibe" id="welcomeDeck">
                        <div class="welcome-center-logo"></div>
                        <h1 id="welcomeTextNode">Syncing system telemetry parameters...</h1>
                        
                        <div class="phone-camera-viewport-container" id="phoneCameraContainer">
                            <video id="phoneCameraView" autoplay playsinline muted></video>
                        </div>
                    </div>
                </div>
            </div>
            <div class="input-area">
                <div class="input-box-wrapper" id="inputBoxWrapperElement">
                    <div class="inline-model-selector-wrapper" id="modelSelectionContainer">
                        <select id="providerSelectMenu" title="Target Engine Core">
                            <option value="gemini" selected>Gemini Core</option>
                        </select>
                    </div>
                    <button class="mic-btn" id="voiceMicTrigger" onclick="toggleVoiceSpeechInput()" title="Voice Input">🎤</button>
                    <input type="text" id="userInput" placeholder="Ask Core..." onkeypress="handleKey(event)" oninput="toggleSendBtnState()" autocomplete="off">
                    <button class="send-btn" id="sendBtn" onclick="transmitPrompt()">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M5 12H19M19 12L13 6M19 12L13 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div class="app-custom-modal-backdrop" id="customModalContainer">
        <div class="app-custom-modal-window">
            <div class="modal-headline" id="modalTitleText">System Message</div>
            <div class="modal-message-body" id="modalDescriptionText">Confirm workspace parameter swap?</div>
            <div class="modal-actions-layout">
                <button class="modal-btn modal-btn-cancel" onclick="modalCancelTriggered()">Keep History</button>
                <button class="modal-btn modal-btn-primary" id="modalConfirmActionButton" onclick="modalConfirmTriggered()">Start Fresh</button>
            </div>
        </div>
    </div>

    <script>
        let activeModalConfirmCallback = null;
        let activeModalCancelCallback = null;
        let currentAbortController = null;
        let isProcessingRequest = false;
        let speechRecognitionEngine = null;
        let isVoiceRecordingActive = false;

        window.addEventListener("DOMContentLoaded", () => {
            syncSystemHardwareIndicators();
            initializeSpeechRecognitionPipeline();
        });

        function toggleMobileSidebarSystem(openState) {
            const sidebar = document.getElementById("appSidebarNode");
            const backdrop = document.getElementById("mobileSidebarDismissalLayer");
            if (sidebar && backdrop) {
                if (openState) {
                    sidebar.classList.add("drawer-open");
                    backdrop.classList.add("drawer-open");
                } else {
                    sidebar.classList.remove("drawer-open");
                    backdrop.classList.remove("drawer-open");
                }
            }
        }

        async function syncSystemHardwareIndicators() {
            try {
                const response = await fetch("/check_status");
                const data = await response.json();
                document.getElementById("indicator-gemini").className = data.gemini_active ? "status-live" : "status-dead";
                document.getElementById("welcomeTextNode").textContent = "State your objective, Ansh.";
            } catch (err) {
                console.error("Telemetry link sync drop:", err);
            }
        }

        // FIX: Completely fixed JavaScript requestModeChangeSequence layout to prevent syntax errors
        function requestModeChangeSequence(targetMode, modeLabel) {
            document.getElementById("executionMode").value = targetMode;
            
            // Step 1: Remove all current highlight states
            document.getElementById("btn-mode-default").classList.remove("engine-active");
            document.getElementById("btn-mode-mm").classList.remove("engine-active");
            document.getElementById("btn-mode-debate").classList.remove("engine-active");
            
            // Step 2: Dynamically add the engine highlight tracking class
            if (targetMode === 'default') {
                document.getElementById("btn-mode-default").classList.add("engine-active");
                document.body.classList.remove("performance-active");
            } else if (targetMode === 'mm-mode') {
                document.getElementById("btn-mode-mm").classList.add("engine-active");
                document.body.classList.add("performance-active");
            } else if (targetMode === 'debate') {
                document.getElementById("btn-mode-debate").classList.add("engine-active");
                document.body.classList.remove("performance-active");
            }
            
            console.log("System workspace swapped to: " + modeLabel);
            toggleMobileSidebarSystem(false);
        }

        function changeEngineTargetDirectly(mode) {
            alert("Universal Screen Control active. Waiting on hardware context variables.");
        }

        function triggerImmediateWorkspaceWipe() {
            document.getElementById("chatDisplay").innerHTML = `
                <div class="welcome-vibe" id="welcomeDeck">
                    <div class="welcome-center-logo"></div>
                    <h1 id="welcomeTextNode">State your objective, Ansh.</h1>
                </div>
            `;
        }

        function triggerPurgeLogsModal() {
            showCustomAppModal({
                title: "Purge Database Core?",
                message: "This will wipe the long-term SQLite memory context loops.",
                confirmText: "Purge Matrix",
                cancelText: "Retain Link",
                onConfirm: async () => {
                    await fetch("/clear_memory", { method: "POST" });
                    triggerImmediateWorkspaceWipe();
                }
            });
        }

        function showCustomAppModal({ title, message, confirmText, cancelText, onConfirm, onCancel }) {
            document.getElementById("modalTitleText").textContent = title;
            document.getElementById("modalDescriptionText").textContent = message;
            const confirmBtn = document.getElementById("modalConfirmActionButton");
            const cancelBtn = document.querySelector(".modal-btn-cancel");
            
            confirmBtn.textContent = confirmText || "Start Fresh";
            cancelBtn.textContent = cancelText || "Keep History";
            
            activeModalConfirmCallback = onConfirm;
            activeModalCancelCallback = onCancel;
            document.getElementById("customModalContainer").classList.add("modal-open");
        }

        function modalConfirmTriggered() {
            if (typeof activeModalConfirmCallback === "function") activeModalConfirmCallback();
            closeAppModalInterface();
        }
        
        function modalCancelTriggered() {
            if (typeof activeModalCancelCallback === "function") activeModalCancelCallback();
            closeAppModalInterface();
        }

        function closeAppModalInterface() {
            document.getElementById("customModalContainer").classList.remove("modal-open");
        }

        function handleKey(e) {
            if (e.key === "Enter") transmitPrompt();
        }

        function toggleSendBtnState() {
            const input = document.getElementById("userInput").value.trim();
            const btn = document.getElementById("sendBtn");
            if (input.length > 0) {
                btn.classList.add("active-input");
            } else {
                btn.classList.remove("active-input");
            }
        }

        function initializeSpeechRecognitionPipeline() {
            const SpeechEngine = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechEngine) return;
            speechRecognitionEngine = new SpeechEngine();
            speechRecognitionEngine.continuous = false;
            speechRecognitionEngine.interimResults = false;
            speechRecognitionEngine.lang = "en-US";

            speechRecognitionEngine.onstart = () => {
                isVoiceRecordingActive = true;
                document.getElementById("voiceMicTrigger").classList.add("recording-active");
            };

            speechRecognitionEngine.onend = () => {
                isVoiceRecordingActive = false;
                document.getElementById("voiceMicTrigger").classList.remove("recording-active");
            };

            speechRecognitionEngine.onresult = (event) => {
                const textResult = event.results[0][0].transcript;
                document.getElementById("userInput").value = textResult;
                toggleSendBtnState();
                transmitPrompt();
            };
        }

        function toggleVoiceSpeechInput() {
            if (!speechRecognitionEngine) return;
            if (isVoiceRecordingActive) {
                speechRecognitionEngine.stop();
            } else {
                speechRecognitionEngine.start();
            }
        }

        async function transmitPrompt() {
            const inputNode = document.getElementById("userInput");
            const prompt = inputNode.value.trim();
            if (!prompt || isProcessingRequest) return;

            isProcessingRequest = true;
            inputNode.value = "";
            toggleSendBtnState();

            const chatDisplay = document.getElementById("chatDisplay");
            const welcomeDeck = document.getElementById("welcomeDeck");
            if (welcomeDeck) welcomeDeck.style.display = "none";

            // Append User Chat Bubble
            const userMsgDiv = document.createElement("div");
            userMsgDiv.className = "bubble user-bubble";
            userMsgDiv.textContent = prompt;
            chatDisplay.appendChild(userMsgDiv);

            // Append Loading Dot Stream Animation
            const loaderDiv = document.createElement("div");
            loaderDiv.className = "loader-bubble";
            loaderDiv.id = "activeLoaderStream";
            loaderDiv.innerHTML = `
                <div class="loader-dots-flex">
                    <div class="loader-dot" style="animation-delay: 0s"></div>
                    <div class="loader-dot" style="animation-delay: 0.2s"></div>
                    <div class="loader-dot" style="animation-delay: 0.4s"></div>
                </div>
            `;
            chatDisplay.appendChild(loaderDiv);
            document.getElementById("mainWorkspaceScrollNode").scrollTop = document.getElementById("mainWorkspaceScrollNode").scrollHeight;

            try {
                const activeMode = document.getElementById("executionMode").value;
                const response = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        prompt: prompt,
                        mode: activeMode,
                        provider: "gemini"
                    })
                });
                const data = await response.json();
                
                // Erase loader component
                const loader = document.getElementById("activeLoaderStream");
                if (loader) loader.remove();

                // Append Core Bot Response Bubble
                const botMsgDiv = document.createElement("div");
                botMsgDiv.className = "bubble bot-bubble";
                botMsgDiv.innerHTML = marked.parse(data.response || "[Engine System Parameter Empty]");
                chatDisplay.appendChild(botMsgDiv);
                
            } catch (err) {
                console.error(err);
                const loader = document.getElementById("activeLoaderStream");
                if (loader) loader.remove();
            } finally {
                isProcessingRequest = false;
                document.getElementById("mainWorkspaceScrollNode").scrollTop = document.getElementById("mainWorkspaceScrollNode").scrollHeight;
            }
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
