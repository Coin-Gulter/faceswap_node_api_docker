from utilities import task_manage, db_manage
from utilities.cdn_manager import CDN
import multiprocessing
import re
import os
import time
from utilities import utils
import warnings

warnings.filterwarnings("ignore")


DATA_PATH = os.environ.get('data_path', './')
PATHS_CONFIG = utils.load_config(os.path.join(DATA_PATH, 'data/config/paths.cnf'), 
                                 [
                                     'mysql',
                                     'rebbit',
                                     'cdn_template_download_path',
                                     'cdn_result_upload_path',
                                     'cdn_result_download_path',
                                     'result_path',
                                     'source_path',
                                     'watermark_path'
                                ])

MYSQL_PATH = os.path.join(DATA_PATH, PATHS_CONFIG['mysql'])
REBBIT_PATH = os.path.join(DATA_PATH, PATHS_CONFIG['rebbit'])

CDN_RESULT_UPLOAD_PATH = PATHS_CONFIG['cdn_result_upload_path']
CDN_TEMPLATE_DOWNLOAD_PATH = PATHS_CONFIG['cdn_template_download_path']
CDN_RESULT_DOWNLOAD_PATH = PATHS_CONFIG['cdn_result_download_path']

RESULT_PATH = os.path.join(DATA_PATH, PATHS_CONFIG['result_path'])
SOURCE_PATH = os.path.join(DATA_PATH, PATHS_CONFIG['source_path'])
WATERMARK_PATH = os.path.join(DATA_PATH, PATHS_CONFIG['watermark_path'])

IMPROVER_BG_TILE = 800


def swap_face(face_source, source_path, swaper_output_path, watermark, watermark_path, is_image):
    from faceSwapLib.roop import core
    core.run_multiple(face_source, source_path, swaper_output_path, watermark, watermark_path, is_it_image=is_image, execution_provider=['cuda'])

def improve(swaper_output_path, output_file_path, bg_tile=400):
    from gfpgan import improver
    improver.improve(input=swaper_output_path, output=output_file_path, bg_tile=bg_tile)
    os.remove(swaper_output_path)


class Consumer():

    def __init__(self, rabbit_config_path='config/rabbit.cnf', mysql_config_path='config/mysql.cnf'):
        self.task_manager = task_manage.TaskManager(rabbit_config_path)  
        self.db = db_manage.MySQLDB(mysql_config_path)
        self.cdn_result_upload = CDN(CDN_RESULT_UPLOAD_PATH)
        self.cdn_template_download = CDN(CDN_TEMPLATE_DOWNLOAD_PATH)

        # Connect to the BD
        self.db.connect()

    def task_swap_face(self, task):
        # Implemented task processing logic
        task_id = task["task_id"]
        decoded_img = task["decoded_image"]
        template_id = task['template_id']
        source_extension = task['source_extension']

        try:
            print(f"Processing task: {task}")
            face_source = []
            from_face = os.listdir(os.path.join(decoded_img, 'from_face'))
            to_face = os.listdir(os.path.join(decoded_img, 'to_face'))
            output_folder_path = f'{RESULT_PATH + str(task_id)}'
            os.mkdir(output_folder_path)
            
            swaper_output_path = f'{output_folder_path}/{str(template_id)}_temp{str(source_extension)}'
            output_file_path = f'{output_folder_path}/{str(template_id) + str(source_extension)}'
            cdn_file_path = f'{str(task_id) + str(source_extension)}'

            query_status = "UPDATE taskApp2 SET status = %s WHERE task_id = %s;"
            query_timer = "UPDATE taskApp2 SET timer = %s WHERE task_id = %s;"
            query_source = "UPDATE taskApp2 SET source = %s WHERE task_id = %s;"

            source_path = f"{SOURCE_PATH + str(template_id) + str(source_extension)}"

            if not os.path.isfile(source_path):
                video_byt = self.cdn_template_download.download_from_cdn(PATHS_CONFIG['source_path'] + str(template_id) + str(source_extension))

                with open(source_path, 'wb') as f:
                    f.write(video_byt)

            self.db.execute_query(query_status, ('in_work', task_id))

            for index, face_path in enumerate(from_face):
                face_source.append([f"{decoded_img + '/from_face/' + face_path}",
                                    f"{decoded_img + '/to_face/' + to_face[index]}"])

            print('resources --- ', face_source, source_path, output_file_path)

            if len(face_source) == 0:
                print(f'No faces in "face_source" - {face_source}')
                self.db.execute_query(query_timer, (int(time.time())-task['timer'], task_id))
                self.db.execute_query(query_status, ('done', task_id))
                self.db.execute_query(query_source, (f'{CDN_RESULT_DOWNLOAD_PATH + cdn_file_path}', task_id))

                self.cdn_result_upload.upload_to_cdn(source_path, cdn_file_path)

                return False

            if task['is_image']:
                swap_p = multiprocessing.Process(target=swap_face, 
                                                 args=(face_source, 
                                                   source_path, 
                                                   swaper_output_path, 
                                                   task['watermark'], 
                                                   WATERMARK_PATH), 
                                                 kwargs={"is_image":task['is_image']}
                                                )
                swap_p.start()
                swap_p.join()

                improv_p = multiprocessing.Process(target=improve,
                                                   args=(swaper_output_path, output_file_path),
                                                   kwargs={"bg_tile":IMPROVER_BG_TILE}
                                                   )
                improv_p.start()
                improv_p.join()

            else:
                swap_p = multiprocessing.Process(target=swap_face, 
                                                 args=(face_source, 
                                                   source_path, 
                                                   output_file_path, 
                                                   task['watermark'], 
                                                   WATERMARK_PATH), 
                                                kwargs={"is_image":task['is_image']}
                                                )
                swap_p.start()
                swap_p.join()


            self.db.execute_query(query_timer, (int(time.time())-task['timer'], task_id))
            self.db.execute_query(query_status, ('done', task_id))
            self.db.execute_query(query_source, (f'{CDN_RESULT_DOWNLOAD_PATH + cdn_file_path}', task_id))

            self.cdn_result_upload.upload_to_cdn(output_file_path, cdn_file_path)

        except Exception as e:
            print(f'Error: unexpected error during face swap: {str(e)}')
            self.db.execute_query(query_timer, (int(time.time())-task['timer'], task_id))
            self.db.execute_query(query_status, ('Error', task_id))
            self.db.execute_query(query_source, (f'{CDN_RESULT_DOWNLOAD_PATH + cdn_file_path}', task_id))

            self.cdn_result_upload.upload_to_cdn(source_path, cdn_file_path)



    def start_consuming(self):
        self.task_manager.listen_for_tasks_1(self.task_swap_face)
        
        # Disconect from BD at the end
        self.db.disconnect()


if __name__=="__main__":
    print(f"Getting configuration for face swap service")
    client = Consumer(rabbit_config_path = REBBIT_PATH, mysql_config_path = MYSQL_PATH)

    print(f"Face swap service started")
    client.start_consuming()

    print(f"Face swap service closed")
