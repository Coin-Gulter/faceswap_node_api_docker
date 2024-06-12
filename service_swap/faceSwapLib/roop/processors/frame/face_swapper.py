from typing import Any, List, Callable
import cv2
import insightface
import threading
import os


from faceSwapLib.roop import globals
from faceSwapLib.roop.processors.frame import core
from faceSwapLib.roop.core import update_status
from faceSwapLib.roop.face_analyser import get_one_face, get_many_faces, find_similar_face, check_similar_face2face
from faceSwapLib.roop.face_reference import get_face_reference, set_face_reference, clear_face_reference
from faceSwapLib.roop.typin import Face, Frame
from faceSwapLib.roop.utilities import conditional_download, resolve_relative_path, is_image, is_video

FACE_SWAPPER = None
THREAD_LOCK = threading.Lock()
NAME = 'ROOP.FACE-SWAPPER'


def get_face_swapper() -> Any:
    global FACE_SWAPPER

    with THREAD_LOCK:
        if FACE_SWAPPER is None:
            model_path = resolve_relative_path('../models/inswapper_128.onnx')
            FACE_SWAPPER = insightface.model_zoo.get_model(model_path, providers=globals.execution_providers)
    return FACE_SWAPPER


def clear_face_swapper() -> None:
    global FACE_SWAPPER

    FACE_SWAPPER = None


def pre_check() -> bool:
    download_directory_path = resolve_relative_path('../models')
    conditional_download(download_directory_path, ['https://huggingface.co/CountFloyd/deepfake/resolve/main/inswapper_128.onnx'])
    return True


def pre_start() -> bool:
    if not is_image(globals.source_path):
        update_status('Select an image for source path.', NAME)
        return False
    elif not get_one_face(cv2.imread(globals.source_path)):
        update_status('No face in source path detected.', NAME)
        return False
    if not is_image(globals.target_path) and not is_video(globals.target_path):
        update_status('Select an image or video for target path.', NAME)
        return False
    return True

def pre_start_for_multiple() -> bool:
    print('source - ', globals.source_path)
    if (not any([is_image(path[0]) for path in globals.source_path])) or \
        (not any([is_image(path[1]) for path in globals.source_path])):

        update_status('Select an image for source path.', NAME)
        return False
    
    elif (not any([get_one_face(cv2.imread(path[0])) for path in globals.source_path])) or \
            (not any([get_one_face(cv2.imread(path[1])) for path in globals.source_path])):

        update_status('No face in source pathes detected.', NAME)
        return False
    
    if not is_image(globals.target_path) and not is_video(globals.target_path):
        update_status('Select an image or video for target path.', NAME)
        return False
    return True


def post_process() -> None:
    clear_face_swapper()
    clear_face_reference()


def swap_face(source_face: Face, target_face: Face, temp_frame: Frame) -> Frame:
    return get_face_swapper().get(temp_frame, target_face, source_face, paste_back=True)


def process_frame(source_face: Face, reference_face: Face, temp_frame: Frame) -> Frame:
    if globals.many_faces:
        many_faces = get_many_faces(temp_frame)
        if many_faces:
            for target_face in many_faces:
                temp_frame = swap_face(source_face, target_face, temp_frame)
    else:
        target_face = find_similar_face(temp_frame, reference_face)
        if target_face:
            temp_frame = swap_face(source_face, target_face, temp_frame)
    return temp_frame


def process_frames(source_path: str, temp_frame_paths: List[str], update: Callable[[], None]) -> None:
    source_face = get_one_face(cv2.imread(source_path))
    reference_face = None if globals.many_faces else get_face_reference()
    for temp_frame_path in temp_frame_paths:
        temp_frame = cv2.imread(temp_frame_path)
        result = process_frame(source_face, reference_face, temp_frame)
        cv2.imwrite(temp_frame_path, result)
        if update:
            update()

def process_image(source_path: str, target_path: str, output_path: str) -> None:
    source_face = get_one_face(cv2.imread(source_path))
    target_frame = cv2.imread(target_path)
    reference_face = None if globals.many_faces else get_one_face(target_frame, globals.reference_face_position)
    result = process_frame(source_face, reference_face, target_frame)
    cv2.imwrite(output_path, result)


def process_video(source_path: str, temp_frame_paths: List[str]) -> None:
    if not globals.many_faces and not get_face_reference():
        reference_frame = cv2.imread(temp_frame_paths[globals.reference_frame_number])
        reference_face = get_one_face(reference_frame, globals.reference_face_position)
        set_face_reference(reference_face)
    core.process_video(source_path, temp_frame_paths, process_frames)


def process_frame_similar_face(source_faces: list[list[Face]], temp_frame: Frame) -> Frame:
    many_faces = get_many_faces(temp_frame)

    for face in many_faces:
        for source_face in source_faces:
            if check_similar_face2face(face.embedding, source_face[0].embedding, 0.5):
                temp_frame = swap_face(source_face[1], face, temp_frame)
                continue

    return temp_frame

def process_frames_multy_faces(source_pathes: list[list[str]], temp_frame_paths: List[str], update: Callable[[], None]) -> None:
    source_faces = []
    for source_path in source_pathes:
        face_pair = []
        face_pair.append(get_one_face(cv2.imread(source_path[0])))
        face_pair.append(get_one_face(cv2.imread(source_path[1])))
        source_faces.append(face_pair)

    for temp_frame_path in temp_frame_paths:
        temp_frame = cv2.imread(temp_frame_path)
        result = process_frame_similar_face(source_faces, temp_frame)
        cv2.imwrite(temp_frame_path, result)
        if update:
            update()

def process_image_multy_faces(source_pathes: list[list[list[str]]], target_path: str, output_path: str) -> None:
    source_faces = []
    for source_path in source_pathes:
        face_pair = []
        face_pair.append(get_one_face(cv2.imread(source_path[0])))
        face_pair.append(get_one_face(cv2.imread(source_path[1])))
        source_faces.append(face_pair)

    target_frame = cv2.imread(target_path)
    result = process_frame_similar_face(source_faces, target_frame)
    cv2.imwrite(output_path, result)

def process_video_multy_faces(source_pathes: list[list[list[str]]], temp_frame_paths: List[str]) -> None:
    if not globals.many_faces and not get_face_reference():
        reference_frame = cv2.imread(temp_frame_paths[globals.reference_frame_number])
        reference_face = get_one_face(reference_frame, globals.reference_face_position)
        set_face_reference(reference_face)
    core.process_video(source_pathes, temp_frame_paths, process_frames_multy_faces)

