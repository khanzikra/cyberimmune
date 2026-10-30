import os
for root, dirs, files in os.walk('.'):
    if 'main.py' in files:
        print(os.path.join(root, 'main.py'))