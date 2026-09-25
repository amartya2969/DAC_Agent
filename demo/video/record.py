import glob, os, shutil, subprocess, time
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

here = os.path.dirname(os.path.abspath(__file__))
raw = os.path.join(here, "raw")
shutil.rmtree(raw, ignore_errors=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
    ctx = browser.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=raw,
                              record_video_size={"width": 1280, "height": 720})
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    start = time.time()
    page.goto("file://" + os.path.join(here, "story.html"))
    page.wait_for_function("window.DEMO_TOTAL_MS > 0")
    total = page.evaluate("window.DEMO_TOTAL_MS")
    page.wait_for_function("window.DEMO_DONE === true", timeout=total + 30000)
    page.wait_for_timeout(1200)
    lead = 0.4
    ctx.close(); browser.close()
print("console errors:", errors, "timeline ms:", total)
webm = glob.glob(os.path.join(raw, "*.webm"))[0]
out = os.path.join(here, "dac-agent-demo.mp4")
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", str(lead), "-i", webm,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
                "-movflags", "+faststart", "-r", "30", out], check=True)
print("wrote", out, os.path.getsize(out) // 1024, "KB")
