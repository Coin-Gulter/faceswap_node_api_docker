import base64
import json
import os
import time
import insightface
import asyncio
import shutil
import io
import re
import numpy as np
import cv2 as cv
from PIL import Image
from utilities import utils
from node import settings
from rest_framework.decorators import api_view
from rest_framework import response, status
from utilities.task_manage import TaskManager
from utilities.cdn_manager import CDN
from .models import facetemplateApp2, templateApp2, taskApp2
from .serializer import facetemplateApp2Serializer, templateApp2Serializer, taskApp2Serializer, categoryToTemplateApp2Serializer

TASK_MANAGER = TaskManager(settings.REBBIT)
CDN_TEMPLATE_UPLOAD = CDN(settings.CDN_TEMPLATE_UPLOAD_PATH)


async def write_files(data, decode_img_path):
        base64_png = "iVBORw0KGg"
        basee64_jpg = "/9j/4"

        from_face_path = f"{decode_img_path + 'from_face/'}"
        to_face_path = f"{decode_img_path + 'to_face/'}"

        os.mkdir(decode_img_path)
        os.mkdir(from_face_path)
        os.mkdir(to_face_path)

        # Validate base64 encoding of face images
        for number, face in enumerate(data['faceFrom']):
            if face.startswith(base64_png):
                file_extension = '.png'
            elif face.startswith(basee64_jpg):
                file_extension = '.jpg'
            else:
                file_extension = '.jpg'

            decoded_data = base64.b64decode(face)
            file_name = f"{from_face_path + str(number) + file_extension}"
            with open(file_name, 'wb') as f:
                f.write(decoded_data)


        for number, face in enumerate(data['faceTo']):
            if face.startswith(base64_png):
                file_extension = '.png'
            elif face.startswith(basee64_jpg):
                file_extension = '.jpg'
            else:
                file_extension = '.jpg'

            decoded_data = base64.b64decode(face)
            file_name = f"{to_face_path + str(number) + file_extension}"
            with open(file_name, 'wb') as f:
                f.write(decoded_data)
                

@api_view(['POST'])
async def post_face_swap(request):

    task_id = utils.generate_unique_task_id(taskApp2)

    decode_img_path = f"{settings.DATA_PATH + settings.IMAGES_PATH + task_id + '/'}" 
    img_model_path = f"{settings.IMAGES_PATH + task_id + '/'}" 

    try:
        data = json.loads(request.body)  # Ensure data is JSON

        # Validate required fields and data types
        required_fields = ['template_id', 'faceFrom', 'faceTo']
        for field in required_fields:
            if field not in data or not isinstance(data[field], (int, str, list)):
                return response.Response(
                    {'error': f"Missing or invalid field: {field}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        await write_files(data, decode_img_path)

        # Add task to rebbit queue to perform face swapping
        try:
            job_status = 'in_queue'
            server = request.get_host()
            template_id = data['template_id']

            template_app_obj = templateApp2.objects.get(id=template_id)
            template_app_serizalizer = templateApp2Serializer(template_app_obj)

            source = template_app_serizalizer.data['source']
            
            action_type = "swap"
            timer = int(time.time())
            
            try:
                watermark = data['watermark']
            except:
                watermark = True

            file_name = os.path.basename(source)
            source_extension = str(os.path.splitext(file_name)[1])
            template_cdn_id = str(os.path.splitext(file_name)[0])

            try:
                is_image = True if source_extension in ('.png', '.jpg', '.jpeg') else False
            except:
                is_image = True

            try:
                new = data['new']
            except:
                new = True

            try:
                premium = data['premium']
            except:
                premium = False

            model_data = {'task_id': task_id,'status':job_status,'server':server,
                          'template_id':template_cdn_id,'watermark':watermark,
                          'is_image': is_image,'new':new, 'decoded_image':img_model_path,
                          'timer': timer, 'source': source, 'premium':premium}
                        
            task_publish_data = {
                "task_id": task_id,
                "template_id": template_cdn_id,
                "action_type": action_type,
                "decoded_image": decode_img_path,
                "watermark": watermark,
                "timer": timer,
                "new": new,
                "is_image": is_image,
                "source_extension": source_extension
            }

            serialized_task = taskApp2Serializer(data=model_data)

            if serialized_task.is_valid():
                serialized_task.save()
                TASK_MANAGER.publish_task_1(task_publish_data)
                print('task swap published')

                return response.Response({'task_id': task_id}, status=status.HTTP_200_OK)
            
        except base64.binascii.Error:
            return response.Response({'error': "Invalid base64 encoding for face images"},
                status=status.HTTP_400_BAD_REQUEST)
        except NotImplementedError:
            if os.path.isdir(decode_img_path):
                shutil.rmtree(decode_img_path) 
            return response.Response({'error': "Face swapping feature not implemented"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            if os.path.isdir(decode_img_path):
                shutil.rmtree(decode_img_path) 
            return response.Response({'error': f"Unexpected error during face swapping: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    except json.JSONDecodeError:
        if os.path.isdir(decode_img_path):
            shutil.rmtree(decode_img_path)
        return response.Response({'error': 'Invalid JSON format'},
                                 status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        if os.path.isdir(decode_img_path):
            shutil.rmtree(decode_img_path)
        return response.Response({'error': f"Unexpected error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_queue_swapface_status(request):

    # Try to find a queue with the given request_id
    try:
        tasks_data = TASK_MANAGER.get_queue_tasks_1() 
        print(tasks_data)
    except Exception as e:
        # Can't connect to the rebbit
        return response.Response({'error': f"Unexpected error during get queue status: {str(e)}"}, 
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if len(tasks_data) == 0:
        return response.Response({"message_count":0, "messages":[]}, status=status.HTTP_200_OK)
    else:
        messages = []
        for task in tasks_data:
            messages.append({
                "request_id": task['task_id'],
                "input": {
                    "template_id": task["template_id"],
                    "decoded_image": task["decoded_image"],
                    "watermark": task["watermark"],
                    "new": task["new"],
                    "is_image": task["is_image"]
                }
                })
        return response.Response({"message_count":len(tasks_data), "messages":messages}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_queue_getface_status(request):

    # Try to find a queue with the given request_id
    try:
        tasks_data = TASK_MANAGER.get_queue_tasks_2() 
        print(tasks_data)
    except Exception as e:
        # Can't connect to the rebbit
        return response.Response({'error': f"Unexpected error during get queue status: {str(e)}"}, 
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if len(tasks_data) == 0:
        return response.Response({"message_count":0, "messages":[]}, status=status.HTTP_200_OK)
    else:
        messages = []
        for task in tasks_data:
            messages.append({
                "input": {
                    "template_id": task["template_id"],
                    "decoded_image": task["decoded_image"],
                    "new": task["new"],
                    "is_image": task["is_image"]
                }
                })
        return response.Response({"message_count":len(tasks_data), "messages":messages}, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_faceswap_result(request):
    task_id = request.GET.get('request_id')

    # Validate request ID format
    if not task_id or not isinstance(task_id, str):
        return response.Response({"error": "Invalid request ID format"}, status=status.HTTP_400_BAD_REQUEST)

    # Attempt to retrieve the result based on request ID
    try:
        face_swap_result = taskApp2.objects.get(task_id=task_id)
    except taskApp2.DoesNotExist:
        return response.Response({"error": "No results found for this request ID"}, status=status.HTTP_404_NOT_FOUND)

    # Serialize the result data
    serializer = taskApp2Serializer(face_swap_result)

    template_id = serializer.data['template_id']
    source = serializer.data['source']
    output_file_path = f'{settings.CDN_RESULT_DOWNLOAD_PATH + str(task_id) + str(os.path.splitext(source)[1])}'
    decoded_img_path = serializer.data['decoded_image']

    answear = {"input": {
                         "template_id": template_id, 
                         "decoded_image": decoded_img_path, 
                         "watermark": serializer.data['watermark'], 
                         "new": serializer.data['new'], 
                         "is_image": serializer.data['is_image']
                         }, 
                "status": serializer.data['status'],
                "output": {
                         "template_id": template_id,
                         "premium": serializer.data['premium'],
                         "source": output_file_path
                }}
    return response.Response(answear, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_faceget_result(request):
    template_id = request.GET.get('template_id')
    faces_list = []

    # Validate request ID format
    if not template_id:
        return response.Response({"error": "Invalid request, no template id"}, status=status.HTTP_400_BAD_REQUEST)

    # Attempt to retrieve the result based on request ID
    try:
        faces_result = facetemplateApp2.objects.filter(template_id=template_id)
    except taskApp2.DoesNotExist:
        return response.Response({"error": "No results found for this request ID"}, status=status.HTTP_404_NOT_FOUND)

    # Serialize the result data
    for face in faces_result:
        serializer = facetemplateApp2Serializer(face)
        faces_list.append(serializer.data['source'])

    answear = {"output": {
                         "template_id": template_id, 
                         "face_sources": faces_list 
                        }
    }

    return response.Response(answear, status=status.HTTP_200_OK)


@api_view(["POST"])
def post_template(request):

    file = request.FILES.get('file')
    thumb_file = request.FILES.get('thumb')
    preview_source_file = request.FILES.get('preview_source')
    categories = request.POST.get('categories')
    premium = request.POST.get('premium')

    if categories:
        categories = categories.split(',')
    else:
        categories = ['0']

    if not premium:
        premium == False

    print(f"premium - {premium}")
    print(f"categories - {categories}")

    try:
        last_id = templateApp2.objects.last().id
    except AttributeError:
        last_id = 0

    sort_id = last_id+1
    is_image = None

    template_model_data = {}
    task_publish_data = {}

    decode_thumb_path = ''
    decode_preview_source_path = ''

    print(f'files - {file}')

    if file:
        file_extension = os.path.splitext(str(file))[1]
        decode_source_path =  f"{settings.DATA_PATH + settings.SOURCE_PATH + str(sort_id) + file_extension}"
        source_cdn_path = f"{settings.SOURCE_PATH + str(sort_id) + file_extension}"

        with open(decode_source_path, 'wb') as destination:
            for f in file:
                destination.write(f)

        if file_extension in ('.jpg','.jpeg','.png'):
            is_image = True
        elif file_extension in ('.mp4'):
            is_image = False

    else:
        return response.Response('There is no file in parameters (image) or (video)', status=status.HTTP_400_BAD_REQUEST)

    CDN_TEMPLATE_UPLOAD.upload_to_cdn(decode_source_path, source_cdn_path)

    if thumb_file:
        file_extension = os.path.splitext(str(thumb_file))[1]
        decode_thumb_path =  f"{settings.DATA_PATH + settings.THUMB_PATH + str(sort_id) + file_extension}"
        thumb_cdn_path = f"{settings.THUMB_PATH + str(sort_id) + file_extension}"

        with open(decode_thumb_path, 'wb') as destination:
            for f in thumb_file:
                destination.write(f)

        CDN_TEMPLATE_UPLOAD.upload_to_cdn(decode_thumb_path, thumb_cdn_path)
        template_model_data['thumb'] = thumb_cdn_path
        task_publish_data['thumb'] = decode_thumb_path

    if preview_source_file:
        file_extension = os.path.splitext(str(preview_source_file))[1]
        decode_preview_source_path =  f"{settings.DATA_PATH + settings.PREVIEW_SOURCE_PATH + str(sort_id) + file_extension}"
        preview_source_cdn_path =  f"{settings.PREVIEW_SOURCE_PATH + str(sort_id) + file_extension}"

        with open(decode_preview_source_path, 'wb') as destination:
            for f in preview_source_file:
                destination.write(f)

        CDN_TEMPLATE_UPLOAD.upload_to_cdn(decode_preview_source_path, preview_source_cdn_path)
        template_model_data['preview_source'] = preview_source_cdn_path
        task_publish_data['task_publish_data'] = decode_preview_source_path


    # Add task to rebbit queue to perform face swapping
    try:
        template_id = sort_id


        template_model_data.update({'sort_id':sort_id,
                        'source':source_cdn_path,
                        'premium': premium})
            
        responce = {
                    "status": 'OK',
                    "request_id": sort_id
                    }

        task_publish_data.update({
            'template_id': template_id,
            'is_image': is_image,
            'sort_id':sort_id,
            'source':decode_source_path,
            'premium': premium
        })

        for category in categories:

            category_model_data = {
                'templ_id': template_id,
                'category_int': int(category)
                }
            
            serialized_category_task = categoryToTemplateApp2Serializer(data=category_model_data)
            if serialized_category_task.is_valid():
                serialized_category_task.save()

            print('categories saved')

        serialized_template_task = templateApp2Serializer(data=template_model_data)
        if serialized_template_task.is_valid():
            serialized_template_task.save()

            TASK_MANAGER.publish_task_2(task_publish_data)

            return response.Response(responce, status=status.HTTP_200_OK)

    except NotImplementedError:
        if os.path.isfile(decode_source_path):
           os.remove(decode_source_path)
        if os.path.isfile(decode_preview_source_path):
           os.remove(decode_preview_source_path)
        if os.path.isfile(decode_thumb_path):
           os.remove(decode_thumb_path)
        return response.Response({'error': "Face swapping feature not implemented"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        if os.path.isfile(decode_source_path):
            os.remove(decode_source_path)
        if os.path.isfile(decode_preview_source_path):
           os.remove(decode_preview_source_path)
        if os.path.isfile(decode_thumb_path):
           os.remove(decode_thumb_path)
        return response.Response({'error': f"Unexpected error during face swapping: {str(e)}"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def check_images_for_state(request):

    try:
        face_analyzer = insightface.app.FaceAnalysis(name='buffalo_l')
        face_analyzer.prepare(ctx_id=0)
        image = request.data['image']
        decoded_data = base64.b64decode(image)

        img = Image.open(io.BytesIO(decoded_data))
        opencv_img= cv.cvtColor(np.array(img), cv.COLOR_BGR2RGB)

        faces = face_analyzer.get(opencv_img)

        if faces:
            return response.Response({'faces': len(faces)}, status=status.HTTP_200_OK)
        else:
            return response.Response({'faces': 0}, status=status.HTTP_200_OK)

    except Exception as e:
        return response.Response({'error': f"Unexpected error during getting faces: {str(e)}"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
