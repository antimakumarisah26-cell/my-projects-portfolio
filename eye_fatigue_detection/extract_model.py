import urllib.request
import os
import bz2



os.makedirs('Model', exist_ok=True)

url = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
output_path = "Model/shape_predictor_68_face_landmarks.dat"

print("Downloading and extracting model...")
try:
    # Download, decompress and save in one step
    with urllib.request.urlopen(url) as response:
        decompressed_data = bz2.decompress(response.read())

    with open(output_path, 'wb') as f:
        f.write(decompressed_data)

    print(" Model downloaded and extracted successfully!")
    print(f" File: {output_path}")

except Exception as e:
    print(f" Error: {e}")