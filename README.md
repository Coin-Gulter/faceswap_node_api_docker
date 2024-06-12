There are three main files:

Using "manage.py" you can run django server to get request.
To use it just run - "python manage.py runserver 5005" where 5005 its a port.

Before usage in node/setting.py file set DEBUG = False and in ALLOW_HOSTS put your host.


"manage_consumer_get_face.py" - Run this file to get from rebbit queue task to get unique faces from video or photo

"manage_consumer_swaper.py" - Run this file to get from rebbit queue task to swap faces in photo or video.


You need to run all this files one by one to start server working.


There are six possible request to this api:
    'face_swap/'
    'face_swap/result/'
    'face_get/result/'
    'queue_status/swapface/'
    'queue_status/getface/
    'template/add/

There one of common and basic usage of this api its:

call 'template/add/ with appropriate parameters inculdes template image or video, only one of them and get 
corresponding template id and wait until unique faces would be extracted. After there are you can call /check/faces method for eaxh image separately to check if there face on images or if images in right format, after that call 'face_get/result/' with template id to get pathes to this face images to download it, if you call 'face_get/result/' before ending face extracting you just got nothing.

(functions return only path to the file on the server if you want to download something from cdn you need add
path that you get from function to the cdn domain and call request)

Next using previos template id and donwloaded extracting faces with chosed new faces as a parameters call request  'face_swap/' to start face swaping on the video/image template as responce you get task id to check state in future.

while face swaping start going you can check status by calling 'face_swap/result/' with task id parameters.
After face swaping ends call the same request with task id 'face_swap/result/' to get source path, another words path to the resulted video/image template that you can download from cdn.

Of course usage depends on what you need.

You are welcome.)