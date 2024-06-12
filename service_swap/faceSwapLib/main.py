from roop import core

if __name__ == '__main__':
    # Just an example of how you can use this library

    # core.run(r"D:\Projects\Face_changer\templateAndFace\face1.png",
    #          r"D:\Projects\Face_changer\templateAndFace\128.mp4",r".\output.mp4", False, None)
    
    core.get_referance_faces_from_video(r"D:\Projects\Face_changer\templateAndFace\128.mp4", r"D:\Projects\Face_changer\templateAndFace\unique_face")

    core.run_multiple([[r"D:\Projects\Face_changer\templateAndFace\unique_face\0.png", r"D:\Projects\Face_changer\templateAndFace\face1.png"],
                       [r"D:\Projects\Face_changer\templateAndFace\unique_face\1.png", r"D:\Projects\Face_changer\templateAndFace\face2.png"],
                       [r"D:\Projects\Face_changer\templateAndFace\unique_face\2.png", r"D:\Projects\Face_changer\templateAndFace\face3.png"]],
                       r"D:\Projects\Face_changer\templateAndFace\128.mp4",
                       r".\output.mp4", False, None)
