from roop import core
import gradio as gr
import shutil
import os

def process_video(file_path, save_to_folder_path):
    cwd = os.getcwd()
    save_to_folder_path = os.path.join(cwd, 'unique_faces\\')

    core.get_referance_faces_from_source(file_path, save_to_folder_path, process_every_n_th_frame = 10)

    zip_path = os.path.join(cwd, 'unique_faces')

    shutil.make_archive(zip_path, 'zip', zip_path)

    return zip_path + '.zip'

iface1 = gr.Interface(
    fn=process_video, 
    inputs="file", 
    outputs="file",
    description="""The UI is to get image of people from video.
                   Choose a video that you want to process and a path where to save images in format as in example - 'C:\\Users\\jastin\\Downloads'.
                   If in the last field you won't write anything it will be saved in project
                   folder in 'unique_faces'"""
    )

iface1.launch(share=True)
