# core python
import numpy as np
import sys, os
import json 
import logging
import subprocess
from datetime import datetime

from util.recording_utils import configure_camera_from_config

# gui
from PyQt6.QtWidgets import (
    QVBoxLayout, 
    QGroupBox, 
    QPlainTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QComboBox,
    QPushButton,
    QFileDialog,
    QFrame,
    QSpinBox,
    QLabel,
    
    )
from PyQt6.QtGui import (
    QFont,
    QImage,
    QPixmap
    )

# video
import PySpin
import ffmpeg


class camera_widget(QWidget):
    'widget for each camera to be viewed'
    def __init__(self, parent=None, camera=None):
        super(camera_widget, self).__init__(parent)
        self.view_finder = parent
        self.GUI = self.view_finder.GUI
        self.camera = camera
        self.logger = logging.getLogger(__name__)
        # Layout
        self._init_camera_setup_groupbox()
        self._set_camera_setup_layout()
        self.setLayout(self.camera_setup_hlayout)
        # Recording setup 
        self._init_recording()
        
        
    def _init_camera_setup_groupbox(self):
        self.camera_setup_groupbox = QGroupBox("Camera Setup")
        
        # Button for starting recording
        self.start_recording_button = QPushButton('Start Recording')
        self.start_recording_button.setStyleSheet('background-color: green')
        self.start_recording_button.clicked.connect(self.toggle_recording)
        
        # Label for displaying the camera feed
        self.image_label = QLabel()
    
        
    def _set_camera_setup_layout(self):
        self.camera_setup_hlayout = QGridLayout()
        
        self.camera_setup_hlayout.addWidget(self.start_recording_button, 0, 0)
        
        self.camera_setup_hlayout.addWidget(self.image_label, 2, 0, 1, 2)
        
    ### Displaying the camera feed functions


    def _init_recording(self):
        # Set the recording flag to False
        self.recording = False
        
        # PySpin camera setup
        self.camera.Init()
        
        camera_config = json.load(open(r"configs\recording_config.json"))
        # Configure the camera from the config file
        configure_camera_from_config(self.camera, camera_config)
        
        self.camera.BeginAcquisition()
        
        
        # Set the widget width and height
        self.width = self.camera.Width.GetValue()
        self.height = self.camera.Height.GetValue()
        


    def fetch_image_data(self) -> None:
        '''
        The `fetch_image_data` function retrieves the latest image from a camera and converts the image
        data to a format suitable for PyQt6 and OpenCV.
        
        image_result is returned as Mono8 Pixel format
        
        :return: The `fetch_image_data` method is returning the image data in a format suitable for
        PyQt6 and OpenCV after retrieving the latest image from the camera.
        '''
        try:
            # Retrieve the latest image from the camera
            image_result = self.camera.GetNextImage()
            # Convert the image data to a format suitable for PyQt6 and OpenCV
            image_data = image_result.GetNDArray()
            self.image_data = image_data
            if self.recording == True:
                # encode the frames
                self.encode_frame_ffmpeg_process(frame=image_data)
                # self.encode_frame_pynvidia_api(frame=image_data)
                
            # Release the image once it has been converted
            image_result.Release()

            return image_data
    
        except PySpin.SpinnakerException as e:
            print(f"Error fetching image data: {e}")

        
    def get_recording_filename(self) -> str:
        
        if os.path.exists(self.GUI.recording_config['save_dir']) == True:
            pass
        else:
            os.makedirs(self.GUI.recording_config['save_dir'])
        
            
        self.recording_filename = self.GUI.recording_config['save_dir'] + '/' + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.mp4'

        
        print(f'Saving recording to: {type(self.recording_filename)}')
        
        
    def display_frame(self, image_data: np.array) -> None:
        
        try:
            # Convert the image data to a format suitable for PyQt6 and OpenCV
            if image_data.ndim == 3:
                # Convert BGR to RGB for displaying in PyQt
                # image_data = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
                image_format = QImage.Format.Format_RGB888
                bytes_per_line = 3 * self.width
            elif image_data.ndim == 1 or image_data.ndim == 2:
                image_format = QImage.Format.Format_Grayscale8
                bytes_per_line = self.width
                            

            # Display the image in the GUI
            image = QImage(image_data.data, self.width, self.height, bytes_per_line, image_format)
            pixmap = QPixmap.fromImage(image)
            self.image_label.setPixmap(pixmap)
            
        except Exception as e:
            print(f"Error displaying image: {e}")
            
    def recording_loop(self):
        '''Function Called by the parent class every FPS (as defined in parent class)'''

        # Fetch the image data
        self.fetch_image_data()
        # Displaying on GUI

    def refresh_display(self):
        '''Function to refresh the display. Called by the parent class '''
        self.display_frame(self.image_data)
        
        
        
    def _init_ffmpeg_process(self) -> None:
        
        self.get_recording_filename()
                
        # Set up an ffmpeg encoding pipline
        self.ffmpeg_process = (
            ffmpeg
            .input(
                'pipe:', 
                format='rawvideo', 
                pix_fmt='gray', 
                s=f'{self.camera.Width.GetValue()}x{self.camera.Height.GetValue()}', 
                framerate=self.GUI.recording_config['fps']
                )
            .output(
                self.recording_filename, 
                vcodec='h264_nvenc', 
                pix_fmt='yuv420p', 
                preset='fast', 
                crf=23
                )
            .run_async(
                pipe_stdin=True
                )
        )
        self.logger.info('FFmpeg pipeline initialized')
        
    def encode_frame_ffmpeg_process(self, frame: np.array) -> None:
        '''
        The `encode_frame_ffmpeg_process` function encodes the frame using the ffmpeg pgrocess.
        
        :param frame: np.array - frame to be encoded
        '''
        try:
            # Write the frame to the ffmpeg process
            self.ffmpeg_process.stdin.write(frame.tobytes())
            
        except Exception as e:
            print(f"Error encoding frame: {e}")
        
    ### Recordinging functions
        
    def toggle_recording(self):
        
        self.recording = not self.recording
        
        if self.recording == True:
            self._init_ffmpeg_process()
            self.start_recording_button.setText('Stop Recording')
            self.start_recording_button.setStyleSheet('background-color: red')
            self.logger.info('Recording Started')
            
        else:
            self.ffmpeg_process.stdin.close()
            self.ffmpeg_process.wait()
            self.start_recording_button.setText('Start Recording')
            self.start_recording_button.setStyleSheet('background-color: green')
            self.logger.info('Recording Stopped')