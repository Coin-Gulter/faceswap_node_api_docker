import requests
import re

class CDN:

    def __init__(self, base_url):
        self.base_url = base_url

    def upload_to_cdn(self, file_path, cdn_file_path):
        """
        Upload file on the CDN.

        Args:
            file_path (str)
            cdn_file_path (str)
        Returns:
            bool
        """
        if file_path.endswith('.mp4'):
            file_type = "video/mp4"
        elif file_path.endswith('.png'):
            file_type = "image/png"
        elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
            file_type = "image/jpg"
        elif file_path.endswith('.webp'):
            file_type = "image/webp"

        headers = {
            "Content-Type": file_type,
        }

        with open(file_path, "rb") as f:
            response = requests.put(
                self.base_url + re.sub(r'^(\.\/)', '', cdn_file_path), headers=headers, data=f
            )
        return response.status_code == 200

    def download_from_cdn(self, file_name):
        """
        Download file from CDN.

        Args:
            file_name (str)
        Returns:
            bytes
        """
        response = requests.get(f"{self.base_url + file_name}")
        return response.content

if __name__=="__main__":
    # Приклад використання
    cdn = CDN("https://fs2template.nikb-contact-us.workers.dev/")

    # # Завантаження файлу
    # file_path = "/path/to/1.mp4"
    # cdn.upload_to_cdn(file_path)

    # Завантаження файлу
    file_name = "data/result/232ab9d0-4cc9-4302-a369-614ed48f98f7/16.mp4"
    file_content = cdn.download_from_cdn(file_name)
    with open('./test.mp4', 'wb') as f:
        f.write(file_content)
