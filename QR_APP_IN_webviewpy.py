import io
import base64
import os
import urllib.parse
from flask import Flask, request, render_template_string, send_file
import qrcode
from PIL import Image, ImageDraw, ImageFont
import webview
from threading import Thread

# --- Flask App Setup ---
app = Flask(__name__)

# --- QR Code Config (defaults; can be overridden by form) ---
DEFAULT_QR_BOX_SIZE = 6
DEFAULT_QR_ERROR = qrcode.constants.ERROR_CORRECT_L

USER_BG_PATH = 'user_bg.png'

BACKGROUND_IMAGE_PATH = 'back.png'
FONT_PATH = 'Poppins-Bold.ttf'

last_qr_data = None
saved_input_data = {}

# --- Add Custom Graphics Function ---
def add_custom_graphics(qr_img: Image.Image, custom_text="") -> Image.Image:
    QR_WIDTH, QR_HEIGHT = qr_img.size
    PADDING = 30
    TEXT_HEIGHT = 40
    CARD_WIDTH = QR_WIDTH + (2 * PADDING)
    CARD_HEIGHT = QR_HEIGHT + (2 * PADDING) + TEXT_HEIGHT

    card = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color='#FFFFFF')
    bg_path_to_use = None
    if os.path.exists(USER_BG_PATH):
        bg_path_to_use = USER_BG_PATH
    elif os.path.exists(BACKGROUND_IMAGE_PATH):
        bg_path_to_use = BACKGROUND_IMAGE_PATH

    try:
        if bg_path_to_use:
            bg = Image.open(bg_path_to_use).convert("RGB")
            bg = bg.resize((CARD_WIDTH, CARD_HEIGHT))
            card.paste(bg, (0, 0))
        else:
            draw = ImageDraw.Draw(card)
            draw.rectangle([(0, 0), (CARD_WIDTH, CARD_HEIGHT)], fill="#f3f4f6")
    except Exception:
        # Fallback if image loading fails
        draw = ImageDraw.Draw(card)
        draw.rectangle([(0, 0), (CARD_WIDTH, CARD_HEIGHT)], fill="#f3f4f6") 

    draw = ImageDraw.Draw(card)
    draw.rectangle(
        [(PADDING - 1, PADDING - 1), (QR_WIDTH + PADDING + 1, QR_HEIGHT + PADDING + 1)],
        outline="white", width=2
    )

    card.paste(qr_img, (PADDING, PADDING))

    try:
        font = ImageFont.truetype(FONT_PATH, 16)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            font = ImageFont.load_default()

    text = custom_text if custom_text else "Scan Me!"
    text_color = "#1e3a8a"

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = (CARD_WIDTH - text_width) / 2
    text_y = QR_HEIGHT + PADDING + (TEXT_HEIGHT - (text_bbox[3] - text_bbox[1])) / 2 + 5

    draw.text((text_x, text_y), text, fill=text_color, font=font)
    return card

# --- URL Builder ---
def generate_target_url(d):
    base = "https://abilash-nickal.github.io/QR-cod-generator/my_detail_moder_UI.html"
    params = {
        "name": d.get("name", ""),
        "msg": d.get("message", ""),
        "img": d.get("image_url", ""),
        "copy": d.get("copy_data", ""),
        "key": d.get("text_key", ""),
        "l1": d.get("link1", ""),
        "l2": d.get("link2", ""),
        "l3": d.get("link3", "")
    }
    params = {k: v for k, v in params.items() if v}
    return f"{base}?{urllib.parse.urlencode(params)}"

# ----------------------------------------------------------------------------------------------------
# HTML TEMPLATE — modified: glass dropdown, modal, 3-dot menu, boxes for box_size/error_level
# ----------------------------------------------------------------------------------------------------

HTML_TEMPLATE = """ 
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>QR Generator</title>
<script src="https://cdn.tailwindcss.com"></script>
<script type="module" src="https://unpkg.com/@splinetool/viewer@1.12.6/build/spline-viewer.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{
  --glass-bg: rgba(255,255,255,0.06);
  --glass-border: rgba(255,255,255,0.12);
  --accent: #4f46e5;
}
html,body{height:100%;
    font-family:Inter,sans-serif;
    color:#031220;display:flex;
    align-items:center;
    justify-content:center;
    background:#080338;
    overflow:hidden;}
spline-viewer {
    position: fixed; /* Fixes it to the viewport */
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    height: 100%;
    z-index: 0; /* Pushes it behind the main content */
}
.glass{background:linear-gradient(135deg, rgba(243, 243, 243, 0.02), rgba(252, 252, 252, 0.01));
border:1px solid var(--glass-border);backdrop-filter:
blur(14px) saturate(120%);
-webkit-backdrop-filter:blur(14px) saturate(120%);
box-shadow:0 10px 40px rgba(0, 0, 0, 0.6);
border-radius:20px;padding:24px;}
.label{color:rgba(220,230,245,0.95);font-weight:600;margin-bottom:6px;display:block;}
.input, .select {
  width:100%; padding:10px 12px; border-radius:10px; background:transparent; border:1px solid rgba(255,255,255,0.06);
  color: #e6eef8; outline:none;
}

.h1 {
font-family: 'Poppins', sans-serif;
font-size:80px;
font-weight:1000; 
color:white;
line-height: 0;
margin-top: -300px; 
width: 800px; 
margin-left: auto;
margin-right: auto;
}
h2 {
font-family: 'Poppins', sans-serif;
color:white;
}
/* --- Base Styles (Provided) --- */
.btn-primary{background:linear-gradient(90deg,var(--accent),#6d28d9);border:none;color:white;padding:12px;border-radius:10px;}
.btn-download{background:linear-gradient(90deg,#059669,#10b981);color:white;padding:10px;border-radius:10px;box-shadow:0 6px 18px rgba(16,185,129,0.18);margin-right: 10px;}
.btn-link{
    background:linear-gradient(90deg,#3b82f6,#2563eb);
    color:white;
    padding:10px;
    border-radius:10px;
    box-shadow:0 6px 18px rgba(37,99,235,0.18);
    margin-right: 10px;
    
    /* Ensure the link acts like a block to accept width */
    display: inline-block; 
    
    /* ADDED: Set the desired width (length) here */
    width: 180px; 
    
    /* ADDED: Center the text/icon inside the button (optional) */
    text-align: center; 
}
/* --- Hover Styles with Glow Added --- */
.btn-link:hover {
    background: gold;
    color: black;
    /* ADDED: Box shadow for the glow effect */
    box-shadow: 0 0 15px gold; 
    /* ADDED: Optional: Smooth transition for the effect */
    transition: box-shadow 0.3s ease; 
    
}
.btn-primary:hover {
    background: gold;
    color: black;
    /* ADDED: Box shadow for the glow effect */
    box-shadow: 0 0 15px gold; 
    /* ADDED: Optional: Smooth transition for the effect */
    transition: box-shadow 0.3s ease; 
}

.btn-download:hover {
    background: gold;
    color: black;
    /* ADDED: Box shadow for the glow effect */
    box-shadow: 0 0 15px gold; 
    /* ADDED: Optional: Smooth transition for the effect */
    transition: box-shadow 0.3s ease;
    
}

.small-btn:hover {
    background: gold;
    color: black;
    /* ADDED: Box shadow for the glow effect */
    box-shadow: 0 0 15px gold;
    /* ADDED: Optional: Smooth transition for the effect */
    transition: box-shadow 0.3s ease;
}

/* * NOTE: To make the glow appear smooth, you should also add a 
* transition property to the base (non-hover) button styles:
*/
.btn-primary, .btn-download, .small-btn ,.btn-link {
    /* ... existing properties ... */
    transition: background 0.3s, box-shadow 0.3s;
}
.small-btn{background:rgba(255,255,255,0.04);padding:6px 8px;border-radius:8px;border:1px solid rgba(255,255,255,0.05);color:#e6eef8;}
.qr-preview{position:relative;border-radius:14px;padding:14px;border:1px solid rgba(255,255,255,0.03);background:rgba(255,255,255,0.01)}
.three-dots{position:absolute; right:20px; top:20px; cursor:pointer; font-size:14px; color:rgba(255,255,255,0.8); padding:6px; border-radius:8px;}
.three-dots:hover{background:rgba(255,255,255,0.02);}
select{
  background:rgba(255,255,255,0.06);
  border:1px solid rgba(255,255,255,0.25);
  backdrop-filter:blur(14px);
  border-radius:8px;
  color:white;
}
select option{
  background:#1e293b;
  color:white;
}
.modal-backdrop{
  position:fixed;
  inset:0;
  background:rgba(2,6,23,0.6);
  display:none;
  align-items:center;
  justify-content:center;
  z-index:50;
  backdrop-filter: blur(12px); /* Added for medium blur */
}

.modal{
  background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  border-radius:12px;
  padding:18px;
  width:400px;
  border:2px solid rgba(255,255,255,0.10);
}

.fixed-buttons-container {
    /* 1. Sets the element relative to the browser window */
    position: absolute; 
    
    /* 2. Positions the element 20px from the bottom edge */
    bottom: 170px; 
    
    /* 3. Positions the element 20px from the left edge */
    left: 400px; 
    z-index: 1000; /* Ensures it stays above other content */
    
    /* Optional: Add a small gap between the two buttons */
    display: flex;
    display: flex;
    flex-direction: column;
    gap: 50px;
}
.small-muted{font-size:12px;color:rgba(230,238,248,0.6);}
.url-box {
  /* --- Existing Styles --- */
  background: rgba(255, 255, 255, 0.03);
  padding: 10px;
  border-radius: 10px;
  font-family: monospace;
  color: #e0eeff;
  margin-top: 10px;
  overflow-wrap: break-word; /* Essential for long URLs to break and wrap */
  
  /* --- The Solution --- */
  
  /* 1. Set the fixed width (you can change this value) */
  width: 400px; 
  
  /* 2. (Optional but recommended) Explicitly set height to auto */
  height: auto; 
}
.row{display:flex;gap:10px;align-items:center;}
.hidden{display:none;}
</style>
</head>
<body>
<h1>
<div class="h1">QR <i class="fa fa-qrcode" style="font-size:500px;color:red"></i> GENERATOR
<div>
</h1>
<div class="fixed-buttons-container">
    <a href="https://github.com/Abilash-Nickal" class="btn-link" target="_blank"> 
        <i class="fa fa-github"></i> Profile
    </a>
    <a href="https://www.linkedin.com/in/arumugam-abilashan-6916a2157?lipi=urn%3Ali%3Apage%3Ad_flagship3_profile_view_base_contact_details%3BcW9f2v%2B2Txulyw5em4cgJw%3D%3D" class="btn-link" target="_blank">
        <i class="fa fa-linkedin"></i> Profile
    </a>
</div>
<spline-viewer loading-anim-type="none" url="https://prod.spline.design/UK2sM5JyhHbgUGpr/scene.splinecode"></spline-viewer>
<div class="glass w-full max-w-4xl">
  <h2 class="text-2xl font-extrabold mb-4">QR Code Data Encoder</h2>
  <div class="grid md:grid-cols-2 gap-6">
    <div>
      <form id="qrForm" method="POST" action="/generate_qr" enctype="multipart/form-data" class="space-y-5">
        <!-- Name -->
        <div>
          <label class="label">Name</label>
          <input class="input" type="text" name="name" required value="{{ saved_data.name }}">
        </div>

        <!-- Message -->
        <div>
          <label class="label">Message</label>
          <input class="input" type="text" name="message" value="{{ saved_data.message }}">
        </div>

        <!-- Platform 1 -->
        <div id="block1" class="hidden">
          <label class="label">Platform 1</label>
          <div class="row">
            <select id="platform1" name="platform1" onchange="updateLink1()" class="dropdown-glass w-1/3">
              <option value="">-- Select --</option>
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="youtube">YouTube</option>
              <option value="linkedin">LinkedIn</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="drive">Google Drive</option>
              <option value="googleform">Google Form</option>
              <option value="tel">Call</option>
              <option value="sms">SMS</option>
              <option value="mailto">Email</option>
              <option value="other">Other (custom link)</option>
            </select>
            <input class="input" type="text" id="username1" name="username_input1" oninput="updateLink1()" placeholder="ID / Number">
          </div>
          <input type="hidden" id="finalLink1" name="link1" value="">
        </div>

        <!-- Add Platform button -->
        <div class="row">
          <button type="button" class="small-btn" onclick="openAddPlatformModal()">+ Add Platforms</button>
        </div>

        <!-- Links Preview -->
        <div id="linksPreview" style="margin-top:10px;display:none;">
          <label class="small-muted" style="display:block;margin-bottom:5px;">Added Links:</label>
          <div id="linksList"></div>
        </div>

        <!-- Platform 2 -->
        <div id="block2" class="hidden">
          <label class="label">Platform 2</label>
          <div class="row">
            <select id="platform2" name="platform2" onchange="updateLink2()" class="dropdown-glass w-1/3">
              <option value="">-- Select --</option>
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="youtube">YouTube</option>
              <option value="linkedin">LinkedIn</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="drive">Google Drive</option>
              <option value="googleform">Google Form</option>
              <option value="tel">Call</option>
              <option value="sms">SMS</option>
              <option value="mailto">Email</option>
              <option value="other">Other (custom link)</option>
            </select>
            <input class="input" type="text" id="username2" name="username_input2" oninput="updateLink2()">
          </div>
          <input type="hidden" id="finalLink2" name="link2" value="">
        </div>

        <!-- Platform 3 -->
        <div id="block3" class="hidden">
          <label class="label">Platform 3</label>
          <div class="row">
            <select id="platform3" name="platform3" onchange="updateLink3()" class="dropdown-glass w-1/3">
              <option value="">-- Select --</option>
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="youtube">YouTube</option>
              <option value="linkedin">LinkedIn</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="drive">Google Drive</option>
              <option value="googleform">Google Form</option>
              <option value="tel">Call</option>
              <option value="sms">SMS</option>
              <option value="mailto">Email</option>
              <option value="other">Other (custom link)</option>
            </select>
            <input class="input" type="text" id="username3" name="username_input3" oninput="updateLink3()">
          </div>
          <input type="hidden" id="finalLink3" name="link3" value="">
        </div>

        <!-- Text Under QR (dropdown glass) -->
        <div>
          <label class="label">Text Under QR</label>
          <select id="labelPreset" class="dropdown-glass" onchange="onLabelPresetChange()">
            <option value="Scan Me!">Scan Me!</option>
            <option value="Visit My Profile">Visit My Profile</option>
            <option value="Contact Me">Contact Me</option>
            <option value="Custom">Custom...</option>
          </select>
          <input id="customLabelInput" class="input hidden" type="text" placeholder="Enter custom label text">
          <!-- Hidden field sent to server -->
          <input type="hidden" id="custom_text" name="custom_text" value="{{ saved_data.custom_text }}">
        </div>

        <!-- Image URL -->
        <div>
          <label class="label">Image URL</label>
          <input class="input" type="url" name="image_url" value="{{ saved_data.image_url }}">
        </div>

        <!-- Text/Key to Copy -->
        <div>
          <label class="label">Text/Key to Copy</label>
          <input class="input" type="text" name="text_key" value="{{ saved_data.get('text_key', '') }}">
        </div>

        <!-- Hidden QR options (box size and error) -->
        <input type="hidden" id="box_size_field" name="box_size" value="">
        <input type="hidden" id="error_level_field" name="error_level" value="">

        <button type="submit" class="btn-primary w-full">Generate QR</button>
      </form>
    </div>

    <div class="flex flex-col items-center">
      <div class="qr-preview w-full max-w-sm">
        {% if qr_image %}
          <img id="qrImage" src="data:image/png;base64,{{ qr_image }}" class="rounded-md max-w-full">
        {% else %}
          <div class="p-8 text-center opacity-60">QR preview shows here</div>
        {% endif %}
      </div>

      {% if qr_image %}
        <div class="url-box" id="displayUrl">{{ display_url }}</div>
        <a href="/download_qr" class="w-full mt-3 py-3 btn-download text-center">Download QR Code (PNG)</a>
      {% endif %}
    </div>
     <!-- three-dot menu overlay -->
        <div id="threeDots" class="three-dots" title="Customize QR">Customize QR ⋮</div>

  </div>
</div>

<!-- Add Platform Modal -->
<div id="addPlatformBackdrop" class="modal-backdrop">
  <div class="modal">
    <h3 class="label">Add Platforms</h3>

    <div style="margin-bottom:10px;">
      <label class="small-muted">Platform 1</label>
      <div style="display:flex;gap:5px;margin-top:5px;">
        <select id="modalPlatform1" class="dropdown-glass" style="flex:1;">
          <option value="">-- Select --</option>
          <option value="facebook">Facebook</option>
          <option value="instagram">Instagram</option>
          <option value="youtube">YouTube</option>
          <option value="linkedin">LinkedIn</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="drive">Google Drive</option>
          <option value="googleform">Google Form</option>
          <option value="tel">Call</option>
          <option value="sms">SMS</option>
          <option value="mailto">Email</option>
          <option value="other">Other (custom link)</option>
        </select>
        <input id="modalUsername1" class="input" style="flex:2;" placeholder="ID / Number">
      </div>
    </div>

    <div style="margin-bottom:10px;">
      <label class="small-muted">Platform 2</label>
      <div style="display:flex;gap:5px;margin-top:5px;">
        <select id="modalPlatform2" class="dropdown-glass" style="flex:1;">
          <option value="">-- Select --</option>
          <option value="facebook">Facebook</option>
          <option value="instagram">Instagram</option>
          <option value="youtube">YouTube</option>
          <option value="linkedin">LinkedIn</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="drive">Google Drive</option>
          <option value="googleform">Google Form</option>
          <option value="tel">Call</option>
          <option value="sms">SMS</option>
          <option value="mailto">Email</option>
          <option value="other">Other (custom link)</option>
        </select>
        <input id="modalUsername2" class="input" style="flex:2;" placeholder="ID / Number">
      </div>
    </div>

    <div style="margin-bottom:14px;">
      <label class="small-muted">Platform 3</label>
      <div style="display:flex;gap:5px;margin-top:5px;">
        <select id="modalPlatform3" class="dropdown-glass" style="flex:1;">
          <option value="">-- Select --</option>
          <option value="facebook">Facebook</option>
          <option value="instagram">Instagram</option>
          <option value="youtube">YouTube</option>
          <option value="linkedin">LinkedIn</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="drive">Google Drive</option>
          <option value="googleform">Google Form</option>
          <option value="tel">Call</option>
          <option value="sms">SMS</option>
          <option value="mailto">Email</option>
          <option value="other">Other (custom link)</option>
        </select>
        <input id="modalUsername3" class="input" style="flex:2;" placeholder="ID / Number">
      </div>
    </div>

    <div style="display:flex; justify-content:flex-end; gap:8px;">
      <button class="small-btn" onclick="closeAddPlatformModal()">Cancel</button>
      <button class="btn-primary" onclick="applyAddPlatform()">Add Links</button>
    </div>
  </div>
</div>

<!-- Modal (open when 3-dots clicked) -->
<div id="modalBackdrop" class="modal-backdrop">
  <div class="modal">
    <h3 class="label">Customize QR & Label</h3>

    <div style="margin-bottom:10px;">
      <label class="small-muted">Label Preset</label>
      <select id="modalLabelPreset" class="dropdown-glass w-full" onchange="onModalLabelPresetChange()">
        <option value="Scan Me!">Scan Me!</option>
        <option value="Visit My Profile">Visit My Profile</option>
        <option value="Contact Me">Contact Me</option>
        <option value="Custom">Custom...</option>
      </select>
      <input id="modalCustomLabel" class="input hidden" placeholder="Custom label text">
    </div>

    <div style="margin-bottom:10px;">
      <label class="small-muted">QR Box Size (integer)</label>
      <input id="modalBoxSize" class="input" type="number" min="1" max="20" value="5">
    </div>
    <div style="margin-bottom:14px;">
      <label class="small-muted">Custom Background Image (PNG/JPG)</label>
      <input id="modalBgImage" type="file" name="background_image_file" accept="image/png, image/jpeg" class="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100">
      <input type="hidden" id="deleteBg" name="delete_bg" value="0">
      <button type="button" class="mt-2 small-btn text-xs" onclick="deleteBackgroundImage()">Remove Current Image</button>
    </div>

    <div style="margin-bottom:14px;">
      <label class="small-muted">Error Correction</label>
      <select id="modalErrorLevel" class="dropdown-glass w-full">
        <option value="L">L - Low</option>
        <option value="M">M - Medium</option>
        <option value="Q">Q - Quartile</option>
        <option value="H">H - High</option>
      </select>
    </div>

    <div style="display:flex; justify-content:flex-end; gap:8px;">
      <button class="small-btn" onclick="closeModal()">Cancel</button>
      <button class="btn-primary" onclick="applyModalSettings()">Apply & Generate</button>
    </div>
  </div>
</div>

<script>
/* ---------- Platform blocks ---------- */
let shown = 1;
function showNext() {
    document.getElementById("block1").classList.remove("hidden");
    document.getElementById("block2").classList.remove("hidden");
    document.getElementById("block3").classList.remove("hidden");
    shown = 3;
}
function deleteBackgroundImage() {
    document.getElementById('modalBgImage').value = ''; // Clear file input
    document.getElementById('deleteBg').value = '1'; // Signal server to remove
    const form = document.getElementById('qrForm');
    const deleteHidden = document.getElementById('deleteBg');
    form.appendChild(deleteHidden);
    form.submit(); // Regenerate QR
}

/* ---------- Platform URL HANDLING ---------- */
const PLATFORM_BASES={
    facebook:'https://www.facebook.com/',
    instagram:'https://www.instagram.com/',
    youtube:'https://www.youtube.com/@',
    linkedin:'https://www.linkedin.com/in/',
    whatsapp:'https://wa.me/',
    drive:'https://drive.google.com/open?id=',
    googleform:'https://docs.google.com/forms/d/',
    tel:'tel:',
    sms:'sms:',
    mailto:'mailto:',
    '': ''
};

function create(platform, username){
    if(!platform || !username) return "";
    if(platform === 'other') return username; // for other, username is the full link
    let base = PLATFORM_BASES[platform];
    if(platform==='googleform'){
        return base + username + '/viewform';
    }
    if(platform==='youtube'){
        username = username.startsWith('@') ? username.substring(1) : username;
    }
    // Clean phone entries for whatsapp/tel/sms
    if(platform==='whatsapp' || platform==='tel' || platform==='sms'){
        username = username.replace(/[^0-9+]/g,'');
    }
    return base + username;
}

function updateLink1(){
    document.getElementById("finalLink1").value =
        create(document.getElementById("platform1").value, document.getElementById("username1").value.trim());
}
function updateLink2(){
    document.getElementById("finalLink2").value =
        create(document.getElementById("platform2").value, document.getElementById("username2").value.trim());
}
function updateLink3(){
    document.getElementById("finalLink3").value =
        create(document.getElementById("platform3").value, document.getElementById("username3").value.trim());
}

/* ---------- Label dropdown logic (main form) ---------- */
function onLabelPresetChange(){
    const sel = document.getElementById('labelPreset');
    const customInput = document.getElementById('customLabelInput');
    const hiddenField = document.getElementById('custom_text');

    if(sel.value === 'Custom'){
        customInput.classList.remove('hidden');
        hiddenField.value = customInput.value || "";
    } else {
        customInput.classList.add('hidden');
        hiddenField.value = sel.value;
    }
}
document.getElementById('customLabelInput').addEventListener('input', function(){
    document.getElementById('custom_text').value = this.value;
});

/* Initialize label fields from server-provided value */
(function initLabelFromServer(){
    try {
        const serverVal = `{{ saved_data.custom_text }}`.trim();
        if(serverVal && serverVal !== 'None'){
            // if matches a preset, select that preset; else choose Custom and populate
            const presets = ['Scan Me!','Visit My Profile','Contact Me'];
            if(presets.includes(serverVal)){
                document.getElementById('labelPreset').value = serverVal;
                document.getElementById('customLabelInput').classList.add('hidden');
                document.getElementById('custom_text').value = serverVal;
            } else {
                document.getElementById('labelPreset').value = 'Custom';
                document.getElementById('customLabelInput').classList.remove('hidden');
                document.getElementById('customLabelInput').value = serverVal;
                document.getElementById('custom_text').value = serverVal;
            }
        }
    } catch(e){}
})();

/* ---------- Add Platform Modal ---------- */
function openAddPlatformModal(){
    // optionally pre-populate from current? but probably clear them
    const modalBackdrop = document.getElementById('addPlatformBackdrop');
    modalBackdrop.style.display = 'flex';
}

function closeAddPlatformModal(){
    const modalBackdrop = document.getElementById('addPlatformBackdrop');
    modalBackdrop.style.display = 'none';
}

/* Apply add platform settings */
function applyAddPlatform(){
    // set the form fields from modal
    document.getElementById('platform1').value = document.getElementById('modalPlatform1').value;
    document.getElementById('username1').value = document.getElementById('modalUsername1').value;
    document.getElementById('platform2').value = document.getElementById('modalPlatform2').value;
    document.getElementById('username2').value = document.getElementById('modalUsername2').value;
    document.getElementById('platform3').value = document.getElementById('modalPlatform3').value;
    document.getElementById('username3').value = document.getElementById('modalUsername3').value;

    // update the hidden links
    updateLink1();
    updateLink2();
    updateLink3();

    // show preview of added links as platform buttons
    const linksList = document.getElementById('linksList');
    linksList.innerHTML = '';
    const platforms = [
        {plat: document.getElementById('platform1').value, user: document.getElementById('username1').value, link: document.getElementById('finalLink1').value, label: 'Platform 1'},
        {plat: document.getElementById('platform2').value, user: document.getElementById('username2').value, link: document.getElementById('finalLink2').value, label: 'Platform 2'},
        {plat: document.getElementById('platform3').value, user: document.getElementById('username3').value, link: document.getElementById('finalLink3').value, label: 'Platform 3'}
    ];

    const PLATFORM_BUTTON_STYLES = {
        facebook: 'bg-blue-600 hover:bg-blue-700 text-white',
        instagram: 'bg-pink-600 hover:bg-pink-700 text-white',
        youtube: 'bg-red-600 hover:bg-red-700 text-white',
        linkedin: 'bg-blue-700 hover:bg-blue-800 text-white',
        whatsapp: 'bg-green-600 hover:bg-green-700 text-white',
        tel: 'bg-green-700 hover:bg-green-800 text-white',
        sms: 'bg-yellow-600 hover:bg-yellow-700 text-white',
        mailto: 'bg-red-600 hover:bg-red-700 text-white',
        other: 'bg-indigo-600 hover:bg-indigo-700 text-white',
        default: 'bg-gray-600 hover:bg-gray-700 text-white'
    };

    const PLATFORM_ICONS = {
        facebook: '<i class="fab fa-facebook-f"></i>',
        instagram: '<i class="fab fa-instagram"></i>',
        youtube: '<i class="fab fa-youtube"></i>',
        linkedin: '<i class="fab fa-linkedin-in"></i>',
        whatsapp: '<i class="fab fa-whatsapp"></i>',
        tel: '<i class="fa-solid fa-phone"></i>',
        sms: '<i class="fa-solid fa-message"></i>',
        mailto: '<i class="fa-solid fa-envelope"></i>',
        other: '<i class="fa-solid fa-link"></i>',
        default: '<i class="fa-solid fa-globe"></i>'
    };

    platforms.forEach((p, idx) => {
        if(p.plat && p.user && p.link){
            const button = document.createElement('button');
            const styleKey = p.plat in PLATFORM_BUTTON_STYLES ? p.plat : 'default';
            const icon = PLATFORM_ICONS[styleKey];
            const name = p.plat === 'tel' ? 'Call' : p.plat === 'sms' ? 'Text' : p.plat === 'mailto' ? 'Email' : p.plat === 'other' ? 'Custom' : p.plat.charAt(0).toUpperCase() + p.plat.slice(1);

            button.innerHTML = `${icon} ${name}`;
            button.className = `m-1 px-3 py-2 rounded-md text-sm font-medium transition ${PLATFORM_BUTTON_STYLES[styleKey]}`;
            button.onclick = () => window.open(p.link, '_blank');
            linksList.appendChild(button);
        }
    });
    document.getElementById('linksPreview').style.display = 'block';

    // close modal
    closeAddPlatformModal();
}

/* ---------- Modal & three-dots ---------- */
const threeDots = document.getElementById('threeDots');
const modalBackdrop = document.getElementById('modalBackdrop');

threeDots && threeDots.addEventListener('click', function(){
    // sync modal inputs with current form values
    const curLabel = document.getElementById('custom_text').value || 'Scan Me!';
    const presetOptions = ['Scan Me!','Visit My Profile','Contact Me'];
    const modalPreset = document.getElementById('modalLabelPreset');
    if(presetOptions.includes(curLabel)){
        modalPreset.value = curLabel;
        document.getElementById('modalCustomLabel').classList.add('hidden');
    } else {
        modalPreset.value = 'Custom';
        document.getElementById('modalCustomLabel').classList.remove('hidden');
        document.getElementById('modalCustomLabel').value = curLabel;
    }
    // populate box size from hidden field or default
    const boxField = document.getElementById('box_size_field').value;
    document.getElementById('modalBoxSize').value = boxField ? boxField : 5;
    // error level
    const errField = document.getElementById('error_level_field').value || 'L';
    document.getElementById('modalErrorLevel').value = errField;

    modalBackdrop.style.display = 'flex';
});

function closeModal(){ modalBackdrop.style.display = 'none'; }

function onModalLabelPresetChange(){
    const sel = document.getElementById('modalLabelPreset');
    const cust = document.getElementById('modalCustomLabel');
    if(sel.value === 'Custom') cust.classList.remove('hidden');
    else cust.classList.add('hidden');
}
document.getElementById('modalLabelPreset').addEventListener('change', onModalLabelPresetChange);

/* Apply modal settings to the form and submit */
function applyModalSettings(){
    // label
    const modalPreset = document.getElementById('modalLabelPreset').value;
    const modalCustom = document.getElementById('modalCustomLabel').value || '';
    if(modalPreset === 'Custom'){
        document.getElementById('labelPreset').value = 'Custom';
        document.getElementById('customLabelInput').classList.remove('hidden');
        document.getElementById('customLabelInput').value = modalCustom;
        document.getElementById('custom_text').value = modalCustom;
    } else {
        document.getElementById('labelPreset').value = modalPreset;
        document.getElementById('customLabelInput').classList.add('hidden');
        document.getElementById('custom_text').value = modalPreset;
    }

    // box size & error
    const boxVal = parseInt(document.getElementById('modalBoxSize').value) || 5;
    document.getElementById('box_size_field').value = boxVal;

    const errVal = document.getElementById('modalErrorLevel').value || 'L';
    document.getElementById('error_level_field').value = errVal;

    // append file input if file is selected
    const form = document.getElementById('qrForm');
    const fileInput = document.getElementById('modalBgImage');
    const deleteHidden = document.getElementById('deleteBg');
    if (fileInput.files.length > 0) {
        form.appendChild(fileInput);
    }
    if (deleteHidden.value === '1') {
        form.appendChild(deleteHidden);
    }

    // close modal and submit form to regenerate QR
    modalBackdrop.style.display = 'none';
    form.submit();
}

/* modal custom label input listener */
document.getElementById('modalCustomLabel').addEventListener('input', function(){
    // live sync not necessary; will apply on Apply
});

/* ---------- keep link inputs updated on submit (just in case) ---------- */
document.getElementById('qrForm').addEventListener('submit', function(){
    updateLink1(); updateLink2(); updateLink3();  
    // ensure custom_text field populated if customLabelInput visible
    const preset = document.getElementById('labelPreset').value;
    if(preset === 'Custom'){
        document.getElementById('custom_text').value = document.getElementById('customLabelInput').value || '';
    } else {
        document.getElementById('custom_text').value = preset;
    }
});

/* small helper to set server default for JS templating safety */
</script>

</body>
</html>

"""

# ----------------------------------------------------------------------------------------------------
# ROUTES
# ----------------------------------------------------------------------------------------------------

@app.route('/')
def index():
    global saved_input_data, last_qr_data
    last_qr_data = None
    saved_input_data = {
        "name": "Abilash",
        "message": "Check out my profile!",
        "copy_data": "",
        "image_url": "",
        "text_key": "",
        "platform1": "", "username_input1": "", "link1": "",
        "platform2": "", "username_input2": "", "link2": "",
        "platform3": "", "username_input3": "", "link3": "",
        "custom_text": "Scan Me!",
        # QR options defaults (sent as empty to allow modal to set them)
        "box_size": "",
        "error_level": ""
    }
    return render_template_string(HTML_TEMPLATE, qr_image=None, saved_data=saved_input_data, DEFAULT_QR_BOX_SIZE=DEFAULT_QR_BOX_SIZE)

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    global saved_input_data, last_qr_data

    # --- 🌟 NEW: Background Image Handling 🌟 ---
    
    # 1. Check for deletion request
    if request.form.get('delete_bg') == '1' and os.path.exists(USER_BG_PATH):
        os.remove(USER_BG_PATH)

    # 2. Check for file upload
    if 'background_image_file' in request.files:
        bg_file = request.files['background_image_file']
        if bg_file and bg_file.filename:
            # Save the new file to the predefined user path
            try:
                # Use PIL to ensure image integrity before saving
                img = Image.open(bg_file.stream)
                img.save(USER_BG_PATH)
            except Exception as e:
                print(f"Error saving background image: {e}")
                # Log error but continue with QR generation
    
    # --- END NEW BACKGROUND HANDLING ---

    # Read form fields (including new box_size and error_level)
    # ... (rest of form reading logic remains the same) ...
    # Read form fields (including new box_size and error_level)
    box_size_raw = request.form.get("box_size", "")
    try:
        box_size = int(box_size_raw) if box_size_raw else DEFAULT_QR_BOX_SIZE
        if box_size < 1: box_size = DEFAULT_QR_BOX_SIZE
    except Exception:
        box_size = DEFAULT_QR_BOX_SIZE

    err_level_raw = request.form.get("error_level", "")  # expected 'L','M','Q','H'
    err_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }
    qr_error = err_map.get(err_level_raw, DEFAULT_QR_ERROR)
    
    # ... (rest of saved_input_data dict remains the same) ...

    saved_input_data = {
        "name": request.form.get("name", ""),
        "message": request.form.get("message", ""),
        "copy_data": request.form.get("copy_data", ""),
        "image_url": request.form.get("image_url", ""),
        "text_key": request.form.get("text_key", ""),
        "platform1": request.form.get("platform1", ""),
        "platform2": request.form.get("platform2", ""),
        "platform3": request.form.get("platform3", ""),
        "username_input1": request.form.get("username_input1", ""),
        "username_input2": request.form.get("username_input2", ""),
        "username_input3": request.form.get("username_input3", ""),
        "link1": request.form.get("link1", ""),
        "link2": request.form.get("link2", ""),
        "link3": request.form.get("link3", ""),
        "custom_text": request.form.get("custom_text", ""),
        "box_size": box_size,
        "error_level": err_level_raw
    }

    # ... (rest of QR generation logic remains the same) ...

    encoded_url = generate_target_url(saved_input_data)
    last_qr_data = encoded_url

    # Create QR with provided box_size and error correction
    qr = qrcode.QRCode(box_size=box_size, error_correction=qr_error)
    qr.add_data(encoded_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    final_card = add_custom_graphics(qr_img, saved_input_data.get("custom_text",""))
    buf = io.BytesIO()
    final_card.save(buf, format="PNG")
    buf.seek(0)
    qr_b64 = base64.b64encode(buf.read()).decode()

    return render_template_string(HTML_TEMPLATE,
        qr_image=qr_b64,
        display_url=urllib.parse.unquote(encoded_url),
        saved_data=saved_input_data,
        DEFAULT_QR_BOX_SIZE=DEFAULT_QR_BOX_SIZE
    )
@app.route('/download_qr')
def download_qr():
    global last_qr_data, saved_input_data
    if not last_qr_data:
        return "No QR generated yet", 400

    # Use last submitted settings if present
    box_size = int(saved_input_data.get("box_size") or DEFAULT_QR_BOX_SIZE)
    err_level_raw = saved_input_data.get("error_level") or 'L'
    err_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }
    qr_error = err_map.get(err_level_raw, DEFAULT_QR_ERROR)

    qr = qrcode.QRCode(box_size=box_size, error_correction=qr_error)
    qr.add_data(last_qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    final_card = add_custom_graphics(qr_img, saved_input_data.get("custom_text",""))
    buf = io.BytesIO()
    final_card.save(buf, format="PNG")
    buf.seek(0)

    filename = (saved_input_data.get("name","qrcode").replace(" ", "_") or "qrcode") + "_qr.png"
    return send_file(buf, mimetype="image/png", as_attachment=True, download_name=filename)

# ----------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    def start_server():
        app.run(host="127.0.0.1", port=5000, use_reloader=False)

    t = Thread(target=start_server)
    t.daemon = True
    t.start()
    
    webview.create_window('QR Code Generator', 'http://127.0.0.1:5000/', width=1200, height=800)
    webview.start()
