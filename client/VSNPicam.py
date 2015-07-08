__author__ = 'Amin'

from twisted.internet import reactor

import socket
import cv2
import numpy
import time

from client.VSNImageProcessing_picam import VSNImageProcessing
from client.VSNActivityController import VSNActivityController
from common.VSNPacket import VSNPacketToServer

from client.VSNClient import VSNClientFactory
from common.VSNPacket import ImageType


class VSNPicam:
    def __init__(self, camera_name=None, video_capture_number=0):
        self._node_name = camera_name
        self._node_number = 3
        self._flag_send_image = False  # default behavior - do not send the image data
        self._image_type = ImageType.foreground

        self._prepare_camera_name_and_number()

        self._client_factory = VSNClientFactory(self._packet_received_callback)
        self._image_processor = VSNImageProcessing(video_capture_number)
        self._activity_controller = VSNActivityController()
        self._packet_to_send = VSNPacketToServer(self._node_number,
                                                 0.0,
                                                 self._activity_controller.get_activation_level(),
                                                 self._flag_send_image)

        self._do_regular_update_time = 0

    def _prepare_camera_name_and_number(self):
        # if the names was not set try getting it by gethostname
        # it is of picamXX type parse XX to a number

        if self._node_name is None:
            self._node_name = socket.gethostname()
        if len(self._node_name) == 7 and self._node_name[0:5] == "picam":
            if self._node_name[5:7].isdigit():
                self._node_number = int(self._node_name[5:7])

        print("Node number: ", self._node_number, "\r\n", "Node name: ", self._node_name)

    def _do_regular_update(self):
        current_time = time.perf_counter()
        print('\nPREVIOUS REGULAR UPDATE WAS %.2f ms AGO' % ((current_time - self._do_regular_update_time) * 1000))
        self._do_regular_update_time = current_time
        # queue the next call to itself
        reactor.callLater(self._activity_controller.get_sample_time(), self._do_regular_update)

        time_start = time.perf_counter()

        if self._activity_controller.is_activation_below_threshold():
            self._image_processor.grab_images(5)

        percentage_of_active_pixels = self._image_processor.get_percentage_of_active_pixels_in_new_frame_from_camera()
        self._activity_controller.update_sensor_state_based_on_captured_image(percentage_of_active_pixels)

        time_after_get_percentage = time.perf_counter()

        # self._flush_image_buffer_when_going_low_power()

        print(self._activity_controller.get_state_as_string())

        self._packet_to_send.set(
            self._node_number,
            percentage_of_active_pixels,
            self._activity_controller.get_activation_level(),
            self._flag_send_image
        )
        self._client_factory.send_packet(self._packet_to_send)

        time_after_sending_packet = time.perf_counter()

        if self._flag_send_image:
            image_as_string = self._encode_image_for_sending()
            self._client_factory.send_image(image_as_string)

        time_after_encoding = time.perf_counter()

        print('Calculating percentage took: %.2f ms' % ((time_after_get_percentage - time_start) * 1000))
        print('Sending packet took: %.2f ms' % ((time_after_sending_packet - time_after_get_percentage) * 1000))
        print('Encoding took: %.2f ms' % ((time_after_encoding - time_after_sending_packet) * 1000))

    def _flush_image_buffer_when_going_low_power(self):
        if self._activity_controller.is_activation_below_threshold():
            self._image_processor.grab_images(8)

    def _encode_image_for_sending(self):
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        image_to_send = self._image_processor.get_image(self._image_type)
        result, image_encoded = cv2.imencode('.jpg', image_to_send, encode_param)
        data = numpy.array(image_encoded)
        image_as_string = data.tostring()
        return image_as_string

    def _packet_received_callback(self, packet):
        print("Received packet: ", packet.activation_neighbours, ", ", packet.image_type, ", ", packet.flag_send_image)
        self._activity_controller.set_params(
            activation_neighbours=packet.activation_neighbours
        )
        self._flag_send_image = packet.flag_send_image
        self._image_type = packet.image_type

    def start(self, server_ip="127.0.0.1", server_port=50001):
        # connect factory to this host and port
        reactor.connectTCP(server_ip, server_port, self._client_factory)
        reactor.callLater(self._activity_controller.get_sample_time(), self._do_regular_update)

        reactor.run()


if __name__ == '__main__':
    # the object can be created by specifying its name:
    # picam = VSNPicam("picam01", 0)
    # or by letting it get its name with gethostname function
    # if it is in picamXY format it will be accepted
    # otherwise picam03 name will be used
    # second argument specify which camera should be used
    picam = VSNPicam()
    # if no args are specified, the 127.0.0.1 IP and 50001 port are used
    picam.start()
