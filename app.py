import os
import uuid
import shutil
from PIL import Image, ImageSequence
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


# --- 新增的辅助函数 ---
def get_gif_duration(image: Image.Image) -> tuple:
    """通过累加所有帧的持续时间来计算GIF的总时长（秒），并返回每帧的时长列表。"""
    frame_durations_ms = []
    for frame in ImageSequence.Iterator(image):
        frame_durations_ms.append(frame.info.get('duration', 100))
    
    # 对于单帧图像，Pillow有时不会正确报告时长, 我们给一个默认值
    if not frame_durations_ms:
        frame_durations_ms.append(image.info.get('duration', 100))

    total_duration_s = sum(frame_durations_ms) / 1000.0
    return round(total_duration_s, 2), frame_durations_ms

def create_default_filename(prefix: str, duration_s: float, suffix: str = "") -> str:
    """根据时长创建默认文件名，例如 'happy_1_5s.gif' 或 'happy_3s_left.gif'。"""
    # 如果是整数秒，显示为整数
    if duration_s == int(duration_s):
        duration_str = str(int(duration_s))
    else:
        duration_str = str(duration_s).replace('.', '_')
    
    if suffix:
        return f"{prefix}_{duration_str}s_{suffix}.gif"
    return f"{prefix}_{duration_str}s.gif"


# --- 配置 ---
OUTPUT_DIR = "processed_gifs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI()

# 挂载静态文件目录，用于提供 index.html 和处理好的 GIF
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/processed", StaticFiles(directory=OUTPUT_DIR), name="processed")


# --- 核心 GIF 处理逻辑 ---
def verify_frame_count(filepath: str, expected_frames: int):
    """验证输出GIF的帧数是否与输入一致。"""
    try:
        img = Image.open(filepath)
        actual_frames = sum(1 for _ in ImageSequence.Iterator(img))
        if actual_frames != expected_frames:
            print(f"警告: 预期 {expected_frames} 帧，实际 {actual_frames} 帧")
        return actual_frames
    except Exception as e:
        print(f"警告: 无法验证文件 {filepath} 的帧数: {e}")
        return 0

def process_gif(input_path: str, original_filename: str):
    """
    处理单个GIF文件: resize, split, and save, with robust transparency handling.
    返回一个包含处理后文件信息的字典列表。
    """
    try:
        original_image = Image.open(input_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法读取GIF文件: {e}")

    filename_prefix = os.path.splitext(original_filename)[0]
    width, height = original_image.size
    duration_s, frame_durations = get_gif_duration(original_image)
    
    # --- 任务1: 准备要处理的帧列表 ---
    images_to_process = []
    all_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(original_image)]
    
    if width == 2 * height: # 分割
        left_box = (0, 0, width // 2, height)
        right_box = (width // 2, 0, width, height)
        
        images_to_process.append({
            'frames': [frame.crop(left_box) for frame in all_frames],
            'default_filename': create_default_filename(filename_prefix, duration_s, 'left')
        })
        images_to_process.append({
            'frames': [frame.crop(right_box) for frame in all_frames],
            'default_filename': create_default_filename(filename_prefix, duration_s, 'right')
        })
    else: # 不分割
        images_to_process.append({
            'frames': all_frames,
            'default_filename': create_default_filename(filename_prefix, duration_s)
        })

    # --- 任务2: Resize 和 保存 ---
    final_results = []
    
    loop = original_image.info.get('loop', 0)
    disposal = original_image.info.get('disposal', 2)

    for item in images_to_process:
        processed_frames = [frame.resize((240, 240), Image.Resampling.LANCZOS) for frame in item['frames']]

        server_filename = f"{uuid.uuid4()}.gif"
        output_path = os.path.join(OUTPUT_DIR, server_filename)
        
        save_params = {
            'save_all': True,
            'append_images': processed_frames[1:] if len(processed_frames) > 1 else [],
            'duration': frame_durations,
            'loop': loop,
            'optimize': False,
            'disposal': disposal
        }

        if processed_frames:
            processed_frames[0].save(output_path, **save_params)
            verify_frame_count(output_path, len(item['frames']))
        
        final_results.append({
            "url": f"/processed/{server_filename}",
            "duration": duration_s,
            "default_filename": item['default_filename']
        })

    return final_results

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """提供前端页面"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/upload")
async def upload_gif(file: UploadFile = File(...)):
    """处理上传的GIF文件"""
    if not file.filename.lower().endswith('.gif'):
        raise HTTPException(status_code=400, detail="仅支持GIF格式的文件。")

    temp_path = os.path.join(OUTPUT_DIR, f"temp_{uuid.uuid4()}.gif")
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        processed_results = process_gif(temp_path, original_filename=file.filename)
    except Exception as e:
        os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
    
    os.remove(temp_path)
    return JSONResponse(content={"results": processed_results})


def _ensure_original_exists(filepath: str) -> str:
    """
    Ensures a backup of the file exists. If not, creates one from the current file.
    Returns the path to the backup file.
    """
    path, filename = os.path.split(filepath)
    name, ext = os.path.splitext(filename)
    original_path = os.path.join(path, f"{name}_original{ext}")
    if not os.path.exists(original_path):
        shutil.copy(filepath, original_path)
    return original_path


@app.post("/flip")
async def flip_gif(filename: str):
    """水平翻转指定的GIF文件"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件未找到。")

    try:
        img = Image.open(filepath)
        _, frame_durations = get_gif_duration(img)
        loop = img.info.get('loop', 0)
        disposal = img.info.get('disposal', 2)

        frames = [frame.convert('RGBA') for frame in ImageSequence.Iterator(img)]
        flipped_frames = [frame.transpose(Image.FLIP_LEFT_RIGHT) for frame in frames]
        
        save_params = {
            'save_all': True,
            'append_images': flipped_frames[1:] if len(flipped_frames) > 1 else [],
            'duration': frame_durations,
            'loop': loop,
            'optimize': False,
            'disposal': disposal
        }
        
        if flipped_frames:
            flipped_frames[0].save(filepath, **save_params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"翻转失败: {e}")

    return JSONResponse(content={"status": "success", "filename": filename})


@app.post("/swap_rgb")
async def swap_rgb_gif(filename: str, rgb_map: str):
    """
    Swaps the RGB channels of a GIF based on the provided map, always starting from the original.
    e.g., rgb_map='gbr' means original R->G, original G->B, original B->R
    """
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件未找到。")
    
    if len(rgb_map) != 3 or not all(c in 'rgb' for c in rgb_map.lower()) or len(set(rgb_map.lower())) != 3:
        raise HTTPException(status_code=400, detail="无效的RGB映射。它必须是'rgb'的排列组合, 例如 'gbr'。")

    original_filepath = _ensure_original_exists(filepath)

    if rgb_map.lower() == 'rgb':
        shutil.copy(original_filepath, filepath)
        return JSONResponse(content={"status": "success", "filename": filename})

    try:
        img = Image.open(original_filepath)
        _, frame_durations = get_gif_duration(img)
        loop = img.info.get('loop', 0)
        disposal = img.info.get('disposal', 2)
        
        frames = []
        source_channels = "RGB"
        channel_map_indices = [source_channels.find(c.upper()) for c in rgb_map]

        for frame in ImageSequence.Iterator(img):
            frame_rgba = frame.convert("RGBA")
            r, g, b, a = frame_rgba.split()
            channels = [r, g, b]
            
            swapped_channels = [channels[i] for i in channel_map_indices]
            
            swapped_frame = Image.merge("RGBA", (*swapped_channels, a))
            frames.append(swapped_frame)
        
        save_params = {
            'save_all': True,
            'append_images': frames[1:] if len(frames) > 1 else [],
            'duration': frame_durations,
            'loop': loop,
            'optimize': False,
            'disposal': disposal
        }
        
        if frames:
            frames[0].save(filepath, **save_params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RGB交换失败: {e}")

    return JSONResponse(content={"status": "success", "filename": filename})


# --- 运行服务器 ---
if __name__ == "__main__":
    import uvicorn
    print("服务器启动于 http://127.0.0.1:28000")
    uvicorn.run(app, host="127.0.0.1", port=28000)