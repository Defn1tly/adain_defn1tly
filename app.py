import io
import os
import uuid
import time
import asyncio
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from torchvision import transforms
from torchvision.utils import save_image
import base64

import net
from function import adaptive_instance_normalization, coral

app = FastAPI(title="AdaIN Style Transfer", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

Path("models").mkdir(exist_ok=True)
Path("uploads").mkdir(exist_ok=True)
Path("outputs").mkdir(exist_ok=True)

device = torch.device("cpu")
vgg = None
decoder = None
model_loaded = False

semaphore = asyncio.Semaphore(1)

def load_model():
    global vgg, decoder, model_loaded
    
    print(f"Loading model on {device}...")
    
    decoder = net.decoder
    vgg = net.vgg
    
    decoder_path = "models/decoder.pth"
    vgg_path = "models/vgg_normalised.pth"
    
    if not os.path.exists(decoder_path) or not os.path.exists(vgg_path):
        print(f"Model weights not found in models/ folder")
        return False
    
    decoder.load_state_dict(torch.load(decoder_path, map_location=device))
    vgg.load_state_dict(torch.load(vgg_path, map_location=device))
    
    vgg = nn.Sequential(*list(vgg.children())[:31])
    
    decoder.to(device)
    vgg.to(device)
    
    decoder.eval()
    vgg.eval()
    
    model_loaded = True
    print(f"Model loaded on {device}")
    return True

def test_transform(size, crop=False):
    transform_list = []
    if size != 0:
        transform_list.append(transforms.Resize(size))
    if crop:
        transform_list.append(transforms.CenterCrop(size))
    transform_list.append(transforms.ToTensor())
    transform = transforms.Compose(transform_list)
    return transform

def style_transfer(content_img, style_img, alpha=1.0, 
                   preserve_color=False, content_size=0, style_size=0, crop=False):
    
    content_tf = test_transform(content_size, crop)
    style_tf = test_transform(style_size, crop)
    
    content_tensor = content_tf(content_img).unsqueeze(0).to(device)
    style_tensor = style_tf(style_img).unsqueeze(0).to(device)
    
    if preserve_color:
        style_tensor = coral(style_tensor.squeeze(0), content_tensor.squeeze(0)).unsqueeze(0)
    
    with torch.no_grad():
        content_feat = vgg(content_tensor)
        style_feat = vgg(style_tensor)
        
        feat = adaptive_instance_normalization(content_feat, style_feat)
        feat = feat * alpha + content_feat * (1 - alpha)
        
        output = decoder(feat)
    
    return output.cpu()

@app.on_event("startup")
async def startup_event():
    load_model()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "model_loaded": model_loaded,
        "version": int(time.time())
    })

@app.post("/upload_and_stylize")
async def upload_and_stylize(
    request: Request,
    background_tasks: BackgroundTasks,
    content_image: UploadFile = File(...),
    style_image: UploadFile = File(...),
    alpha: float = Form(1.0),
    preserve_color: bool = Form(False),
    content_size: int = Form(0),
    style_size: int = Form(0),
    crop: bool = Form(False)
):
    
    if not model_loaded:
        return JSONResponse(
            status_code=500,
            content={"error": "Model not loaded"}
        )
    
    async with semaphore:
        try:
            tic = time.time()
            if await request.is_disconnected():
                print(" Клиент отвалился до начала обработки")
                return JSONResponse(
                    status_code=499,
                    content={"error": "Client disconnected before processing"}
                )
            
            content_data = await content_image.read()
            style_data = await style_image.read()
            
            content_img = Image.open(io.BytesIO(content_data)).convert('RGB')
            style_img = Image.open(io.BytesIO(style_data)).convert('RGB')
            
            output_tensor = await asyncio.to_thread(
                style_transfer,
                content_img, style_img,
                alpha=alpha,
                preserve_color=preserve_color,
                content_size=content_size,
                style_size=style_size,
                crop=crop
            )
            
            elapsed_time = time.time() - tic
            print(f"Elapsed time: {elapsed_time:.4f} seconds")
            
            output_id = str(uuid.uuid4())
            output_path = f"outputs/{output_id}.jpg"
            save_image(output_tensor, output_path)
            
            if content_size > 0 or style_size > 0:
                content_tf = test_transform(content_size, crop)
                style_tf = test_transform(style_size, crop)
                content_display = transforms.ToPILImage()(content_tf(content_img))
                style_display = transforms.ToPILImage()(style_tf(style_img))
            else:
                content_display = content_img
                style_display = style_img
            
            content_path = f"uploads/{output_id}_content.jpg"
            style_path = f"uploads/{output_id}_style.jpg"
            content_display.save(content_path, "JPEG", quality=95)
            style_display.save(style_path, "JPEG", quality=95)
            
            with open(content_path, "rb") as f:
                content_base64 = base64.b64encode(f.read()).decode('utf-8')
            with open(style_path, "rb") as f:
                style_base64 = base64.b64encode(f.read()).decode('utf-8')
            with open(output_path, "rb") as f:
                output_base64 = base64.b64encode(f.read()).decode('utf-8')

            background_tasks.add_task(os.remove, content_path)
            background_tasks.add_task(os.remove, style_path)
            background_tasks.add_task(os.remove, output_path)
            
            return JSONResponse({
                "success": True,
                "content_image": f"data:image/jpeg;base64,{content_base64}",
                "style_image": f"data:image/jpeg;base64,{style_base64}",
                "output_image": f"data:image/jpeg;base64,{output_base64}",
                "elapsed_time": f"{elapsed_time:.4f}",
                "output_size": list(output_tensor.shape)
            })
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": model_loaded,
        "device": str(device),
        "queue": "locked" if semaphore.locked() else "free"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
