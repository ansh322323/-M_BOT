import os
import base64
import time
import sqlite3
import threading
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from groq import Groq  

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "*"}})

app.secret_key = "m_performance_matrix_secure_771"
DB_PATH = os.path.join(BASE_DIR, "m_memory_matrix.db")

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

groq_client = None
def verify_and_get_client():
    global groq_client
    if groq_client is not None:
        return groq_client
    
    api_key_check = os.environ.get("GROQ_API_KEY")
    if not api_key_check:
        print("[-] Groq API Key is missing from Environment Variables.")
        return None
    try:
        groq_client = Groq(api_key=api_key_check)
        return groq_client
    except Exception as e:
        print(f"[-] Client initialization error: {e}")
        return None

def query_groq(prompt, system_instruction="", context_history=None):
    client = verify_and_get_client()
    if not client:
        return "[Groq Setup Error: Configuration key missing. Set GROQ_API_KEY]"
        
    if context_history is None:
        context_history = []
        
    max_retries = 3
    delay = 2
    messages = []
    
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
        
    for msg in context_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": prompt})
    
    for attempt in range(max_retries):
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024
            )
            return chat_completion.choices[0].message.content.strip()
            
        except Exception as e:
            if "429" in str(e) or "RATE_LIMIT_EXHAUSTED" in str(e).upper():
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
            return f"[Groq Resource Quota Exhausted or Error: {e}]"

@app.route("/check_status", methods=["GET"])
def check_status_endpoint():
    client_status = verify_and_get_client()
    return jsonify({"gemini_active": client_status is not None, "tracking_active": False})

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    data = request.json or {}
    prompt = data.get("prompt", "").strip()
    mode = data.get("mode", "default")
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
                    mapped_role = "user" if row[0] in ["user", "user-bubble"] else "assistant"
                    context_history.append({"role": mapped_role, "content": row[1]})
        except Exception as db_err:
            print(f"DB Read Error: {db_err}")

        system_instruction = "You are an advanced assistant named M-BOT. Keep replies precise, perfectly engineered, and completely natural."
        if mode == "mm-mode":
            system_instruction += " Focus on high-octane performance metrics and engineering layout rules."

        reply = query_groq(prompt, system_instruction, context_history)

    if not isinstance(reply, str) or not reply.strip():
        reply = "[No response could be generated. Please try again.]"

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)", (session_id, "user", prompt))
            cursor.execute("INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)", (session_id, "assistant", reply))
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
    return send_from_directory(app.static_folder, 'logo.png', mimetype='image/png')


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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--sidebar-color);
        }
        
        .app-container { display: flex; width: 100vw; height: 100dvh; position: relative; overflow: hidden; }
        .main-content { flex: 1; display: flex; flex-direction: column; height: 100%; overflow: hidden; position: relative; }
        
        /* Default Stack Matrix: Shifting Blue Light Gradients strictly inside the Workspace area */
        body:not(.performance-active) .main-content {
            background: linear-gradient(135deg, #0e0f12, #141923, #1a233a, #0e0f12) !important;
            background-size: 400% 400% !important;
            animation: driftingBlueMatrix 15s ease infinite !important;
        }
        
        @keyframes driftingBlueMatrix {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        /* Performance View: Fit image strictly between Sidebar Boundary & Left/Right Screen limits */
        body.performance-active .main-content {
            background-color: #050608 !important;       
            background-image: 
                linear-gradient(to right, rgba(30, 30, 31, 1) 0%, rgba(5, 6, 8, 0.4) 15%, rgba(0, 0, 0, 0) 100%),
                linear-gradient(to top, rgba(5, 6, 8, 0.95) 0%, rgba(5, 6, 8, 0.2) 100%),
                url('/static/bmw.jpeg') !important;
            background-size: cover !important; 
            background-position: center center !important; 
            background-repeat: no-repeat !important;
        }
        
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
        
        .active-tools-indicator-box { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px; padding: 12px; margin-top: 8px; }
        .active-tools-indicator-box span { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #b0b3b8; margin-bottom: 6px; }
        .active-tools-indicator-box span::before { content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #808185; }
        .active-tools-indicator-box span.status-live::before { background: #00ff66 !important; }
        .active-tools-indicator-box span.status-dead::before { background: #ff2e2e !important; }
        .logout-box { padding: 8px; }
        .logout-box button { background: transparent; border: none; color: #808185; font-size: 13px; cursor: pointer; }
        
        .chat-container-scroll-wrapper { flex: 1; overflow-y: auto; overflow-x: hidden; width: 100%; position: relative; scroll-behavior: smooth; }
        .chat-container { padding: 30px 25px; display: flex; flex-direction: column; gap: 24px; width: 100%; max-width: 950px; margin: 0 auto; min-height: min-content; }
        .welcome-vibe { margin: auto; text-align: center; max-width: 600px; padding-top: 20px; }
        .welcome-vibe h1 { font-size: 26px; font-weight: 500; margin-bottom: 12px; color: #ffffff; }
        
        .bubble { max-width: 100%; padding: 14px 20px; border-radius: 18px; line-height: 1.6; font-size: 16px; word-wrap: break-word; }
        .user-bubble { background: #2b2c2f; color: #ffffff; align-self: flex-end; border-bottom-right-radius: 4px; white-space: pre-wrap; max-width: 80%; display: flex; flex-direction: column; gap: 10px; }
        .bot-bubble { background: transparent; color: #e3e3e3; align-self: flex-start; padding-left: 0; width: 100%; }
        
        .bot-bubble pre { background: #1e1e1f; border-radius: 8px; padding: 14px; margin: 10px 0; overflow-x: auto; border: 1px solid rgba(255,255,255,0.05); }
        .bot-bubble code { font-family: 'Courier New', Courier, monospace; font-size: 14px; }
        
        .loader-bubble { align-self: flex-start; background: rgba(255, 255, 255, 0.05); padding: 15px 25px; border-radius: 18px; display: flex; align-items: center; gap: 12px; }
        .loader-dots-flex { display: flex; align-items: center; gap: 6px; }
        .loader-dot { width: 8px; height: 8px; background-color: #e3e3e3; border-radius: 50%; animation: pulseDots 1.4s infinite ease-in-out both; }
        @keyframes pulseDots { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }
        
        .input-area { padding: 12px 20px 24px 20px; width: 100%; max-width: 950px; margin: 0 auto; display: flex; flex-direction: column; gap: 10px; background: transparent; flex-shrink: 0; z-index: 10; }
        .input-box-wrapper { display: flex; align-items: center; background-color: #202124; border-radius: 32px; padding: 6px 14px 6px 16px; width: 100%; border: 1px solid rgba(255,255,255,0.05); gap: 10px; }
        .input-box-wrapper input { flex: 1; background: transparent; border: none; outline: none; color: #ffffff; font-size: 16px; height: 44px; min-width: 50px; }
        
        .inline-model-selector-wrapper { position: relative; display: flex; align-items: center; flex-shrink: 0; }
        .inline-model-selector-wrapper select {
            background-color: #2b2c2f; color: #e3e3e3; font-size: 13px; font-weight: 600;
            padding: 6px 24px 6px 12px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08);
            outline: none; cursor: pointer; appearance: none;
        }
        .inline-model-selector-wrapper::after {
            content: "▼"; font-size: 9px; color: #b0b3b8; position: absolute; right: 10px; top: 50%;
            transform: translateY(-50%); pointer-events: none;
        }
        
        .action-btn { background-color: #303134; color: #808185; border: none; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all 0.2s ease; }
        .send-btn.active-input { background-color: var(--accent-blue); color: white; }
        .mic-btn.listening { background-color: var(--accent-red) !important; color: white !important; animation: micPulse 1.5s infinite; }
        
        @keyframes micPulse { 0% { transform: scale(1); } 50% { transform: scale(1.08); } 100% { transform: scale(1); } }

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
            body.performance-active .main-content {
                background-size: cover !important;
                background-position: center center !important;
                background-repeat: no-repeat !important;
                background-color: #050608 !important;
                background-image: 
                    linear-gradient(to top, rgba(5, 6, 8, 0.98) 0%, rgba(5, 6, 8, 0.4) 100%),
                    url('/static/bmw.jpeg') !important;
            }
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
            .welcome-vibe h1 { font-size: 20px; }
        }
    </style>
</head>
<body>

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
                </div>
                <div class="menu-label">Active Tool Baseline</div>
                <div class="active-tools-indicator-box">
                    <span class="status-live">Memory Matrix Active</span>
                    <span id="indicator-gemini" class="status-dead">Processor Nodes</span>
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
                    </div>
                </div>
            </div>
            <div class="input-area">
                <div class="input-box-wrapper" id="inputBoxWrapperElement">
                    <div class="inline-model-selector-wrapper" id="modelSelectionContainer">
                        <select id="providerSelectMenu" title="Target Engine Core">
                            <option value="groq" selected>Groq Core</option>
                        </select>
                    </div>
                    <input type="text" id="userInput" placeholder="Ask Core..." onkeypress="handleKey(event)" oninput="toggleSendBtnState()" autocomplete="off">
                    
                    <button class="action-btn mic-btn" id="micBtn" onclick="toggleVoiceRecognition()" title="Voice Matrix Link">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v1a7 7 0 0 1-14 0v-1"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                    </button>

                    <button class="action-btn send-btn" id="sendBtn" onclick="transmitPrompt()">
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
        let isProcessingRequest = false;
        let voiceRecognitionInstance = null;
        let isListeningMode = false;

        window.addEventListener("DOMContentLoaded", () => {
            syncSystemHardwareIndicators();
            initializeSpeechMatrix();
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

        function toggleSendBtnState() {
            const input = document.getElementById("userInput").value.trim();
            const btn = document.getElementById("sendBtn");
            if(input) { btn.classList.add("active-input"); } else { btn.classList.remove("active-input"); }
        }

        function handleKey(e) {
            if(e.key === "Enter") transmitPrompt();
        }

        function initializeSpeechMatrix() {
            const SpeechEngine = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechEngine) {
                console.warn("Speech API unavailable.");
                document.getElementById("micBtn").style.display = "none";
                return;
            }
            voiceRecognitionInstance = new SpeechEngine();
            voiceRecognitionInstance.continuous = false;
            voiceRecognitionInstance.interimResults = false;
            voiceRecognitionInstance.lang = "en-US";

            voiceRecognitionInstance.onstart = () => {
                isListeningMode = true;
                document.getElementById("micBtn").classList.add("listening");
                document.getElementById("userInput").placeholder = "Listening to audio matrix...";
            };

            voiceRecognitionInstance.onend = () => {
                isListeningMode = false;
                document.getElementById("micBtn").classList.remove("listening");
                document.getElementById("userInput").placeholder = "Ask Core...";
            };

            voiceRecognitionInstance.onresult = (event) => {
                const spokenText = event.results[0][0].transcript;
                const inputNode = document.getElementById("userInput");
                inputNode.value = spokenText;
                toggleSendBtnState();
                transmitPrompt();
            };

            voiceRecognitionInstance.onerror = (e) => {
                console.error("Speech diagnostic error:", e.error);
            };
        }

        function toggleVoiceRecognition() {
            if (!voiceRecognitionInstance) return;
            if (isListeningMode) {
                voiceRecognitionInstance.stop();
            } else {
                voiceRecognitionInstance.start();
            }
        }

        async function transmitPrompt() {
            const inputNode = document.getElementById("userInput");
            const promptText = inputNode.value.trim();
            if(!promptText || isProcessingRequest) return;

            isProcessingRequest = true;
            inputNode.value = "";
            document.getElementById("sendBtn").classList.remove("active-input");

            const welcomeDeck = document.getElementById("welcomeDeck");
            if(welcomeDeck) welcomeDeck.style.display = "none";

            const chatDisplay = document.getElementById("chatDisplay");
            
            const userBox = document.createElement("div");
            userBox.className = "bubble user-bubble";
            userBox.textContent = promptText;
            chatDisplay.appendChild(userBox);

            const loaderBox = document.createElement("div");
            loaderBox.className = "bubble loader-bubble";
            loaderBox.id = "active-loader-node";
            loaderBox.innerHTML = '<div class="loader-dots-flex"><div class="loader-dot"></div><div class="loader-dot"></div><div class="loader-dot"></div></div>';
            chatDisplay.appendChild(loaderBox);
            
            document.getElementById("mainWorkspaceScrollNode").scrollTop = document.getElementById("mainWorkspaceScrollNode").scrollHeight;

            try {
                const response = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        prompt: promptText,
                        mode: document.getElementById("executionMode").value
                    })
                });
                const data = await response.json();
                
                const loader = document.getElementById("active-loader-node");
                if(loader) loader.remove();

                const botBox = document.createElement("div");
                botBox.className = "bubble bot-bubble";
                botBox.innerHTML = marked.parse(data.response);
                chatDisplay.appendChild(botBox);

            } catch (err) {
                const loader = document.getElementById("active-loader-node");
                if(loader) loader.remove();
                
                const errBox = document.createElement("div");
                errBox.className = "bubble bot-bubble";
                errBox.textContent = "[Communication Line Failure. Core Unreachable.]";
                chatDisplay.appendChild(errBox);
            }

            isProcessingRequest = false;
            document.getElementById("mainWorkspaceScrollNode").scrollTop = document.getElementById("mainWorkspaceScrollNode").scrollHeight;
        }

        function requestModeChangeSequence(targetMode, modeLabel) {
            document.getElementById("executionMode").value = targetMode;
            
            document.getElementById("btn-mode-default").classList.remove("engine-active");
            document.getElementById("btn-mode-mm").classList.remove("engine-active");
            document.getElementById("btn-mode-debate").classList.remove("engine-active");
            
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
            
            toggleMobileSidebarSystem(false);
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
            const modal = document.getElementById("customModalContainer");
            modal.classList.add("modal-open");
        }

        function modalCancelTriggered() {
            document.getElementById("customModalContainer").classList.remove("modal-open");
        }

        async function modalConfirmTriggered() {
            document.getElementById("customModalContainer").classList.remove("modal-open");
            try {
                await fetch('/clear_memory', { method: 'POST' });
                triggerImmediateWorkspaceWipe();
            } catch(e) {
                console.error(e);
            }
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    # Check if running in the cloud (Render)
    if os.environ.get("RENDER") or os.environ.get("PORT"):
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    else:
        # Only import and run desktop webview locally
        try:
            import webview
            
            def start_flask():
                app.run(host="127.0.0.1", port=5000, debug=False)

            flask_thread = threading.Thread(target=start_flask)
            flask_thread.daemon = True
            flask_thread.start()

            webview.create_window(
                title="///M-BOT Desktop (Groq Core Engine)", 
                url="http://127.0.0.1:5000", 
                width=1250, 
                height=850,
                resizable=True
            )
            webview.start()
        except ImportError:
            # Fallback if running locally without pywebview installed
            app.run(host="127.0.0.1", port=5000, debug=True)
