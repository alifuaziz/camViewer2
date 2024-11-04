import sys
import main_gui as mg

def main():
    app = mg.QtWidgets.QApplication(sys.argv)
    gui = mg.GUIApp()
    app.exec()
    
    
if __name__ == '__main__':
    main()