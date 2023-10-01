# Introduccion a los Sistemas Distribuidos
Repositorio que contiene el trabajo práctico de la materia Introducción a los Sistemas Distribuidos [75.43]

# Server
python3 start-server.py -v -s "./custom_folder"

# Subir un archivo
python3 upload.py -n "lorem-ipsum.txt" -v

# Generar un archivo random de 1Gb 
base64 /dev/urandom | head -c 1000000000 > file.txt


# Instalar librerias externas (sólo para la barra de progreso)
pip install tqdm