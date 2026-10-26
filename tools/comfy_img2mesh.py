"""Image to 3D mesh with Hunyuan3D 2.1 through a running ComfyUI (geometry only, no texture).

    python tools/comfy_img2mesh.py <image in ComfyUI/input> <out.glb> [seed] [octree_resolution]
"""
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

SERVER = 'http://127.0.0.1:8188'
COMFY = Path('/Users/buivanthien/Learn/CSAI/ComfyUI')


def graph(image, seed, octree):
    return {
        '1': {'class_type': 'ImageOnlyCheckpointLoader', 'inputs': {'ckpt_name': 'hunyuan_3d_v2.1.safetensors'}},
        '2': {'class_type': 'LoadImage', 'inputs': {'image': image}},
        '3': {'class_type': 'CLIPVisionEncode', 'inputs': {'clip_vision': ['1', 1], 'image': ['2', 0], 'crop': 'center'}},
        '4': {'class_type': 'Hunyuan3Dv2Conditioning', 'inputs': {'clip_vision_output': ['3', 0]}},
        '5': {'class_type': 'EmptyLatentHunyuan3Dv2', 'inputs': {'resolution': 4096, 'batch_size': 1}},
        '6': {'class_type': 'ModelSamplingAuraFlow', 'inputs': {'model': ['1', 0], 'shift': 1.0}},
        '7': {'class_type': 'KSampler', 'inputs': {
            'model': ['6', 0], 'positive': ['4', 0], 'negative': ['4', 1], 'latent_image': ['5', 0],
            'seed': seed, 'steps': 30, 'cfg': 5.0, 'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1.0}},
        '8': {'class_type': 'VAEDecodeHunyuan3D', 'inputs': {'samples': ['7', 0], 'vae': ['1', 2],
                                                             'num_chunks': 8000, 'octree_resolution': octree}},
        '9': {'class_type': 'VoxelToMesh', 'inputs': {'voxel': ['8', 0], 'algorithm': 'surface net', 'threshold': 0.6}},
        '10': {'class_type': 'SaveGLB', 'inputs': {'mesh': ['9', 0], 'filename_prefix': 'mesh/bloxorz'}},
    }


def call(path, data=None):
    req = urllib.request.Request(SERVER + path, data=json.dumps(data).encode() if data else None,
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req))


def main():
    image, out = sys.argv[1], Path(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    octree = int(sys.argv[4]) if len(sys.argv) > 4 else 256
    pid = call('/prompt', {'prompt': graph(image, seed, octree)})['prompt_id']
    while pid not in (hist := call('/history/' + pid)):
        time.sleep(3)
    entry = hist[pid]
    if entry.get('status', {}).get('status_str') == 'error':
        sys.exit('ComfyUI error: ' + json.dumps(entry['status'])[:800])
    files = [f for node in entry['outputs'].values() for key in ('3d', 'meshes', 'files', 'images')
             for f in node.get(key, [])]
    src = next((COMFY / 'output' / f.get('subfolder', '') / f['filename'] for f in files
                if f['filename'].endswith('.glb')), None)
    if src is None:                                   # fall back to the newest glb ComfyUI wrote
        src = max((COMFY / 'output' / 'mesh').glob('*.glb'), key=lambda p: p.stat().st_mtime)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, out)
    print('saved', out)


if __name__ == '__main__':
    main()
