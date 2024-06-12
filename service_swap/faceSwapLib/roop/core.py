import os
from torchvision.transforms import functional
import sys

sys.modules["torchvision.transforms.functional_tensor"] = functional

from PIL import Image

# single thread doubles cuda performance - needs to be set before torch import
if any(arg.startswith('--execution-provider') for arg in sys.argv):
    os.environ['OMP_NUM_THREADS'] = '1'
# reduce tensorflow log level
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import warnings
from typing import List
import platform
import shutil
import onnxruntime
import tensorflow
import ffmpeg
import cv2
from faceSwapLib.roop import globals
from faceSwapLib.roop import metadata
from faceSwapLib.roop import ui
from faceSwapLib import roop
from faceSwapLib.roop.face_analyser import get_unique_faces_from_video, get_unique_faces_from_photos
from faceSwapLib.roop.predictor import predict_image, predict_video
from faceSwapLib.roop.processors.frame.core import get_frame_processors_modules
from faceSwapLib.roop.utilities import has_image_extension, is_image, is_video, detect_fps, create_video, \
                            extract_frames, get_temp_frame_paths, restore_audio, create_temp, \
                            move_temp, clean_temp, normalize_output_path, \
                            normalize_output_path_for_multiple

warnings.filterwarnings('ignore', category=FutureWarning, module='insightface')
warnings.filterwarnings('ignore', category=UserWarning, module='torchvision')


def encode_execution_providers(execution_providers: List[str]) -> List[str]:
    return [execution_provider.replace('ExecutionProvider', '').lower() for execution_provider in execution_providers]


def decode_execution_providers(execution_providers: List[str]) -> List[str]:
    return [provider for provider, encoded_execution_provider in zip(onnxruntime.get_available_providers(), encode_execution_providers(onnxruntime.get_available_providers()))
            if any(execution_provider in encoded_execution_provider for execution_provider in execution_providers)]


def suggest_execution_providers() -> List[str]:
    return encode_execution_providers(onnxruntime.get_available_providers())


def suggest_execution_threads() -> int:
    if 'CUDAExecutionProvider' in onnxruntime.get_available_providers():
        return 6
    return 1


def limit_resources() -> None:
    # prevent tensorflow memory leak
    gpus = tensorflow.config.experimental.list_physical_devices('GPU')
    for gpu in gpus:
        tensorflow.config.experimental.set_virtual_device_configuration(gpu, [
            tensorflow.config.experimental.VirtualDeviceConfiguration(memory_limit=1024)
        ])
    # limit memory usage
    if roop.globals.max_memory:
        memory = roop.globals.max_memory * 1024 ** 5
        if platform.system().lower() == 'darwin':
            memory = roop.globals.max_memory * 1024 ** 5
        if platform.system().lower() == 'windows':
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            kernel32.SetProcessWorkingSetSize(-1, ctypes.c_size_t(memory), ctypes.c_size_t(memory))
        else:
            import resource
            resource.setrlimit(resource.RLIMIT_DATA, (memory, memory))


def pre_check() -> bool:
    if sys.version_info < (3, 9):
        update_status('Python version is not supported - please upgrade to 3.9 or higher.')
        return False
    if not shutil.which('ffmpeg'):
        update_status('ffmpeg is not installed.')
        return False
    return True


def update_status(message: str, scope: str = 'ROOP.CORE') -> None:
    print(f'[{scope}] {message}')
    if not roop.globals.headless:
        ui.update_status(message)


def start() -> bool:
    for frame_processor in get_frame_processors_modules(roop.globals.frame_processors):
        if not frame_processor.pre_start():
            return False

    # process image to image
    if has_image_extension(roop.globals.target_path):
        if predict_image(roop.globals.target_path):
            destroy()
        shutil.copy2(roop.globals.target_path, roop.globals.output_path)
        # process frame
        for frame_processor in get_frame_processors_modules(roop.globals.frame_processors):
            update_status('Progressing...', frame_processor.NAME)
            frame_processor.process_image(roop.globals.source_path, roop.globals.output_path, roop.globals.output_path)
            frame_processor.post_process()
        # validate image
        if is_image(roop.globals.target_path):
            update_status('Processing to image succeed!')
            return True
        else:
            update_status('Processing to image failed!')
        return False

    # process image to videos
    if predict_video(roop.globals.target_path):
        destroy()
    update_status('Creating temporary resources...')
    create_temp(roop.globals.target_path)
    # extract frames
    if roop.globals.keep_fps:
        fps = detect_fps(roop.globals.target_path)
        update_status(f'Extracting frames with {fps} FPS...')
        extract_frames(roop.globals.target_path, fps)
    else:
        update_status('Extracting frames with 30 FPS...')
        extract_frames(roop.globals.target_path)

    # process frame
    temp_frame_paths = get_temp_frame_paths(roop.globals.target_path)
    if temp_frame_paths:
        for frame_processor in get_frame_processors_modules(roop.globals.frame_processors):
            update_status('Progressing...', frame_processor.NAME)
            frame_processor.process_video(roop.globals.source_path, temp_frame_paths)
            frame_processor.post_process()
    else:
        update_status('Frames not found...')
        return False

    # create video
    if roop.globals.keep_fps:
        fps = detect_fps(roop.globals.target_path)
        update_status(f'Creating video with {fps} FPS...')
        create_video(roop.globals.target_path, fps)
    else:
        update_status('Creating video with 30 FPS...')
        create_video(roop.globals.target_path)

    # handle audio
    if roop.globals.skip_audio:
        move_temp(roop.globals.target_path, roop.globals.output_path)
        update_status('Skipping audio...')
    else:
        if roop.globals.keep_fps:
            update_status('Restoring audio...')
        else:
            update_status('Restoring audio might cause issues as fps are not kept...')
        restore_audio(roop.globals.target_path, roop.globals.output_path)
    # clean temp
    update_status('Cleaning temporary resources...')
    clean_temp(roop.globals.target_path)
    # validate video
    if is_video(roop.globals.target_path):
        update_status('Processing to video succeed!')
        return True
    else:
        update_status('Processing to video failed!')
        return False


def destroy() -> None:
    if roop.globals.target_path:
        clean_temp(roop.globals.target_path)
    sys.exit()


def process_video_with_audio(original_video_path, watermark_path):
    filename = os.path.splitext(original_video_path)[0]
    processed_video_path = f"{filename}_watermark.mp4"

    # Process the video with watermark
    add_watermark(original_video_path, watermark_path, processed_video_path)

    print(f'add_water, {original_video_path} {watermark_path} {processed_video_path}')

    # Extract audio from original video and save in original format (AAC)
    try:
        temp_audio_path = f"{filename}_temp_audio.aac"
        ffmpeg.input(original_video_path).output(temp_audio_path, acodec='copy').run(overwrite_output=True)
        print('extracy audio')
        os.remove(original_video_path)

        if os.path.isfile(temp_audio_path):
            audio_stream = ffmpeg.input(temp_audio_path)
        else:
            audio_stream = ffmpeg.input('anullsrc=channel_layout=stereo:sample_rate=44100')

        # Merge audio with the processed video
        video_stream = ffmpeg.input(processed_video_path)
        print('merging ...')
        ffmpeg.output(video_stream, audio_stream, original_video_path, vcodec='copy', acodec='copy').run(overwrite_output=True)
        print('merged audio')
        # Cleanup the temporary audio file
        os.remove(temp_audio_path)
        os.remove(processed_video_path)

    except Exception as e:
        print(f"Warning: {e} - there is a problem")

        if os.path.isfile(temp_audio_path):
            os.remove(temp_audio_path)

        if os.path.isfile(original_video_path):
            os.remove(original_video_path)
            os.rename(processed_video_path, original_video_path)
    print("watermark done")
    return original_video_path



def add_watermark(video_path, watermark_path, output_path):
    # Load the video
    cap = cv2.VideoCapture(video_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    # Load the watermark image
    watermark = cv2.imread(watermark_path, cv2.IMREAD_UNCHANGED)  # Load with alpha channel
    watermark_h, watermark_w, watermark_channels = watermark.shape

    margin = 50  # Margin for watermark
    # Time each watermark position should last (in frames)
    time_per_position = int(3 * fps)  # 3 seconds
    positions = [(margin, margin),  # Top left
                 (frame_width - watermark_w - margin, margin),  # Top right
                 (frame_width - watermark_w - margin, frame_height - watermark_h - margin),  # Bottom right
                 (margin, frame_height - watermark_h - margin)]  # Bottom left
    position_index = 0

    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Calculate position for watermark
        if frame_count % time_per_position == 0:
            position_index = (position_index + 1) % len(positions)
        x, y = positions[position_index]

        # Handling the alpha channel for blending
        alpha_s = watermark[:, :, 3] / 255.0
        alpha_l = 1.0 - alpha_s

        for c in range(0, 3):
            frame[y:y + watermark_h, x:x + watermark_w, c] = (alpha_s * watermark[:, :, c] +
                                                              alpha_l * frame[y:y + watermark_h, x:x + watermark_w, c])

        # Write the frame
        out.write(frame)

        frame_count += 1

    # Release everything
    cap.release()
    out.release()
    cv2.destroyAllWindows()


def add_watermark_to_photo(input_image_path, watermark_image_path):
    position = (25, 25)
    original_image = Image.open(input_image_path)

    watermark = Image.open(watermark_image_path)

    original_width, original_height = original_image.size
    watermark_width, watermark_height = watermark.size

    # position = (position[0], original_height - watermark_height - position[1])

    original_image.paste(watermark, position, watermark)

    original_image.save(input_image_path)
    return input_image_path


def run(source_path: str,
        target_path: str,
        output_path: str,
        watermark_flag: bool,
        watermark_path: str,
        frame_processor: list[str] = ['face_swapper'],
        keep_fps: bool = True,
        keep_frames: bool = True,
        skip_audio: bool = False,
        many_faces: bool = True,
        max_memory: int = 5,
        reference_face_position: int = 0,
        reference_frame_number: int = 0,
        similar_face_distance: float = 0.85,
        temp_frame_format: str = 'png',
        temp_frame_quality: int = 0,
        output_video_encoder: str = 'libx264',
        output_video_quality: int = 35,
        execution_provider: list[str] = ['cpu'],
        is_it_image: bool = False) -> bool:

    try:
        roop.globals.source_path = source_path
        roop.globals.target_path = target_path
        roop.globals.output_path = normalize_output_path(roop.globals.source_path, roop.globals.target_path,
                                                         output_path)
        roop.globals.headless = roop.globals.source_path is not None and roop.globals.target_path is not None and roop.globals.output_path is not None
        roop.globals.frame_processors = frame_processor
        roop.globals.keep_fps = keep_fps
        roop.globals.keep_frames = keep_frames
        roop.globals.skip_audio = skip_audio
        roop.globals.many_faces = many_faces
        roop.globals.reference_face_position = reference_face_position
        roop.globals.reference_frame_number = reference_frame_number
        roop.globals.similar_face_distance = similar_face_distance
        roop.globals.temp_frame_format = temp_frame_format
        roop.globals.temp_frame_quality = temp_frame_quality
        roop.globals.output_video_encoder = output_video_encoder
        roop.globals.output_video_quality = output_video_quality
        roop.globals.max_memory = max_memory
        roop.globals.execution_providers = decode_execution_providers(execution_provider)
        roop.globals.execution_threads = suggest_execution_threads()

        if not pre_check():
            return False

        for frame_processor in get_frame_processors_modules(roop.globals.frame_processors):
            if not frame_processor.pre_check():
                return False
        limit_resources()
        
        result = start()

        if watermark_flag:
            if not is_it_image:
                process_video_with_audio(roop.globals.output_path,
                                         os.path.abspath(watermark_path))
            else:
                add_watermark_to_photo(roop.globals.output_path,
                                       os.path.abspath(watermark_path))

        return result  # if video successes -> True, else -> False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def get_referance_faces_from_source(source_path: str, output_path: str, process_every_n_th_frame:int = 6):
    if source_path.endswith('.mp4'):
        try:
            unique_faces, _ = get_unique_faces_from_video(source_path, every_n_th_frame=process_every_n_th_frame)
            for index, unique_face in enumerate(unique_faces):
                file_name = os.path.join(output_path, f'{str(index)}.png')
                cv2.imwrite(file_name, unique_face)
                print(f'Saved_image - {file_name}')
        except Exception as e:
            print(f"ERROR: {e}")
            return False
    elif source_path.endswith(('.png', '.jpg', '.jpeg')):
        try:
            unique_faces, _ = get_unique_faces_from_photos(source_path)
            for index, unique_face in enumerate(unique_faces):
                file_name = os.path.join(output_path, f'{str(index)}.png')
                cv2.imwrite(file_name, unique_face)
                print(f'Saved_image - {file_name}')
        except Exception as e:
            print(f"ERROR: {e}")
            return False
    else:
        print(f"ERROR: wrong files format")
        return False

def start_multiple() -> bool:
    for frame_processor in get_frame_processors_modules(roop.globals.frame_processors):
        if not frame_processor.pre_start_for_multiple():
            return False

    # process image to image
    if has_image_extension(roop.globals.target_path):
        if predict_image(roop.globals.target_path):
            destroy()
        shutil.copy2(roop.globals.target_path, roop.globals.output_path)
        # process frame
        for frame_processor in get_frame_processors_modules(roop.globals.frame_processors):
            update_status('Progressing...', frame_processor.NAME)
            frame_processor.process_image_multy_faces(roop.globals.source_path, roop.globals.output_path, roop.globals.output_path)
            frame_processor.post_process()
        # validate image
        if is_image(roop.globals.target_path):
            update_status('Processing to image succeed!')
            return True
        else:
            update_status('Processing to image failed!')
        return False

    # process image to videos
    if predict_video(roop.globals.target_path):
        destroy()
    update_status('Creating temporary resources...')
    create_temp(roop.globals.target_path)
    # extract frames
    if roop.globals.keep_fps:
        fps = detect_fps(roop.globals.target_path)
        update_status(f'Extracting frames with {fps} FPS...')
        extract_frames(roop.globals.target_path, fps)
    else:
        update_status('Extracting frames with 30 FPS...')
        extract_frames(roop.globals.target_path)

    # process frame
    temp_frame_paths = get_temp_frame_paths(roop.globals.target_path)
    if temp_frame_paths:
        for frame_processor in get_frame_processors_modules(roop.globals.frame_processors):
            update_status('Progressing...', frame_processor.NAME)
            frame_processor.process_video_multy_faces(roop.globals.source_path, temp_frame_paths)
            frame_processor.post_process()
    else:
        update_status('Frames not found...')
        return False

    # create video
    if roop.globals.keep_fps:
        fps = detect_fps(roop.globals.target_path)
        update_status(f'Creating video with {fps} FPS...')
        create_video(roop.globals.target_path, fps)
    else:
        update_status('Creating video with 30 FPS...')
        create_video(roop.globals.target_path)

    # handle audio
    if roop.globals.skip_audio:
        move_temp(roop.globals.target_path, roop.globals.output_path)
        update_status('Skipping audio...')
    else:
        if roop.globals.keep_fps:
            update_status('Restoring audio...')
        else:
            update_status('Restoring audio might cause issues as fps are not kept...')
        restore_audio(roop.globals.target_path, roop.globals.output_path)
    # clean temp
    update_status('Cleaning temporary resources...')
    clean_temp(roop.globals.target_path)
    # validate video
    if is_video(roop.globals.target_path):
        update_status('Processing to video succeed!')
        return True 
    else:
        update_status('Processing to video failed!')
        return False


def run_multiple(source_path: list[list[str]],
        target_path: str,
        output_path: str,
        watermark_flag: bool,
        watermark_path: str,
        frame_processor: list[str] = ['face_swapper'],
        keep_fps: bool = True,
        keep_frames: bool = True,
        skip_audio: bool = False,
        many_faces: bool = True,
        max_memory: int = 5,
        reference_face_position: int = 0,
        reference_frame_number: int = 0,
        similar_face_distance: float = 0.85,
        temp_frame_format: str = 'png',
        temp_frame_quality: int = 0,
        output_video_encoder: str = 'libx264',
        output_video_quality: int = 35,
        execution_provider: list[str] = ['cpu'],
        is_it_image: bool = True) -> bool:

    try:
        print('get variables')
        roop.globals.source_path = source_path
        roop.globals.target_path = target_path
        print('normalize')
        roop.globals.output_path = normalize_output_path_for_multiple(roop.globals.source_path, roop.globals.target_path, output_path)
        roop.globals.headless = roop.globals.source_path is not None and roop.globals.target_path is not None and roop.globals.output_path is not None
        roop.globals.frame_processors = frame_processor
        roop.globals.keep_fps = keep_fps
        roop.globals.keep_frames = keep_frames
        roop.globals.skip_audio = skip_audio
        roop.globals.many_faces = many_faces
        roop.globals.reference_face_position = reference_face_position
        roop.globals.reference_frame_number = reference_frame_number
        roop.globals.similar_face_distance = similar_face_distance
        roop.globals.temp_frame_format = temp_frame_format
        roop.globals.temp_frame_quality = temp_frame_quality
        roop.globals.output_video_encoder = output_video_encoder
        roop.globals.output_video_quality = output_video_quality
        roop.globals.max_memory = max_memory
        roop.globals.execution_providers = decode_execution_providers(execution_provider)
        roop.globals.execution_threads = suggest_execution_threads()
        print('varibles getted')
        if not pre_check():
            return False
        print('pre_check')
        for frame_processor in get_frame_processors_modules(roop.globals.frame_processors):
            if not frame_processor.pre_check():
                return False
        limit_resources()
        print('frame pre_check source - ', roop.globals.source_path)
        result = start_multiple()

        if watermark_flag:
            print('add watermark')
            if is_it_image:
                print('is image water')
                add_watermark_to_photo(roop.globals.output_path,
                                       os.path.abspath(watermark_path))
            else:
                print('is not image water')
                process_video_with_audio(roop.globals.output_path,
                                         os.path.abspath(watermark_path))
                
        return result  # if video successes -> True, else -> False
    except Exception as e:
        print(f"ERROR: {e}")
        return False