import threading
from typing import Any, Optional, List
import insightface
import numpy
import cv2
import numpy as np
from sklearn.metrics.pairwise import cosine_distances

from faceSwapLib import roop
from faceSwapLib.roop import globals
from faceSwapLib.roop.typin import Frame, Face
from faceSwapLib.roop.utilities import printProgressBar, extract_face_using_bbox

FACE_ANALYSER = None
THREAD_LOCK = threading.Lock()


def get_face_analyser() -> Any:
    global FACE_ANALYSER

    with THREAD_LOCK:
        if FACE_ANALYSER is None:
            FACE_ANALYSER = insightface.app.FaceAnalysis(name='buffalo_l', providers=roop.globals.execution_providers)
            FACE_ANALYSER.prepare(ctx_id=0)
    return FACE_ANALYSER


def clear_face_analyser() -> Any:
    global FACE_ANALYSER

    FACE_ANALYSER = None


def get_one_face(frame: Frame, position: int = 0) -> Optional[Face]:
    many_faces = get_many_faces(frame)
    if many_faces:
        try:
            return many_faces[position]
        except IndexError:
            return many_faces[-1]
    return None


def get_many_faces(frame: Frame) -> Optional[List[Face]]:
    try:
        return get_face_analyser().get(frame)
    except ValueError:
        return None


def find_similar_face(frame: Frame, reference_face: Face) -> Optional[Face]:
    many_faces = get_many_faces(frame)
    if many_faces:
        for face in many_faces:
            if hasattr(face, 'normed_embedding') and hasattr(reference_face, 'normed_embedding'):
                distance = numpy.sum(numpy.square(face.normed_embedding - reference_face.normed_embedding))
                if distance < roop.globals.similar_face_distance:
                    return face
    return None

def check_similar_face2face(face: Face, reference_face: Face, similar_face_distance=0.5) -> Optional[Face]:
    face = face.reshape(1, -1)
    reference_face = reference_face.reshape(1, -1)
    distance = cosine_distances(face, reference_face)
    if distance < similar_face_distance:
        return True
    return None

def get_unique_faces_from_video(path2target_video: str, every_n_th_frame=5) -> List[Face]:
    video = cv2.VideoCapture(path2target_video)
    unique_faces = []
    seen_faces = []
    number = 0

    # Get the total number of frames in the video
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

    # Initial call to print 0% progress
    printProgressBar(0, total_frames, prefix = 'Progress:', suffix = 'Complete', length = 20)

    while video.isOpened():
        ret, frame = video.read()
        number += 1

        if not ret:
            break

        # Update Progress Bar
        printProgressBar(number, total_frames, prefix = 'Progress:', suffix = 'Complete', length = 20)

        # Skip frames that are not multiples of 5
        if number % every_n_th_frame != 0:
            continue

        faces = get_many_faces(frame)

        if faces:
            for face in faces:
                embedding = face.embedding
                face_img = extract_face_using_bbox(face, frame)

                if len(unique_faces)==0:
                    unique_faces.append(face_img)
                    seen_faces.append(embedding)

                else:
                    if not any([check_similar_face2face(embedding, seen_face, 0.6) for seen_face in seen_faces]):
                        unique_faces.append(face_img)
                        seen_faces.append(embedding)


    video.release()
    return (unique_faces, seen_faces)


def get_unique_faces_from_photos(path_to_photo: str):

    unique_faces = []
    seen_faces = []

    img = cv2.imread(path_to_photo)

    faces = get_many_faces(img)

    if faces:
        for face in faces:
            embedding = face.embedding
            face_img = extract_face_using_bbox(face, img)

            if len(unique_faces)==0:
                unique_faces.append(face_img)
                seen_faces.append(embedding)
            else:
                if not any([check_similar_face2face(embedding, seen_face, 0.6) for seen_face in seen_faces]):
                    unique_faces.append(face_img)
                    seen_faces.append(embedding)


    return (unique_faces, seen_faces)
