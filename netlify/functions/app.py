import os
import io
import json
import shutil
import tempfile
import gc
import numpy as np
import serverless_wsgi
from flask import Flask, request, send_file, render_template
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
 
# MoviePy 2.0+ Imports
from moviepy import VideoFileClip, concatenate_videoclips
import moviepy.video.fx as vfx
 
# Initialize App
app = Flask(__name__, 
            template_folder="../../templates", 
            static_folder="../../static")
CORS(app)
 
def add_text_to_image(img, text, color, size):
    if not text: return img
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    w, h = img.size
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((w - tw) / 2 + 2, h - th - 38), text, font=font, fill="black")
    draw.text(((w - tw) / 2, h - th - 40), text, font=font, fill=color)
    return img
 
@app.route('/')
def index():
    return render_template('index.html')
 
@app.route('/generate', methods=['POST'])
def generate_gif():
    mode = request.form.get('mode')
    speed_multiplier = float(request.form.get('duration', 1.0))
    overlay_text = request.form.get('overlay_text', '')
    text_color = request.form.get('text_color', '#ffffff')
    text_size = request.form.get('text_size', '40')
    uploaded_files = request.files.getlist('files')
    if not uploaded_files:
        return "No files received", 400
 
    # Works for both local and cloud
    session_dir = tempfile.mkdtemp()
    try:
        if mode == 'photo':
            crops = json.loads(request.form.get('crops', '[]'))
            frames = []
            frame_delay = int(400 / speed_multiplier)
 
            for i, file in enumerate(uploaded_files):
                img = Image.open(file).convert("RGB")
                if i < len(crops):
                    c = crops[i]
                    img = img.crop((c['x'], c['y'], c['x'] + c['width'], c['y'] + c['height']))
                if i == 0:
                    base_size = img.size
                else:
                    img = img.resize(base_size, Image.Resampling.LANCZOS)
                img = add_text_to_image(img, overlay_text, text_color, text_size)
                frames.append(img)
 
            out = io.BytesIO()
            frames[0].save(out, format='GIF', save_all=True, append_images=frames[1:], duration=frame_delay, loop=0)
            out.seek(0)
            return send_file(out, mimetype='image/gif', download_name='result.gif')
 
        elif mode in ['gif', 'video']:
            clips = []
            for i, file in enumerate(uploaded_files):
                ext = os.path.splitext(file.filename or "")[1] or ('.gif' if mode == 'gif' else '.mp4')
                path = os.path.join(session_dir, f"input_{i}{ext}")
                file.save(path)
                clip = VideoFileClip(path)
                if speed_multiplier != 1.0:
                    clip = clip.with_effects([vfx.MultiplySpeed(speed_multiplier)])
                if overlay_text:
                    clip = clip.transform(lambda get_frame, t:
                        np.array(add_text_to_image(Image.fromarray(get_frame(t)), overlay_text, text_color, text_size))
                    )
                clips.append(clip)
 
            final_clip = concatenate_videoclips(clips, method="compose")
            output_path = os.path.join(session_dir, "output.gif")
            final_clip.write_gif(output_path, fps=12, logger=None)
            final_clip.close()
 
            with open(output_path, 'rb') as f:
                return_data = io.BytesIO(f.read())
            return_data.seek(0)
            return send_file(return_data, mimetype='image/gif', download_name='result.gif')
 
    except Exception as e:
        return f"Error: {str(e)}", 500
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)
 
# NETLIFY HANDLER
def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)
 
# LOCAL RUNNER
if __name__ == '__main__':
    app.run(port=5000, debug=True)