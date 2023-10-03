# Introduccion a los Sistemas Distribuidos
## Repositorio que contiene el trabajo práctico de la materia Introducción a los Sistemas Distribuidos [75.43]
 Es necesario contar con python instalado tanto en el cliente como en el servidor.

# Instalar librerias externas (sólo para la barra de progreso) [Opcional]
    pip install tqdm

# Server
    python3 start-server.py -v -s "./custom_folder"

# Subir un archivo
    python3 upload.py -n "lorem-ipsum.txt" -v -p 15000

# Subir un archivo
    python3 download.py -n "lorem-ipsum.txt" -v -p 15001
    
El programa preguntará el protocolo a utilizar, seleccionar 1 para Selective Repeat, 2 para Stop&Wait

# Generar un archivo con contenido aleatorio de de 1Gb 
    base64 /dev/urandom | head -c 1000000000 > file.txt


