from PIL import Image

def process_gif(image_paths, output_path, duration=500, match_size=True, crops=None):
    """
    image_paths: list of paths
    crops: optional list of (left, top, right, bottom) tuples
    """
    frames = []
    
    # Base size for Auto-mode
    first_img = Image.open(image_paths[0])
    target_size = first_img.size

    for i, path in enumerate(image_paths):
        img = Image.open(path).convert("RGBA")
        
        # If manual crops provided
        if crops and i < len(crops):
            img = img.crop(crops[i])
        
        # If auto-mode or if images still don't match size after crop
        if match_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)
            
        frames.append(img)

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        optimize=True
    )