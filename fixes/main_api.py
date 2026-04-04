import subprocess, uuid, os, threading, asyncio
import edge_tts
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

OUTPUT_DIR = "/root/autodl-tmp/output"
BASE_URL = "https://u946450-b2d1-6dbf3f52.westc.seetacloud.com:8443"
TEMPLATE_DIR = "/root/autodl-tmp/templates"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

tasks = {}

VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "yunjian": "zh-CN-YunjianNeural",
    "yunxi": "zh-CN-YunxiNeural",
    "yunxia": "zh-CN-YunxiaNeural",
    "yunyang": "zh-CN-YunyangNeural",
}

# ===== TTS 生成音频 =====
def run_tts(task_id, text, voice, out_path):
    tasks[task_id] = {"status": "running", "step": "生成音频"}
    try:
        audio_file = f"{out_path}/audio.mp3"
        voice_name = VOICES.get(voice, "zh-CN-XiaoxiaoNeural")
        async def _gen():
            tts = edge_tts.Communicate(text, voice_name)
            await tts.save(audio_file)
        asyncio.run(_gen())
        tasks[task_id] = {
            "status": "done", "type": "audio",
            "audio_url": f"{BASE_URL}/file/{task_id}/audio.mp3"
        }
    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}

@app.post("/generate-audio")
async def generate_audio(text: str = Form(...), voice: str = Form(default="xiaoxiao")):
    task_id = str(uuid.uuid4())[:8]
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)
    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_tts, args=(task_id, text, voice, out_path), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})

# ===== LivePortrait 正确流程 =====
# source = 用户照片（静态人脸）
# driving = 内置说话模板视频（系统提供）
def run_liveportrait(task_id, img_path, template_name, out_path):
    tasks[task_id] = {"status": "running", "step": "生成数字人视频"}

    # 选择模板视频
    template_path = f"{TEMPLATE_DIR}/{template_name}.mp4"
    if not os.path.exists(template_path):
        # 使用默认示例视频
        template_path = "/root/autodl-tmp/LivePortrait/assets/examples/driving/d0.mp4"

    result = subprocess.run([
        "python", "inference.py",
        "-s", img_path,
        "-d", template_path,
        "--output-dir", out_path,
        "--flag-relative-motion",  # 相对运动模式，效果更自然
    ], capture_output=True, text=True, cwd="/root/autodl-tmp/LivePortrait")

    if result.returncode != 0:
        # 尝试不加flag重试
        result = subprocess.run([
            "python", "inference.py",
            "-s", img_path,
            "-d", template_path,
            "--output-dir", out_path,
        ], capture_output=True, text=True, cwd="/root/autodl-tmp/LivePortrait")

    if result.returncode != 0:
        tasks[task_id] = {"status": "failed", "error": result.stderr[-500:]}
        return

    for f in os.listdir(out_path):
        if f.endswith(".mp4") and "concat" not in f:
            tasks[task_id] = {
                "status": "done", "type": "video",
                "video_url": f"{BASE_URL}/file/{task_id}/{f}"
            }
            return
    tasks[task_id] = {"status": "failed", "error": "未生成视频"}

@app.post("/generate-video")
async def generate_video(
    source_image: UploadFile = File(...),
    template: str = Form(default="default")
):
    task_id = str(uuid.uuid4())[:8]
    img_path = f"/tmp/{task_id}_source.jpg"
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)

    with open(img_path, "wb") as f:
        f.write(await source_image.read())

    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_liveportrait, args=(task_id, img_path, template, out_path), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})

# ===== 上传自定义模板视频 =====
@app.post("/upload-template")
async def upload_template(
    video: UploadFile = File(...),
    name: str = Form(default="custom")
):
    safe_name = name.replace("/", "").replace("..", "")
    path = f"{TEMPLATE_DIR}/{safe_name}.mp4"
    with open(path, "wb") as f:
        f.write(await video.read())
    return JSONResponse({"success": True, "template": safe_name})

# ===== 列出可用模板 =====
@app.get("/templates")
def list_templates():
    templates = []
    # 默认模板
    templates.append({"id": "default", "name": "默认模板", "builtin": True})
    # 自定义模板
    for f in os.listdir(TEMPLATE_DIR):
        if f.endswith(".mp4"):
            name = f.replace(".mp4", "")
            templates.append({"id": name, "name": name, "builtin": False})
    return JSONResponse({"templates": templates})

# ===== 合并视频+音频+字幕 =====
def run_merge(task_id, video_path, audio_path, subtitle_text, out_path):
    tasks[task_id] = {"status": "running", "step": "合并视频音频字幕"}
    try:
        # 生成 SRT 字幕
        srt_path = f"{out_path}/subtitle.srt"
        sentences = [s.strip() for s in subtitle_text.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n") if s.strip()]
        if not sentences:
            sentences = [subtitle_text]
        duration_per = max(2, len(subtitle_text) // (len(sentences) * 4))

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, s in enumerate(sentences):
                start = i * duration_per
                end = start + duration_per
                sh, sm, ss = start // 3600, (start % 3600) // 60, start % 60
                eh, em, es = end // 3600, (end % 3600) // 60, end % 60
                f.write(f"{i+1}\n")
                f.write(f"{sh:02d}:{sm:02d}:{ss:02d},000 --> {eh:02d}:{em:02d}:{es:02d},000\n")
                f.write(f"{s}\n\n")

        output_file = f"{out_path}/final.mp4"

        # 先合并视频和音频
        merged_path = f"{out_path}/merged.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            merged_path
        ], capture_output=True)

        # 再烧字幕
        srt_escaped = srt_path.replace(":", "\\:").replace("'", "\\'")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", merged_path,
            "-vf", f"subtitles={srt_escaped}:force_style='FontName=PingFang SC,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2'",
            "-c:v", "libx264", "-crf", "23",
            "-c:a", "copy",
            output_file
        ], capture_output=True, text=True)

        if result.returncode != 0:
            # 降级：不加字幕直接输出
            os.rename(merged_path, output_file)

        tasks[task_id] = {
            "status": "done", "type": "final",
            "video_url": f"{BASE_URL}/file/{task_id}/final.mp4"
        }
    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}

@app.post("/merge")
async def merge(
    video_url: str = Form(...),
    audio_url: str = Form(...),
    subtitle_text: str = Form(...)
):
    import requests as req_lib
    task_id = str(uuid.uuid4())[:8]
    out_path = f"{OUTPUT_DIR}/{task_id}"
    os.makedirs(out_path, exist_ok=True)

    video_path = f"{out_path}/input.mp4"
    audio_path = f"{out_path}/input.mp3"

    with open(video_path, "wb") as f:
        f.write(req_lib.get(video_url, timeout=60).content)
    with open(audio_path, "wb") as f:
        f.write(req_lib.get(audio_url, timeout=60).content)

    tasks[task_id] = {"status": "pending"}
    threading.Thread(target=run_merge, args=(task_id, video_path, audio_path, subtitle_text, out_path), daemon=True).start()
    return JSONResponse({"success": True, "task_id": task_id})

# ===== 通用 =====
@app.get("/status/{task_id}")
def get_status(task_id: str):
    return JSONResponse(tasks.get(task_id, {"status": "not_found"}))

@app.get("/file/{task_id}/{filename}")
def get_file(task_id: str, filename: str):
    path = f"{OUTPUT_DIR}/{task_id}/{filename}"
    if not os.path.exists(path):
        return JSONResponse({"error": "不存在"}, status_code=404)
    return FileResponse(path)

@app.get("/voices")
def get_voices():
    return JSONResponse({"voices": [
        {"id": "xiaoxiao", "name": "晓晓", "desc": "温柔女声"},
        {"id": "xiaoyi", "name": "晓伊", "desc": "活泼女声"},
        {"id": "yunjian", "name": "云健", "desc": "成熟男声"},
        {"id": "yunxi", "name": "云希", "desc": "阳光男声"},
        {"id": "yunxia", "name": "云夏", "desc": "自然男声"},
        {"id": "yunyang", "name": "云扬", "desc": "播音男声"},
    ]})

@app.get("/health")
def health():
    return {"status": "ok", "services": ["liveportrait", "tts", "merge"]}
