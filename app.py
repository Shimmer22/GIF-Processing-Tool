import os
import uuid
import shutil
from PIL import Image, ImageSequence
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


# --- 新增的辅助函数 ---
def get_gif_duration(image: Image.Image) -> float:
    """通过累加所有帧的持续时间来计算GIF的总时长（秒）。"""
    duration_ms = 0
    frames = 0
    for frame in ImageSequence.Iterator(image):
        duration_ms += frame.info.get('duration', 100)
        frames += 1
    
    # 对于单帧图像，Pillow有时不会正确报告时长, 我们给一个默认值
    if frames <= 1:
        return round(image.info.get('duration', 100) / 1000.0, 2)

    return round(duration_ms / 1000.0, 2)

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
    duration_s = get_gif_duration(original_image)
    
    # --- 任务1: 准备要处理的帧列表 ---
    images_to_process = []
    if width == 2 * height: # 分割
        left_box = (0, 0, width // 2, height)
        right_box = (width // 2, 0, width, height)
        
        # 为分割后的左右部分准备帧
        all_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(original_image)]
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
            'frames': [frame.convert("RGBA") for frame in ImageSequence.Iterator(original_image)],
            'default_filename': create_default_filename(filename_prefix, duration_s)
        })

    # --- 任务2: Resize 和 保存 ---
    final_results = []
    
    # 从原始图像中提取元数据
    original_duration = original_image.info.get('duration', 100)
    loop = original_image.info.get('loop', 0)

    for item in images_to_process:
        # 调整所有帧的尺寸
        processed_frames = [frame.resize((240, 240), Image.Resampling.LANCZOS) for frame in item['frames']]

        # 为服务器端存储生成一个唯一的文件名
        server_filename = f"{uuid.uuid4()}.gif"
        output_path = os.path.join(OUTPUT_DIR, server_filename)
        
        # Pillow在从RGBA帧保存为GIF时会自动处理调色板和透明度
        save_params = {
            'save_all': True,
            'append_images': processed_frames[1:],
            'duration': original_duration,
            'loop': loop,
            'optimize': False,
            'disposal': 2  # 对于透明GIF至关重要，指示渲染器在渲染下一帧前清除当前帧
        }

        processed_frames[0].save(output_path, **save_params)
        
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
        
        # 统一转换为RGBA处理，以正确保留透明度
        frames = [frame.convert('RGBA') for frame in ImageSequence.Iterator(img)]
        flipped_frames = [frame.transpose(Image.FLIP_LEFT_RIGHT) for frame in frames]
        
        duration = img.info.get('duration', 100)
        loop = img.info.get('loop', 0)
        
        save_params = {
            'save_all': True,
            'append_images': flipped_frames[1:],
            'duration': duration,
            'loop': loop,
            'optimize': False,
            'disposal': 2
        }
        
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
        
        duration = img.info.get('duration', 100)
        loop = img.info.get('loop', 0)
        
        save_params = {
            'save_all': True,
            'append_images': frames[1:],
            'duration': duration,
            'loop': loop,
            'optimize': False,
            'disposal': 2
        }
        
        frames[0].save(filepath, **save_params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RGB交换失败: {e}")

    return JSONResponse(content={"status": "success", "filename": filename})


# --- 运行服务器 ---
if __name__ == "__main__":
    import uvicorn
    print("服务器启动于 http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)