import onnxruntime
print(onnxruntime.get_version_string())
print(onnxruntime.get_device())
print(onnxruntime.get_available_providers())
print(onnxruntime.get_all_providers())