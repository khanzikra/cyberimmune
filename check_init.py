import os
for root, dirs, files in os.walk('src'):
    if '__init__.py' in files:
        print(os.path.join(root, '__init__.py'))