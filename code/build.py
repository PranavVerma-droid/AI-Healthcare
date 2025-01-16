import PyInstaller.__main__ # type: ignore
import os
import nltk
import matplotlib

current_dir = os.path.dirname(os.path.abspath(__file__))

nltk.download('vader_lexicon', download_dir=os.path.join(current_dir, 'nltk_data'))

PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--windowed',
    '--name=AI HealthCare App',
    '--icon=stacy.ico',
    '--add-data=config.py;.',
    f'--add-data={os.path.join(current_dir, "nltk_data")};nltk_data',
    f'--add-data={matplotlib.get_data_path()};matplotlib/mpl-data',
    '--hidden-import=PIL._tkinter_finder',
    '--hidden-import=numpy',
    '--hidden-import=matplotlib',
    '--hidden-import=nltk',
    '--hidden-import=textblob',
    '--hidden-import=pytz',
    '--hidden-import=tkinter',
    '--hidden-import=requests',
    '--hidden-import=ollama',
    '--hidden-import=numpy.core.multiarray',
    '--hidden-import=numpy.core.numeric',
    '--hidden-import=numpy.lib.format',
    '--hidden-import=numpy.linalg.linalg',
    '--hidden-import=psutil',
    '--hidden-import=matplotlib.backends.backend_tkagg',
    f'--workpath={os.path.join(current_dir, "build")}',
    f'--distpath={os.path.join(current_dir, "dist")}',
    '--clean',
    '--exclude-module=brotli',
    '--exclude-module=IPython',
    '--exclude-module=jupyter',
    '--exclude-module=scipy',
    '--exclude-module=pandas',
    '--exclude-module=sklearn',
    '--exclude-module=tornado'
])
