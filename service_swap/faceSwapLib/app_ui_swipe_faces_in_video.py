from roop import core
import gradio as gr
import os

def create_video(img1_path, img1_to_face_path, img2_path, img2_to_face_path, img3_path, img3_to_face_path, video_path):

    images_parameters_path = [[img1_path, img1_to_face_path],
                              [img2_path, img2_to_face_path],
                              [img3_path, img3_to_face_path]]
    output_name = os.path.basename(video_path)
    image_path_pairs = []
    print(img3_path)
    print(img3_to_face_path)
    output_file_path = os.path.join(os.getcwd(), 'result', output_name)

    for pair in images_parameters_path:
        if all(pair):
            image_path_pairs.append(pair)

    core.run_multiple(image_path_pairs,
                       video_path,
                       output_file_path,
                       False, None)

    return output_file_path

iface2 = gr.Interface(
    fn=create_video, 
    inputs=["file", "file", "file", "file", "file", "file", "file"], 
    outputs="file",
    description="""The UI is to swipe multiple faces on a video.
                    In the fields choose images of someones, for examples in the field 'img1_path'
                    put image of someone from video and in the field 'img1_to_face_path'
                    put image of someone with whom you want to swipe his face.
                    To work without error in this UI you need to put face images in all fields that purposed.
                    In the field 'video_path' put video in which you need to swipe faces.
                    And 'output_file_path' write disk and path where to save resulted video in format as in example - 'C:\\Users\\jastin\\Downloads'.
                    If in the last field you won't write anything it will be saved in project
                    folder in 'result'"""
)

iface2.launch(share=True)
