"""
Chained video generation experiment.
3 scenes, each 3s. Last frame of scene N = first frame of scene N+1.
Concatenated into one 9s video.
"""
import asyncio
import subprocess
import os
import requests
import fal_client

FAL_KEY = "6a928c28-2fa4-4b73-8761-418508ee0428:0fc46b589df4b29cd2482b69279b7cff"
os.environ["FAL_KEY"] = FAL_KEY

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Config ---

START_IMAGE = "https://v3b.fal.media/files/b/0a8e783c/Vh9bbFex9d4ociCslQwGh_3j8jKVaj.jpg"

VIDEO_MODEL = "fal-ai/kling-video/v3/standard/image-to-video"
DURATION = "3"
ASPECT_RATIO = "9:16"

SCENES = [
    {
        "name": "scene1_sagittarius",
        "prompt": (
            "Subject: abstract colored ink clouds on black background\n"
            "Motion: ink tendrils pull together toward center, swirling and condensing into the shape of a centaur archer drawing a bow — Sagittarius symbol forms from the ink\n"
            "Camera: static\n"
            "Speed: medium\n"
            "Details: purple and teal ink strands weave together, small droplets drift outward as shape solidifies\n"
            "Continuity: maintain pure black background, preserve ink colors and fluid texture"
        ),
    },
    {
        "name": "scene2_virgo",
        "prompt": (
            "Subject: Sagittarius symbol formed from colored ink on black background\n"
            "Motion: Sagittarius shape dissolves back into abstract ink swirls, ink changes color and reforms into a maiden silhouette — Virgo symbol emerges from the ink\n"
            "Camera: slow push-in\n"
            "Speed: medium\n"
            "Details: color shifts from purple-teal to warm gold-rose as new symbol forms, ink particles scatter during transition\n"
            "Continuity: maintain pure black background, smooth color transition, no flickering"
        ),
    },
    {
        "name": "scene3_heart_fire",
        "prompt": (
            "Subject: Virgo symbol formed from colored ink on black background\n"
            "Motion: Virgo shape breaks apart into swirling ink, both ink colors merge and ignite into a bright flaming heart shape — fire burns vividly\n"
            "Camera: slow pull-out\n"
            "Speed: fast\n"
            "Details: flame flickers with orange and red hues, embers and sparks drift upward, ink remnants dissolve into the fire\n"
            "Continuity: maintain pure black background, fire should feel organic not CG, preserve warmth of colors"
        ),
    },
]


# --- Functions ---

async def generate_video(image_url: str, prompt: str) -> str:
    """Submit and wait for video generation, return video URL."""
    handler = await fal_client.submit_async(
        VIDEO_MODEL,
        arguments={
            "prompt": prompt,
            "image_url": image_url,
            "duration": DURATION,
            "aspect_ratio": ASPECT_RATIO,
            "negative_prompt": "text, watermark, logo, blurry, low quality",
        },
    )
    request_id = handler.request_id
    print(f"  Submitted: {request_id}")

    # Poll until done
    while True:
        status = await fal_client.status_async(VIDEO_MODEL, request_id, with_logs=False)
        status_class = type(status).__name__
        print(f"  [{request_id[:8]}] {status_class}")

        if status_class == "Completed":
            result = await fal_client.result_async(VIDEO_MODEL, request_id)
            return result["video"]["url"]
        elif status_class in ["Failed", "Error"]:
            raise RuntimeError(f"Generation failed: {status}")

        await asyncio.sleep(10)


def download(url: str, path: str):
    """Download file."""
    resp = requests.get(url, stream=True)
    with open(path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    print(f"  Downloaded: {path} ({os.path.getsize(path) // 1024}KB)")


def extract_last_frame(video_path: str, output_path: str):
    """Extract last frame from video using ffmpeg."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True,
    )
    duration = float(result.stdout.strip())
    subprocess.run(
        ["ffmpeg", "-y", "-sseof", "-0.1", "-i", video_path,
         "-frames:v", "1", "-q:v", "2", output_path],
        capture_output=True, check=True,
    )
    print(f"  Last frame: {output_path} (from {duration:.1f}s video)")


async def upload_image(path: str) -> str:
    """Upload image to fal.ai storage."""
    url = await fal_client.upload_file_async(path)
    print(f"  Uploaded: {url[:60]}...")
    return url


def concatenate_videos(video_paths: list, output_path: str):
    """Concatenate videos using ffmpeg."""
    list_file = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(list_file, "w") as f:
        for p in video_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
         "-c", "copy", output_path],
        capture_output=True, check=True,
    )
    print(f"\nFinal video: {output_path} ({os.path.getsize(output_path) // 1024}KB)")


# --- Main ---

async def main():
    print("=== Chained Video Generation ===\n")

    current_image = START_IMAGE
    video_paths = []

    for i, scene in enumerate(SCENES):
        print(f"\n--- Scene {i + 1}: {scene['name']} ---")
        print(f"  Input image: {current_image[:60]}...")
        print(f"  Prompt: {scene['prompt'][:80]}...")

        # Generate video
        video_url = await generate_video(current_image, scene["prompt"])
        print(f"  Video URL: {video_url}")

        # Download video
        video_path = os.path.join(OUTPUT_DIR, f"{scene['name']}.mp4")
        download(video_url, video_path)
        video_paths.append(video_path)

        # Extract last frame for next scene (except last scene)
        if i < len(SCENES) - 1:
            frame_path = os.path.join(OUTPUT_DIR, f"{scene['name']}_last_frame.jpg")
            extract_last_frame(video_path, frame_path)

            # Upload frame for next scene
            print("  Uploading last frame...")
            current_image = await upload_image(frame_path)

    # Concatenate
    print("\n--- Concatenating ---")
    final_path = os.path.join(OUTPUT_DIR, "final_9s.mp4")
    concatenate_videos(video_paths, final_path)

    print("\n=== Done ===")
    print(f"Individual scenes: {OUTPUT_DIR}/scene*.mp4")
    print(f"Final video: {final_path}")


if __name__ == "__main__":
    asyncio.run(main())
