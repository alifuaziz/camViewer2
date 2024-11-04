import PySpin
import json

def load_camera_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config

def configure_camera_from_config(cam, config):
    # Set width and height if available
    if cam.Width and cam.Width.GetAccessMode() == PySpin.RW and "width" in config:
        cam.Width.SetValue(config["width"])
    if cam.Height and cam.Height.GetAccessMode() == PySpin.RW and "height" in config:
        cam.Height.SetValue(config["height"])

    # Set frame rate if available
    if cam.AcquisitionFrameRateEnable and cam.AcquisitionFrameRateEnable.GetAccessMode() == PySpin.RW:
        cam.AcquisitionFrameRateEnable.SetValue(True)
    if cam.AcquisitionFrameRate and cam.AcquisitionFrameRate.GetAccessMode() == PySpin.RW and "frame_rate" in config:
        cam.AcquisitionFrameRate.SetValue(config["frame_rate"])

    # Set exposure time if available
    if cam.ExposureAuto and cam.ExposureAuto.GetAccessMode() == PySpin.RW:
        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
    if cam.ExposureTime and cam.ExposureTime.GetAccessMode() == PySpin.RW and "exposure_time" in config:
        cam.ExposureTime.SetValue(config["exposure_time"])

    # Set gain if available
    if cam.GainAuto and cam.GainAuto.GetAccessMode() == PySpin.RW:
        cam.GainAuto.SetValue(PySpin.GainAuto_Off)
    if cam.Gain and cam.Gain.GetAccessMode() == PySpin.RW and "gain" in config:
        cam.Gain.SetValue(config["gain"])



def print_camera_settings(cam):
    """Prints the current camera settings."""
    try:
        print("Current Camera Settings:")
        if cam.Width.GetAccessMode() == PySpin.RO:
            print(" - Width:", cam.Width.GetValue())
        if cam.Height.GetAccessMode() == PySpin.RO:
            print(" - Height:", cam.Height.GetValue())
        if cam.AcquisitionFrameRate.GetAccessMode() == PySpin.RO:
            print(" - Frame Rate:", cam.AcquisitionFrameRate.GetValue())
        if cam.ExposureTime.GetAccessMode() == PySpin.RO:
            print(" - Exposure Time:", cam.ExposureTime.GetValue())
        if cam.Gain.GetAccessMode() == PySpin.RO:
            print(" - Gain:", cam.Gain.GetValue())
    except PySpin.SpinnakerException as ex:
        print("Error accessing camera settings:", ex)


def main():
    config = load_camera_config('configs/pysin.json')

    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    if cam_list.GetSize() == 0:
        print("No cameras detected.")
        system.ReleaseInstance()
        return

    cam = cam_list[0]
    cam.Init()

    try:
        configure_camera_from_config(cam, config)

        cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        cam.BeginAcquisition()
        print("Camera acquisition started with JSON configuration.")

        for i in range(10):
            image = cam.GetNextImage()
            if image.IsIncomplete():
                print("Image incomplete with status %d..." % image.GetImageStatus())
                continue
            
            print_camera_settings(cam)
            print("Captured frame %d" % i)
            image.Release()

    except PySpin.SpinnakerException as ex:
        print("Error: %s" % ex)
    finally:
        try:
            cam.EndAcquisition()
        except PySpin.SpinnakerException as ex:
            print("Error ending acquisition: %s" % ex)
        cam.DeInit()
        cam_list.Clear()
        system.ReleaseInstance()

if __name__ == "__main__":
    main()
