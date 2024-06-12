from utilities import task_manage, db_manage
from utilities.cdn_manager import CDN
from faceSwapLib.roop import core
import shutil
import os
from utilities import utils
import warnings

warnings.filterwarnings("ignore")

DATA_PATH = os.environ.get('data_path', './')

PATHS_CONFIG = utils.load_config(os.path.join(DATA_PATH, 'data/config/paths.cnf'), 
                                 [
                                     'mysql',
                                     'rebbit',
                                     'cdn_template_upload_path',
                                     'cdn_template_download_path',
                                     'faces_path',
                                ])

MYSQL_PATH = os.path.join(DATA_PATH, PATHS_CONFIG['mysql'])
REBBIT_PATH = os.path.join(DATA_PATH, PATHS_CONFIG['rebbit'])

CDN_TEMPLATE_UPLOAD_PATH = PATHS_CONFIG['cdn_template_upload_path']
CDN_TEMPLATE_DOWNLOAD_PATH = PATHS_CONFIG['cdn_template_download_path']

FACES_PATH = os.path.join(DATA_PATH, PATHS_CONFIG['faces_path'])

class Consumer():

    def __init__(self, rabbit_config_path='config/rabbit.cnf', mysql_config_path='config/mysql.cnf'):
        self.task_manager = task_manage.TaskManager(rabbit_config_path)  
        self.db = db_manage.MySQLDB(mysql_config_path)
        self.cdn_template_upload = CDN(CDN_TEMPLATE_UPLOAD_PATH)

        # Connect to the BD
        self.db.connect()
    

    def task_get_face(self, task):
        # Implemented task processing logic
        template_id = task["template_id"]

        try:
            print(f"Processing task: {task}")

            faces_dir = f'{FACES_PATH + str(template_id)}'
            os.mkdir(faces_dir)
            
            core.get_referance_faces_from_source(task["source"], faces_dir)

            # Prepare the SQL query with placeholders for values
            query = "INSERT INTO facetemplateApp2 (template_id, source) VALUES (%s, %s)"

            for face in os.listdir(faces_dir):
                decode_faces_path = f'{faces_dir}/{face}'

                faces_path = PATHS_CONFIG['faces_path']
                
                faces_cdn_path = f'{faces_path + str(template_id)}/{face}'
                self.cdn_template_upload.upload_to_cdn(decode_faces_path, faces_cdn_path)
                # Provide the values to insert
                values = (template_id, CDN_TEMPLATE_DOWNLOAD_PATH + faces_cdn_path)  

                # Execute the query
                cursor = self.db.execute_query(query, values)

                if cursor:
                    print(f"File {decode_faces_path} uploaded successfully!")
                else:
                    print(f"Error uploading file {decode_faces_path}")


            if os.path.isdir(task["source"]):
                shutil.rmtree(faces_dir) 
        except Exception as e:
            print(f'Error: unexpected error during face getting: {str(e)}')


    def start_consuming(self):
        self.task_manager.listen_for_tasks_2(self.task_get_face)
        
        # Disconect from BD at the end
        self.db.disconnect()


if __name__=="__main__":
    print(f"Getting configuration for face getter service")
    client = Consumer(rabbit_config_path = REBBIT_PATH, mysql_config_path = MYSQL_PATH)

    print(f"Face get service started")
    client.start_consuming()

    print(f"Face getter service closed")
