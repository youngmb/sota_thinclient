import io
import queue
import pygame
from PIL import Image
import time
from sota_thinclient import ConnectionManager

SOTA_IP = "192.168.0.23"
# SOTA_IP = "10.151.63.71"
HTTP_PORT = "8080"
UDP_PORT = 52003

sota = ConnectionManager(SOTA_IP, HTTP_PORT)
sota.video.enable(data_udp_port=UDP_PORT, request_image_size="QVGA", request_bitrate_kbps="6000")
print ("Video stream enabled")

video_state = sota.video.get_state(use_cached=True)

print("\nInitial video state")
print(sota.video.get_state())

print("\nVideo stream capabilities")
print(sota.video.get_capabilities())


pygame.init()
image_size = video_state.get("streamImageSize")
screen = pygame.display.set_mode((image_size['width'], image_size['height']))

running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    try:
        jpeg_bytes = sota.video.data_queue.get_nowait()

        image = Image.open(io.BytesIO(jpeg_bytes))

        mode = image.mode
        size = image.size

        data = image.tobytes()

        surface = pygame.image.fromstring(data, size, mode)

        screen.blit(surface, (0, 0))

        pygame.display.flip()

    except queue.Empty:
        pass

pygame.quit()
sota.video.disable()

