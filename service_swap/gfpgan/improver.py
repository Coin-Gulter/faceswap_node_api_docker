import argparse
import cv2
import glob
import numpy as np
import os
import torch
from basicsr.utils import imwrite

from gfpgan.GFPGAN.utils import GFPGANer


def main():
    """Interface demo for GFPGAN (for users).
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, default='input/', help='Input image or folder. Default: input/')
    parser.add_argument('-o', '--output', type=str, default='result/', help='Output folder. Default: result/')
    # we use version to select models, which is more user-friendly
    parser.add_argument('-v', '--version', type=str, default='1.3', help='GFPGAN model version. Option: 1 | 1.2 | 1.3. Default: 1.3')
    parser.add_argument('-s', '--upscale', type=int, default=1, help='The final upsampling scale of the image. Default: 1')

    parser.add_argument('--bg_upsampler', type=str, default='realesrgan', help='background upsampler. Default: realesrgan')
    parser.add_argument('--bg_tile', type=int, default=800, help='Tile size for background sampler, 0 for no tile during testing. Default: 800')
    parser.add_argument('--only_center_face', action='store_true', help='Only restore the center face')
    parser.add_argument('--aligned', action='store_true', help='Input are aligned faces')
    parser.add_argument('--extention', type=str, default='auto', help='Image extension. Options: auto | jpg | png, auto means using the same extension as inputs. Default: auto')

    args = parser.parse_args()

    improve(args.input,
            args.output,
            args.version,
            args.upscale,
            args.bg_upsampler,
            args.bg_tile,
            args.only_center_face,
            args.aligned,
            args.extention,)


def improve(input:str="input/" , output:str="result/", version:str="1.3", upscale:int=1, bg_upsampler="realesrgan", bg_tile:int=0, only_center_face:bool=False, aligned:bool=False, extention:str="auto"):


    # ------------------------ input & output ------------------------
    try:
        if input.endswith('/'):
            input = input[:-1]
        
        if os.path.isfile(input):
            img_list = [input]
        else:
            img_list = sorted(glob.glob(os.path.join(input, '*')))

        if output.endswith('/'):
            os.makedirs(output, exist_ok=True)
    except Exception as e:
        print(f"Error: can't get files to proccess because of - {e}")

    # ------------------------ set up background upsampler ------------------------
    try:
        if bg_upsampler == 'realesrgan':

            if not torch.cuda.is_available():  # CPU
                proccesor_half = False
            else:
                proccesor_half = True
                torch.backends.cudnn.benchmark = False  # Disabling cudnn heuristics might help (optional)


            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
            bg_upsampler = RealESRGANer(
                scale=2,
                model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
                model=model,
                tile=bg_tile,
                tile_pad=10,
                pre_pad=0,
                half=proccesor_half)  # need to set False in CPU mode and True in GPU mode
        else:
            bg_upsampler = None
    except Exception as e:
        print(f"Error: can't set up background upsampler because of - {e}")

    # ------------------------ set up GFPGAN restorer ------------------------
    try:
        if version == '1':
            arch = 'original'
            channel_multiplier = 1
            model_name = 'GFPGANv1'
            url = 'https://github.com/TencentARC/GFPGAN/releases/download/v0.1.0/GFPGANv1.pth'
        elif version == '1.2':
            arch = 'clean'
            channel_multiplier = 2
            model_name = 'GFPGANCleanv1-NoCE-C2'
            url = 'https://github.com/TencentARC/GFPGAN/releases/download/v0.2.0/GFPGANCleanv1-NoCE-C2.pth'
        elif version == '1.3':
            arch = 'clean'
            channel_multiplier = 2
            model_name = 'GFPGANv1.3'
            url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth'
        elif version == '1.4':
            arch = 'clean'
            channel_multiplier = 2
            model_name = 'GFPGANv1.4'
            url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth'
        elif version == 'RestoreFormer':
            arch = 'RestoreFormer'
            channel_multiplier = 2
            model_name = 'RestoreFormer'
            url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/RestoreFormer.pth'
        else:
            raise ValueError(f'Wrong model version {version}.')
    except ValueError:
        print(f"Error: can't set up GPFGAN network because of wrong version - {e}")
    except Exception as e:
        print(f"Error: can't set up GPFGAN network because of - {e}")

    # determine model paths
    try:
        model_path = os.path.join('GFPGAN/weights', model_name + '.pth')
        if not os.path.isfile(model_path):
            # download pre-trained models from url
            model_path = url

        restorer = GFPGANer(
            model_path=model_path,
            upscale=upscale,
            arch=arch,
            channel_multiplier=channel_multiplier,
            bg_upsampler=bg_upsampler)
    except Exception as e:
        print(f"Error: can't get weights for GPFGAN network because of - {e}")

    # ------------------------ restore ------------------------
    # try:
    for img_path in img_list:
        # read image
        img_name = os.path.basename(img_path)
        print(f'Processing {img_name} ...')
        basename, ext = os.path.splitext(img_name)
        input_img = cv2.imread(img_path, cv2.IMREAD_COLOR)

        # restore faces and background if necessary
        _, _, restored_img = restorer.enhance(
            input_img,
            has_aligned=aligned,
            only_center_face=only_center_face,
            paste_back=True,
            weight=0.5)

        # save restored img
        if restored_img is not None:
            if extention == 'auto':
                extension = ext[1:]

            if output.endswith('/'):
                save_restore_path = os.path.join(output, f'{basename}.{extension}')
                imwrite(restored_img, save_restore_path)
                print(f'Results are in the [{save_restore_path}] file.')
            else:
                imwrite(restored_img, output)
                print(f'Results are in the [{output}] file.')

    torch.cuda.empty_cache() 

    # except Exception as e:
        # print(f"Error: can't procces and restore photos because of - {e}")



if __name__=="__main__":

    main()
